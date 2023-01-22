"""Darker - apply black reformatting to only areas edited since the last commit"""

import concurrent.futures
import logging
import sys
import warnings
from argparse import Action, ArgumentError
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Collection, Generator, List, Optional, Tuple

from darker.black_diff import (
    BlackConfig,
    filter_python_files,
    read_black_config,
    run_black,
)
from darker.chooser import choose_lines
from darker.command_line import parse_command_line
from darker.concurrency import get_executor
from darker.config import Exclusions, OutputMode, dump_config
from darker.diff import diff_chunks
from darker.exceptions import DependencyError, MissingPackageError
from darker.fstring import apply_flynt, flynt
from darker.git import (
    PRE_COMMIT_FROM_TO_REFS,
    WORKTREE,
    EditedLinenumsDiffer,
    RevisionRange,
    get_missing_at_revision,
    get_path_in_repo,
    git_get_content_at_revision,
    git_get_modified_python_files,
    git_is_repository,
)
from darker.help import get_extra_instruction
from darker.highlighting import colorize, should_use_color
from darker.import_sorting import apply_isort, isort
from darker.linting import run_linters
from darker.utils import (
    GIT_DATEFORMAT,
    DiffChunk,
    TextDocument,
    debug_dump,
    get_common_root,
    glob_any,
)
from darker.verification import ASTVerifier, BinarySearch, NotEquivalentError

logger = logging.getLogger(__name__)

ProcessedDocument = Tuple[Path, TextDocument, TextDocument]


