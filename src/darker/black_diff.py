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
import inspect
import logging
import sys
from pathlib import Path
from typing import Collection, Optional, Pattern, Set, Tuple

# `FileMode as Mode` required to satisfy mypy==0.782. Strange.
from black import FileMode as Mode
from black import (
    TargetVersion,
    find_pyproject_toml,
    parse_pyproject_toml,
    re_compile_maybe_verbose,
)
from black.const import DEFAULT_EXCLUDES, DEFAULT_INCLUDES
from black.files import gen_python_files
from black.report import Report
from darker.linewise_black import format_str_to_lines

from darker.utils import TextDocument

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

__all__ = ["BlackConfig", "Mode", "run_black"]

logger = logging.getLogger(__name__)


DEFAULT_EXCLUDE_RE = re_compile_maybe_verbose(DEFAULT_EXCLUDES)
DEFAULT_INCLUDE_RE = re_compile_maybe_verbose(DEFAULT_INCLUDES)


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


def filter_python_files(
    paths: Collection[Path],  # pylint: disable=unsubscriptable-object
    root: Path,
    black_config: BlackConfig,
) -> Set[Path]:
    """Get Python files and explicitly listed files not excluded by Black's config

    :param paths: Relative file/directory paths from CWD to Python sources
    :param root: A common root directory for all ``paths``
    :param black_config: Black configuration which contains the exclude options read
                         from Black's configuration files
    :return: Absolute paths of files which should be reformatted according to
             ``black_config``

    """
    sig = inspect.signature(gen_python_files)
    # those two exist and are required in black>=21.7b1.dev9
    kwargs = dict(verbose=False, quiet=False) if "verbose" in sig.parameters else {}
    absolute_paths = {p.resolve() for p in paths}
    directories = {p for p in absolute_paths if p.is_dir()}
    files = {p for p in absolute_paths if p not in directories}
    files_from_directories = set(
        gen_python_files(
            directories,
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
    return files_from_directories | files


def run_black(src_contents: TextDocument, black_config: BlackConfig) -> TextDocument:
    """Run the black formatter for the Python source code given as a string

    :param src_contents: The source code
    :param black_config: Configuration to use for running Black
    :return: The reformatted content

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

    # The custom handling of empty and all-whitespace files below will be unnecessary if
    # https://github.com/psf/black/pull/2484 lands in Black.
    contents_for_black = src_contents.string_with_newline("\n")
    if contents_for_black.strip():
        dst_lines = format_str_to_lines(contents_for_black, mode=Mode(**mode))
        dst_contents = "".join(dst_lines)
    else:
        dst_contents = "\n" if "\n" in src_contents.string else ""
    return TextDocument.from_str(
        dst_contents,
        encoding=src_contents.encoding,
        override_newline=src_contents.newline,
    )
