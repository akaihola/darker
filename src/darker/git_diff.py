"""Helpers for doing a ``git diff`` and getting modified line numbers

The :func:`git_diff_u0` runs ``git diff -U0 -- <path>``
in the containing directory of ``<path>``,
and returns Git output as a bytestring.

That output can be fed into :func:`get_edit_linenums`
to obtain a list of line numbers in the to-file (modified file)
which were changed from the from-file (file before modification)::

    >>> diff_result = GitDiffResult(b'''\\
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
    ... ''', ['git', 'diff'])
    >>> path, linenums = next(get_edit_linenums(diff_result))
    >>> print(path)
    mymodule.py
    >>> linenums
    [1, 2, 11]

"""
import logging
from pathlib import Path
from subprocess import check_output
from typing import Generator, Iterable, List, NamedTuple, Tuple

from darker.utils import Buf

logger = logging.getLogger(__name__)


class GitDiffResult(NamedTuple):
    output: bytes
    command: List[str]


def git_diff(paths: Iterable[Path], cwd: Path, context_lines: int) -> GitDiffResult:
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
    return GitDiffResult(check_output(cmd, cwd=str(cwd)), cmd)


def parse_range(s: str) -> Tuple[int, int]:
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


def should_reformat_file(path: Path) -> bool:
    return path.suffix == ".py"


class GitDiffParseError(Exception):
    pass


def get_edit_chunks(
    git_diff_result: GitDiffResult,
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
    if not git_diff_result.output:
        return
    lines = Buf(git_diff_result.output)
    command = " ".join(git_diff_result.command)

    def expect_line(expect_startswith: str = "", catch_stop: bool = True) -> str:
        if catch_stop:
            try:
                line = next(lines)
            except StopIteration:
                raise GitDiffParseError(f"Unexpected end of output from '{command}'")
        else:
            line = next(lines)
        if not line.startswith(expect_startswith):
            raise GitDiffParseError(
                f"Expected an '{expect_startswith}' line, got '{line}' from '{command}'"
            )
        return line

    while True:
        try:
            diff_git_line = expect_line("diff --git ", catch_stop=False)
        except StopIteration:
            return
        try:
            _, _, path_a, path_b = diff_git_line.split(" ")
        except ValueError:
            raise GitDiffParseError(f"Can't parse '{diff_git_line}'")
        path = Path(path_a)

        try:
            expect_line("index ")
        except GitDiffParseError:
            lines.seek_line(-1)
            expect_line("old mode ")
            expect_line("new mode ")
            expect_line("index ")
        expect_line(f"--- {path_a}")
        expect_line(f"+++ {path_a}")
        if should_reformat_file(path):
            yield path, list(get_edit_chunks_for_one_file(lines))
        else:
            skip_file(lines, path)


def get_edit_linenums(
    git_diff_result: GitDiffResult,
) -> Generator[Tuple[Path, List[int]], None, None]:
    """Yield changed line numbers in Git diff to-file

    The patch must be in ``git diff -U<num>`` format, and only contain differences for a
    single file.

    """
    try:
        paths_and_ranges = get_edit_chunks(git_diff_result)
    except GitDiffParseError:
        raise RuntimeError(
            "Can't get line numbers for diff output from: %s",
            " ".join(git_diff_result.command),
        )
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


def git_diff_name_only(paths: Iterable[Path], cwd: Path) -> List[Path]:
    """Run ``git diff --name-only`` and return file names from the output"""
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--relative",
        "--",
        *[str(path) for path in relative_paths],
    ]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    lines = check_output(cmd, cwd=str(cwd)).decode("utf-8").splitlines()
    changed_paths = ((cwd / line).resolve() for line in lines)
    return [path for path in changed_paths if should_reformat_file(path)]
