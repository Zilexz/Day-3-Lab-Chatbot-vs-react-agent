import math


def calculator(expression: str) -> str:
    """
    Tính toán biểu thức toán học một cách an toàn.
    Hỗ trợ: +, -, *, /, **, sqrt, abs, round, floor, ceil, pi, e
    Ví dụ: calculator("2 * (3 + 4)") -> "14"
    """
    allowed_names = {
        "abs": abs, "round": round,
        "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil,
        "pi": math.pi, "e": math.e,
        "pow": pow, "log": math.log, "log10": math.log10,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(round(result, 6)) if isinstance(result, float) else str(result)
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: Cannot evaluate '{expression}' — {e}"


TOOL_SPEC = {
    "name": "calculator",
    "description": (
        "Evaluate a mathematical expression. "
        "Supports +, -, *, /, **, sqrt(), abs(), round(), floor(), ceil(), pi, e. "
        "Input must be a valid Python math expression string. "
        "Example: calculator(2 * (3 + 4))"
    ),
    "func": calculator,
}
