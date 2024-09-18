"""Load and save configuration in TOML format"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union

from darkgraylib.config import BaseConfig, ConfigurationError

if TYPE_CHECKING:
    from argparse import Namespace

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

UnvalidatedConfig: TypeAlias = Dict[str, Union[List[str], str, bool, int]]


REMOVED_CONFIG_OPTIONS = {
    "skip_string_normalization": (
        "Please move the `skip_string_normalization` option from the [tool.darker]"
        " section to the [tool.black] section in your `pyproject.toml` file."
    ),
    "skip_magic_trailing_comma": (
        "Please move the `skip_magic_trailing_comma` option from the [tool.darker]"
        " section to the [tool.black] section in your `pyproject.toml` file."
    ),
}
DEPRECATED_CONFIG_OPTIONS: set[str] = set()


class DarkerConfig(BaseConfig, total=False):
    """Dictionary representing ``[tool.darker]`` from ``pyproject.toml``"""

    check: bool
    diff: bool
    flynt: bool
    isort: bool
    line_length: int
    lint: list[str]
    skip_magic_trailing_comma: bool
    skip_string_normalization: bool
    target_version: str
    formatter: str


class OutputMode:
    """The output mode to use: all file content, just the diff, or no output"""

    NOTHING = "NOTHING"
    DIFF = "DIFF"
    CONTENT = "CONTENT"

    @classmethod
    def from_args(cls, args: Namespace) -> str:
        """Resolve output mode based on  ``diff`` and ``stdout`` options"""
        OutputMode.validate_diff_stdout(args.diff, args.stdout)
        if args.diff:
            return cls.DIFF
        if args.stdout:
            return cls.CONTENT
        return cls.NOTHING

    @staticmethod
    def validate_diff_stdout(diff: bool, stdout: bool) -> None:
        """Raise an exception if ``diff`` and ``stdout`` options are both enabled"""
        if diff and stdout:
            raise ConfigurationError(
                "The `diff` and `stdout` options can't both be enabled"
            )

    @staticmethod
    def validate_stdout_src(
        src: list[str], stdin_filename: str | None, *, stdout: bool
    ) -> None:
        """Raise an exception in ``stdout`` mode if not exactly one input is provided"""
        if not stdout:
            return
        if stdin_filename is None and len(src) == 1 and Path(src[0]).is_file():
            return
        if stdin_filename is not None and len(src) == 0 or src == ["-"]:
            return
        raise ConfigurationError(
            "Either --stdin-filename=<path> or exactly one Python source file which"
            " exists on disk must be provided when using the `stdout` option"
        )


def validate_config_output_mode(config: DarkerConfig) -> None:
    """Make sure both ``diff`` and ``stdout`` aren't enabled in configuration"""
    OutputMode.validate_diff_stdout(
        config.get("diff", False), config.get("stdout", False)
    )


@dataclass
class Exclusions:
    """File exclusions patterns for pre-processing steps

    For each pre-processor, there is a collection of glob patterns. When running Darker,
    any files matching at least one of the glob patterns is supposed to be skipped when
    running the corresponding pre-processor. If the collection of glob patterns is
    empty, the pre-processor is run for all files.

    The pre-processors whose exclusion lists are currently stored in this data
    structure are
    - Black
    - ``isort``
    - ``flynt``

    """

    formatter: set[str] = field(default_factory=set)
    isort: set[str] = field(default_factory=set)
    flynt: set[str] = field(default_factory=set)
