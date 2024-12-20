"""Re-format Python source code using Black.

In examples below, a simple two-line snippet is used.
The first line will be reformatted by Black, and the second left intact::

    >>> from pathlib import Path
    >>> from unittest.mock import Mock
    >>> src = Path("dummy/file/path.py")
    >>> src_content = TextDocument.from_lines(
    ...     [
    ...         "for i in range(5): print(i)",
    ...         'print("done")',
    ...     ]
    ... )

First, :func:`run_black` uses Black to reformat the contents of a given file.
Reformatted lines are returned e.g.::

    >>> from darker.formatters.black_formatter import BlackFormatter
    >>> dst = BlackFormatter().run(src_content)
    >>> dst.lines
    ('for i in range(5):', '    print(i)', 'print("done")')

See :mod:`darker.diff` and :mod:`darker.chooser`
for how this result is further processed with:

- :func:`~darker.diff.diff_and_get_opcodes`
  to get a diff of the reformatting
- :func:`~darker.diff.opcodes_to_chunks`
  to split the diff into chunks of original and reformatted content
- :func:`~darker.chooser.choose_lines`
  to reconstruct the source code from original and reformatted chunks
  based on whether reformats touch user-edited lines

"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

from black import FileMode as Mode
from black import (
    TargetVersion,
    format_str,
    parse_pyproject_toml,
    re_compile_maybe_verbose,
)

from darker.files import find_pyproject_toml
from darker.formatters.base_formatter import BaseFormatter
from darkgraylib.config import ConfigurationError
from darkgraylib.utils import TextDocument

if TYPE_CHECKING:
    from argparse import Namespace
    from typing import Pattern

    from darker.formatters.formatter_config import BlackConfig

__all__ = ["Mode"]

logger = logging.getLogger(__name__)


class BlackModeAttributes(TypedDict, total=False):
    """Type definition for items accepted by ``black.Mode``."""

    target_versions: set[TargetVersion]
    line_length: int
    string_normalization: bool
    is_pyi: bool
    magic_trailing_comma: bool
    preview: bool


class BlackFormatter(BaseFormatter):
    """Black code formatter plugin interface."""

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        """Initialize the Black code re-formatter plugin."""
        self.config: BlackConfig = {}

    name = "black"

    def read_config(self, src: tuple[str, ...], args: Namespace) -> None:
        """Read Black configuration from ``pyproject.toml``.

        :param src: The source code files and directories to be processed by Darker
        :param args: Command line arguments

        """
        config_path = args.config or find_pyproject_toml(src)
        if config_path:
            self._read_config_file(config_path)
        self._read_cli_args(args)

    def _read_config_file(self, config_path: str) -> None:  # noqa: C901
        raw_config = parse_pyproject_toml(config_path)
        if "line_length" in raw_config:
            self.config["line_length"] = raw_config["line_length"]
        if "skip_magic_trailing_comma" in raw_config:
            self.config["skip_magic_trailing_comma"] = raw_config[
                "skip_magic_trailing_comma"
            ]
        if "skip_string_normalization" in raw_config:
            self.config["skip_string_normalization"] = raw_config[
                "skip_string_normalization"
            ]
        if "preview" in raw_config:
            self.config["preview"] = raw_config["preview"]
        if "target_version" in raw_config:
            target_version = raw_config["target_version"]
            if isinstance(target_version, str):
                self.config["target_version"] = target_version
            elif isinstance(target_version, list):
                # Convert TOML list to a Python set
                self.config["target_version"] = set(target_version)
            else:
                message = (
                    f"Invalid target-version = {target_version!r} in {config_path}"
                )
                raise ConfigurationError(message)
        if "exclude" in raw_config:
            self.config["exclude"] = re_compile_maybe_verbose(raw_config["exclude"])
        if "extend_exclude" in raw_config:
            self.config["extend_exclude"] = re_compile_maybe_verbose(
                raw_config["extend_exclude"]
            )
        if "force_exclude" in raw_config:
            self.config["force_exclude"] = re_compile_maybe_verbose(
                raw_config["force_exclude"]
            )

    def _read_cli_args(self, args: Namespace) -> None:
        if args.config:
            self.config["config"] = args.config
        if getattr(args, "line_length", None):
            self.config["line_length"] = args.line_length
        if getattr(args, "target_version", None):
            self.config["target_version"] = {args.target_version}
        if getattr(args, "skip_string_normalization", None) is not None:
            self.config["skip_string_normalization"] = args.skip_string_normalization
        if getattr(args, "skip_magic_trailing_comma", None) is not None:
            self.config["skip_magic_trailing_comma"] = args.skip_magic_trailing_comma
        if getattr(args, "preview", None):
            self.config["preview"] = args.preview

    def run(self, content: TextDocument) -> TextDocument:
        """Run the Black code re-formatter for the Python source code given as a string.

        :param content: The source code
        :return: The reformatted content

        """
        contents_for_black = content.string_with_newline("\n")
        if contents_for_black.strip():
            dst_contents = format_str(
                contents_for_black, mode=self._make_black_options()
            )
        else:
            # The custom handling of empty and all-whitespace files was needed until
            # Black 22.12.0. See https://github.com/psf/black/pull/2484
            dst_contents = "\n" if "\n" in content.string else ""
        return TextDocument.from_str(
            dst_contents,
            encoding=content.encoding,
            override_newline=content.newline,
        )

    def _make_black_options(self) -> Mode:
        """Create a Black ``Mode`` object from the configuration options."""
        # Collect relevant Black configuration options from ``self.config`` in order to
        # pass them to Black's ``format_str()``. File exclusion options aren't needed
        # since at this point we already have a single file's content to work on.
        mode = BlackModeAttributes()
        if "line_length" in self.config:
            mode["line_length"] = self.config["line_length"]
        if "target_version" in self.config:
            if isinstance(self.config["target_version"], set):
                target_versions_in = self.config["target_version"]
            else:
                target_versions_in = {self.config["target_version"]}
            all_target_versions = {tgt_v.name.lower(): tgt_v for tgt_v in TargetVersion}
            bad_target_versions = target_versions_in - set(all_target_versions)
            if bad_target_versions:
                message = f"Invalid target version(s) {bad_target_versions}"
                raise ConfigurationError(message)
            mode["target_versions"] = {
                all_target_versions[n] for n in target_versions_in
            }
        if "skip_magic_trailing_comma" in self.config:
            mode["magic_trailing_comma"] = not self.config["skip_magic_trailing_comma"]
        if "skip_string_normalization" in self.config:
            # The ``black`` command line argument is
            # ``--skip-string-normalization``, but the parameter for
            # ``black.Mode`` needs to be the opposite boolean of
            # ``skip-string-normalization``, hence the inverse boolean
            mode["string_normalization"] = not self.config["skip_string_normalization"]
        if "preview" in self.config:
            mode["preview"] = self.config["preview"]
        return Mode(**mode)

    def get_config_path(self) -> str | None:
        """Get the path of the Black configuration file."""
        return self.config.get("config")

    def get_line_length(self) -> int | None:
        """Get the ``line-length`` Black configuration option value."""
        return self.config.get("line_length")

    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` Black configuration option value."""
        return self.config.get("exclude", default)

    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` Black configuration option value."""
        return self.config.get("extend_exclude")

    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` Black configuration option value."""
        return self.config.get("force_exclude")
