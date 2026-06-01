"""
parse_logs.py — Đọc file log JSON và xuất ra bản tóm tắt dễ đọc

Cách chạy:
  python parse_logs.py                        # đọc log hôm nay
  python parse_logs.py logs/2026-06-01.log    # chỉ định file cụ thể
"""

import json
import sys
import os
from datetime import datetime
from collections import defaultdict


def load_log(path: str):
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def parse_sessions(events):
    """Ghép các event thành từng session (mỗi câu hỏi = 1 chatbot session + 1 agent session)."""
    sessions = []
    current = None

    for e in events:
        evt = e["event"]
        data = e["data"]
        ts = e["timestamp"]

        if evt == "CHATBOT_START":
            current = {
                "question": data["input"],
                "model": data["model"],
                "chatbot": {"steps": [], "answer": None, "latency_ms": None, "tokens": None, "cost": None},
                "agent":   {"steps": [], "answer": None, "latency_ms": None, "tokens": None, "cost": None, "num_steps": 0},
            }
            sessions.append(current)

        elif evt == "CHATBOT_END" and current:
            current["chatbot"]["answer"]     = data["response_preview"]
            current["chatbot"]["latency_ms"] = data["latency_ms"]
            current["chatbot"]["tokens"]     = data["usage"].get("total_tokens")

        elif evt == "AGENT_START" and current:
            pass  # câu hỏi đã được ghi từ CHATBOT_START

        elif evt == "LLM_RESPONSE" and current:
            # Phân biệt step của agent
            current["agent"]["steps"].append({
                "step": data.get("step"),
                "content": data.get("content", ""),
                "latency_ms": data.get("latency_ms"),
            })

        elif evt == "TOOL_CALL" and current:
            # Gắn observation vào step tương ứng
            step_idx = data.get("step", 1) - 1
            if step_idx < len(current["agent"]["steps"]):
                current["agent"]["steps"][step_idx]["tool"] = data["tool"]
                current["agent"]["steps"][step_idx]["args"] = data["args"]
                current["agent"]["steps"][step_idx]["observation"] = data["observation"]

        elif evt == "AGENT_END" and current:
            current["agent"]["num_steps"] = data.get("steps", 0)
            usage = data.get("total_usage", {})
            current["agent"]["tokens"] = usage.get("total_tokens")

        elif evt == "LLM_METRIC" and current:
            cost = data.get("cost_usd", 0)
            if current["agent"]["steps"]:  # metric thuộc về agent
                if current["agent"]["cost"] is None:
                    current["agent"]["cost"] = 0
                current["agent"]["cost"] = round(current["agent"]["cost"] + cost, 8)
            else:  # metric thuộc về chatbot
                current["chatbot"]["cost"] = cost

    # Lấy Final Answer từ bước cuối của agent
    for s in sessions:
        for step in reversed(s["agent"]["steps"]):
            content = step.get("content", "")
            if "Final Answer" in content:
                answer = content.split("Final Answer:", 1)[-1].strip()
                s["agent"]["answer"] = answer
                break

    return sessions


def write_summary(sessions, out_path: str):
    lines = []
    lines.append("=" * 70)
    lines.append("  TỔNG HỢP KẾT QUẢ: CHATBOT vs REACT AGENT")
    lines.append(f"  Thời gian tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    total_chatbot_tokens = 0
    total_agent_tokens   = 0
    total_chatbot_cost   = 0.0
    total_agent_cost     = 0.0

    for i, s in enumerate(sessions, 1):
        lines.append(f"\n{'─' * 70}")
        lines.append(f"CÂU HỎI #{i}: {s['question']}")
        lines.append(f"Model: {s['model']}")
        lines.append(f"{'─' * 70}")

        # --- CHATBOT ---
        lines.append("\n[CHATBOT]")
        lines.append(f"  Trả lời : {s['chatbot']['answer'] or '(không có)'}")
        lines.append(f"  Latency : {s['chatbot']['latency_ms']} ms")
        lines.append(f"  Tokens  : {s['chatbot']['tokens']}")
        lines.append(f"  Chi phí : ${s['chatbot']['cost'] or 0:.6f}")
        total_chatbot_tokens += s['chatbot']['tokens'] or 0
        total_chatbot_cost   += s['chatbot']['cost'] or 0

        # --- AGENT ---
        lines.append(f"\n[REACT AGENT] ({s['agent']['num_steps']} bước)")
        for step in s["agent"]["steps"]:
            lines.append(f"\n  --- Bước {step['step']} ({step['latency_ms']} ms) ---")
            # Tách Thought
            content = step.get("content", "")
            if "Thought:" in content:
                thought = content.split("Thought:", 1)[1].split("\n")[0].strip()
                lines.append(f"  Thought    : {thought}")
            if "tool" in step:
                lines.append(f"  Action     : {step['tool']}({step['args']})")
                lines.append(f"  Observation: {step['observation']}")
            if "Final Answer" in content:
                fa = content.split("Final Answer:", 1)[1].strip()
                lines.append(f"  Final Ans  : {fa}")

        lines.append(f"\n  Trả lời cuối : {s['agent']['answer'] or '(không có)'}")
        lines.append(f"  Tổng tokens  : {s['agent']['tokens']}")
        lines.append(f"  Tổng chi phí : ${s['agent']['cost'] or 0:.6f}")
        total_agent_tokens += s['agent']['tokens'] or 0
        total_agent_cost   += s['agent']['cost'] or 0

    # --- TỔNG KẾT ---
    lines.append(f"\n{'=' * 70}")
    lines.append("  TỔNG KẾT TOÀN SESSION")
    lines.append(f"{'=' * 70}")
    lines.append(f"  Số câu hỏi         : {len(sessions)}")
    lines.append(f"  Chatbot — tokens   : {total_chatbot_tokens}  |  chi phí: ${total_chatbot_cost:.6f}")
    lines.append(f"  Agent   — tokens   : {total_agent_tokens}  |  chi phí: ${total_agent_cost:.6f}")
    lines.append(f"  Agent tốn hơn      : {total_agent_tokens - total_chatbot_tokens} tokens  ({total_agent_tokens/max(total_chatbot_tokens,1):.1f}x)")
    lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Đã xuất kết quả ra: {out_path}")


def main():
    # Xác định file log cần đọc
    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join("logs", f"{today}.log")

    if not os.path.exists(log_path):
        print(f"Không tìm thấy file log: {log_path}")
        sys.exit(1)

    out_path = log_path.replace(".log", "_summary.txt")

    events   = load_log(log_path)
    sessions = parse_sessions(events)
    write_summary(sessions, out_path)


if __name__ == "__main__":
    main()
