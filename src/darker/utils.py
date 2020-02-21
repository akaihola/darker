"""Miscellaneous utility functions"""

from pprint import pprint
from typing import List, Tuple


def debug_dump(
    black_chunks: List[Tuple[int, List[str], List[str]]],
    old_content: str,
    new_content: str,
    edited_linenums: List[int],
) -> None:
    """Print debug output. This is used in case of an unexpected failure."""
    for offset, old_lines, new_lines in black_chunks:
        print(80 * "-")
        for delta, old_line in enumerate(old_lines):
            linenum = offset + delta
            edited = "*" if linenum in edited_linenums else " "
            print(f"{edited}-{linenum:4} {old_line}")
        for _, new_line in enumerate(new_lines):
            print(f" +     {new_line}")
    print(80 * "-")


def joinlines(lines: List[str]) -> str:
    """Join a list of lines back, adding a linefeed after each line

    This is the reverse of ``str.splitlines()``.

    """
    return "".join(f"{line}\n" for line in lines)
