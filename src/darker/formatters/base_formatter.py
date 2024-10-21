"""Base class for code re-formatters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Pattern

if TYPE_CHECKING:
    from argparse import Namespace

    from darker.formatters.formatter_config import FormatterConfig
    from darkgraylib.utils import TextDocument


class BaseFormatter:
    """Base class for code re-formatters."""

    def __init__(self) -> None:
        """Initialize the code re-formatter plugin base class."""
        self.config: FormatterConfig = {}

    name: str

    def read_config(self, src: tuple[str, ...], args: Namespace) -> None:
        """Read the formatter configuration from a configuration file

        If not implemented by the subclass, this method does nothing, so the formatter
        has no configuration options.

        :param src: The source code files and directories to be processed by Darker
        :param args: Command line arguments

        """

    def run(self, content: TextDocument) -> TextDocument:
        """Reformat the content."""
        raise NotImplementedError

    def get_config_path(self) -> str | None:
        """Get the path of the configuration file."""
        return None

    def get_line_length(self) -> int | None:
        """Get the ``line-length`` configuration option value."""
        return None

    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` configuration option value."""
        return default

    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` configuration option value."""
        return None

    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` configuration option value."""
        return None

    def __eq__(self, other: object) -> bool:
        """Compare two formatters for equality."""
        if not isinstance(other, BaseFormatter):
            return NotImplemented
        return type(self) is type(other) and self.config == other.config
