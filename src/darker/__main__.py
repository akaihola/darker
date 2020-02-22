"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
from pathlib import Path
from typing import List

from darker.black_diff import diff_and_get_opcodes, opcodes_to_chunks, run_black
from darker.chooser import choose_lines
from darker.command_line import ISORT_INSTRUCTION, parse_command_line
from darker.git_diff import get_edit_linenums, git_diff
from darker.utils import joinlines
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
    logger.info(
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


def apply_black_on_edited_lines(src: Path, context_lines: int = 1) -> None:
    """Apply black formatting to chunks with edits since the last commit

    1. do a ``git diff -U0 <path>``
    2. extract line numbers in the edited to-file for changed lines
    3. run black on the contents of the edited to-file
    4. get a diff between the edited to-file and the reformatted content
    5. convert the diff into chunks, keeping original and reformatted content for each
       chunk
    6. choose reformatted content for each chunk if there were any changed lines inside
       the chunk in the edited to-file, or choose the chunk's original contents if no
       edits were done in that chunk
    7. concatenate all chosen chunks
    8. verify that the resulting reformatted source code parses to an identical AST as
       the original edited to-file
    9. write the reformatted source back to the original file

    """
    git_diff_output = git_diff(src, context_lines)
    edited_linenums = list(get_edit_linenums(git_diff_output))
    if not edited_linenums:
        return
    edited, formatted = run_black(src)
    logger.info("Read %s lines from edited file %s", len(edited), src)
    logger.info("Black reformat resulted in %s lines", len(formatted))
    opcodes = diff_and_get_opcodes(edited, formatted)
    black_chunks = list(opcodes_to_chunks(opcodes, edited, formatted))
    chosen_lines: List[str] = list(choose_lines(black_chunks, edited_linenums))
    result_str = joinlines(chosen_lines)
    logger.info(
        "Verifying that the %s original edited lines and %s reformatted lines parse "
        "into an identical abstract syntax tree",
        len(edited),
        len(chosen_lines),
    )
    verify_ast_unchanged(edited, result_str, black_chunks, edited_linenums)
    logger.info("Writing %s bytes into %s", len(result_str), src)
    src.write_text(result_str)


def main() -> None:
    """Parse the command line and apply black formatting for each source file"""
    args = parse_command_line()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    if args.version:
        print(__version__)
    for path in args.src:
        src = Path(path)
        if args.isort:
            if not SortImports:
                logger.error(f"{ISORT_INSTRUCTION} to use the `--isort` option.")
                exit(1)
            apply_isort(src)
        for context_lines in range(MAX_CONTEXT_LINES + 1):
            try:
                apply_black_on_edited_lines(src, context_lines)
            except NotEquivalentError:
                # Diff produced misaligned chunks which couldn't be reconstructed into
                # a partially re-formatted Python file which produces an identical AST.
                # Try again with a larger `-U<context_lines>` option for `git diff`,
                # or give up if `context_lines` is already very large.
                if context_lines == MAX_CONTEXT_LINES:
                    raise
                logger.info(
                    "AST verification failed. "
                    "Trying again with %s lines of context for `git diff -U`",
                    context_lines + 1,
                )
            else:
                # A re-formatted Python file which produces an identical AST was created
                # successfully.
                break


if __name__ == "__main__":
    main()
