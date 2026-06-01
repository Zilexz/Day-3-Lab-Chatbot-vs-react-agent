import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """
    ReAct Agent thực hiện vòng lặp Thought-Action-Observation.
    Dừng khi tìm thấy Final Answer hoặc đạt max_steps.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )
        tool_names = ", ".join([t["name"] for t in self.tools])
        return f"""You are an intelligent assistant that solves problems step-by-step using tools.

Available tools:
{tool_descriptions}

You MUST follow this EXACT format on every turn:
Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)

When you have enough information to answer, use:
Thought: I now have all the information needed.
Final Answer: <your complete answer to the user>

Rules:
1. Only use tools from this list: {tool_names}
2. One Action per turn — wait for Observation before continuing.
3. Arguments must be plain text or numbers — no JSON, no quotes around the argument.
4. If a tool returns an error, try a different approach.
5. Never invent tool results — always wait for the real Observation.
"""

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        # Xây dựng conversation prompt tích lũy
        scratchpad = f"Question: {user_input}\n"
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        steps = 0

        while steps < self.max_steps:
            steps += 1
            logger.log_event("AGENT_STEP_START", {"step": steps, "scratchpad": scratchpad})

            # --- Gọi LLM ---
            try:
                result = self.llm.generate(scratchpad, system_prompt=self.get_system_prompt())
            except Exception as e:
                logger.error(f"LLM call failed at step {steps}: {e}")
                return f"Agent error: LLM call failed — {e}"

            content = result.get("content", "").strip()
            usage = result.get("usage", {})
            latency = result.get("latency_ms", 0)

            # Cộng dồn token
            for k in total_usage:
                total_usage[k] += usage.get(k, 0)

            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=usage,
                latency_ms=latency,
            )

            logger.log_event("LLM_RESPONSE", {"step": steps, "content": content, "latency_ms": latency})

            # --- Parse Final Answer ---
            final_answer = self._parse_final_answer(content)
            if final_answer:
                logger.log_event("AGENT_END", {
                    "steps": steps,
                    "outcome": "success",
                    "total_usage": total_usage,
                })
                return final_answer

            # --- Parse Action ---
            thought, tool_name, tool_args = self._parse_action(content)

            if not tool_name:
                # LLM không theo format — thêm hint và thử lại
                scratchpad += f"{content}\nObservation: Please follow the exact format: Thought: ... then Action: tool_name(argument) or Final Answer: ...\n"
                logger.log_event("PARSE_ERROR", {"step": steps, "raw": content})
                continue

            # --- Thực thi tool ---
            observation = self._execute_tool(tool_name, tool_args)
            logger.log_event("TOOL_CALL", {
                "step": steps,
                "tool": tool_name,
                "args": tool_args,
                "observation": observation,
            })

            # Cập nhật scratchpad với thought + action + observation
            scratchpad += f"Thought: {thought}\nAction: {tool_name}({tool_args})\nObservation: {observation}\n"

        # Hết max_steps — tóm tắt những gì đã thu thập
        logger.log_event("AGENT_END", {
            "steps": steps,
            "outcome": "max_steps_reached",
            "total_usage": total_usage,
        })
        # Yêu cầu LLM tổng hợp kết quả dựa trên scratchpad
        try:
            fallback = self.llm.generate(
                scratchpad + "Final Answer:",
                system_prompt="Summarize the gathered information and provide a final answer.",
            )
            return fallback.get("content", "").strip() or "Reached max steps without a conclusive answer."
        except Exception:
            return "Reached max steps without a conclusive answer."

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_final_answer(self, text: str) -> Optional[str]:
        match = re.search(r"Final Answer\s*:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _parse_action(self, text: str) -> Tuple[str, Optional[str], str]:
        """
        Trả về (thought, tool_name, tool_args).
        tool_name là None nếu không parse được.
        """
        thought = ""
        thought_match = re.search(r"Thought\s*:\s*(.+?)(?=Action\s*:|Final Answer\s*:|$)", text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

        # Dạng: Action: tool_name(args)
        action_match = re.search(r"Action\s*:\s*(\w+)\s*\(([^)]*)\)", text, re.IGNORECASE)
        if action_match:
            tool_name = action_match.group(1).strip()
            tool_args = action_match.group(2).strip()
            return thought, tool_name, tool_args

        # Dạng thay thế: Action: tool_name args (không có ngoặc)
        action_match2 = re.search(r"Action\s*:\s*(\w+)\s+(.+)", text, re.IGNORECASE)
        if action_match2:
            tool_name = action_match2.group(1).strip()
            tool_args = action_match2.group(2).strip()
            return thought, tool_name, tool_args

        return thought, None, ""

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"].lower() == tool_name.lower():
                try:
                    func = tool["func"]
                    # Nếu có nhiều argument (dạng "arg1, arg2") thì split
                    if "," in args:
                        parts = [a.strip() for a in args.split(",", 1)]
                        return str(func(*parts))
                    return str(func(args))
                except Exception as e:
                    logger.log_event("TOOL_ERROR", {"tool": tool_name, "args": args, "error": str(e)})
                    return f"Tool '{tool_name}' error: {e}"

        # Hallucination — tool không tồn tại
        known = [t["name"] for t in self.tools]
        logger.log_event("HALLUCINATION", {"tool_name": tool_name, "known_tools": known})
        return f"Tool '{tool_name}' not found. Available tools: {', '.join(known)}"
