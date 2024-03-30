"""Load and save configuration in TOML format"""

from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from darkgraylib.config import BaseConfig, ConfigurationError

UnvalidatedConfig = Dict[str, Union[List[str], str, bool, int]]


DEPRECATED_CONFIG_OPTIONS = {"skip_string_normalization", "skip_magic_trailing_comma"}


class DarkerConfig(BaseConfig, total=False):
    """Dictionary representing ``[tool.darker]`` from ``pyproject.toml``"""

    diff: bool
    check: bool
    isort: bool
    lint: List[str]
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool
    line_length: int
    target_version: str


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
        stdout: bool, src: List[str], stdin_filename: Optional[str]
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

    black: Set[str] = field(default_factory=set)
    isort: Set[str] = field(default_factory=set)
    flynt: Set[str] = field(default_factory=set)
