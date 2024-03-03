"""Miscellaneous utility functions"""

import logging
from pathlib import Path
from typing import Collection, List

from darkgraylib.utils import DiffChunk

logger = logging.getLogger(__name__)


def debug_dump(black_chunks: List[DiffChunk], edited_linenums: List[int]) -> None:
    """Print debug output. This is used in case of an unexpected failure."""
    if logger.getEffectiveLevel() > logging.DEBUG:
        return
    for offset, old_lines, new_lines in black_chunks:
        print(80 * "-")
        for delta, old_line in enumerate(old_lines):
            linenum = offset + delta
            edited = "*" if linenum in edited_linenums else " "
            print(f"{edited}-{linenum:4} {old_line}")
        for _, new_line in enumerate(new_lines):
            print(f" +     {new_line}")
    print(80 * "-")


def glob_any(path: Path, patterns: Collection[str]) -> bool:
    """Return `True` if path matches any of the patterns

    Return `False` if there are no patterns to match.

    :param path: The file path to match
    :param patterns: The patterns to match against
    :return: `True` if at least one pattern matches

    """
    return any(path.glob(pattern) for pattern in patterns)
