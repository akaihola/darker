"""Helpers for invoking ``flynt`` and acting on its output"""

import logging
from pathlib import Path
from typing import Any, Optional

from darker.exceptions import MissingPackageError
from darker.git import EditedLinenumsDiffer
from darkgraylib.utils import TextDocument

try:
    import flynt

    flynt_version = tuple(map(int, flynt.__version__.split(".")))
    if flynt_version >= (0, 78):
        from flynt.state import State
    else:
        State = None  # pylint: disable=invalid-name
    if flynt_version < (1, 0, 0):
        from flynt.process import fstringify_code_by_line
        from flynt.pyproject_finder import find_pyproject_toml, parse_pyproject_toml
    else:
        from flynt.code_editor import fstringify_code_by_line
        from flynt.utils.pyproject_finder import (
            find_pyproject_toml,
            parse_pyproject_toml,
        )
except ImportError:
    # `flynt` is an optional dependency. Prevent the `ImportError` if it's missing.
    flynt = None
    State = None

    def fstringify_code_by_line(*args: Any, **kwargs: Any) -> str:  # type: ignore[explicit-any]
        """Fake `flynt.fstringify_code_by_line()` to use when `flynt` isn't installed"""
        raise MissingPackageError(
            "No module named 'flynt'. Please install the 'flynt' package before using"
            " the --flynt / -i option."
        )


__all__ = ["apply_flynt", "flynt"]

logger = logging.getLogger(__name__)


def apply_flynt(
    content: TextDocument,
    src: Path,
    edited_linenums_differ: EditedLinenumsDiffer,
) -> TextDocument:
    """Run flynt on the given Python source file content

    This function includes all modifications from ``flynt`` in the result. It is the
    responsibility of the caller to filter output to modified lines only.

    :param content: The contents of the Python source code file to sort imports in
    :param src: The path to the file relative to the repository root. This must be the
                actual path in the repository, which may differ from the path given on
                the command line in case of VSCode temporary files.
    :param edited_linenums_differ: Helper for finding out which lines were edited
    :return: Original Python source file contents with modifications from ``flynt``

    """
    edited_linenums = edited_linenums_differ.revision_vs_lines(
        src,
        content,
        context_lines=0,
    )
    if not edited_linenums:
        return content
    state = _get_flynt_configuration(edited_linenums_differ.root / src)
    return _call_flynt_fstringify(content, state)


def _get_flynt_configuration(  # type: ignore[no-any-unimported]
    src: Path,
) -> Optional[State]:
    """Read ``pyproject.toml`` Flynt configuration for the given Python file

    :param src: The absolute path to the Python file to run Flynt on. This must be the
                actual path in the repository, which may differ from the path given on
                the command line in case of VSCode temporary files.
    :return: A ``flynt`` configuration, or ``None`` for Flynt versions <0.78

    """
    if State is None:  # flynt<0.78
        return None
    state = State(quiet=True)
    toml_file = find_pyproject_toml((str(src),))
    if toml_file:
        cfg = parse_pyproject_toml(toml_file)
        mapping = {
            # (state attribute name, `pyproject.toml` option)
            ("aggressive", "aggressive"),
            ("len_limit", "line_length"),
            ("multiline", "not no_multiline"),
            ("transform_concat", "transform_concats"),
            ("transform_format", "transform_format"),
            ("transform_join", "transform_joins"),
            ("transform_percent", "transform_percent"),
        }
        for state_attr, cfg_option in mapping:
            if cfg_option not in cfg:
                continue
            if cfg_option.startswith("not "):
                value = not cfg[cfg_option[4:]]
            else:
                value = cfg[cfg_option]
            setattr(state, state_attr, value)
    return state


def _call_flynt_fstringify(  # type: ignore[no-any-unimported]
    content: TextDocument, state: Optional[State]
) -> TextDocument:
    """Call ``flynt.code_editor.fstringify_code_by_line()``, return ``TextDocument``

    :param content: The contents of the Python source code file to fstringify
    :param state: The ``flynt`` configuration to use, or ``None`` for ``flynt<0.78``
    :return: Original Python source code contents with modifications from ``flynt``

    """
    logger.debug("flynt.code_editor.fstringify_code_by_line(code=...)")
    args = () if state is None else (state,)  # `()` for flynt<0.78, (state,) for >=0.78
    result, _ = fstringify_code_by_line(content.string, *args)
    return TextDocument.from_str(
        result,
        encoding=content.encoding,
        mtime=content.mtime,
    )
