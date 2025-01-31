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
    >>> dst = RuffFormatter().run(src_content, src)
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
import sys
from pathlib import Path
from subprocess import PIPE, SubprocessError, run  # nosec
from typing import TYPE_CHECKING, Collection

from darker.formatters.base_formatter import BaseFormatter, HasConfig
from darker.formatters.formatter_config import (
    BlackCompatibleConfig,
    read_black_compatible_cli_args,
    validate_target_versions,
)
from darkgraylib.config import ConfigurationError
from darkgraylib.utils import TextDocument

if sys.version_info >= (3, 11):
    # On Python 3.11+, we can use the `tomllib` module from the standard library.
    try:
        import tomllib
    except ImportError:
        # Help users on older Python 3.11 alphas
        import tomli as tomllib  # type: ignore[no-redef,import-not-found]
else:
    # On older Pythons, we must use the backport.
    import tomli as tomllib

if TYPE_CHECKING:
    from argparse import Namespace
    from re import Pattern

logger = logging.getLogger(__name__)


class RuffFormatter(BaseFormatter, HasConfig[BlackCompatibleConfig]):
    """Ruff code formatter plugin interface."""

    config: BlackCompatibleConfig  # type: ignore[assignment]

    name = "ruff format"
    config_section = "tool.ruff"
    preserves_ast = True

    def run(self, content: TextDocument, path_from_cwd: Path) -> TextDocument:
        """Run the Ruff code re-formatter for the Python source code given as a string.

        :param content: The source code
        :param path_from_cwd: The path to the file being reformatted, either absolute or
                              relative to the current working directory
        :return: The reformatted content

        """
        # Collect relevant Ruff configuration options from ``self.config`` in order to
        # pass them to Ruff's ``format_str()``. File exclusion options aren't needed
        # since at this point we already have a single file's content to work on.
        # Ignore ISC001 (single-line-implicit-string-concatenation) since it conflicts
        # with Black's string formatting
        args = ['--config=lint.ignore=["ISC001"]']
        if "line_length" in self.config:
            args.append(f"--line-length={self.config['line_length']}")
        if "target_version" in self.config:
            supported_target_versions = _get_supported_target_versions()
            target_versions_in = validate_target_versions(
                self.config["target_version"], supported_target_versions
            )
            target_version_str = supported_target_versions[min(target_versions_in)]
            args.append(f"--target-version={target_version_str}")
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
        dst_contents = _ruff_format_stdin(contents_for_ruff, path_from_cwd, args)
        return TextDocument.from_str(
            dst_contents,
            encoding=content.encoding,
            override_newline=content.newline,
        )

    def _read_config_file(self, config_path: str) -> None:
        """Read Ruff configuration from a configuration file.

        :param config_path: Path to the configuration file
        :raises ConfigurationError: If the configuration file cannot be read or parsed

        """
        try:
            with Path(config_path).open(mode="rb") as config_file:
                raw_config = tomllib.load(config_file).get("tool", {}).get("ruff", {})
            if "line-length" in raw_config:
                self.config["line_length"] = int(raw_config["line-length"])
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            message = f"Failed to read Ruff config: {exc}"
            raise ConfigurationError(message) from exc

    def _read_cli_args(self, args: Namespace) -> None:
        return read_black_compatible_cli_args(args, self.config)

    def get_config_path(self) -> str | None:
        """Get the path of the configuration file."""
        return self.config.get("config")

    # pylint: disable=duplicate-code
    def get_line_length(self) -> int | None:
        """Get the ``line-length`` Ruff configuration option value."""
        return self.config.get("line_length")

    # pylint: disable=duplicate-code
    def get_exclude(self, default: Pattern[str]) -> Pattern[str]:
        """Get the ``exclude`` Ruff configuration option value."""
        return self.config.get("exclude", default)

    # pylint: disable=duplicate-code
    def get_extend_exclude(self) -> Pattern[str] | None:
        """Get the ``extend_exclude`` Ruff configuration option value."""
        return self.config.get("extend_exclude")

    # pylint: disable=duplicate-code
    def get_force_exclude(self) -> Pattern[str] | None:
        """Get the ``force_exclude`` Ruff configuration option value."""
        return self.config.get("force_exclude")


TYPE_PREFIX = 'Type: "'
VER_PREFIX = "py"


def _get_supported_target_versions() -> dict[tuple[int, int], str]:
    """Get the supported target versions for Ruff.

    Calls ``ruff config target-version`` as a subprocess, looks for the line looking
    like ``Type: "py38" | "py39" | "py310"``, and returns the target versions as a dict
    of int-tuples mapped to version strings.

    :returns: A dictionary mapping Python version tuples to their string
              representations. For example: ``{(3, 8): "py38", (3, 9): "py39"}``
    :raises ConfigurationError: If target versions cannot be determined from Ruff output
    """
    try:
        cmdline = "ruff config target-version"
        output = run(  # noqa: S603  # nosec
            cmdline.split(), stdout=PIPE, check=True, text=True
        ).stdout.splitlines()
        # Find a line like: Type: "py37" | "py38" | "py39" | "py310" | "py311" | "py312"
        type_lines = [
            line
            for line in output
            if line.startswith(TYPE_PREFIX + VER_PREFIX) and line.endswith('"')
        ]
        if not type_lines:
            message = (
                f"`{cmdline}` returned no target versions on a"
                f" '{TYPE_PREFIX}{VER_PREFIX}...' line"
            )
            raise ConfigurationError(message)
        # Drop 'Type:' prefix and the initial and final double quotes
        delimited_versions = type_lines[0][len(TYPE_PREFIX) : -len('"')]
        # Now we have: py37" | "py38" | "py39" | "py310" | "py311" | "py312
        # Split it by '" | "' (turn strs to lists since Mypy disallows str unpacking)
        py_versions = [
            list(py_version) for py_version in delimited_versions.split('" | "')
        ]
        # Now we have: [("p", "y", "3", "7"), ("p", "y", "3", "8"), ...]
        # Turn it into {(3, 7): "py37", (3, 8): "py38", (3, 9): "py39", ...}
        return {
            (int(major), int("".join(minor))): f"{VER_PREFIX}{major}{''.join(minor)}"
            for _p, _y, major, *minor in py_versions
        }

    except (OSError, ValueError, SubprocessError) as exc:
        message = f"Failed to get Ruff target versions: {exc}"
        raise ConfigurationError(message) from exc


def _ruff_format_stdin(
    contents: str, path_from_cwd: Path, args: Collection[str]
) -> str:
    """Run the contents through ``ruff format``.

    :param contents: The source code to be reformatted
    :param path_from_cwd: The path to the file being reformatted, either absolute or
                          relative to the current working directory
    :param args: Additional command line arguments to pass to Ruff
    :return: The reformatted source code

    """
    cmdline = [
        "ruff",
        "format",
        "--force-exclude",  # apply `exclude =` from conffile even with stdin
        f"--stdin-filename={path_from_cwd}",  # allow to match exclude patterns
        *args,
        "-",
    ]
    logger.debug("Running %s", " ".join(cmdline))
    result = run(  # noqa: S603  # nosec
        cmdline, input=contents, stdout=PIPE, check=True, text=True, encoding="utf-8"
    )
    return result.stdout
