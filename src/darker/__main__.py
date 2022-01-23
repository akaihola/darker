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
    filter_python_files,
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
    git_get_modified_python_files,
    git_is_repository,
)
from darker.help import ISORT_INSTRUCTION
from darker.highlighting import colorize
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linters
from darker.utils import GIT_DATEFORMAT, TextDocument, debug_dump, get_common_root
from darker.verification import ASTVerifier, BinarySearch, NotEquivalentError

logger = logging.getLogger(__name__)


def format_edited_parts(
    root: Path,
    changed_files: Collection[Path],  # pylint: disable=unsubscriptable-object
    black_exclude: Collection[Path],  # pylint: disable=unsubscriptable-object
    revrange: RevisionRange,
    enable_isort: bool,
    black_config: BlackConfig,
    report_unmodified: bool,
) -> Generator[Tuple[Path, TextDocument, TextDocument], None, None]:
    """Black (and optional isort) formatting for chunks with edits since the last commit

    Files inside given directories and excluded by Black's configuration are not
    reformatted using Black, but their imports are still sorted. Also, linters will be
    run for all files in a separate step after this function has completed.

    Files listed explicitly on the command line are always reformatted.

    :param root: The common root of all files to reformat
    :param changed_files: Python files and explicitly requested files which have been
                          modified in the repository between the given Git revisions
    :param black_exclude: Python files to not reformat using Black, according to Black
                          configuration
    :param revrange: The Git revisions to compare
    :param enable_isort: ``True`` to also run ``isort`` first on each changed file
    :param black_config: Configuration to use for running Black
    :param report_unmodified: ``True`` to yield also files which weren't modified
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    for path_in_repo in sorted(changed_files):
        src = root / path_in_repo
        rev2_content = git_get_content_at_revision(path_in_repo, revrange.rev2, root)

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
        if path_in_repo not in black_exclude:
            # 9. A re-formatted Python file which produces an identical AST was
            #    created successfully - write an updated file or print the diff if
            #    there were any changes to the original
            content_after_reformatting = _reformat_single_file(
                root,
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
    root: Path,
    relative_path: Path,
    revrange: RevisionRange,
    rev2_content: TextDocument,
    rev2_isorted: TextDocument,
    enable_isort: bool,
    black_config: BlackConfig,
) -> TextDocument:
    """In a Python file, reformat chunks with edits since the last commit using Black

    :param root: The common root of all files to reformat
    :param relative_path: Relative path to a Python source code file
    :param revrange: The Git revisions to compare
    :param rev2_content: Contents of the file at ``revrange.rev2``
    :param rev2_isorted: Contents of the file after optional import sorting
    :param enable_isort: ``True`` if ``isort`` was already run for the file
    :param black_config: Configuration to use for running Black
    :return: Contents of the file after reformatting
    :raise: NotEquivalentError

    """
    src = root / relative_path
    rev1_relative_path = _get_rev1_path(relative_path)
    edited_linenums_differ = EditedLinenumsDiffer(root, revrange)

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

    verifier = ASTVerifier(baseline=rev2_isorted)

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
            rev1_relative_path, rev2_isorted, context_lines
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
        if not verifier.is_equivalent_to_baseline(chosen):
            debug_dump(black_chunks, edited_linenums)
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
        raise NotEquivalentError(relative_path)
    return last_successful_reformat


def _get_rev1_path(path: Path) -> Path:
    """Return the relative path to the file in the old revision

    This is usually the same as the relative path on the command line. But in the
    special case of VSCode temporary files (like ``file.py.12345.tmp``), we actually
    want to diff against the corresponding ``.py`` file instead.

    """
    if path.suffixes[-3::2] != [".py", ".tmp"]:
        # The file name is not like `*.py.<HASH>.tmp`. Return it as such.
        return path
    # This is a VSCode temporary file. Drop the hash and the `.tmp` suffix to get the
    # original file name for retrieving the previous revision to diff against.
    path_with_hash = path.with_suffix("")
    return path_with_hash.with_suffix("")


def modify_file(path: Path, new_content: TextDocument) -> None:
    """Write new content to a file and inform the user by logging"""
    logger.info("Writing %s bytes into %s", len(new_content.string), path)
    path.write_bytes(new_content.encoded_string)


def print_diff(
    path: Path, old: TextDocument, new: TextDocument, root: Path = None
) -> None:
    """Print ``black --diff`` style output for the changes

    :param path: The path of the file to print the diff output for, relative to CWD
    :param old: Old contents of the file
    :param new: New contents of the file
    :param root: The root for the relative path (current working directory if omitted)

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
    print(colorize(diff, "diff"))


def print_source(new: TextDocument) -> None:
    """Print the reformatted Python source code"""
    if sys.stdout.isatty():
        try:
            (
                highlight,
                TerminalFormatter,  # pylint: disable=invalid-name
                PythonLexer,
            ) = _import_pygments()  # type: ignore
        except ImportError:
            print(new.string, end="")
        else:
            print(highlight(new.string, PythonLexer(), TerminalFormatter()), end="")
    else:
        print(new.string, end="")


def _import_pygments():  # type: ignore
    """Import within a function to ease mocking the import in unit-tests.

    Cannot be typed as it imports parts of its own return type.
    """
    # pylint: disable=import-outside-toplevel
    from pygments import highlight
    from pygments.formatters import (  # pylint: disable=no-name-in-module
        TerminalFormatter,
    )
    from pygments.lexers.python import PythonLexer

    return highlight, TerminalFormatter, PythonLexer


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
    root = get_common_root(paths)

    revrange = RevisionRange.parse_with_common_ancestor(args.revision, root)
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

    missing = get_missing_at_revision(paths, revrange.rev2, root)
    if missing:
        missing_reprs = " ".join(repr(str(path)) for path in missing)
        rev2_repr = "the working tree" if revrange.rev2 == WORKTREE else revrange.rev2
        raise ArgumentError(
            Action(["PATH"], "path"),
            f"Error: Path(s) {missing_reprs} do not exist in {rev2_repr}",
        )

    # These are absolute paths:
    files_to_process = filter_python_files(paths, root, {})
    files_to_blacken = filter_python_files(paths, root, black_config)
    if output_mode == OutputMode.CONTENT:
        # With `-d` / `--stdout`, process the file whether modified or not. Paths have
        # previously been validated to contain exactly one existing file.
        changed_files_to_process = {
            p.resolve().relative_to(root) for p in files_to_process
        }
        black_exclude = set()
    else:
        # In other modes, only process files which have been modified.
        if git_is_repository(root):
            changed_files_to_process = git_get_modified_python_files(
                files_to_process, revrange, root
            )
        else:
            changed_files_to_process = {
                path.relative_to(root) for path in files_to_process
            }
        black_exclude = {
            f for f in changed_files_to_process if root / f not in files_to_blacken
        }

    formatting_failures_on_modified_lines = False
    for path, old, new in format_edited_parts(
        root,
        changed_files_to_process,
        black_exclude,
        revrange,
        args.isort,
        black_config,
        report_unmodified=output_mode == OutputMode.CONTENT,
    ):
        formatting_failures_on_modified_lines = True
        if output_mode == OutputMode.DIFF:
            print_diff(path, old, new, root)
        elif output_mode == OutputMode.CONTENT:
            print_source(new)
        if write_modified_files:
            modify_file(path, new)
    linter_failures_on_modified_lines = run_linters(
        args.lint, root, changed_files_to_process, revrange
    )
    return (
        1
        if linter_failures_on_modified_lines
        or (args.check and formatting_failures_on_modified_lines)
        else 0
    )


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
