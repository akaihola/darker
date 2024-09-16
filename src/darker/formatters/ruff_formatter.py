"""Re-format Python source code using Ruff.

In examples below, a simple two-line snippet is used.
The first line will be reformatted by Ruff, and the second left intact::

    >>> from pathlib import Path
    >>> from unittest.mock import Mock
    >>> src = Path("dummy/file/path.py")
    >>> src_content = TextDocument.from_lines(
    ...     [
    ...         "for i in range(5): print(i)",
    ...         'print("done")',
    ...     ]
    ... )

First, `RuffFormatter.run` uses Ruff to reformat the contents of a given file.
Reformatted lines are returned e.g.::

    >>> from darker.formatters.ruff_formatter import RuffFormatter
    >>> dst = RuffFormatter().run(src_content)
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
from pathlib import Path
from subprocess import PIPE, run  # nosec
from typing import TYPE_CHECKING, Collection

import toml

from darker.formatters.base_formatter import BaseFormatter, HasConfig
from darker.formatters.formatter_config import (
    BlackCompatibleConfig,
    get_minimum_target_version,
    read_black_compatible_cli_args,
    validate_target_versions,
)
from darkgraylib.config import ConfigurationError
from darkgraylib.utils import TextDocument

if TYPE_CHECKING:
    from argparse import Namespace
    from typing import Pattern

logger = logging.getLogger(__name__)


class RuffFormatter(BaseFormatter, HasConfig[BlackCompatibleConfig]):
    """Ruff code formatter plugin interface."""

    config: BlackCompatibleConfig  # type: ignore[assignment]

    def run(self, content: TextDocument) -> TextDocument:
        """Run the Ruff code re-formatter for the Python source code given as a string.

        :param content: The source code
        :return: The reformatted content

        """
        # Collect relevant Ruff configuration options from ``self.config`` in order to
        # pass them to Ruff's ``format_str()``. File exclusion options aren't needed
        # since at this point we already have a single file's content to work on.
        args = ['--config=lint.ignore=["ISC001"]']
        if "line_length" in self.config:
            args.append(f"--line-length={self.config['line_length']}")
        if "target_version" in self.config:
            supported_target_versions = _get_supported_target_versions()
            target_versions_in = validate_target_versions(
                self.config["target_version"], supported_target_versions
            )
            target_version = get_minimum_target_version(target_versions_in)
            args.append(f"--target-version={target_version}")
        if self.config.get("skip_magic_trailing_comma", False):
            args.append('--config="format.skip-magic-trailing-comma=true"')
            args.append('--config="lint.isort.split-on-trailing-comma=false"')
        if self.config.get("skip_string_normalization", False):
            args.append('''--config=format.quote-style="preserve"''')
        if self.config.get("preview", False):
            args.append("--preview")

        # The custom handling of empty and all-whitespace files below will be
        # unnecessary if https://github.com/psf/ruff/pull/2484 lands in Ruff.
        contents_for_ruff = content.string_with_newline("\n")
        dst_contents = _ruff_format_stdin(contents_for_ruff, args)
        return TextDocument.from_str(
            dst_contents,
            encoding=content.encoding,
            override_newline=content.newline,
        )

    def _read_config_file(self, config_path: str) -> None:
        """Read Ruff configuration from a configuration file."""
        with Path(config_path).open(encoding="utf-8") as config_file:
            raw_config = toml.load(config_file).get("tool", {}).get("ruff", {})
        if "line_length" in raw_config:
            self.config["line_length"] = raw_config["line_length"]

    def _read_cli_args(self, args: Namespace) -> None:
        return read_black_compatible_cli_args(args, self.config)

    def get_config_path(self) -> str | None:
        """Get the path of the configuration file."""
        return self.config.get("config")

    def get_line_length(self) -> int | None:
        """Get the ``line-length`` configuration option value."""
        return self.config.get("line_length")

    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` configuration option value."""
        return self.config.get("exclude", default)

    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` configuration option value."""
        return self.config.get("extend_exclude")

    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` configuration option value."""
        return self.config.get("force_exclude")


def _get_supported_target_versions() -> set[str]:
    """Get the supported target versions for Ruff.

    Calls ``ruff config target-version`` as a subprocess, looks for the line looking
    like ``Type: "py38" | "py39" | "py310"``, and returns the target versions as a set
    of strings.

    """
    cmdline = "ruff config target-version"
    output = run(  # noqa: S603  # nosec
        cmdline.split(), stdout=PIPE, check=True, text=True
    ).stdout
    type_lines = [line for line in output.splitlines() if line.startswith('Type: "py')]
    if not type_lines:
        message = f"`{cmdline}` returned no target versions on a 'Type: \"py...' line"
        raise ConfigurationError(message)
    quoted_targets = type_lines[0][6:].split(" | ")
    if any(tgt_ver[0] != '"' or tgt_ver[-1] != '"' for tgt_ver in quoted_targets):
        message = f"`{cmdline}` returned invalid target versions {type_lines[0]!r}"
        raise ConfigurationError(message)
    return {tgt_ver[1:-1] for tgt_ver in quoted_targets}


def _ruff_format_stdin(contents: str, args: Collection[str]) -> str:
    """Run the contents through ``ruff format``.

    :param contents: The source code to be reformatted
    :param args: Additional command line arguments to pass to Ruff
    :return: The reformatted source code

    """
    cmdline = ["ruff", "format", *args, "-"]
    logger.debug("Running %s", " ".join(cmdline))
    result = run(  # noqa: S603  # nosec
        cmdline, input=contents, stdout=PIPE, check=True, text=True
    )
    return result.stdout