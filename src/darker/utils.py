"""Miscellaneous utility functions"""

import io
from itertools import chain
from pathlib import Path
from typing import Iterable, List, Tuple, Union


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


def get_path_ancestry(path: Path) -> Iterable[Path]:
    reverse_parents = reversed(path.parents)
    if path.is_dir():
        return chain(reverse_parents, [path])
    else:
        return reverse_parents


def get_common_root(paths: Iterable[Path]) -> Path:
    """Find the deepest common parent directory of given paths"""
    resolved_paths = [path.resolve() for path in paths]
    parents = reversed(list(zip(*(get_path_ancestry(path) for path in resolved_paths))))
    for first_path, *other_paths in parents:
        if all(path == first_path for path in other_paths):
            return first_path
    raise ValueError(f"Paths have no common parent Git root: {resolved_paths}")


class Buf:
    def __init__(self, initial_bytes: bytes):
        self._buf = io.BytesIO(initial_bytes)
        self._line_starts: List[int] = []

    def __next__(self) -> str:
        self._line_starts.append(self._buf.tell())
        return next(self._buf).rstrip(b"\n").decode("utf-8")

    def __iter__(self) -> "Buf":
        return self

    def seek_line(self, lines_delta: int) -> None:
        assert lines_delta <= 0
        for _ in range(-lines_delta):
            self._buf.seek(self._line_starts.pop())

    def next_line_startswith(self, prefix: Union[str, Tuple[str, ...]]) -> bool:
        try:
            return next(self).startswith(prefix)
        except StopIteration:
            return False
        finally:
            self.seek_line(-1)
