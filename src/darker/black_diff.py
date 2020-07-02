"""Re-format Python source code using Black

In examples below, a simple two-line snippet is used.
The first line will be reformatted by Black, and the second left intact::

    >>> from unittest.mock import Mock
    >>> src = Mock()
    >>> src_content = '''\\
    ... for i in range(5): print(i)
    ... print("done")
    ... '''

First, :func:`run_black` uses Black to reformat the contents of a given file.
Reformatted lines are returned e.g.::

    >>> dst_lines = run_black(src, src_content, black_args={})
    >>> dst_lines
    ['for i in range(5):',
     '    print(i)',
     'print("done")']

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
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, cast

from black import FileMode, format_str, read_pyproject_toml
from click import Command, Context, Option

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def read_black_config(src: Path, value: Optional[str]) -> Dict[str, Union[bool, int]]:
    """Read the black configuration from pyproject.toml"""
    command = Command("main")

    context = Context(command)
    context.params["src"] = (str(src),)

    parameter = Option(["--config"])

    read_pyproject_toml(context, parameter, value)

    return {
        key: value
        for key, value in (context.default_map or {}).items()
        if key in ["line_length", "skip_string_normalization"]
    }


def run_black(
    src: Path, src_contents: str, black_args: Dict[str, Union[bool, int, str]]
) -> List[str]:
    """Run the black formatter for the Python source code given as a string

    Return lines of the original file as well as the formatted content.

    :param src: The originating file path for the source code
    :param src_contents: The source code as a string
    :param black_args: Command-line arguments to send to ``black.FileMode``

    """
    config = black_args.pop("config", None)
    defaults = read_black_config(src, config)
    args = cast(Dict[str, Union[bool, int]], black_args)
    combined_args = {**defaults, **args}

    effective_args = {}
    if "line_length" in combined_args:
        effective_args["line_length"] = combined_args["line_length"]
    if "skip_string_normalization" in combined_args:
        # The ``black`` command line argument is
        # ``--skip-string-normalization``, but the parameter for
        # ``black.FileMode`` needs to be the opposite boolean of
        # ``skip-string-normalization``, hence the inverse boolean
        effective_args["string_normalization"] = not combined_args[
            "skip_string_normalization"
        ]

    # Override defaults and pyproject.toml settings if they've been specified
    # from the command line arguments
    mode = FileMode(**effective_args)

    dst_contents = format_str(src_contents, mode=mode)
    dst_lines: List[str] = dst_contents.splitlines()
    return dst_lines
