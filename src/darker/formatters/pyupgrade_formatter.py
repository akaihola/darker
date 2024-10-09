"""Re-format Python source code using Pyupgrade.

In examples below, a simple two-line snippet is used.
Everything will upgraded by Pyupgrade to newer Python syntax, except the last line::

    >>> from pathlib import Path
    >>> from unittest.mock import Mock
    >>> src = Path("dummy/file/path.py")
    >>> src_content = TextDocument.from_lines(
    ...     [
    ...         "from typing import List",
    ...         "ls: List[int] = [42]",
    ...         "print('success!')"
    ...     ]
    ... )

First, `PyupgradeFormatter.run` uses Pyupgrade to upgrade the contents of a given file.
All lines are returned e.g.::

    >>> from darker.formatters.pyupgrade_formatter import PyupgradeFormatter
    >>> dst = PyupgradeFormatter().run(src_content, src)
    >>> dst.lines
    ('from typing import List', 'ls: list[int] = [42]', "print('success!')")

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

import io
import logging
import sys
from pathlib import Path
from subprocess import PIPE, run  # nosec
from typing import TYPE_CHECKING, Collection

from pyupgrade import _main
from pyupgrade._data import Settings
from pyupgrade._main import _fix_plugins, _fix_tokens

from darker.formatters.base_formatter import BaseFormatter, HasConfig
from darker.formatters.pyupgrade_config import (
    PyupgradeConfig,
)

from darker.formatters.formatter_config import validate_target_versions
from darkgraylib.config import ConfigurationError
from darkgraylib.utils import TextDocument

if TYPE_CHECKING:
    from argparse import Namespace
    from typing import Pattern

logger = logging.getLogger(__name__)


class PyupgradeFormatter(BaseFormatter, HasConfig[PyupgradeConfig]):
    """Pyupgrade code formatter plugin interface."""

    config: PyupgradeConfig  # type: ignore[assignment]

    def run(self, content: TextDocument, path_from_cwd: Path) -> TextDocument:
        """Run the Pyupgrade code upgrader for the Python source code given as a string.

        :param content: The source code
        :param path_from_cwd: The path to the file being upgraded, either absolute or
                              relative to the current working directory
        :return: The upgraded content

        """
        # Collect relevant Pyupgrade configuration options from ``self.config`` in order
        # to pass them to Pyupgrade.
        if "target_version" in self.config:
            supported_target_versions = _get_supported_target_versions()
            target_versions_in = validate_target_versions(
                self.config["target_version"], supported_target_versions
            )
            target_version_str = min(target_versions_in)
            target_version = (int(target_version_str[0]), int(target_version_str[1:]))
        else:
            target_version = (3, 9)

        contents_for_pyupgrade = content.string_with_newline("\n")
        dst_contents = _pyupgrade_format_stdin(contents_for_pyupgrade, target_version)
        return TextDocument.from_str(
            dst_contents,
            encoding=content.encoding,
            override_newline=content.newline,
        )

    def _read_cli_args(self, args: Namespace) -> None:
        if getattr(args, "target_version", None):
            self.config["target_version"] = {args.target_version}


def _get_supported_target_versions() -> set[tuple[int, int]]:
    """Get the supported target versions for Pyupgrade.

    Calls ``pyupgrade --help`` as a subprocess, looks for lines looking like
    ``  --py???-plus``, and returns the target versions as a set of int-tuples.

    """
    stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        _main(["--help"])
    finally:
        sys.stdout = stdout
    version_strs = (
        line[6:-5]
        for line in buf.getvalue().splitlines()
        if line.startswith("  --py") and line.endswith("-plus")
    )
    return {(int(v[0]), int(v[1:])) for v in version_strs}


def _pyupgrade_format_stdin(contents: str, min_version: tuple[int, int]) -> str:
    """Run the contents through ``pyupgrade format``.

    :param contents: The source code to be reformatted
    :param min_version: The minimum Python version to target
    :return: The reformatted source code

    """
    return _fix_tokens(
        _fix_plugins(contents, settings=Settings(min_version=min_version))
    )
