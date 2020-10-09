"""Miscellaneous utility functions"""

import io
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Iterable, List, Tuple, Union

TextLines = Tuple[str, ...]


GIT_DATEFORMAT = "%Y-%m-%d %H:%M:%S.%f +0000"


class TextDocument:
    def __init__(
        self, string: str = None, lines: Iterable[str] = None, mtime: str = ""
    ):
        self._string = string
        self._lines = None if lines is None else tuple(lines)
        self._mtime = mtime

    @property
    def string(self) -> str:
        if self._string is None:
            self._string = joinlines(self._lines or ())
        return self._string

    @property
    def lines(self) -> TextLines:
        if self._lines is None:
            self._lines = tuple((self._string or "").splitlines())
        return self._lines

    @property
    def mtime(self) -> str:
        return self._mtime

    @classmethod
    def from_str(cls, s: str, mtime: str = "") -> "TextDocument":
        return cls(s, None, mtime=mtime)

    @classmethod
    def from_file(cls, path: Path) -> "TextDocument":
        mtime = datetime.utcfromtimestamp(path.stat().st_mtime).strftime(GIT_DATEFORMAT)
        return cls.from_str(path.read_text(encoding="utf-8"), mtime=mtime)

    @classmethod
    def from_lines(cls, lines: Iterable[str], mtime: str = "") -> "TextDocument":
        return cls(None, lines, mtime=mtime)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextDocument):
            return NotImplemented
        if not self._string:
            if not self._lines:
                return not other._string and not other._lines
            return self._lines == other.lines
        return self._string == other.string

    def __repr__(self) -> str:
        return f"{type(self).__name__}([{len(self.lines)} lines])"


DiffChunk = Tuple[int, TextLines, TextLines]


def debug_dump(
    black_chunks: List[DiffChunk],
    old_content: TextDocument,
    new_content: TextDocument,
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


def joinlines(lines: TextLines) -> str:
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

    def next_line_startswith(self, prefix: Union[str, TextLines]) -> bool:
        try:
            return next(self).startswith(prefix)
        except StopIteration:
            return False
        finally:
            self.seek_line(-1)
