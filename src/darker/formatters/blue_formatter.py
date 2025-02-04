"""Re-format Python source code using Blue."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from darker.formatters.base_formatter import BaseFormatter, HasConfig
from darker.formatters.formatter_config import (
    BlackCompatibleConfig,
    read_black_compatible_cli_args,
    validate_target_versions,
)
from darkgraylib.config import ConfigurationError
from darkgraylib.utils import TextDocument

if TYPE_CHECKING:
    from argparse import Namespace
    from re import Pattern

logger = logging.getLogger(__name__)


class BlueFormatter(BaseFormatter, HasConfig[BlackCompatibleConfig]):
    """Blue code formatter plugin interface."""

    config: BlackCompatibleConfig  # type: ignore[assignment]

    name = "blue"
    config_section = "tool.blue"
    preserves_ast = True

    def read_config(self, src: tuple[str, ...], args: Namespace) -> None:
        """Read Blue configuration from ``pyproject.toml``."""
        config_path = args.config or self._find_pyproject_toml(src)
        if config_path:
            self._read_config_file(config_path)
        self._read_cli_args(args)

    def _read_config_file(self, config_path: str) -> None:
        """Parse Blue configuration from a TOML configuration file."""
        from darker.formatters.blue_wrapper import (
            parse_pyproject_toml,
            re_compile_maybe_verbose,
        )

        raw_config = parse_pyproject_toml(config_path).get("tool", {}).get("blue", {})
        
        if "line-length" in raw_config:
            self.config["line_length"] = int(raw_config["line-length"])
        if "skip-string-normalization" in raw_config:
            self.config["skip_string_normalization"] = raw_config["skip-string-normalization"]
        if "skip-magic-trailing-comma" in raw_config:
            self.config["skip_magic_trailing_comma"] = raw_config["skip-magic-trailing-comma"]
        if "target-version" in raw_config:
            target_version = raw_config["target-version"]
            if isinstance(target_version, str):
                self.config["target_version"] = (
                    int(target_version[2]),
                    int(target_version[3:]),
                )
            elif isinstance(target_version, list):
                self.config["target_version"] = {
                    (int(v[2]), int(v[3:])) for v in target_version
                }

    def _read_cli_args(self, args: Namespace) -> None:
        return read_black_compatible_cli_args(args, self.config)

    def run(self, content: TextDocument, path_from_cwd: Path) -> TextDocument:
        """Run Blue on the given Python source code."""
        from darker.formatters.blue_wrapper import format_str

        contents_for_blue = content.string_with_newline("\n")
        if contents_for_blue.strip():
            dst_contents = format_str(
                contents_for_blue, mode=self._make_blue_options()
            )
        else:
            dst_contents = "\n" if "\n" in content.string else ""
            
        return TextDocument.from_str(
            dst_contents,
            encoding=content.encoding,
            override_newline=content.newline,
        )

    def _make_blue_options(self) -> dict:
        """Create Blue formatting options from configuration."""
        options = {}
        if "line_length" in self.config:
            options["line_length"] = self.config["line_length"]
        if "skip_string_normalization" in self.config:
            options["string_normalization"] = not self.config["skip_string_normalization"]
        if "skip_magic_trailing_comma" in self.config:
            options["magic_trailing_comma"] = not self.config["skip_magic_trailing_comma"]
        return options

    def get_config_path(self) -> str | None:
        """Get the path of the Blue configuration file."""
        return self.config.get("config")

    def get_line_length(self) -> int | None:
        """Get the ``line-length`` Blue configuration option value."""
        return self.config.get("line_length")

    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` Blue configuration option value."""
        return self.config.get("exclude", default)

    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` Blue configuration option value."""
        return self.config.get("extend_exclude")

    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` Blue configuration option value."""
        return self.config.get("force_exclude")
