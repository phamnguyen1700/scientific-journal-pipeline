import os
import sys


RESET = "\033[0m"
COLORS = {
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
}


def supports_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def colorize(message: str, color: str) -> str:
    if not supports_color():
        return message
    return f"{COLORS[color]}{message}{RESET}"


def success(message: str) -> str:
    return colorize(message, "green")


def error(message: str) -> str:
    return colorize(message, "red")


def warning(message: str) -> str:
    return colorize(message, "yellow")


def info(message: str) -> str:
    return colorize(message, "cyan")
