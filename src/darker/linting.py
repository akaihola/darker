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


def _strict_nonneg_int(text: str) -> int:
    """Strict parsing of strings to non-negative integers

    Allow no leading or trailing whitespace, nor plus or minus signs.

    :param text: The string to convert
    :raises ValueError: Raises if the string has any non-numeric characters
    :return: [description]
    :rtype: [type]
    """
    if text.strip("+-\t ") != text:
        raise ValueError(r"invalid literal for int() with base 10: {text}")
    return int(text)


def _parse_linter_line(line: str, root: Path) -> Tuple[Path, int, str, str]:
    """Parse one line of linter output

    Only parses lines with
    - a file path (without leading-trailing whitespace),
    - a non-negative line number (without leading/trailing whitespace),
    - optionally a column number (without leading/trailing whitespace), and
    - a description.

    Examples of successfully parsed lines::

        path/to/file.py:42: Description
        path/to/file.py:42:5: Description

    Given a root of ``Path("path/")``, these would be parsed into::

        (Path("to/file.py"), 42, "path/to/file.py:42:", "Description")
        (Path("to/file.py"), 42, "path/to/file.py:42:5:", "Description")

    For all other lines, a dummy entry is returned: an empty path, zero as the line
    number, an empty location string and an empty description. Such lines should be
    simply ignored, since many linters display supplementary information insterspersed
    with the actual linting notifications.

    :param line: The linter output line to parse. May have a trailing newline.
    :param root: The root directory to resolve full file paths against
    :return: A 4-tuple of
             - a ``root``-relative file path,
             - the line number,
             - the path and location string, and
             - the description.

    """
    try:
        location, description = line.rstrip().split(": ", 1)
        if location[1:3] == ":\\":
            # Absolute Windows paths need special handling. Separate out the ``C:`` (or
            # similar), then split by colons, and finally re-insert the ``C:``.
            path_in_drive, linenum_str, *rest = location[2:].split(":")
            path_str = f"{location[:2]}{path_in_drive}"
        else:
            path_str, linenum_str, *rest = location.split(":")
        if path_str.strip() != path_str:
            raise ValueError(r"Filename {path_str!r} has leading/trailing whitespace")
        linenum = _strict_nonneg_int(linenum_str)
        if len(rest) > 1:
            raise ValueError("Too many colon-separated tokens in {location!r}")
        if len(rest) == 1:
            # Make sure it column looks like an int on "<path>:<linenum>:<column>"
            _column = _strict_nonneg_int(rest[0])  # noqa: F841
    except ValueError:
        # Encountered a non-parsable line which doesn't express a linting error.
        # For example, on Mypy:
        # "Found XX errors in YY files (checked ZZ source files)"
        # "Success: no issues found in 1 source file"
        logger.debug("Unparsable linter output: %s", line[:-1])
        return Path(), 0, "", ""
    path_from_cwd = Path(path_str).absolute()
    try:
        path_in_repo = path_from_cwd.relative_to(root)
    except ValueError:
        logger.warning(
            "Linter message for a file %s outside requested directory %s",
            path_from_cwd,
            root,
        )
        return Path(), 0, "", ""
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
    cmdline_and_paths = cmdline.split() + [str(root / path) for path in sorted(paths)]
    logger.debug("[%s]$ %s", Path.cwd(), " ".join(cmdline_and_paths))
    with Popen(  # nosec
        cmdline_and_paths,
        stdout=PIPE,
        encoding="utf-8",
    ) as linter_process:
        # condition needed for MyPy (see https://stackoverflow.com/q/57350490/15770)
        if linter_process.stdout is None:
            raise RuntimeError("Stdout piping failed")
        yield linter_process.stdout


def run_linter(
    cmdline: str, root: Path, paths: Set[Path], revrange: RevisionRange, use_color: bool
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
            if path_in_repo.suffix != ".py":
                logger.warning(
                    "Linter message for a non-Python file: %s %s",
                    location,
                    description,
                )
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
                print(colorize(location, "lint_location", use_color), end=" ")
                print(colorize(description, "lint_description", use_color))
                error_count += 1
    return error_count


def run_linters(
    linter_cmdlines: List[str],
    root: Path,
    paths: Set[Path],
    revrange: RevisionRange,
    use_color: bool,
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
        run_linter(linter_cmdline, root, paths, revrange, use_color)
        for linter_cmdline in linter_cmdlines
    )
