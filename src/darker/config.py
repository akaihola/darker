"""Load and save configuration in TOML format"""

import logging
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Optional, Union

import toml
from black import find_project_root


class TomlArrayLinesEncoder(toml.TomlEncoder):  # type: ignore[name-defined]
    """Format TOML so list items are each on their own line"""

    def dump_list(self, v: List[str]) -> str:
        """Format a list value"""
        return "[{}\n]".format(
            "".join("\n    {}".format(self.dump_value(item)) for item in v)
        )


DarkerConfig = Dict[str, Union[str, bool, List[str]]]


def load_config(path: Optional[str], srcs: List[str]) -> DarkerConfig:
    """Find and load Darker configuration from given path or pyproject.toml"""
    if not path:
        path_pyproject_toml = find_project_root(tuple(srcs)) / "pyproject.toml"
        path = str(path_pyproject_toml) if path_pyproject_toml.is_file() else None
    if path:
        pyproject_toml = toml.load(path)
        config = pyproject_toml.get("tool", {}).get("darker", {}) or {}
        if "log_level" in config:
            config["log_level"] = logging.getLevelName(config["log_level"])
        return config
    return {}


def get_effective_config(args: Namespace) -> DarkerConfig:
    """Return all configuration options"""
    config = vars(args).copy()
    config["log_level"] = logging.getLevelName(config["log_level"])
    return config


def get_modified_config(parser: ArgumentParser, args: Namespace) -> DarkerConfig:
    """Return configuration options which are set to non-default values"""
    not_default = {
        argument: value
        for argument, value in vars(args).items()
        if value != parser.get_default(argument)
    }
    if "log_level" in not_default:
        not_default["log_level"] = logging.getLevelName(not_default["log_level"])
    return not_default


def dump_config(config: DarkerConfig) -> None:
    """Print the configuration in TOML format"""
    print('[tool.darker]')
    print(toml.dumps(config, encoder=TomlArrayLinesEncoder()))  # type: ignore[call-arg]
