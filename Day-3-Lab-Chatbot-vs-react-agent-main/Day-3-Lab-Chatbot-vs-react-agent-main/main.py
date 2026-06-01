"""
main.py — Entry point cho Lab 3: Chatbot vs ReAct Agent

Cách chạy:
  python main.py              # Chạy demo mặc định với provider từ .env
  python main.py --provider openai
  python main.py --provider google
  python main.py --mode agent
  python main.py --mode chatbot
  python main.py --mode compare
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Đảm bảo src/ có thể import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


# ------------------------------------------------------------------
# Provider factory
# ------------------------------------------------------------------

def build_provider(provider_name: str):
    provider_name = provider_name.lower()

    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("DEFAULT_MODEL", "gpt-4o")
        return OpenAIProvider(model_name=model, api_key=api_key)

    elif provider_name in ("google", "gemini"):
        from src.core.gemini_provider import GeminiProvider
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
        return GeminiProvider(model_name=model, api_key=api_key)

    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)

    else:
        raise ValueError(f"Unknown provider: '{provider_name}'. Choose: openai | google | local")


# ------------------------------------------------------------------
# Demo test cases
# ------------------------------------------------------------------

TEST_CASES = [
    {
        "id": 1,
        "question": "What is 123 multiplied by 456?",
        "type": "calculation",
        "note": "Cần dùng calculator tool — chatbot dễ sai",
    },
    {
        "id": 2,
        "question": "How much tax would I pay on 1,000,000 VND in Vietnam?",
        "type": "multi-step",
        "note": "Cần calc_tax tool với country_code=VN",
    },
    {
        "id": 3,
        "question": "What is the weather like in Hanoi today?",
        "type": "real-time",
        "note": "Cần get_weather tool — chatbot không có real-time data",
    },
    {
        "id": 4,
        "question": "Search for information about ReAct agents and then calculate 2 to the power of 10.",
        "type": "multi-tool",
        "note": "Cần 2 tools: search + calculator",
    },
    {
        "id": 5,
        "question": "What is the capital of Vietnam?",
        "type": "simple-qa",
        "note": "Câu hỏi đơn giản — chatbot nên xử lý được",
    },
]


# ------------------------------------------------------------------
# Run modes
# ------------------------------------------------------------------

def run_chatbot_demo(llm, questions):
    from src.chatbot.chatbot import Chatbot
    bot = Chatbot(llm)
    print("\n" + "="*60)
    print("  CHATBOT BASELINE")
    print("="*60)
    for tc in questions:
        print(f"\n[Q{tc['id']}] {tc['question']}")
        print(f"     (Type: {tc['type']} | {tc['note']})")
        response = bot.chat(tc["question"])
        print(f"     > {response[:300]}")
    print()


def run_agent_demo(llm, questions):
    from src.agent.agent import ReActAgent
    from src.tools import ALL_TOOLS
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=6)
    print("\n" + "="*60)
    print("  REACT AGENT")
    print("="*60)
    for tc in questions:
        print(f"\n[Q{tc['id']}] {tc['question']}")
        print(f"     (Type: {tc['type']} | {tc['note']})")
        response = agent.run(tc["question"])
        print(f"     > {response[:300]}")
    print()


def run_compare_demo(llm, questions):
    from src.chatbot.chatbot import Chatbot
    from src.agent.agent import ReActAgent
    from src.tools import ALL_TOOLS
    from src.telemetry.metrics import tracker

    bot = Chatbot(llm)
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=6)

    print("\n" + "="*70)
    print("  CHATBOT vs REACT AGENT — COMPARISON")
    print("="*70)

    for tc in questions:
        print(f"\n{'─'*70}")
        print(f"[Q{tc['id']}] {tc['question']}")
        print(f"     Type: {tc['type']} | {tc['note']}")
        print()

        chatbot_answer = bot.chat(tc["question"])
        print(f"  [CHATBOT] {chatbot_answer[:300]}")
        print()

        agent_answer = agent.run(tc["question"])
        print(f"  [AGENT]   {agent_answer[:300]}")

    # Hiển thị metrics
    summary = tracker.get_session_summary()
    if summary:
        print(f"\n{'='*70}")
        print("  SESSION METRICS SUMMARY")
        print(f"{'='*70}")
        print(f"  Total requests   : {summary['total_requests']}")
        print(f"  Total tokens     : {summary['total_tokens']}")
        print(f"  Total cost (USD) : ${summary['total_cost_usd']:.6f}")
        print(f"  Avg latency      : {summary['avg_latency_ms']} ms")
        print(f"  P50 latency      : {summary['latency_p50_ms']} ms")
        print(f"  P99 latency      : {summary['latency_p99_ms']} ms")
    print()


# ------------------------------------------------------------------
# Interactive mode
# ------------------------------------------------------------------

def run_interactive(llm, mode: str):
    from src.chatbot.chatbot import Chatbot
    from src.agent.agent import ReActAgent
    from src.tools import ALL_TOOLS

    if mode == "agent":
        runner = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=6)
        run_fn = runner.run
        label = "Agent"
    else:
        runner = Chatbot(llm)
        run_fn = runner.chat
        label = "Chatbot"

    print(f"\n{'='*60}")
    print(f"  Interactive {label} — gõ 'quit' để thoát")
    print(f"{'='*60}\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break
        response = run_fn(user_input)
        print(f"{label}: {response}\n")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Lab 3: Chatbot vs ReAct Agent")
    parser.add_argument(
        "--provider", default=os.getenv("DEFAULT_PROVIDER", "openai"),
        choices=["openai", "google", "gemini", "local"],
        help="LLM provider to use",
    )
    parser.add_argument(
        "--mode", default="compare",
        choices=["chatbot", "agent", "compare", "interactive-chatbot", "interactive-agent"],
        help="Run mode",
    )
    parser.add_argument(
        "--questions", nargs="*", type=int,
        help="Chỉ chạy test case theo ID (vd: --questions 1 3)",
    )
    args = parser.parse_args()

    print(f"\nLab 3 — Provider: {args.provider} | Mode: {args.mode}")

    llm = build_provider(args.provider)

    questions = TEST_CASES
    if args.questions:
        questions = [tc for tc in TEST_CASES if tc["id"] in args.questions]

    if args.mode == "chatbot":
        run_chatbot_demo(llm, questions)
    elif args.mode == "agent":
        run_agent_demo(llm, questions)
    elif args.mode == "compare":
        run_compare_demo(llm, questions)
    elif args.mode == "interactive-chatbot":
        run_interactive(llm, "chatbot")
    elif args.mode == "interactive-agent":
        run_interactive(llm, "agent")


if __name__ == "__main__":
    main()
