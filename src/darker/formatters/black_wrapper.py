"""Attempt to import Black internals needed by the Black formatter plugin."""

import logging

from darker.exceptions import DependencyError

logger = logging.getLogger(__name__)

try:
    import black  # noqa: F401  # pylint: disable=unused-import
except ImportError as exc:
    logger.warning(
        "Since Darker 3.0.0, Black is no longer installed by default. "
        "To re-format code using Black, install it using e.g."
        " `pip install 'darker[black]'` or"
        " `pip install black`"
    )
    logger.warning(
        "To use a different formatter or no formatter, select it on the"
        " command line (e.g. `--formatter=ruff`) or configuration"
        " (e.g. `formatter=none`)"
    )
    MESSAGE = "Can't find the Black package"
    raise DependencyError(MESSAGE) from exc

from black import (  # noqa: E402  # pylint: disable=unused-import,wrong-import-position
    FileMode,
    TargetVersion,
    format_str,
    parse_pyproject_toml,
    re_compile_maybe_verbose,
)

__all__ = [
    "FileMode",
    "TargetVersion",
    "format_str",
    "parse_pyproject_toml",
    "re_compile_maybe_verbose",
]
