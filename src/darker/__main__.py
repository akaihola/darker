"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Generator, Iterable, List, Tuple

from darker.black_diff import BlackArgs, run_black
from darker.chooser import choose_lines
from darker.command_line import ISORT_INSTRUCTION, parse_command_line
from darker.diff import diff_and_get_opcodes, opcodes_to_chunks
from darker.git import EditedLinenumsDiffer, git_get_modified_files
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linter
from darker.utils import get_common_root, joinlines
from darker.verification import NotEquivalentError, verify_ast_unchanged

logger = logging.getLogger(__name__)


def format_edited_parts(
    srcs: Iterable[Path],
    revision: str,
    enable_isort: bool,
    linter_cmdlines: List[List[str]],
    black_args: BlackArgs,
) -> Generator[Tuple[Path, str, str, List[str]], None, None]:
    """Black (and optional isort) formatting for chunks with edits since the last commit

    1. run isort on each edited file (optional)
    2. diff the given revision and worktree (optionally with isort modifications) for
       all file & dir paths on the command line
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
    11. run linter subprocesses for all edited files (11.-14. optional)
    12. diff the given revision and worktree (after isort and Black reformatting) for
        each file reported by a linter
    13. extract line numbers in each file reported by a linter for changed lines
    14. print only linter error lines which fall on changed lines

    :param srcs: Directories and files to re-format
    :param revision: The Git revision against which to compare the working tree
    :param enable_isort: ``True`` to also run ``isort`` first on each changed file
    :param linter_cmdlines: The command line(s) for running linters on the changed
                            files. Each entry is a list of tokens on the command line.
    :param black_args: Command-line arguments to send to ``black.FileMode``
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    git_root = get_common_root(srcs)
    changed_files = git_get_modified_files(srcs, revision, git_root)
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revision)

    for path_in_repo in sorted(changed_files):
        src = git_root / path_in_repo
        worktree_content = src.read_text()

        # 1. run isort
        if enable_isort:
            edited_content = apply_isort(
                worktree_content,
                src,
                black_args.get("config"),
                black_args.get("line_length"),
            )
        else:
            edited_content = worktree_content
        edited_lines = edited_content.splitlines()
        max_context_lines = len(edited_lines)
        for context_lines in range(max_context_lines + 1):
            # 2. diff the given revision and worktree for the file
            # 3. extract line numbers in the edited to-file for changed lines
            edited_linenums = edited_linenums_differ.revision_vs_lines(
                path_in_repo, edited_lines, context_lines
            )
            if (
                enable_isort
                and not edited_linenums
                and edited_content == worktree_content
            ):
                logger.debug("No changes in %s after isort", src)
                break

            # 4. run black
            formatted = run_black(src, edited_content, black_args)
            logger.debug("Read %s lines from edited file %s", len(edited_lines), src)
            logger.debug("Black reformat resulted in %s lines", len(formatted))

            # 5. get the diff between the edited and reformatted file
            opcodes = diff_and_get_opcodes(edited_lines, formatted)

            # 6. convert the diff into chunks
            black_chunks = list(opcodes_to_chunks(opcodes, edited_lines, formatted))

            # 7. choose reformatted content
            chosen_lines: List[str] = list(choose_lines(black_chunks, edited_linenums))

            # 8. concatenate chosen chunks
            result_str = joinlines(chosen_lines)

            # 9. verify
            logger.debug(
                "Verifying that the %s original edited lines and %s reformatted lines "
                "parse into an identical abstract syntax tree",
                len(edited_lines),
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
                if context_lines == max_context_lines:
                    raise
                logger.debug(
                    "AST verification failed. "
                    "Trying again with %s lines of context for `git diff -U`",
                    context_lines + 1,
                )
                continue
            else:
                # 10. A re-formatted Python file which produces an identical AST was
                #     created successfully - write an updated file or print the diff
                #     if there were any changes to the original
                if result_str != worktree_content:
                    # `result_str` is just `chosen_lines` concatenated with newlines.
                    # We need both forms when showing diffs or modifying files.
                    # Pass them both on to avoid back-and-forth conversion.
                    yield src, worktree_content, result_str, chosen_lines
                break
    # 11. run linter subprocesses for all edited files (11.-14. optional)
    # 12. diff the given revision and worktree (after isort and Black reformatting) for
    #     each file reported by a linter
    # 13. extract line numbers in each file reported by a linter for changed lines
    # 14. print only linter error lines which fall on changed lines
    for linter_cmdline in linter_cmdlines:
        run_linter(linter_cmdline, git_root, changed_files, revision)


def modify_file(path: Path, new_content: str) -> None:
    """Write new content to a file and inform the user by logging"""
    logger.info("Writing %s bytes into %s", len(new_content), path)
    path.write_text(new_content)


def print_diff(path: Path, old_content: str, new_lines: List[str]) -> None:
    """Print ``black --diff`` style output for the changes"""
    relative_path = path.resolve().relative_to(Path.cwd()).as_posix()
    diff = "\n".join(
        line.rstrip("\n")
        for line in unified_diff(
            old_content.splitlines(), new_lines, relative_path, relative_path,
        )
    )

    if sys.stdout.isatty():
        try:
            from pygments import highlight
            from pygments.formatters import TerminalFormatter
            from pygments.lexers import DiffLexer
        except ImportError:
            print(diff)
        else:
            print(highlight(diff, DiffLexer(), TerminalFormatter()))
    else:
        print(diff)


def main(argv: List[str] = None) -> int:
    """Parse the command line and apply black formatting for each source file

    :param argv: The command line arguments to the ``darker`` command
    :return: 1 if the ``--check`` argument was provided and at least one file was (or
             should be) reformatted; 0 otherwise.

    """
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

    if args.isort and not isort:
        logger.error(f"{ISORT_INSTRUCTION} to use the `--isort` option.")
        exit(1)

    black_args = BlackArgs()
    if args.config:
        black_args["config"] = args.config
    if args.line_length:
        black_args["line_length"] = args.line_length
    if args.skip_string_normalization is not None:
        black_args["skip_string_normalization"] = args.skip_string_normalization

    paths = {Path(p) for p in args.src}
    some_files_changed = False
    # `new_content` is just `new_lines` concatenated with newlines.
    # We need both forms when showing diffs or modifying files.
    # Pass them both on to avoid back-and-forth conversion.
    for path, old_content, new_content, new_lines in format_edited_parts(
        paths, args.revision, args.isort, args.lint, black_args
    ):
        some_files_changed = True
        if args.diff:
            print_diff(path, old_content, new_lines)
        if not args.check and not args.diff:
            modify_file(path, new_content)
    return 1 if args.check and some_files_changed else 0


if __name__ == "__main__":
    RETVAL = main()
    sys.exit(RETVAL)
