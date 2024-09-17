"""Code re-formatter plugin configuration type definitions."""

from typing import Pattern, Set, TypedDict, Union


class FormatterConfig(TypedDict):
    """Base class for code re-formatter configuration."""


class BlackConfig(FormatterConfig, total=False):
    """Type definition for Black configuration dictionaries"""

    config: str
    exclude: Pattern[str]
    extend_exclude: Pattern[str]
    force_exclude: Pattern[str]
    target_version: Union[str, Set[str]]
    line_length: int
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool
    preview: bool
