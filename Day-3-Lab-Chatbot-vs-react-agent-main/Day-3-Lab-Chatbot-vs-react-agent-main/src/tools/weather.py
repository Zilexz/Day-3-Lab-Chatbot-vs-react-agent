import random
from datetime import datetime

# Mock weather data theo thành phố
MOCK_WEATHER = {
    "hanoi":       {"city": "Hà Nội",        "temp": 32, "humidity": 80, "condition": "Nắng nóng"},
    "ho chi minh": {"city": "TP. Hồ Chí Minh","temp": 34, "humidity": 75, "condition": "Nắng"},
    "da nang":     {"city": "Đà Nẵng",        "temp": 30, "humidity": 72, "condition": "Có mây"},
    "tokyo":       {"city": "Tokyo",           "temp": 22, "humidity": 60, "condition": "Mát mẻ"},
    "london":      {"city": "London",          "temp": 14, "humidity": 85, "condition": "Âm u"},
    "new york":    {"city": "New York",        "temp": 18, "humidity": 55, "condition": "Có mây"},
    "singapore":   {"city": "Singapore",       "temp": 30, "humidity": 88, "condition": "Mưa nhẹ"},
    "paris":       {"city": "Paris",           "temp": 16, "humidity": 70, "condition": "Có mây"},
    "sydney":      {"city": "Sydney",          "temp": 20, "humidity": 62, "condition": "Nắng"},
    "beijing":     {"city": "Bắc Kinh",        "temp": 15, "humidity": 50, "condition": "Khô"},
}


def get_weather(city: str) -> str:
    """
    Lấy thông tin thời tiết hiện tại của một thành phố (mock data).
    Input: tên thành phố bằng tiếng Anh.
    Ví dụ: get_weather(hanoi), get_weather(london)
    """
    city_lower = city.lower().strip()

    # Tìm kiếm khớp
    for key, data in MOCK_WEATHER.items():
        if key in city_lower or city_lower in key:
            return (
                f"Weather in {data['city']}: "
                f"{data['condition']}, {data['temp']}°C, "
                f"Humidity {data['humidity']}%"
            )

    return (
        f"Weather data not available for '{city}'. "
        "Try: hanoi, ho chi minh, da nang, tokyo, london, new york, singapore."
    )


TOOL_SPEC = {
    "name": "get_weather",
    "description": (
        "Get current weather information for a city. "
        "Returns temperature (Celsius), humidity, and conditions. "
        "Input: city name in English. "
        "Example: get_weather(hanoi)"
    ),
    "func": get_weather,
}
