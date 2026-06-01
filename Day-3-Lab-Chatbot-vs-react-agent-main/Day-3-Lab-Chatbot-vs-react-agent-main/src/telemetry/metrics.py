import time
from typing import Dict, Any, List
from src.telemetry.logger import logger


# Bảng giá thực tế (USD per 1M tokens) — cập nhật tháng 6/2025
PRICING_TABLE = {
    # OpenAI
    "gpt-4o":           {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":      {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo":    {"input": 0.50,  "output": 1.50},
    # Google Gemini
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro":   {"input": 3.50,  "output": 10.50},
    "gemini-2.0-flash": {"input": 0.10,  "output": 0.40},
    # Anthropic
    "claude-sonnet-4-6":{"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80,  "output": 4.00},
}


class PerformanceTracker:
    """
    Theo dõi các chỉ số hiệu suất theo chuẩn ngành.
    Ghi lại latency, token usage, và chi phí ước tính.
    """

    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_usd": self._calculate_cost(model, usage),
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Tính chi phí dựa trên bảng giá thực tế.
        Đơn vị: USD. Giá tính theo 1 triệu token.
        """
        pricing = PRICING_TABLE.get(model)
        if pricing is None:
            # Fallback: dùng giá trung bình nếu model chưa có trong bảng
            per_million_input = 1.00
            per_million_output = 3.00
        else:
            per_million_input = pricing["input"]
            per_million_output = pricing["output"]

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        cost = (prompt_tokens * per_million_input + completion_tokens * per_million_output) / 1_000_000
        return round(cost, 8)

    def get_session_summary(self) -> Dict[str, Any]:
        """Tổng hợp chỉ số của toàn bộ session."""
        if not self.session_metrics:
            return {}
        latencies = [m["latency_ms"] for m in self.session_metrics]
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        return {
            "total_requests": n,
            "total_tokens": sum(m["total_tokens"] for m in self.session_metrics),
            "total_cost_usd": round(sum(m["cost_usd"] for m in self.session_metrics), 6),
            "latency_p50_ms": latencies_sorted[n // 2],
            "latency_p99_ms": latencies_sorted[int(n * 0.99)] if n > 1 else latencies_sorted[-1],
            "avg_latency_ms": int(sum(latencies) / n),
        }


# Global tracker instance
tracker = PerformanceTracker()
