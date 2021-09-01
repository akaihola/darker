"""Re-format Python source code using Black

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

    >>> dst = run_black(src_content, black_config={})
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

import logging
import sys
from distutils.version import LooseVersion
from pathlib import Path
from typing import Collection, Optional, Pattern, Set, Tuple

# `FileMode as Mode` required to satisfy mypy==0.782. Strange.
from black import FileMode as Mode
from black import TargetVersion
from black import __version__ as black_version
from black import (
    find_pyproject_toml,
    format_str,
    parse_pyproject_toml,
    re_compile_maybe_verbose,
)
from black.const import DEFAULT_EXCLUDES, DEFAULT_INCLUDES
from black.files import gen_python_files
from black.report import Report

from darker.utils import TextDocument

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

__all__ = ["BlackConfig", "Mode", "run_black"]

logger = logging.getLogger(__name__)


DEFAULT_EXCLUDE_RE = re_compile_maybe_verbose(DEFAULT_EXCLUDES)
DEFAULT_INCLUDE_RE = re_compile_maybe_verbose(DEFAULT_INCLUDES)
BLACK_VERSION = LooseVersion(black_version)


class BlackConfig(TypedDict, total=False):
    """Type definition for Black configuration dictionaries"""
    config: str
    exclude: Pattern[str]
    extend_exclude: Pattern[str]
    force_exclude: Pattern[str]
    line_length: int
    skip_string_normalization: bool
    skip_magic_trailing_comma: bool


class BlackModeAttributes(TypedDict, total=False):
    """Type definition for items accepted by ``black.Mode``"""
    target_versions: Set[TargetVersion]
    line_length: int
    string_normalization: bool
    is_pyi: bool
    magic_trailing_comma: bool


def read_black_config(src: Tuple[str, ...], value: Optional[str]) -> BlackConfig:
    """Read the black configuration from ``pyproject.toml``

    :param src: The source code files and directories to be processed by Darker
    :param value: The path of the Black configuration file
    :return: A dictionary of those Black parameters from the configuration file which
             are supported by Darker

    """
    value = value or find_pyproject_toml(src)

    if not value:
        return BlackConfig()

    raw_config = parse_pyproject_toml(value)

    config: BlackConfig = {}
    for key in {
        "line_length",
        "skip_magic_trailing_comma",
        "skip_string_normalization",
    }:
        if key in raw_config:
            config[key] = raw_config[key]  # type: ignore
    for key in {"exclude", "extend_exclude", "force_exclude"}:
        if key in raw_config:
            config[key] = re_compile_maybe_verbose(raw_config[key])  # type: ignore
    return config


def apply_black_excludes(
    paths: Collection[Path],  # pylint: disable=unsubscriptable-object
    root: Path,
    black_config: BlackConfig,
) -> Set[Path]:
    """Get the subset of files which are not excluded by Black's configuration

    :param paths: Relative paths from ``root`` to Python source file paths to consider
    :param root: A common root directory for all ``paths``
    :param black_config: Black configuration which contains the exclude options read
                         from Black's configuration files
    :return: Absolute paths of files which should be reformatted using Black

    """
    kwargs = (
        {}
        if BLACK_VERSION < LooseVersion("21.8b0")
        else {"quiet": True, "verbose": False}
    )
    return set(
        gen_python_files(
            (root / path for path in paths),
            root,
            include=DEFAULT_INCLUDE_RE,
            exclude=black_config.get("exclude", DEFAULT_EXCLUDE_RE),
            extend_exclude=black_config.get("extend_exclude"),
            force_exclude=black_config.get("force_exclude"),
            report=Report(),
            gitignore=None,
            **kwargs,
        )
    )


def run_black(src_contents: TextDocument, black_config: BlackConfig) -> TextDocument:
    """Run the black formatter for the Python source code given as a string

    Return lines of the original file as well as the formatted content.

    :param src_contents: The source code
    :param black_config: Configuration to use for running Black

    """
    # Collect relevant Black configuration options from ``black_config`` in order to
    # pass them to Black's ``format_str()``. File exclusion options aren't needed since
    # at this point we already have a single file's content to work on.
    mode = BlackModeAttributes()
    if "line_length" in black_config:
        mode["line_length"] = black_config["line_length"]
    if "skip_magic_trailing_comma" in black_config:
        mode["magic_trailing_comma"] = not black_config["skip_magic_trailing_comma"]
    if "skip_string_normalization" in black_config:
        # The ``black`` command line argument is
        # ``--skip-string-normalization``, but the parameter for
        # ``black.Mode`` needs to be the opposite boolean of
        # ``skip-string-normalization``, hence the inverse boolean
        mode["string_normalization"] = not black_config["skip_string_normalization"]

    contents_for_black = src_contents.string_with_newline("\n")
    return TextDocument.from_str(
        format_str(contents_for_black, mode=Mode(**mode)),
        encoding=src_contents.encoding,
        override_newline=src_contents.newline,
    )
