"""Miscellaneous utility functions"""

import logging
from pathlib import Path
from typing import Collection, List

from darker.terminal import output
from darkgraylib.utils import DiffChunk

logger = logging.getLogger(__name__)


def debug_dump(black_chunks: List[DiffChunk], edited_linenums: List[int]) -> None:
    """Print debug output. This is used in case of an unexpected failure."""
    if logger.getEffectiveLevel() > logging.DEBUG:
        return
    for offset, old_lines, new_lines in black_chunks:
        output(80 * "-", end="\n")
        for delta, old_line in enumerate(old_lines):
            linenum = offset + delta
            edited = "*" if linenum in edited_linenums else " "
            output(f"{edited}-{linenum:4} {old_line}", end="\n")
        for _, new_line in enumerate(new_lines):
            output(f" +     {new_line}", end="\n")
    output(80 * "-", end="\n")


def glob_any(path: Path, patterns: Collection[str]) -> bool:
    """Return `True` if path matches any of the patterns

    Return `False` if there are no patterns to match.

    :param path: The file path to match
    :param patterns: The patterns to match against
    :return: `True` if at least one pattern matches

    """
    return any(path.glob(pattern) for pattern in patterns)
