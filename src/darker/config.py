"""Load and save configuration in TOML format"""

import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterable, List, Optional, cast

import toml

from darker.black_compat import find_project_root

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class TomlArrayLinesEncoder(toml.TomlEncoder):  # type: ignore
    """Format TOML so list items are each on their own line"""

    def dump_list(self, v: Iterable[object]) -> str:
        """Format a list value"""
        return "[{}\n]".format("".join(f"\n    {self.dump_value(item)}," for item in v))


class DarkerConfig(TypedDict, total=False):
    """Dictionary representing ``[tool.darker]`` from ``pyproject.toml``"""

    src: List[str]
    revision: str
    diff: bool
    stdout: bool
    check: bool
    isort: bool
    lint: List[str]
    config: str
    log_level: int
    color: bool
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool
    line_length: int
    workers: int


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
    def validate_stdout_src(stdout: bool, src: List[str]) -> None:
        """Raise an exception in ``stdout`` mode if not exactly one path is provided"""
        if not stdout:
            return
        if len(src) == 1 and Path(src[0]).is_file():
            return
        raise ConfigurationError(
            "Exactly one Python source file which exists on disk must be provided when"
            " using the `stdout` option"
        )


class ConfigurationError(Exception):
    """Exception class for invalid configuration values"""


def replace_log_level_name(config: DarkerConfig) -> None:
    """Replace numeric log level in configuration with the name of the log level"""
    if "log_level" in config:
        config["log_level"] = logging.getLevelName(config["log_level"])


def validate_config_output_mode(config: DarkerConfig) -> None:
    """Make sure both ``diff`` and ``stdout`` aren't enabled in configuration"""
    OutputMode.validate_diff_stdout(
        config.get("diff", False), config.get("stdout", False)
    )


def override_color_with_environment(pyproject_config: DarkerConfig) -> DarkerConfig:
    """Override ``color`` if the ``PY_COLORS`` environment variable is '0' or '1'

    :param config: The configuration read from ``pyproject.toml``
    :return: The modified configuration

    """
    config = pyproject_config.copy()
    py_colors = os.getenv("PY_COLORS")
    if py_colors in {"0", "1"}:
        config["color"] = py_colors == "1"
    elif os.getenv("NO_COLOR") is not None:
        config["color"] = False
    elif os.getenv("FORCE_COLOR") is not None:
        config["color"] = True
    return config


def load_config(path: Optional[str], srcs: Iterable[str]) -> DarkerConfig:
    """Find and load Darker configuration from a TOML configuration file

    Darker determines the location for the configuration file by trying the following:
    - the file path in the `path` argument, given using the ``-c``/``--config`` command
      line option
    - ``pyproject.toml`` inside the directory specified by the `path` argument
    - ``pyproject.toml`` from a common parent directory to all items in `srcs`
    - ``pyproject.toml`` in the current working directory if `srcs` is empty

    :param path: The file or directory specified using the ``-c``/``--config`` command
                 line option, or `None` if the option was omitted.
    :param srcs: File(s) and directory/directories to be processed by Darker.

    """
    if path:
        for candidate_path in [Path(path), Path(path, "pyproject.toml")]:
            if candidate_path.is_file():
                config_path = candidate_path
                break
        else:
            if Path(path).is_dir() or path.endswith(os.sep):
                raise ConfigurationError(
                    f"Configuration file {Path(path, 'pyproject.toml')} not found"
                )
            raise ConfigurationError(f"Configuration file {path} not found")
    else:
        config_path = find_project_root(tuple(srcs or ["."])) / "pyproject.toml"
        if not config_path.is_file():
            return {}
    pyproject_toml = toml.load(config_path)
    config = cast(DarkerConfig, pyproject_toml.get("tool", {}).get("darker", {}) or {})
    replace_log_level_name(config)
    validate_config_output_mode(config)
    return config


def get_effective_config(args: Namespace) -> DarkerConfig:
    """Return all configuration options"""
    config = cast(DarkerConfig, vars(args).copy())
    replace_log_level_name(config)
    validate_config_output_mode(config)
    return config


def get_modified_config(parser: ArgumentParser, args: Namespace) -> DarkerConfig:
    """Return configuration options which are set to non-default values"""
    not_default = cast(
        DarkerConfig,
        {
            argument: value
            for argument, value in vars(args).items()
            if value != parser.get_default(argument)
        },
    )
    replace_log_level_name(not_default)
    return not_default


def dump_config(config: DarkerConfig) -> str:
    """Return the configuration in TOML format"""
    dump = toml.dumps(config, encoder=TomlArrayLinesEncoder())
    return f"[tool.darker]\n{dump}"


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

    """

    black: Collection[str]
    isort: Collection[str]
