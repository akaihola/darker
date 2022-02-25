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
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, Popen  # nosec
from typing import IO, Generator, List, Set, Tuple

from darker.git import WORKTREE, EditedLinenumsDiffer, RevisionRange
from darker.highlighting import colorize

logger = logging.getLogger(__name__)


def _parse_linter_line(line: str, root: Path) -> Tuple[Path, int, str, str]:
    # Parse an error/note line.
    # Given: line == "dir/file.py:123: error: Foo\n"
    # Sets: path = Path("abs/path/to/dir/file.py:123"
    #       linenum = 123
    #       description = "error: Foo"
    try:
        location, description = line[:-1].split(": ", 1)
        path_str, linenum_str, *rest = location.split(":")
        linenum = int(linenum_str)
        if len(rest) > 1:
            raise ValueError("Too many colon-separated tokens")
        if len(rest) == 1:
            # Make sure it column looks like an int on "<path>:<linenum>:<column>"
            _column = int(rest[0])  # noqa: F841
    except ValueError:
        # Encountered a non-parsable line which doesn't express a linting error.
        # For example, on Mypy:
        # "Found XX errors in YY files (checked ZZ source files)"
        # "Success: no issues found in 1 source file"
        logger.debug("Unparsable linter output: %s", line[:-1])
        return Path(), 0, "", ""
    path_from_cwd = Path(path_str).absolute()
    path_in_repo = path_from_cwd.relative_to(root)
    return path_in_repo, linenum, location + ":", description


def _require_rev2_worktree(rev2: str) -> None:
    """Exit with an error message if ``rev2`` is not ``WORKTREE``

    This is used when running linters since linting arbitrary commits is not supported.

    :param rev2: The ``rev2`` revision to lint.

    """
    if rev2 != WORKTREE:
        raise NotImplementedError(
            "Linting arbitrary commits is not supported. "
            "Please use -r {<rev>|<rev>..|<rev>...} instead."
        )


@contextmanager
def _check_linter_output(
    cmdline: str, root: Path, paths: Set[Path]
) -> Generator[IO[str], None, None]:
    """Run a linter as a subprocess and return its standard output stream

    :param cmdline: The command line for running the linter
    :param root: The common root of all files to lint
    :param paths: Paths of files to check, relative to ``git_root``
    :return: The standard output stream of the linter subprocess

    """
    with Popen(  # nosec
        cmdline.split() + [str(root / path) for path in sorted(paths)],
        stdout=PIPE,
        encoding="utf-8",
    ) as linter_process:
        # condition needed for MyPy (see https://stackoverflow.com/q/57350490/15770)
        if linter_process.stdout is None:
            raise RuntimeError("Stdout piping failed")
        yield linter_process.stdout


def run_linter(
    cmdline: str, root: Path, paths: Set[Path], revrange: RevisionRange
) -> int:
    """Run the given linter and print linting errors falling on changed lines

    :param cmdline: The command line for running the linter
    :param root: The common root of all files to lint
    :param paths: Paths of files to check, relative to ``root``
    :param revrange: The Git revision rango to compare
    :return: The number of modified lines with linting errors from this linter

    """
    _require_rev2_worktree(revrange.rev2)
    if not paths:
        return 0
    error_count = 0
    edited_linenums_differ = EditedLinenumsDiffer(root, revrange)
    missing_files = set()
    with _check_linter_output(cmdline, root, paths) as linter_stdout:
        prev_path, prev_linenum = None, 0
        for line in linter_stdout:
            (
                path_in_repo,
                linter_error_linenum,
                location,
                description,
            ) = _parse_linter_line(line, root)
            if (
                path_in_repo is None
                or path_in_repo in missing_files
                or linter_error_linenum == 0
            ):
                continue
            try:
                edited_linenums = edited_linenums_differ.compare_revisions(
                    path_in_repo, context_lines=0
                )
            except FileNotFoundError:
                logger.warning("Missing file %s from %s", path_in_repo, cmdline)
                missing_files.add(path_in_repo)
                continue
            if linter_error_linenum in edited_linenums:
                if path_in_repo != prev_path or linter_error_linenum > prev_linenum + 1:
                    print()
                prev_path, prev_linenum = path_in_repo, linter_error_linenum
                print(colorize(location, "lint_location"), end=" ")
                print(colorize(description, "lint_description"))
                error_count += 1
    return error_count


def run_linters(
    linter_cmdlines: List[str],
    root: Path,
    paths: Set[Path],
    revrange: RevisionRange,
) -> int:
    """Run the given linters on a set of files in the repository

    :param linter_cmdlines: The command lines for linter tools to run on the files
    :param root: The root of the relative paths
    :param paths: The files to check, relative to ``root``. This should only include
                  files which have been modified in the repository between the given Git
                  revisions.
    :param revrange: The Git revisions to compare
    :return: Total number of linting errors found on modified lines

    """
    # 10. run linter subprocesses for all edited files (10.-13. optional)
    # 11. diff the given revision and worktree (after isort and Black reformatting)
    #     for each file reported by a linter
    # 12. extract line numbers in each file reported by a linter for changed lines
    # 13. print only linter error lines which fall on changed lines
    return sum(
        run_linter(linter_cmdline, root, paths, revrange)
        for linter_cmdline in linter_cmdlines
    )
