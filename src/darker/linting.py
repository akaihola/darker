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
from typing import List, Optional, Set, Tuple, Union

from darker.git import WORKTREE, EditedLinenumsDiffer, RevisionRange

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
            _column = int(rest[0])  # noqa: F841
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
    cmdline: str, git_root: Path, paths: Set[Path], revrange: RevisionRange
) -> Optional[int]:
    """Run the given linter and print linting errors falling on changed lines

    :param cmdline: The command line for running the linter
    :param git_root: The repository root for the changed files
    :param paths: Paths of files to check, relative to ``git_root``
    :param revrange: The Git revision rango to compare
    :return: The number of modified lines with linting errors from this linter, or
             ``None`` if there are no paths to check

    """
    if not paths:
        return None
    if revrange.rev2 is not WORKTREE:
        raise NotImplementedError(
            "Linting arbitrary commits is not supported. "
            "Please use -r {<rev>|<rev>..|<rev>...} instead."
        )
    error_count = 0
    linter_process = Popen(
        cmdline.split() + [str(git_root / path) for path in sorted(paths)],
        stdout=PIPE,
        encoding="utf-8",
    )
    # assert needed for MyPy (see https://stackoverflow.com/q/57350490/15770)
    assert linter_process.stdout is not None
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revrange)
    for line in linter_process.stdout:
        path_in_repo, linter_error_linenum = _parse_linter_line(line, git_root)
        if path_in_repo is None:
            continue
        edited_linenums = edited_linenums_differ.compare_revisions(
            path_in_repo, context_lines=0
        )
        if linter_error_linenum in edited_linenums:
            print(line, end="")
            error_count += 1
    return error_count


def run_linters(
    linter_cmdlines: List[str],
    git_root: Path,
    paths: Set[Path],
    revrange: RevisionRange,
) -> bool:
    """Run the given linters on a set of files in the repository

    :param linter_cmdlines: The command lines for linter tools to run on the files
    :param git_root: The root of the Git repository the files are in
    :param paths: The files to check in the repository. This should only include files
                  which have been modified in the repository between the given Git
                  revisions.
    :param revrange: The Git revisions to compare
    :return: ``True`` if at least one linting error was found on a modified line

    """
    some_linters_failed = False
    for linter_cmdline in linter_cmdlines:
        # 10. run linter subprocesses for all edited files (10.-13. optional)
        # 11. diff the given revision and worktree (after isort and Black reformatting)
        #     for each file reported by a linter
        # 12. extract line numbers in each file reported by a linter for changed lines
        # 13. print only linter error lines which fall on changed lines
        if run_linter(linter_cmdline, git_root, paths, revrange):
            some_linters_failed = True
    return some_linters_failed
