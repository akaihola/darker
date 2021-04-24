"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
from difflib import unified_diff
from pathlib import Path
from typing import Generator, Iterable, List, Tuple

from darker.black_diff import BlackArgs, run_black
from darker.chooser import choose_lines
from darker.command_line import parse_command_line
from darker.config import dump_config
from darker.diff import diff_and_get_opcodes, opcodes_to_chunks
from darker.git import EditedLinenumsDiffer, RevisionRange, git_get_modified_files
from darker.help import ISORT_INSTRUCTION
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linter
from darker.utils import TextDocument, get_common_root
from darker.verification import NotEquivalentError, verify_ast_unchanged

logger = logging.getLogger(__name__)


def format_edited_parts(
    srcs: Iterable[Path],
    revrange: RevisionRange,
    enable_isort: bool,
    linter_cmdlines: List[str],
    black_args: BlackArgs,
) -> Generator[Tuple[Path, TextDocument, TextDocument], None, None]:
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
    8. verify that the resulting reformatted source code parses to an identical AST as
       the original edited to-file
    9. write the reformatted source back to the original file
    10. run linter subprocesses for all edited files (11.-14. optional)
    11. diff the given revision and worktree (after isort and Black reformatting) for
        each file reported by a linter
    12. extract line numbers in each file reported by a linter for changed lines
    13. print only linter error lines which fall on changed lines

    :param srcs: Directories and files to re-format
    :param revrange: The Git revision against which to compare the working tree
    :param enable_isort: ``True`` to also run ``isort`` first on each changed file
    :param linter_cmdlines: The command line(s) for running linters on the changed
                            files.
    :param black_args: Command-line arguments to send to ``black.FileMode``
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    git_root = get_common_root(srcs)
    changed_files = git_get_modified_files(srcs, revrange, git_root)
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revrange)

    for path_in_repo in sorted(changed_files):
        src = git_root / path_in_repo
        worktree_content = TextDocument.from_file(src)

        # 1. run isort
        if enable_isort:
            edited = apply_isort(
                worktree_content,
                src,
                black_args.get("config"),
                black_args.get("line_length"),
            )
        else:
            edited = worktree_content
        max_context_lines = len(edited.lines)
        for context_lines in range(max_context_lines + 1):
            # 2. diff the given revision and worktree for the file
            # 3. extract line numbers in the edited to-file for changed lines
            edited_linenums = edited_linenums_differ.revision_vs_lines(
                path_in_repo, edited, context_lines
            )
            if enable_isort and not edited_linenums and edited == worktree_content:
                logger.debug("No changes in %s after isort", src)
                break

            # 4. run black
            formatted = run_black(src, edited, black_args)
            logger.debug("Read %s lines from edited file %s", len(edited.lines), src)
            logger.debug("Black reformat resulted in %s lines", len(formatted.lines))

            # 5. get the diff between the edited and reformatted file
            opcodes = diff_and_get_opcodes(edited, formatted)

            # 6. convert the diff into chunks
            black_chunks = list(opcodes_to_chunks(opcodes, edited, formatted))

            # 7. choose reformatted content
            chosen = TextDocument.from_lines(
                choose_lines(black_chunks, edited_linenums),
                encoding=worktree_content.encoding,
                newline=worktree_content.newline,
            )

            # 8. verify
            logger.debug(
                "Verifying that the %s original edited lines and %s reformatted lines "
                "parse into an identical abstract syntax tree",
                len(edited.lines),
                len(chosen.lines),
            )
            try:
                verify_ast_unchanged(edited, chosen, black_chunks, edited_linenums)
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
                # 9. A re-formatted Python file which produces an identical AST was
                #    created successfully - write an updated file or print the diff if
                #    there were any changes to the original
                if chosen != worktree_content:
                    yield src, worktree_content, chosen
                break
    # 10. run linter subprocesses for all edited files (11.-14. optional)
    # 11. diff the given revision and worktree (after isort and Black reformatting) for
    #     each file reported by a linter
    # 12. extract line numbers in each file reported by a linter for changed lines
    # 13. print only linter error lines which fall on changed lines
    for linter_cmdline in linter_cmdlines:
        run_linter(linter_cmdline, git_root, changed_files, revrange)


def modify_file(path: Path, new_content: TextDocument) -> None:
    """Write new content to a file and inform the user by logging"""
    logger.info("Writing %s bytes into %s", len(new_content.string), path)
    path.write_bytes(new_content.encoded_string)


def print_diff(path: Path, old: TextDocument, new: TextDocument) -> None:
    """Print ``black --diff`` style output for the changes"""
    relative_path = path.resolve().relative_to(Path.cwd()).as_posix()
    diff = "\n".join(
        line.rstrip("\n")
        for line in unified_diff(old.lines, new.lines, relative_path, relative_path)
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
    args, config, config_nondefault = parse_command_line(argv)
    logging.basicConfig(level=args.log_level)
    if args.log_level == logging.INFO:
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        logging.getLogger().handlers[0].setFormatter(formatter)

    # Make sure we don't get excessive debug log output from Black
    logging.getLogger("blib2to3.pgen2.driver").setLevel(logging.WARNING)

    if args.log_level <= logging.DEBUG:
        print("\n# Effective configuration:\n")
        print(dump_config(config))
        print("\n# Configuration options which differ from defaults:\n")
        print(dump_config(config_nondefault))
        print("\n")

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
    revrange = RevisionRange.parse(args.revision)
    for path, old, new in format_edited_parts(
        paths, revrange, args.isort, args.lint, black_args
    ):
        some_files_changed = True
        if args.diff:
            print_diff(path, old, new)
        if not args.check and not args.diff:
            modify_file(path, new)
    return 1 if args.check and some_files_changed else 0


if __name__ == "__main__":
    RETVAL = main()
    sys.exit(RETVAL)
