"""A dummy code formatter plugin interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from darker.formatters.base_formatter import BaseFormatter

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path
    from re import Pattern

    from darkgraylib.utils import TextDocument


class NoneFormatter(BaseFormatter):
    """A dummy code formatter plugin interface."""

    name = "dummy reformat"
    preserves_ast = True

    def run(
        self, content: TextDocument, path_from_cwd: Path  # noqa: ARG002
    ) -> TextDocument:
        """Return the Python source code unmodified.

        :param content: The source code
        :param path_from_cwd: The path to the source code file being reformatted, either
                              absolute or relative to the current working directory
        :return: The source code unmodified

        """
        return content

    def read_config(self, src: tuple[str, ...], args: Namespace) -> None:
        """Keep configuration options empty for the dummy formatter.

        :param src: The source code files and directories to be processed by Darker
        :param args: Command line arguments

        """

    def get_config_path(self) -> str | None:
        """Get the path of the configuration file."""
        return None

    def get_line_length(self) -> int | None:
        """Get the ``line-length`` configuration option value."""
        return 88

    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` configuration option value."""
        return default

    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` configuration option value."""
        return None

    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` configuration option value."""
        return None
