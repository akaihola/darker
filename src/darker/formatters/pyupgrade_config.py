"""Pyupgrade code formatter plugin configuration type definitions."""

from darker.formatters.formatter_config import FormatterConfig


class PyupgradeConfig(FormatterConfig, total=False):
    """Type definition for configuration dictionaries of Black compatible formatters."""

    target_version: tuple[int, int]
