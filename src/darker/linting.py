"""Run arbitrary linters on given files in a Git repository

This supports any linter which reports on standard output and has a fairly standard
correct output format::

    <path>:<linenum>: <description>
    <path>:<linenum>:<column>: <description>

For example, Mypy outputs::

    module.py:57: error: Function is missing a type annotation for one or more arguments

Pylint, on the other hand::

    module.py:44:8: R1720: Unnecessary "elif" after "raise" (no-else-raise)

All such output from the linter will be printed on the standard output
provided that the ``<linenum>`` falls on a changed line.

"""

import logging
from pathlib import Path
from subprocess import PIPE, Popen
from typing import List, Set, Tuple, Union

from darker.git import EditedLinenumsDiffer

logger = logging.getLogger(__name__)


def _parse_linter_line(
    line: str, git_root: Path
) -> Union[Tuple[Path, int], Tuple[None, None]]:
    # Parse an error/note line.
    # Given: line == "dir/file.py:123: error: Foo\n"
    # Sets: path = Path("abs/path/to/dir/file.py:123"
    #       linenum = 123
    #       description = "error: Foo"
    try:
        location, _ = line[:-1].split(": ", 1)
        path_str, linenum_bytes, *rest = location.split(":")
        linenum = int(linenum_bytes)
        if len(rest) > 1:
            raise ValueError("Too many colon-separated tokens")
        if len(rest) == 1:
            # Make sure it column looks like an int on "<path>:<linenum>:<column>"
            _column = int(rest[0])
    except ValueError:
        # Encountered a non-parseable line which doesn't express a linting error.
        # For example, on Mypy:
        # "Found XX errors in YY files (checked ZZ source files)"
        # "Success: no issues found in 1 source file"
        logger.debug("Unparseable linter output: %s", line[:-1])
        return None, None
    path_from_cwd = Path(path_str).absolute()
    path_in_repo = path_from_cwd.relative_to(git_root)
    return path_in_repo, linenum


def run_linter(
    cmdline: List[str], git_root: Path, paths: Set[Path], revision: str
) -> None:
    """Run the given linter and print linting errors falling on changed lines

    :param cmdline: The command line for running the linter
    :param git_root: The repository root for the changed files
    :param paths: Paths of files to check, relative to ``git_root``
    :param revision: The Git revision against which to compare the working tree

    """
    if not paths:
        return
    linter_process = Popen(
        cmdline + [str(git_root / path) for path in sorted(paths)],
        stdout=PIPE,
        encoding="utf-8",
    )
    # assert needed for MyPy (see https://stackoverflow.com/q/57350490/15770)
    assert linter_process.stdout is not None
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revision)
    for line in linter_process.stdout:
        path_in_repo, linter_error_linenum = _parse_linter_line(line, git_root)
        if path_in_repo is None:
            continue
        edited_linenums = edited_linenums_differ.revision_vs_worktree(
            path_in_repo, context_lines=0
        )
        if linter_error_linenum in edited_linenums:
            print(line, end="")
