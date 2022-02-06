import logging
import sys
from pathlib import Path
from typing import Any, List, Optional

from darker.black_compat import find_project_root
from darker.diff import diff_chunks
from darker.exceptions import IncompatiblePackageError, MissingPackageError
from darker.git import EditedLinenumsDiffer
from darker.utils import DiffChunk, TextDocument

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


try:
    import isort

    # Work around Mypy problem
    # https://github.com/python/mypy/issues/7030#issuecomment-504128883
    try:
        isort_code = getattr(isort, "code")
    except AttributeError:
        # Postpone error message about incompatbile `isort` version until `--isort` is
        # actually used.
        def isort_code(*args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
            """Fake `isort.code()` function to use when `isort < 5` is installed"""
            raise IncompatiblePackageError(
                "An incompatible 'isort' package was found. Please install version"
                " 5.0.0 or later."
            )
except ImportError:
    # `isort` is an optional dependency. Prevent the `ImportError` if it's missing.
    isort = None  # type: ignore

    def isort_code(*args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
        """Fake `isort.code()` function to use when `isort` isn't installed"""
        raise MissingPackageError(
            "No module named 'isort'. Please install the 'isort' package before using"
            " the --isort / -i option."
        )


__all__ = ["apply_isort", "isort"]

logger = logging.getLogger(__name__)


class IsortArgs(TypedDict, total=False):
    line_length: int
    settings_file: str
    settings_path: str


def apply_isort(
    content: TextDocument,
    src: Path,
    edited_linenums_differ: EditedLinenumsDiffer,
    config: Optional[str] = None,
    line_length: Optional[int] = None,
) -> TextDocument:
    """Run isort on the given Python source file content

    :param content: The contents of the Python source code file to sort imports in
    :param src: The relative path to the file. This must be the actual path in the
                repository, which may differ from the path given on the command line in
                case of VSCode temporary files.
    :param edited_linenums_differ: Helper for finding out which lines were edited
    :param config: Path to configuration file
    :param line_length: Maximum line length to use

    """
    edited_linenums = edited_linenums_differ.revision_vs_lines(
        src,
        content,
        context_lines=0,
    )
    if not edited_linenums:
        return content
    isort_args = _build_isort_args(src, config, line_length)
    rev2_isorted = _call_isort_code(content, isort_args)
    # Get the chunks in the diff between the edited and import-sorted file
    isort_chunks = diff_chunks(content, rev2_isorted)
    if not isort_chunks:
        # No imports were sorted. Return original content.
        return content
    if not _diff_overlaps_with_edits(edited_linenums, isort_chunks):
        # No lines had been modified in the range of modified import lines. Return
        # original content.
        return content
    # The range lines modified by sorted imports overlaps with user modifications in the
    # code. Return the import-sorted file.
    return rev2_isorted


def _build_isort_args(
    src: Path,
    config: Optional[str] = None,
    line_length: Optional[int] = None,
) -> IsortArgs:
    """Build ``isort.code()`` keyword arguments

    :param src: The relative path to the file. This must be the actual path in the
                repository, which may differ from the path given on the command line in
                case of VSCode temporary files.
    :param config: Path to configuration file
    :param line_length: Maximum line length to use

    """
    isort_args: IsortArgs = {}
    if config:
        isort_args["settings_file"] = config
    else:
        isort_args["settings_path"] = str(find_project_root((str(src),)))
    if line_length:
        isort_args["line_length"] = line_length
    return isort_args


def _call_isort_code(content: TextDocument, isort_args: IsortArgs) -> TextDocument:
    """Call ``isort.code()`` and return the result as a `TextDocument` object

    :param content: The contents of the Python source code file to sort imports in
    :param isort_args: Keyword arguments for ``isort.code()``

    """
    code = content.string
    logger.debug(
        "isort.code(code=..., %s)",
        ", ".join(f"{k}={v!r}" for k, v in isort_args.items()),
    )
    try:
        code = isort_code(code=code, **isort_args)
    except isort.exceptions.FileSkipComment:
        pass
    return TextDocument.from_str(
        code,
        encoding=content.encoding,
        mtime=content.mtime,
    )


def _diff_overlaps_with_edits(
    edited_linenums: List[int], isort_chunks: List[DiffChunk]
) -> bool:
    """Return ``True`` if the complete diff overlaps the range of edited lines

    :param edited_linenums: The line numbers of all edited lines
    :param isort_chunks: The diff chunks
    :return: ``True`` if the two overlap

    """
    if not edited_linenums:
        return False
    first_edited_linenum, last_edited_linenum = edited_linenums[0], edited_linenums[-1]
    modified_chunks = [
        (linenum, old, new) for linenum, old, new in isort_chunks if old != new
    ]
    if not modified_chunks:
        return False
    (first_isort_line, _, _) = modified_chunks[0]
    (last_isort_chunk_start, last_isort_chunk_original_lines, _) = modified_chunks[-1]
    last_isort_line = last_isort_chunk_start + len(last_isort_chunk_original_lines)
    return (
        first_edited_linenum < last_isort_line
        and last_edited_linenum >= first_isort_line
    )
