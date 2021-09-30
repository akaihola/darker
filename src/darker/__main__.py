"""Darker - apply black reformatting to only areas edited since the last commit"""

import logging
import sys
import warnings
from argparse import Action, ArgumentError
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Collection, Generator, List, Tuple

from darker.black_diff import (
    BlackConfig,
    apply_black_excludes,
    read_black_config,
    run_black,
)
from darker.chooser import choose_lines
from darker.command_line import parse_command_line
from darker.config import OutputMode, dump_config
from darker.diff import diff_and_get_opcodes, opcodes_to_chunks
from darker.exceptions import DependencyError, MissingPackageError
from darker.git import (
    PRE_COMMIT_FROM_TO_REFS,
    WORKTREE,
    EditedLinenumsDiffer,
    RevisionRange,
    get_missing_at_revision,
    git_get_content_at_revision,
    git_get_modified_files,
)
from darker.help import ISORT_INSTRUCTION
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linters
from darker.utils import GIT_DATEFORMAT, TextDocument, get_common_root
from darker.verification import BinarySearch, NotEquivalentError, verify_ast_unchanged

logger = logging.getLogger(__name__)


def format_edited_parts(
    git_root: Path,
    changed_files: Collection[Path],  # pylint: disable=unsubscriptable-object
    revrange: RevisionRange,
    enable_isort: bool,
    black_config: BlackConfig,
    report_unmodified: bool,
) -> Generator[Tuple[Path, TextDocument, TextDocument], None, None]:
    """Black (and optional isort) formatting for chunks with edits since the last commit

    Files excluded by Black's configuration are not reformatted using Black, but their
    imports are still sorted. Also, linters will be run for all files in a separate step
    after this function has completed.

    :param git_root: The root of the Git repository the files are in
    :param changed_files: Files which have been modified in the repository between the
                          given Git revisions
    :param revrange: The Git revisions to compare
    :param enable_isort: ``True`` to also run ``isort`` first on each changed file
    :param black_config: Configuration to use for running Black
    :param report_unmodified: ``True`` to yield also files which weren't modified
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    files_to_blacken = apply_black_excludes(changed_files, git_root, black_config)
    for path_in_repo in sorted(changed_files):
        src = git_root / path_in_repo
        rev2_content = git_get_content_at_revision(
            path_in_repo, revrange.rev2, git_root
        )

        # 1. run isort
        if enable_isort:
            rev2_isorted = apply_isort(
                rev2_content,
                src,
                black_config.get("config"),
                black_config.get("line_length"),
            )
        else:
            rev2_isorted = rev2_content
        if src in files_to_blacken:
            # 9. A re-formatted Python file which produces an identical AST was
            #    created successfully - write an updated file or print the diff if
            #    there were any changes to the original
            content_after_reformatting = _reformat_single_file(
                git_root,
                path_in_repo,
                revrange,
                rev2_content,
                rev2_isorted,
                enable_isort,
                black_config,
            )
        else:
            # File was excluded by Black configuration, don't reformat
            content_after_reformatting = rev2_isorted
        if report_unmodified or content_after_reformatting != rev2_content:
            yield (src, rev2_content, content_after_reformatting)


def _reformat_single_file(  # pylint: disable=too-many-arguments,too-many-locals
    git_root: Path,
    path_in_repo: Path,
    revrange: RevisionRange,
    rev2_content: TextDocument,
    rev2_isorted: TextDocument,
    enable_isort: bool,
    black_config: BlackConfig,
) -> TextDocument:
    """In a Python file, reformat chunks with edits since the last commit using Black

    :param git_root: The root of the Git repository the files are in
    :param path_in_repo: Relative path to a Python source code file
    :param revrange: The Git revisions to compare
    :param rev2_content: Contents of the file at ``revrange.rev2``
    :param rev2_isorted: Contents of the file after optional import sorting
    :param enable_isort: ``True`` if ``isort`` was already run for the file
    :param black_config: Configuration to use for running Black
    :return: Contents of the file after reformatting
    :raise: NotEquivalentError

    """
    src = git_root / path_in_repo
    edited_linenums_differ = EditedLinenumsDiffer(git_root, revrange)

    # 4. run black
    formatted = run_black(rev2_isorted, black_config)
    logger.debug("Read %s lines from edited file %s", len(rev2_isorted.lines), src)
    logger.debug("Black reformat resulted in %s lines", len(formatted.lines))

    # 5. get the diff between the edited and reformatted file
    opcodes = diff_and_get_opcodes(rev2_isorted, formatted)

    # 6. convert the diff into chunks
    black_chunks = list(opcodes_to_chunks(opcodes, rev2_isorted, formatted))

    # Exit early if nothing to do
    if not black_chunks:
        return rev2_isorted

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
            last_successful_reformat = rev2_isorted
            break

        # 7. choose reformatted content
        chosen = TextDocument.from_lines(
            choose_lines(black_chunks, edited_linenums),
            encoding=rev2_content.encoding,
            newline=rev2_content.newline,
            mtime=datetime.utcnow().strftime(GIT_DATEFORMAT),
        )

        # 8. verify
        logger.debug(
            "Verifying that the %s original edited lines and %s reformatted lines "
            "parse into an identical abstract syntax tree",
            len(rev2_isorted.lines),
            len(chosen.lines),
        )
        try:
            verify_ast_unchanged(rev2_isorted, chosen, black_chunks, edited_linenums)
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
            last_successful_reformat = chosen
    if not last_successful_reformat:
        raise NotEquivalentError(path_in_repo)
    return last_successful_reformat


def modify_file(path: Path, new_content: TextDocument) -> None:
    """Write new content to a file and inform the user by logging"""
    logger.info("Writing %s bytes into %s", len(new_content.string), path)
    path.write_bytes(new_content.encoded_string)


def print_diff(
    path: Path, old: TextDocument, new: TextDocument, root: Path = None
) -> None:
    """Print ``black --diff`` style output for the changes

    :param path: The relative path of the file to print the diff output for
    :param old: Old contents of the file
    :param new: New contents of the file
    :param root: The root of the repository (current working directory if omitted)

    Modification times should be in the format "YYYY-MM-DD HH:MM:SS:mmmmmm +0000"

    """
    if root is None:
        root = Path.cwd()
    relative_path = path.resolve().relative_to(root).as_posix()
    diff = "\n".join(
        line.rstrip("\n")
        for line in unified_diff(
            old.lines,
            new.lines,
            fromfile=relative_path,
            tofile=relative_path,
            fromfiledate=old.mtime,
            tofiledate=new.mtime,
            n=5,  # Black shows 5 lines of context, do the same
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


def print_source(new: TextDocument) -> None:
    """Print the reformatted Python source code"""
    if sys.stdout.isatty():
        try:
            # pylint: disable=import-outside-toplevel
            from pygments import highlight
            from pygments.formatters import TerminalFormatter
            from pygments.lexers.python import PythonLexer
        except ImportError:
            print(new.string)
        else:
            print(highlight(new.string, PythonLexer(), TerminalFormatter()))
    else:
        print(new.string)


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
        raise MissingPackageError(f"{ISORT_INSTRUCTION} to use the `--isort` option.")

    black_config = read_black_config(tuple(args.src), args.config)
    if args.config:
        black_config["config"] = args.config
    if args.line_length:
        black_config["line_length"] = args.line_length
    if args.skip_string_normalization is not None:
        black_config["skip_string_normalization"] = args.skip_string_normalization
    if args.skip_magic_trailing_comma is not None:
        black_config["skip_magic_trailing_comma"] = args.skip_magic_trailing_comma

    paths = {Path(p) for p in args.src}
    git_root = get_common_root(paths)
    failures_on_modified_lines = False

    revrange = RevisionRange.parse(args.revision)
    output_mode = OutputMode.from_args(args)
    write_modified_files = not args.check and output_mode == OutputMode.NOTHING
    if write_modified_files:
        if args.revision == PRE_COMMIT_FROM_TO_REFS and revrange.rev2 == "HEAD":
            warnings.warn(
                "Darker was called by pre-commit, comparing HEAD to an older commit."
                " As an experimental feature, allowing overwriting of files."
                " See https://github.com/akaihola/darker/issues/180 for details."
            )
        elif revrange.rev2 != WORKTREE:
            raise ArgumentError(
                Action(["-r", "--revision"], "revision"),
                f"Can't write reformatted files for revision '{revrange.rev2}'."
                " Either --diff or --check must be used.",
            )

    missing = get_missing_at_revision(paths, revrange.rev2)
    if missing:
        missing_reprs = " ".join(repr(str(path)) for path in missing)
        rev2_repr = "the working tree" if revrange.rev2 == WORKTREE else revrange.rev2
        raise ArgumentError(
            Action(["PATH"], "path"),
            f"Error: Path(s) {missing_reprs} do not exist in {rev2_repr}",
        )

    if output_mode == OutputMode.CONTENT:
        # With `-d` / `--stdout`, process the file whether modified or not. Paths have
        # previously been validated to contain exactly one existing file.
        changed_files = paths
    else:
        # In other modes, only process files which have been modified.
        changed_files = git_get_modified_files(paths, revrange, git_root)
    for path, old, new in format_edited_parts(
        git_root,
        changed_files,
        revrange,
        args.isort,
        black_config,
        report_unmodified=output_mode == OutputMode.CONTENT,
    ):
        failures_on_modified_lines = True
        if output_mode == OutputMode.DIFF:
            print_diff(path, old, new, git_root)
        elif output_mode == OutputMode.CONTENT:
            print_source(new)
        if write_modified_files:
            modify_file(path, new)
    if run_linters(args.lint, git_root, changed_files, revrange):
        failures_on_modified_lines = True
    return 1 if args.check and failures_on_modified_lines else 0


def main_with_error_handling() -> int:
    """Entry point for console script"""
    try:
        return main()
    except (ArgumentError, DependencyError) as exc_info:
        if logger.root.level < logging.WARNING:
            raise
        sys.exit(str(exc_info))


if __name__ == "__main__":
    RETVAL = main_with_error_handling()
    sys.exit(RETVAL)
