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

    >>> dst = run_black(src, src_content, black_args={})
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
from functools import lru_cache
from pathlib import Path
from typing import Optional, Set, cast

# `FileMode as Mode` required to satisfy mypy==0.782. Strange.
from black import FileMode as Mode
from black import TargetVersion, find_pyproject_toml, format_str, parse_pyproject_toml

from darker.utils import TextDocument

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

__all__ = ["BlackArgs", "Mode", "run_black"]

logger = logging.getLogger(__name__)


class BlackArgs(TypedDict, total=False):
    config: str
    line_length: int
    skip_string_normalization: bool


class BlackModeAttributes(TypedDict, total=False):
    target_versions: Set[TargetVersion]
    line_length: int
    string_normalization: bool
    is_pyi: bool


@lru_cache(maxsize=1)
def read_black_config(src: Path, value: Optional[str]) -> BlackArgs:
    """Read the black configuration from pyproject.toml"""
    value = value or find_pyproject_toml((str(src),))

    if not value:
        return BlackArgs()

    config = parse_pyproject_toml(value)

    return cast(
        BlackArgs,
        {
            key: value
            for key, value in config.items()
            if key in ["line_length", "skip_string_normalization"]
        },
    )


def run_black(
    src: Path, src_contents: TextDocument, black_args: BlackArgs
) -> TextDocument:
    """Run the black formatter for the Python source code given as a string

    Return lines of the original file as well as the formatted content.

    :param src: The originating file path for the source code
    :param src_contents: The source code
    :param black_args: Command-line arguments to send to ``black.FileMode``

    """
    config = black_args.pop("config", None)
    combined_args = read_black_config(src, config)
    combined_args.update(black_args)

    effective_args = BlackModeAttributes()
    if "line_length" in combined_args:
        effective_args["line_length"] = combined_args["line_length"]
    if "skip_string_normalization" in combined_args:
        # The ``black`` command line argument is
        # ``--skip-string-normalization``, but the parameter for
        # ``black.Mode`` needs to be the opposite boolean of
        # ``skip-string-normalization``, hence the inverse boolean
        effective_args["string_normalization"] = not combined_args[
            "skip_string_normalization"
        ]

    # Override defaults and pyproject.toml settings if they've been specified
    # from the command line arguments
    mode = Mode(**effective_args)
    logger.debug(f"black.format_str(")
    logger.debug(f"    <{len(src_contents.string)} characters>,")
    logger.debug(f"    mode={mode}")
    logger.debug(f")")
    return TextDocument.from_str(
        format_str(src_contents.string, mode=mode),
        encoding=src_contents.encoding,
        override_newline=src_contents.newline,
    )
