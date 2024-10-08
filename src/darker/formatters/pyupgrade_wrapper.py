"""Attempt to import Pyupgrade internals needed by the Pyupgrade formatter plugin."""

import logging

from darker.exceptions import DependencyError

logger = logging.getLogger(__name__)

try:
    import pyupgrade  # noqa: F401  # pylint: disable=unused-import
except ImportError as exc:
    logger.warning(
        "To update modified code using Pyupgrade, install it using e.g."
        " `pip install 'darker[pyupgrade]'` or"
        " `pip install pyupgrade`"
    )
    logger.warning(
        "To use a different formatter or no formatter, select it on the"
        " command line (e.g. `--formatter=none`) or configuration"
        " (e.g. `formatter=none`)"
    )
    MESSAGE = "Can't find the Pyupgrade package"
    raise DependencyError(MESSAGE) from exc

# pylint: disable=wrong-import-position
from pyupgrade._data import Settings  # noqa: E402
from pyupgrade._main import _fix_plugins, _fix_tokens, main  # noqa: E402

__all__ = [
    "Settings",
    "_fix_plugins",
    "_fix_tokens",
    "main",
]
