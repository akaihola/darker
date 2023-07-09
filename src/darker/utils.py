"""Miscellaneous utility functions"""

import logging
import sys
from itertools import chain
from pathlib import Path
from typing import Collection, Iterable, List, Tuple

logger = logging.getLogger(__name__)

TextLines = Tuple[str, ...]


WINDOWS = sys.platform.startswith("win")
GIT_DATEFORMAT = "%Y-%m-%d %H:%M:%S.%f +0000"


def detect_newline(string: str) -> str:
    """Detect LF or CRLF newlines in a string by looking at the end of the first line"""
    first_lf_pos = string.find("\n")
    if first_lf_pos > 0 and string[first_lf_pos - 1] == "\r":
        return "\r\n"
    return "\n"


DiffChunk = Tuple[int, TextLines, TextLines]


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


def joinlines(lines: Iterable[str], newline: str = "\n") -> str:
    """Join a list of lines back, adding a linefeed after each line

    This is the reverse of ``str.splitlines()``.

    """
    return "".join(f"{line}{newline}" for line in lines)


def get_path_ancestry(path: Path) -> Iterable[Path]:
    """Return paths to directories leading to the given path

    :param path: The directory or file to get ancestor directories for
    :return: A list of paths, starting from filesystem root and ending in the given
             path (if it's a directory) or the parent of the given path (if it's a file)

    """
    reverse_parents = reversed(path.parents)
    if path.is_dir():
        return chain(reverse_parents, [path])
    return reverse_parents


def get_common_root(paths: Iterable[Path]) -> Path:
    """Find the deepest common parent directory of given paths"""
    resolved_paths = [path.resolve() for path in paths]
    parents = reversed(list(zip(*(get_path_ancestry(path) for path in resolved_paths))))
    for first_path, *other_paths in parents:
        if all(path == first_path for path in other_paths):
            return first_path
    raise ValueError(f"Paths have no common parent Git root: {resolved_paths}")


def glob_any(path: Path, patterns: Collection[str]) -> bool:
    """Return `True` if path matches any of the patterns

    Return `False` if there are no patterns to match.

    :param path: The file path to match
    :param patterns: The patterns to match against
    :return: `True` if at least one pattern matches

    """
    return any(path.glob(pattern) for pattern in patterns)
