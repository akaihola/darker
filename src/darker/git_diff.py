"""Helpers for doing a ``git diff`` and getting modified line numbers

The :func:`git_diff_u0` runs ``git diff -U0 -- <path>``
in the containing directory of ``<path>``,
and returns Git output as a bytestring.

That output can be fed into :func:`get_edit_linenums`
to obtain a list of line numbers in the to-file (modified file)
which were changed from the from-file (file before modification)::

    >>> path, linenums = next(get_edit_linenums(b'''\\
    ... diff --git mymodule.py mymodule.py
    ... index a57921c..a8afb81 100644
    ... --- mymodule.py
    ... +++ mymodule.py
    ... @@ -1 +1,2 @@      # will pick +1,2 from this line...
    ... -Old first line
    ... +Replacement for
    ... +first line
    ... @@ -10 +11 @@    # ...and +11 from this line
    ... -Old tenth line
    ... +Replacement for tenth line
    ... '''))
    >>> print(path)
    mymodule.py
    >>> linenums
    [1, 2, 11]

"""
import logging
from pathlib import Path
from subprocess import check_output
from typing import Generator, Iterable, List, Tuple

from darker.utils import Buf

logger = logging.getLogger(__name__)


def git_diff(paths: Iterable[Path], cwd: Path, context_lines: int) -> bytes:
    """Run ``git diff -U<context_lines> <path>`` and return the output"""
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    cmd = [
        "git",
        "diff",
        f"-U{context_lines}",
        "--relative",
        "--no-prefix",
        "--",
        *[str(path) for path in relative_paths],
    ]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    return check_output(cmd, cwd=str(cwd))


def parse_range(s: str):
    start_str, *length_str = s.split(",")
    start_linenum = int(start_str)
    if length_str:
        # e.g. `+42,2` means lines 42 and 43 were edited
        return start_linenum, int(length_str[0])
    else:
        # e.g. `+42` means only line 42 was edited
        return start_linenum, 1


def get_edit_chunks_for_one_file(lines: Buf) -> Generator[Tuple[int, int], None, None]:
    while lines.next_line_startswith("@@ "):
        _, remove, add, ats2, *_ = next(lines).split(" ", 4)
        add_linenum, num_added = parse_range(add)
        while lines.next_line_startswith((" ", "-", "+")):
            next(lines)
        if num_added:
            # e.g. `+42,0` means lines were deleted starting on line 42 - skip those
            yield add_linenum, add_linenum + num_added


def skip_file(lines: Buf, path: Path) -> None:
    logger.info("Skipping non-Python file %s", path)
    while lines.next_line_startswith("@@ "):
        _ = next(lines)
        while lines.next_line_startswith((" ", "-", "+")):
            next(lines)


def get_edit_chunks(
    patch: bytes,
) -> Generator[Tuple[Path, List[Tuple[int, int]]], None, None]:
    """Yield ranges of changed line numbers in Git diff to-file

    The patch must be in ``git diff -U<num>`` format, and only contain differences for a
    single file.

    Yield 2-tuples of one-based line number ranges which are

    - one-based
    - start inclusive
    - end exclusive

    E.g. ``[42, 7]`` means lines 42, 43, 44, 45, 46, 47 and 48 were changed.

    """
    if not patch:
        return
    lines = Buf(patch)
    while True:
        try:
            if not lines.next_line_startswith("diff --git "):
                return
        except StopIteration:
            return
        _, _, path_a, path_b = next(lines).split(" ")
        path = Path(path_a)

        assert next(lines).startswith("index ")
        path_a_line = next(lines)
        assert path_a_line == f"--- {path_a}", (path_a_line, path_a)
        assert next(lines) == f"+++ {path_a}"
        if path.suffix == ".py":
            yield path, list(get_edit_chunks_for_one_file(lines))
        else:
            skip_file(lines, path)


def get_edit_linenums(patch: bytes,) -> Generator[Tuple[Path, List[int]], None, None]:
    """Yield changed line numbers in Git diff to-file

    The patch must be in ``git diff -U<num>`` format, and only contain differences for a
    single file.

    """
    paths_and_ranges = get_edit_chunks(patch)
    for path, ranges in paths_and_ranges:
        if not ranges:
            logger.debug(f"Found no edited lines for %s", path)
            return
        log_linenums = (
            str(start) if end == start + 1 else f"{start}-{end - 1}"
            for start, end in ranges
        )
        logger.debug("Found edited line(s) for %s: %s", path, ", ".join(log_linenums))
        yield path, [
            linenum
            for start_linenum, end_linenum in ranges
            for linenum in range(start_linenum, end_linenum)
        ]
