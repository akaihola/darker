"""Code re-formatter plugin configuration type definitions."""

from __future__ import annotations

from typing import Pattern, TypedDict


class FormatterConfig(TypedDict):
    """Base class for code re-formatter configuration."""


class BlackConfig(FormatterConfig, total=False):
    """Type definition for Black configuration dictionaries."""

    config: str
    exclude: Pattern[str]
    extend_exclude: Pattern[str] | None
    force_exclude: Pattern[str] | None
    target_version: str | set[str]
    line_length: int
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool
    preview: bool
