import re
from typing import Optional


# Mock knowledge base để giả lập web search
MOCK_KNOWLEDGE_BASE = {
    "vietnam": "Việt Nam là quốc gia Đông Nam Á với dân số ~98 triệu người. GDP năm 2024 đạt khoảng 430 tỷ USD.",
    "ai agent": "AI Agent là hệ thống AI có khả năng nhận thức môi trường, lập kế hoạch và thực hiện hành động để đạt mục tiêu cụ thể.",
    "react": "ReAct (Reason + Act) là kiến trúc agent kết hợp lập luận ngôn ngữ với hành động công cụ theo chu kỳ Thought-Action-Observation.",
    "openai": "OpenAI là công ty AI thành lập năm 2015, nổi tiếng với GPT-4, DALL-E, Whisper và ChatGPT.",
    "python": "Python là ngôn ngữ lập trình mã nguồn mở, phổ biến nhất trong lĩnh vực AI/ML, phiên bản mới nhất là Python 3.12.",
    "llm": "LLM (Large Language Model) là mô hình ngôn ngữ lớn được huấn luyện trên lượng dữ liệu khổng lồ, như GPT-4, Gemini, Claude.",
    "chatgpt": "ChatGPT là sản phẩm chatbot AI của OpenAI ra mắt tháng 11/2022, đạt 100 triệu người dùng trong 2 tháng.",
    "gemini": "Gemini là mô hình AI đa phương thức của Google DeepMind, được tích hợp vào Google Search và Google Workspace.",
}


def search(query: str) -> str:
    """
    Tìm kiếm thông tin trên web (mock).
    Trả về kết quả liên quan đến query.
    """
    query_lower = query.lower().strip()

    # Tìm kiếm khớp trực tiếp hoặc một phần
    for keyword, content in MOCK_KNOWLEDGE_BASE.items():
        if keyword in query_lower or any(w in query_lower for w in keyword.split()):
            return f"[Search result for '{query}']: {content}"

    return (
        f"[Search result for '{query}']: Không tìm thấy thông tin cụ thể về '{query}'. "
        "Hãy thử từ khóa khác hoặc đặt câu hỏi rõ ràng hơn."
    )


TOOL_SPEC = {
    "name": "search",
    "description": (
        "Search for information about a topic on the web. "
        "Returns a relevant summary. "
        "Input: a search query string. "
        "Example: search(what is ReAct agent)"
    ),
    "func": search,
}
