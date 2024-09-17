"""A dummy code formatter plugin interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Pattern

from darker.formatters.base_formatter import BaseFormatter

if TYPE_CHECKING:
    from argparse import Namespace

    from darkgraylib.utils import TextDocument


class NoneFormatter(BaseFormatter):
    """A dummy code formatter plugin interface."""

    def run(self, content: TextDocument) -> TextDocument:
        """Return the Python source code unmodified.

        :param content: The source code
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
