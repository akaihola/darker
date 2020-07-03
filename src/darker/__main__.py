"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Dict, Iterable, List, Union

from darker.black_diff import run_black
from darker.chooser import choose_lines
from darker.command_line import ISORT_INSTRUCTION, parse_command_line
from darker.diff import (
    diff_and_get_opcodes,
    opcodes_to_chunks,
    opcodes_to_edit_linenums,
)
from darker.git import git_diff_name_only, git_get_unmodified_content
from darker.import_sorting import SortImports, apply_isort
from darker.utils import get_common_root, joinlines
from darker.verification import NotEquivalentError, verify_ast_unchanged
from darker.version import __version__

logger = logging.getLogger(__name__)

# Maximum `git diff -U<context_lines> value to try with
MAX_CONTEXT_LINES = 1000


def format_edited_parts(
    srcs: Iterable[Path],
    isort: bool,
    black_args: Dict[str, Union[bool, int]],
    print_diff: bool,
) -> None:
    """Black (and optional isort) formatting for chunks with edits since the last commit

    1. run isort on each edited file
    2. diff HEAD and worktree for all file & dir paths on the command line
    3. extract line numbers in each edited to-file for changed lines
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
    :param black_args: Command-line arguments to send to ``black.FileMode``
    :param print_diff: ``True`` to output diffs instead of modifying source files

    """
    git_root = get_common_root(srcs)
    changed_files = git_diff_name_only(srcs, git_root)
    head_srcs = {
        src: git_get_unmodified_content(src, git_root) for src in changed_files
    }
    worktree_srcs = {src: (git_root / src).read_text() for src in changed_files}

    # 1. run isort
    if isort:
        edited_srcs = {
            src: apply_isort(edited_content)
            for src, edited_content in worktree_srcs.items()
        }
    else:
        edited_srcs = worktree_srcs

    for src_relative, edited_content in edited_srcs.items():
        for context_lines in range(MAX_CONTEXT_LINES + 1):
            src = git_root / src_relative
            edited = edited_content.splitlines()
            head_lines = head_srcs[src_relative]

            # 2. diff HEAD and worktree for all file & dir paths on the command line
            edited_opcodes = diff_and_get_opcodes(head_lines, edited)

            # 3. extract line numbers in each edited to-file for changed lines
            edited_linenums = list(opcodes_to_edit_linenums(edited_opcodes))
            if (
                isort
                and not edited_linenums
                and edited_content == worktree_srcs[src_relative]
            ):
                logger.debug("No changes in %s after isort", src)
                break

            # 4. run black
            formatted = run_black(src, edited_content, black_args)
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
                verify_ast_unchanged(
                    edited_content, result_str, black_chunks, edited_linenums
                )
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
                continue
            else:
                # 10. A re-formatted Python file which produces an identical AST was
                #     created successfully - write an updated file
                #     or print the diff
                if print_diff:
                    difflines = list(
                        unified_diff(
                            worktree_srcs[src_relative].splitlines(),
                            chosen_lines,
                            src.as_posix(),
                            src.as_posix(),
                        )
                    )
                    if len(difflines) > 2:
                        h1, h2, *rest = difflines
                        print(h1, end="")
                        print(h2, end="")
                        print("\n".join(rest))
                else:
                    logger.info("Writing %s bytes into %s", len(result_str), src)
                    src.write_text(result_str)
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

    black_args = {}
    if args.config:
        black_args["config"] = args.config
    if args.line_length:
        black_args["line_length"] = args.line_length
    if args.skip_string_normalization:
        black_args["skip_string_normalization"] = args.skip_string_normalization

    paths = {Path(p) for p in args.src}
    format_edited_parts(paths, args.isort, black_args, args.diff)


if __name__ == "__main__":
    main()
