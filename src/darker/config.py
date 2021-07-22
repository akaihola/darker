"""Load and save configuration in TOML format"""

import logging
from argparse import ArgumentParser, Namespace
from typing import Dict, Iterable, List, Union, cast

import toml
from black import find_project_root


class TomlArrayLinesEncoder(toml.TomlEncoder):  # type: ignore[name-defined]
    """Format TOML so list items are each on their own line"""

    def dump_list(self, v: List[str]) -> str:
        """Format a list value"""
        return "[{}\n]".format(
            "".join("\n    {},".format(self.dump_value(item)) for item in v)
        )


DarkerConfig = Dict[str, Union[str, bool, List[str]]]


class OutputMode:
    """The output mode to use: all file content, just the diff, or no output"""

    NOTHING = "NOTHING"
    DIFF = "DIFF"
    CONTENT = "CONTENT"

    @classmethod
    def from_args(cls, args: Namespace) -> str:
        """Resolve output mode based on  ``diff`` and ``stdout`` options"""
        OutputMode.validate(args.diff, args.stdout)
        if args.diff:
            return cls.DIFF
        if args.stdout:
            return cls.CONTENT
        return cls.NOTHING

    @staticmethod
    def validate(diff: bool, stdout: bool) -> None:
        """Raise an exception if both ``diff`` and ``stdout`` are enabled"""
        if diff and stdout:
            raise ConfigurationError(
                "The `diff` and `stdout` options can't both be enabled"
            )


class ConfigurationError(Exception):
    """Exception class for invalid configuration values"""


def replace_log_level_name(config: DarkerConfig) -> None:
    """Replace numeric log level in configuration with the name of the log level"""
    if "log_level" in config:
        config["log_level"] = logging.getLevelName(cast(int, config["log_level"]))


def validate_config_output_mode(config: DarkerConfig) -> None:
    """Make sure both ``diff`` and ``stdout`` aren't enabled in configuration"""
    OutputMode.validate(config.get("diff", False), config.get("stdout", False))


def load_config(srcs: Iterable[str]) -> DarkerConfig:
    """Find and load Darker configuration from given path or pyproject.toml

    :param srcs: File(s) and directory/directories which will be processed. Their paths
                 are used to look for the ``pyproject.toml`` configuration file.

    """
    path = find_project_root(tuple(srcs or ["."])) / "pyproject.toml"
    if path.is_file():
        pyproject_toml = toml.load(path)
        config: DarkerConfig = pyproject_toml.get("tool", {}).get("darker", {}) or {}
        replace_log_level_name(config)
        validate_config_output_mode(config)
        return config
    return {}


def get_effective_config(args: Namespace) -> DarkerConfig:
    """Return all configuration options"""
    config = vars(args).copy()
    replace_log_level_name(config)
    validate_config_output_mode(config)
    return config


def get_modified_config(parser: ArgumentParser, args: Namespace) -> DarkerConfig:
    """Return configuration options which are set to non-default values"""
    not_default = {
        argument: value
        for argument, value in vars(args).items()
        if value != parser.get_default(argument)
    }
    replace_log_level_name(not_default)
    return not_default


def dump_config(config: DarkerConfig) -> str:
    """Return the configuration in TOML format"""
    dump = toml.dumps(config, encoder=TomlArrayLinesEncoder())  # type: ignore[call-arg]
    return f"[tool.darker]\n{dump}"
