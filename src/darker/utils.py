"""Miscellaneous utility functions"""

from pprint import pprint
from typing import List, Tuple


def _debug_dump(
    black_chunks: List[Tuple[int, List[str], List[str]]],
    old_content: str,
    new_content: str,
    edited_linenums: List[int],
) -> None:
    """Print debug output. This is used in case of an unexpected failure."""
    print(edited_linenums)
    pprint(black_chunks)
    pprint(
        [(linenum + 1, line) for linenum, line in enumerate(old_content.splitlines())]
    )
    print(new_content)


def joinlines(lines: List[str]) -> str:
    """Join a list of lines back, adding a linefeed after each line

    This is the reverse of ``str.splitlines()``.

    """
    return "".join(f"{line}\n" for line in lines)
