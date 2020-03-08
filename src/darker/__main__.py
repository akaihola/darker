"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
from pathlib import Path
from typing import Iterable, List, Set

from darker.black_diff import diff_and_get_opcodes, opcodes_to_chunks, run_black
from darker.chooser import choose_lines
from darker.command_line import ISORT_INSTRUCTION, parse_command_line
from darker.git_diff import get_edit_linenums, git_diff
from darker.utils import get_common_root, joinlines
from darker.verification import NotEquivalentError, verify_ast_unchanged
from darker.version import __version__

try:
    from isort import SortImports
except ImportError:
    SortImports = None

logger = logging.getLogger(__name__)

# Maximum `git diff -U<context_lines> value to try with
MAX_CONTEXT_LINES = 1000


def apply_isort(src: Path) -> None:
    logger.debug(
        f"SortImports({str(src)!r}, multi_line_output=3, include_trailing_comma=True,"
        " force_grid_wrap=0, use_parentheses=True,"
        " line_length=88)"
    )
    _ = SortImports(
        src,
        multi_line_output=3,
        include_trailing_comma=True,
        force_grid_wrap=0,
        use_parentheses=True,
        line_length=88,
    )


def format_edited_parts(srcs: Iterable[Path], isort: bool) -> None:
    """Apply black formatting to chunks with edits since the last commit

    1. do a ``git diff -U0 <path> ...`` for all file & dir paths on the command line
    2. extract line numbers in each edited to-file for changed lines
    3. run isort on each edited to-file
    4. run black on the contents of each edited to-file
    5. get a diff between the edited to-file and the reformatted content
    6. convert the diff into chunks, keeping original and reformatted content for each
       chunk
    7. choose reformatted content for each chunk if there were any changed lines inside
       the chunk in the edited to-file, or choose the chunk's original contents if no
       edits were done in that chunk
    8. concatenate all chosen chunks
    9. verify that the resulting reformatted source code parses to an identical AST as
       the original edited to-file
    10. write the reformatted source back to the original file

    :param srcs: Directories and files to re-format
    :param isort: ``True`` to also run ``isort`` first on each changed file

    """
    failed_srcs: Set[Path] = set()
    for context_lines in range(MAX_CONTEXT_LINES + 1):

        # 1. do the git diff
        diff_srcs = failed_srcs or set(srcs)
        logger.debug("Looking at %s", ", ".join(str(s) for s in diff_srcs))
        git_root = get_common_root(diff_srcs)
        logger.debug("Git root: %s", git_root)
        git_diff_output = git_diff(diff_srcs, git_root, context_lines)

        # 2. extract changed line numbers for each to-file
        failed_srcs = set()
        for src_relative, edited_linenums in get_edit_linenums(git_diff_output):
            src = git_root / src_relative
            if not edited_linenums:
                continue

            # 3. run isort
            if isort:
                apply_isort(src)

            # 4. run black
            edited, formatted = run_black(src)
            logger.debug("Read %s lines from edited file %s", len(edited), src)
            logger.debug("Black reformat resulted in %s lines", len(formatted))

            # 5. get the diff between each edited and reformatted file
            opcodes = diff_and_get_opcodes(edited, formatted)

            # 6. convert the diff into chunks
            black_chunks = list(opcodes_to_chunks(opcodes, edited, formatted))

            # 7. choose reformatted content
            chosen_lines: List[str] = list(choose_lines(black_chunks, edited_linenums))

            # 8. concatenate chosen chunks
            result_str = joinlines(chosen_lines)

            # 9. verify
            logger.debug(
                "Verifying that the %s original edited lines and %s reformatted lines "
                "parse into an identical abstract syntax tree",
                len(edited),
                len(chosen_lines),
            )
            try:
                verify_ast_unchanged(edited, result_str, black_chunks, edited_linenums)
            except NotEquivalentError:
                # Diff produced misaligned chunks which couldn't be reconstructed into
                # a partially re-formatted Python file which produces an identical AST.
                # Try again with a larger `-U<context_lines>` option for `git diff`,
                # or give up if `context_lines` is already very large.
                if context_lines == MAX_CONTEXT_LINES:
                    raise
                logger.debug(
                    "AST verification failed. "
                    "Trying again with %s lines of context for `git diff -U`",
                    context_lines + 1,
                )
                failed_srcs.add(src)
            else:
                # 10. A re-formatted Python file which produces an identical AST was
                #     created successfully - write an updated file
                logger.info("Writing %s bytes into %s", len(result_str), src)
                src.write_text(result_str)
        if not failed_srcs:
            break


def main(argv: List[str] = None) -> None:
    """Parse the command line and apply black formatting for each source file"""
    if argv is None:
        argv = sys.argv[1:]
    args = parse_command_line(argv)
    log_level = logging.WARNING - sum(args.log_level or ())
    logging.basicConfig(level=log_level)
    if log_level == logging.INFO:
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        logging.getLogger().handlers[0].setFormatter(formatter)

    # Make sure we don't get excessive debug log output from Black
    logging.getLogger("blib2to3.pgen2.driver").setLevel(logging.WARNING)

    if args.version:
        print(__version__)

    if args.isort and not SortImports:
        logger.error(f"{ISORT_INSTRUCTION} to use the `--isort` option.")
        exit(1)

    paths = {Path(p) for p in args.src}
    format_edited_parts(paths, args.isort)


if __name__ == "__main__":
    main()
