"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
from argparse import Action, ArgumentError
from difflib import unified_diff
from pathlib import Path
from typing import Generator, Iterable, List, Tuple

from darker.black_diff import BlackArgs, run_black
from darker.chooser import choose_lines
from darker.command_line import parse_command_line
from darker.config import dump_config
from darker.diff import diff_and_get_opcodes, opcodes_to_chunks
from darker.git import (
    WORKTREE,
    EditedLinenumsDiffer,
    RevisionRange,
    git_get_content_at_revision,
    git_get_modified_files,
)
from darker.help import ISORT_INSTRUCTION
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linters
from darker.utils import TextDocument, get_common_root
from darker.verification import BinarySearch, NotEquivalentError, verify_ast_unchanged

logger = logging.getLogger(__name__)


def format_edited_parts(
    git_root: Path,
    changed_files: Iterable[Path],
    revrange: RevisionRange,
    enable_isort: bool,
    black_args: BlackArgs,
) -> Generator[Tuple[Path, TextDocument, TextDocument], None, None]:
    """Black (and optional isort) formatting for chunks with edits since the last commit

    :param git_root: The root of the Git repository the files are in
    :param changed_files: Files which have been modified in the repository between the
                          given Git revisions
    :param revrange: The Git revisions to compare
    :param enable_isort: ``True`` to also run ``isort`` first on each changed file
    :param black_args: Command-line arguments to send to ``black.FileMode``
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revrange)

    for path_in_repo in sorted(changed_files):
        src = git_root / path_in_repo
        rev2_content = git_get_content_at_revision(src, revrange.rev2, git_root)

        # 1. run isort
        if enable_isort:
            rev2_isorted = apply_isort(
                rev2_content,
                src,
                black_args.get("config"),
                black_args.get("line_length"),
            )
        else:
            rev2_isorted = rev2_content
        max_context_lines = len(rev2_isorted.lines)
        minimum_context_lines = BinarySearch(0, max_context_lines + 1)
        last_successful_reformat = None
        while not minimum_context_lines.found:
            context_lines = minimum_context_lines.get_next()
            if context_lines > 0:
                logger.debug(
                    "Trying with %s lines of context for `git diff -U %s`",
                    context_lines,
                    src,
                )
            # 2. diff the given revision and worktree for the file
            # 3. extract line numbers in the edited to-file for changed lines
            edited_linenums = edited_linenums_differ.revision_vs_lines(
                path_in_repo, rev2_isorted, context_lines
            )
            if enable_isort and not edited_linenums and rev2_isorted == rev2_content:
                logger.debug("No changes in %s after isort", src)
                last_successful_reformat = (src, rev2_content, rev2_isorted)
                break

            # 4. run black
            formatted = run_black(src, rev2_isorted, black_args)
            logger.debug(
                "Read %s lines from edited file %s", len(rev2_isorted.lines), src
            )
            logger.debug("Black reformat resulted in %s lines", len(formatted.lines))

            # 5. get the diff between the edited and reformatted file
            opcodes = diff_and_get_opcodes(rev2_isorted, formatted)

            # 6. convert the diff into chunks
            black_chunks = list(opcodes_to_chunks(opcodes, rev2_isorted, formatted))

            # 7. choose reformatted content
            chosen = TextDocument.from_lines(
                choose_lines(black_chunks, edited_linenums),
                encoding=rev2_content.encoding,
                newline=rev2_content.newline,
            )

            # 8. verify
            logger.debug(
                "Verifying that the %s original edited lines and %s reformatted lines "
                "parse into an identical abstract syntax tree",
                len(rev2_isorted.lines),
                len(chosen.lines),
            )
            try:
                verify_ast_unchanged(
                    rev2_isorted, chosen, black_chunks, edited_linenums
                )
            except NotEquivalentError:
                # Diff produced misaligned chunks which couldn't be reconstructed into
                # a partially re-formatted Python file which produces an identical AST.
                # Try again with a larger `-U<context_lines>` option for `git diff`,
                # or give up if `context_lines` is already very large.
                logger.debug(
                    "AST verification of %s with %s lines of context failed",
                    src,
                    context_lines,
                )
                minimum_context_lines.respond(False)
            else:
                minimum_context_lines.respond(True)
                last_successful_reformat = (src, rev2_content, chosen)
        if not last_successful_reformat:
            raise NotEquivalentError(path_in_repo)
        # 9. A re-formatted Python file which produces an identical AST was
        #    created successfully - write an updated file or print the diff if
        #    there were any changes to the original
        src, rev2_content, chosen = last_successful_reformat
        if chosen != rev2_content:
            yield (src, rev2_content, chosen)


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
    """Parse the command line and reformat and optionally lint each source file

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
    10. run linter subprocesses for all edited files (10.-13. optional)
    11. diff the given revision and worktree (after isort and Black reformatting) for
        each file reported by a linter
    12. extract line numbers in each file reported by a linter for changed lines
    13. print only linter error lines which fall on changed lines

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
    git_root = get_common_root(paths)
    failures_on_modified_lines = False

    revrange = RevisionRange.parse(args.revision)
    write_modified_files = not args.check and not args.diff
    if revrange.rev2 != WORKTREE and write_modified_files:
        raise ArgumentError(
            Action(["-r", "--revision"], "revision"),
            f"Can't write reformatted files for revision '{revrange.rev2}'."
            " Either --diff or --check must be used.",
        )
    changed_files = git_get_modified_files(paths, revrange, git_root)
    for path, old, new in format_edited_parts(
        git_root, changed_files, revrange, args.isort, black_args
    ):
        failures_on_modified_lines = True
        if args.diff:
            print_diff(path, old, new)
        if write_modified_files:
            modify_file(path, new)
    if run_linters(args.lint, git_root, changed_files, revrange):
        failures_on_modified_lines = True
    return 1 if args.check and failures_on_modified_lines else 0


if __name__ == "__main__":
    RETVAL = main()
    sys.exit(RETVAL)