def format_edited_parts(  # pylint: disable=too-many-arguments
    root: Path,
    changed_files: Collection[Path],  # pylint: disable=unsubscriptable-object
    exclude: Exclusions,
    revrange: RevisionRange,
    black_config: BlackConfig,
    report_unmodified: bool,
    workers: int = 1,
) -> Generator[ProcessedDocument, None, None]:
    """Black (and optional isort and flynt) formatting modified chunks in a set of files

    Files inside given directories and excluded by Black's configuration are not
    reformatted using Black, but their imports are still sorted. Also, linters will be
    run for all files in a separate step after this function has completed.

    Files listed explicitly on the command line are always reformatted.

    :param root: The common root of all files to reformat
    :param changed_files: Python files and explicitly requested files which have been
                          modified in the repository between the given Git revisions
    :param exclude: Files to exclude when running Black,``isort`` or ``flynt``
    :param revrange: The Git revisions to compare
    :param black_config: Configuration to use for running Black
    :param report_unmodified: ``True`` to yield also files which weren't modified
    :param workers: number of cpu processes to use (0 - autodetect)
    :return: A generator which yields details about changes for each file which should
             be reformatted, and skips unchanged files.

    """
    with get_executor(max_workers=workers) as executor:
        # pylint: disable=unsubscriptable-object
        futures: List[concurrent.futures.Future[ProcessedDocument]] = []
        edited_linenums_differ = EditedLinenumsDiffer(root, revrange)
        for relative_path_in_rev2 in sorted(changed_files):
            future = executor.submit(
                _modify_and_reformat_single_file,
                root,
                relative_path_in_rev2,
                edited_linenums_differ,
                exclude,
                revrange,
                black_config,
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            (
                absolute_path_in_rev2,
                rev2_content,
                content_after_reformatting,
            ) = future.result()
            if report_unmodified or content_after_reformatting != rev2_content:
                yield (absolute_path_in_rev2, rev2_content, content_after_reformatting)


def _modify_and_reformat_single_file(  # pylint: disable=too-many-arguments
    root: Path,
    relative_path_in_rev2: Path,
    edited_linenums_differ: EditedLinenumsDiffer,
    exclude: Exclusions,
    revrange: RevisionRange,
    black_config: BlackConfig,
) -> ProcessedDocument:
    """Black, isort and/or flynt formatting for modified chunks in a single file

    :param root: Root directory for the relative path
    :param relative_path_in_rev2: Relative path to a Python source code file
    :param exclude: Files to exclude when running Black, ``isort`` or ``flynt``
    :param revrange: The Git revisions to compare
    :param black_config: Configuration to use for running Black
    :return: Details about changes for the file

    """
    # With VSCode, `relative_path_in_rev2` may be a `.py.<HASH>.tmp` file in the
    # working tree instead of a `.py` file.
    absolute_path_in_rev2 = root / relative_path_in_rev2
    rev2_content = git_get_content_at_revision(
        relative_path_in_rev2, revrange.rev2, root
    )
    # 1. run isort on each edited file (optional).
    rev2_isorted = apply_isort(
        rev2_content,
        relative_path_in_rev2,
        exclude.isort,
        edited_linenums_differ,
        black_config.get("config"),
        black_config.get("line_length"),
    )
    has_isort_changes = rev2_isorted != rev2_content
    # 2. run flynt (optional) on the isorted contents of each edited to-file
    # 3. run black on the isorted and fstringified contents of each edited to-file
    content_after_reformatting = _blacken_and_flynt_single_file(
        root,
        relative_path_in_rev2,
        get_path_in_repo(relative_path_in_rev2),
        exclude,
        edited_linenums_differ,
        rev2_content,
        rev2_isorted,
        has_isort_changes,
        black_config,
    )
    return absolute_path_in_rev2, rev2_content, content_after_reformatting


def _blacken_and_flynt_single_file(
    # pylint: disable=too-many-arguments,too-many-locals
    root: Path,
    relative_path_in_rev2: Path,
    relative_path_in_repo: Path,
    exclude: Exclusions,
    edited_linenums_differ: EditedLinenumsDiffer,
    rev2_content: TextDocument,
    rev2_isorted: TextDocument,
    has_isort_changes: bool,
    black_config: BlackConfig,
) -> TextDocument:
    """In a Python file, reformat chunks with edits since the last commit using Black

    :param root: The common root of all files to reformat
    :param relative_path_in_rev2: Relative path to a Python source code file. Possibly a
                                  VSCode ``.py.<HASH>.tmp`` file in the working tree.
    :param relative_path_in_repo: Relative path to source in the Git repository. Same as
                                  ``relative_path_in_rev2`` save for VSCode temp files.
    :param exclude: Files to exclude when running Black, ``isort`` or ``flynt``
    :param edited_linenums_differ: Helper for finding out which lines were edited
    :param rev2_content: Contents of the file at ``revrange.rev2``
    :param rev2_isorted: Contents of the file after optional import sorting
    :param has_isort_changes: ``True`` if ``isort`` was run and modified the file
    :param black_config: Configuration to use for running Black
    :return: Contents of the file after reformatting
    :raise: NotEquivalentError

    """
    absolute_path_in_rev2 = root / relative_path_in_rev2

    # 2. run flynt (optional) on the isorted contents of each edited to-file
    logger.debug(
        "Read %s lines from edited file %s",
        len(rev2_isorted.lines),
        absolute_path_in_rev2,
    )
    fstringified = _maybe_flynt_single_file(
        relative_path_in_rev2, exclude.flynt, edited_linenums_differ, rev2_isorted
    )
    has_fstring_changes = fstringified != rev2_isorted
    logger.debug(
        "Flynt resulted in %s lines, with %s changes from fstringification",
        len(fstringified.lines),
        "some" if has_fstring_changes else "no",
    )
    # 3. run black on the isorted and fstringified contents of each edited to-file
    formatted = _maybe_blacken_single_file(
        relative_path_in_rev2, exclude.black, fstringified, black_config
    )
    logger.debug(
        "Black reformat resulted in %s lines, with %s changes from reformatting",
        len(formatted.lines),
        "no" if formatted == fstringified else "some",
    )

    # 4. get a diff between the edited to-file and the processed content
    # 5. convert the diff into chunks, keeping original and reformatted content for each
    #    chunk
    new_chunks = diff_chunks(rev2_isorted, formatted)

    # Exit early if nothing to do
    if not new_chunks:
        return rev2_isorted

    result = _drop_changes_on_unedited_lines(
        new_chunks,
        absolute_path_in_rev2,
        relative_path_in_repo,
        edited_linenums_differ,
        rev2_content,
        rev2_isorted,
        has_isort_changes,
        has_fstring_changes,
    )
    if not result:
        raise NotEquivalentError(relative_path_in_rev2)
    return result


def _maybe_flynt_single_file(
    relpath_in_rev2: Path,
    exclude: Collection[str],
    edited_linenums_differ: EditedLinenumsDiffer,
    rev2_isorted: TextDocument,
) -> TextDocument:
    """Fstringify Python source code if the source code file path isn't excluded

    :param relpath_in_rev2: Relative path to a Python source code file. Possibly a
                            VSCode ``.py.<HASH>.tmp`` file in the working tree.
    :param exclude: Files to exclude when running ``flynt``
    :param edited_linenums_differ: Helper for finding out which lines were edited
    :param rev2_isorted: Contents of the file after optional import sorting
    :return: Python source code after fstringification

    """
    if glob_any(relpath_in_rev2, exclude):
        # `--flynt` option not specified, don't reformat
        return rev2_isorted
    return apply_flynt(rev2_isorted, relpath_in_rev2, edited_linenums_differ)


def _maybe_blacken_single_file(
    relpath_in_rev2: Path,
    exclude: Collection[str],
    fstringified: TextDocument,
    black_config: BlackConfig,
) -> TextDocument:
    """Format Python source code with Black if the source code file path isn't excluded

    :param relpath_in_rev2: Relative path to a Python source code file. Possibly a
                            VSCode ``.py.<HASH>.tmp`` file in the working tree.
    :param exclude: Files to exclude when running Black
    :param fstringified: Contents of the file after optional import sorting and flynt
    :param black_config: Configuration to use for running Black
    :return: Python source code after reformatting

    """
    if glob_any(relpath_in_rev2, exclude):
        # File was excluded by Black configuration, don't reformat
        return fstringified
    return run_black(fstringified, black_config)


def _drop_changes_on_unedited_lines(
    # pylint: disable=too-many-arguments
    new_chunks: List[DiffChunk],
    abspath_in_rev2: Path,
    relpath_in_repo: Path,
    edited_linenums_differ: EditedLinenumsDiffer,
    rev2_content: TextDocument,
    rev2_isorted: TextDocument,
    has_isort_changes: bool,
    has_fstring_changes: bool,
) -> Optional[TextDocument]:
    """In a Python file, reformat chunks with edits since the last commit using Black

    :param new_chunks: Chunks in the diff between the edited and the processed content
    :param abspath_in_rev2: Absolute path to a Python source code file. Possibly a
                            VSCode ``.py.<HASH>.tmp`` file in the working tree.
    :param relpath_in_repo: Relative path to source in the Git repository. Same as
                            ``relative_path_in_rev2`` save for VSCode temp files.
    :param edited_linenums_differ: Helper for finding out which lines were edited
    :param rev2_content: Contents of the file at ``revrange.rev2``
    :param rev2_isorted: Contents of the file after optional import sorting
    :param has_isort_changes: ``True`` if ``isort`` was run and modified the file
    :param has_fstring_changes: ``True`` if ``flynt`` was run and modified the file
    :return: Contents of the file after reformatting
    :raise: NotEquivalentError

    """
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
                abspath_in_rev2,
            )
        # 6. diff the given revisions (optionally with isort modifications) for each
        #    file
        # 7. extract line numbers in each edited to-file for changed lines
        edited_linenums = edited_linenums_differ.revision_vs_lines(
            relpath_in_repo, rev2_isorted, context_lines
        )
        if has_isort_changes and not edited_linenums:
            logger.debug("No changes in %s after isort", abspath_in_rev2)
            last_successful_reformat = rev2_isorted
            break

        # 8. choose processed content for each chunk if there were any changed lines
        #    inside the chunk in the edited to-file, or choose the chunk's original
        #    contents if no edits were done in that chunk
        chosen = TextDocument.from_lines(
            choose_lines(new_chunks, edited_linenums),
            encoding=rev2_content.encoding,
            newline=rev2_content.newline,
            mtime=datetime.utcnow().strftime(GIT_DATEFORMAT),
        )

        # 9. verify that the resulting reformatted source code parses to an identical
        #    AST as the original edited to-file
        if not has_fstring_changes and not verifier.is_equivalent_to_baseline(chosen):
            logger.debug(
                "Verifying that the %s original edited lines and %s reformatted lines "
                "parse into an identical abstract syntax tree",
                len(rev2_isorted.lines),
                len(chosen.lines),
            )
            debug_dump(new_chunks, edited_linenums)
            logger.debug(
                "AST verification of %s with %s lines of context failed",
                abspath_in_rev2,
                context_lines,
            )
            minimum_context_lines.respond(False)
        else:
            if has_fstring_changes:
                logger.debug("AST verification disabled due to fstringification")
            else:
                logger.debug("AST verification success")
            minimum_context_lines.respond(True)
            last_successful_reformat = chosen
    return last_successful_reformat


