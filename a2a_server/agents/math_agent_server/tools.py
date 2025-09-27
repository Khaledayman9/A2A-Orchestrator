from langchain_core.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Add two numbers together.
    Example: add(3, 5) → 8"""
    return a + b


@tool
def subtract(a: int, b: int) -> int:
    """Subtract the second number from the first number.
    Example: subtract(10, 4) → 6"""
    return a - b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together.
    Example: multiply(7, 6) → 42"""
    return a * b


@tool
def divide(a: int, b: int) -> float:
    """Divide the first number by the second number.
    Returns a floating-point result.
    Example: divide(20, 4) → 5.0"""
    return a / b


@tool
def square(a: int) -> int:
    """Calculate the square of a number (number multiplied by itself).
    Example: square(9) → 81"""
    return a * a


@tool
def cube(a: int) -> int:
    """Calculate the cube of a number (number multiplied by itself twice).
    Example: cube(3) → 27"""
    return a * a * a


@tool
def power(a: int, b: int) -> int:
    """Raise the first number to the power of the second number (exponentiation).
    Example: power(2, 5) → 32"""
    return a**b
