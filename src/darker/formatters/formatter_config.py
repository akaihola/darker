"""Code re-formatter plugin configuration type definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, TypedDict

from darkgraylib.config import ConfigurationError

if TYPE_CHECKING:
    from argparse import Namespace
    from re import Pattern


class FormatterConfig(TypedDict):
    """Base class for code re-formatter configuration."""


def validate_target_versions(
    value: tuple[int, int] | set[tuple[int, int]],
    valid_target_versions: Iterable[tuple[int, int]],
) -> set[tuple[int, int]]:
    """Validate the target-version configuration option value."""
    target_versions_in = value if isinstance(value, set) else {value}
    if not isinstance(value, (tuple, set)):
        message = f"Invalid target version(s) {value!r}"  # type: ignore[unreachable]
        raise ConfigurationError(message)
    bad_target_versions = target_versions_in - set(valid_target_versions)
    if bad_target_versions:
        message = f"Invalid target version(s) {bad_target_versions}"
        raise ConfigurationError(message)
    return target_versions_in


class BlackCompatibleConfig(FormatterConfig, total=False):
    """Type definition for configuration dictionaries of Black compatible formatters."""

    config: str
    exclude: Pattern[str]
    extend_exclude: Pattern[str] | None
    force_exclude: Pattern[str] | None
    target_version: tuple[int, int] | set[tuple[int, int]]
    line_length: int
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool
    preview: bool


def read_black_compatible_cli_args(
    args: Namespace, config: BlackCompatibleConfig
) -> None:
    """Read Black-compatible configuration from command line arguments."""
    if args.config:
        config["config"] = args.config
    if getattr(args, "line_length", None):
        config["line_length"] = args.line_length
    if getattr(args, "target_version", None):
        config["target_version"] = {
            (int(args.target_version[2]), int(args.target_version[3:]))
        }
    if getattr(args, "skip_string_normalization", None) is not None:
        config["skip_string_normalization"] = args.skip_string_normalization
    if getattr(args, "skip_magic_trailing_comma", None) is not None:
        config["skip_magic_trailing_comma"] = args.skip_magic_trailing_comma
    if getattr(args, "preview", None):
        config["preview"] = args.preview