def modify_file(path: Path, new_content: TextDocument) -> None:
    """Write new content to a file and inform the user by logging"""
    logger.info("Writing %s bytes into %s", len(new_content.string), path)
    path.write_bytes(new_content.encoded_string)


def print_diff(
    path: Path,
    old: TextDocument,
    new: TextDocument,
    root: Path,
    use_color: bool,
) -> None:
    """Print ``black --diff`` style output for the changes

    :param path: The path of the file to print the diff output for, relative to CWD
    :param old: Old contents of the file
    :param new: New contents of the file
    :param root: The root for the relative path (current working directory if omitted)

    Modification times should be in the format "YYYY-MM-DD HH:MM:SS:mmmmmm +0000"

    """
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
    print(colorize(diff, "diff", use_color))


def print_source(new: TextDocument, use_color: bool) -> None:
    """Print the reformatted Python source code"""
    if use_color:
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


def main(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    argv: List[str] = None,
) -> int:
    """Parse the command line and reformat and optionally lint each source file

    1. run isort on each edited file (optional)
    2. run flynt (optional) on the isorted contents of each edited to-file
    3. run black on the isorted and fstringified contents of each edited to-file
    4. get a diff between the edited to-file and the processed content
    5. convert the diff into chunks, keeping original and reformatted content for each
       chunk
    6. diff the given revisions (optionally with isort modifications) for each
       file
    7. extract line numbers in each edited to-file for changed lines
    8. choose processed content for each chunk if there were any changed lines inside
       the chunk in the edited to-file, or choose the chunk's original contents if no
       edits were done in that chunk
    9. verify that the resulting reformatted source code parses to an identical AST as
       the original edited to-file
    9. write the reformatted source back to the original file or print the diff
    10. run linter subprocesses twice for all modified and unmodified files which are
        mentioned on the command line: first establish a baseline by running against
        ``rev1``, then get current linting status by running against the working tree
        (steps 10.-12. are optional)
    11. create a mapping from line numbers of unmodified lines in the current versions
        to corresponding line numbers in ``rev1``
    12. hide linter messages which appear in the current versions and identically on
        corresponding lines in ``rev1``, and show all other linter messages

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
        raise MissingPackageError(
            f"{get_extra_instruction('isort')} to use the `--isort` option."
        )

    if args.flynt and not flynt:
        raise MissingPackageError(
            f"{get_extra_instruction('flynt')} to use the `--flynt` option."
        )

    black_config = read_black_config(tuple(args.src), args.config)
    if args.config:
        black_config["config"] = args.config
    if args.line_length:
        black_config["line_length"] = args.line_length
    if args.target_version:
        black_config["target_version"] = {args.target_version}
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
                f"Can't write reformatted files for revision {revrange.rev2!r}."
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

    # These paths are relative to `root`:
    files_to_process = filter_python_files(paths, root, {})
    files_to_blacken = filter_python_files(paths, root, black_config)
    # Now decide which files to reformat (Black & isort). Note that this doesn't apply
    # to linting.
    if output_mode == OutputMode.CONTENT:
        # With `-d` / `--stdout`, reformat the file whether modified or not. Paths have
        # previously been validated to contain exactly one existing file.
        changed_files_to_reformat = files_to_process
        black_exclude = set()
    else:
        # In other modes, only reformat files which have been modified.
        if git_is_repository(root):
            changed_files_to_reformat = git_get_modified_python_files(
                files_to_process, revrange, root
            )
        else:
            changed_files_to_reformat = files_to_process
        black_exclude = {
            str(path)
            for path in changed_files_to_reformat
            if path not in files_to_blacken
        }
    use_color = should_use_color(config["color"])
    formatting_failures_on_modified_lines = False
    for path, old, new in sorted(
        format_edited_parts(
            root,
            changed_files_to_reformat,
            Exclusions(
                black=black_exclude,
                isort=set() if args.isort else {"**/*"},
                flynt=set() if args.flynt else {"**/*"},
            ),
            revrange,
            black_config,
            report_unmodified=output_mode == OutputMode.CONTENT,
            workers=config["workers"],
        ),
    ):
        # 10. A re-formatted Python file which produces an identical AST was
        #     created successfully - write an updated file or print the diff if
        #     there were any changes to the original
        formatting_failures_on_modified_lines = True
        if output_mode == OutputMode.DIFF:
            print_diff(path, old, new, root, use_color)
        elif output_mode == OutputMode.CONTENT:
            print_source(new, use_color)
        if write_modified_files:
            modify_file(path, new)
    linter_failures_on_modified_lines = run_linters(
        args.lint,
        root,
        # paths to lint are not limited to modified files or just Python files:
        {p.resolve().relative_to(root) for p in paths},
        revrange,
        use_color,
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
