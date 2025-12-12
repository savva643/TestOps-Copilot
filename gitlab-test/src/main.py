def add(a: int, b: int) -> int:
    """Simple pure function for demo coverage."""
    return a + b


def safe_div(a: float, b: float) -> float:
    """Division with zero check to illustrate negative path."""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

