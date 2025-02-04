"""Wrapper for Blue internals needed by the Blue formatter plugin."""

import logging

from darker.exceptions import DependencyError

logger = logging.getLogger(__name__)

try:
    from blue import format_str, parse_pyproject_toml
except ImportError as exc:
    logger.warning(
        "To use Blue formatting, install it using: pip install 'darker[blue]'"
    )
    raise DependencyError("Blue package not found") from exc

__all__ = ["format_str", "parse_pyproject_toml"]
