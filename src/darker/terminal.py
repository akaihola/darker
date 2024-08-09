"""Terminal output helpers."""

import sys


def output(*args: str, end: str = "") -> None:
    """Print encoded binary output to terminal, with no newline by default."""
    sys.stdout.buffer.write(*[arg.encode() for arg in args])
    if end:
        sys.stdout.buffer.write(end.encode())
