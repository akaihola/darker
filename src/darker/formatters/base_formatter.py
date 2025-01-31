"""Base class for code re-formatters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from darker.files import find_pyproject_toml
from darker.formatters.formatter_config import FormatterConfig

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path
    from re import Pattern

    from darkgraylib.utils import TextDocument


T = TypeVar("T", bound=FormatterConfig)


class HasConfig(Generic[T]):  # pylint: disable=too-few-public-methods
    """Base class for code re-formatters."""

    def __init__(self) -> None:
        """Initialize the code re-formatter plugin base class."""
        self.config = {}  # type: ignore[var-annotated]


class BaseFormatter(HasConfig[FormatterConfig]):
    """Base class for code re-formatters."""

    name: str
    preserves_ast: bool

    def read_config(self, src: tuple[str, ...], args: Namespace) -> None:
        """Read code re-formatter configuration from a configuration file.

        :param src: The source code files and directories to be processed by Darker
        :param args: Command line arguments

        """
        config_path = args.config or find_pyproject_toml(src)
        if config_path:
            self._read_config_file(config_path)
        self._read_cli_args(args)

    def run(self, content: TextDocument, path_from_cwd: Path) -> TextDocument:
        """Reformat the content."""
        raise NotImplementedError

    def _read_cli_args(self, args: Namespace) -> None:
        pass

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

    def _read_config_file(self, config_path: str) -> None:
        pass
