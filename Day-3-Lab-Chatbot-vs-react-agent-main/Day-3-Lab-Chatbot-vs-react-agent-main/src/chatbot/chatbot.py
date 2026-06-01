from typing import Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class Chatbot:
    """
    Chatbot cơ bản — chỉ gọi LLM một lần, không có tool, không lập luận đa bước.
    Dùng làm baseline để so sánh với ReAct Agent.
    """

    SYSTEM_PROMPT = (
        "You are a helpful assistant. "
        "Answer the user's question directly and concisely based on your knowledge. "
        "If you are unsure, say so honestly."
    )

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def chat(self, user_input: str) -> str:
        logger.log_event("CHATBOT_START", {"input": user_input, "model": self.llm.model_name})

        try:
            result = self.llm.generate(user_input, system_prompt=self.SYSTEM_PROMPT)
        except Exception as e:
            logger.error(f"Chatbot LLM call failed: {e}")
            return f"Error: {e}"

        content = result.get("content", "").strip()
        usage = result.get("usage", {})
        latency = result.get("latency_ms", 0)

        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=usage,
            latency_ms=latency,
        )

        logger.log_event("CHATBOT_END", {
            "response_preview": content[:200],
            "latency_ms": latency,
            "usage": usage,
        })

        return content
