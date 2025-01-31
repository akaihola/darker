"""Helper functions for working with files and directories."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING, Collection, Iterable, Iterator

from darkgraylib.files import find_project_root

if TYPE_CHECKING:
    from pathlib import Path

    from darker.formatters.base_formatter import BaseFormatter


def find_pyproject_toml(path_search_start: tuple[str, ...]) -> str | None:
    """Find the absolute filepath to a pyproject.toml if it exists"""

    path_project_root = find_project_root(path_search_start)
    path_pyproject_toml = path_project_root / "pyproject.toml"
    if path_pyproject_toml.is_file():
        return str(path_pyproject_toml)
    return None


DEFAULT_EXCLUDE_RE = re.compile(
    r"/(\.direnv"
    r"|\.eggs"
    r"|\.git"
    r"|\.hg"
    r"|\.ipynb_checkpoints"
    r"|\.mypy_cache"
    r"|\.nox"
    r"|\.pytest_cache"
    r"|\.ruff_cache"
    r"|\.tox"
    r"|\.svn"
    r"|\.venv"
    r"|\.vscode"
    r"|__pypackages__"
    r"|_build"
    r"|buck-out"
    r"|build"
    r"|dist"
    r"|venv)/"
)
DEFAULT_INCLUDE_RE = re.compile(r"(\.pyi?|\.ipynb)$")


@lru_cache
def _cached_resolve(path: Path) -> Path:
    return path.resolve()


def _resolves_outside_root_or_cannot_stat(path: Path, root: Path) -> bool:
    """Return whether path is a symlink that points outside the root directory.

    Also returns True if we failed to resolve the path.

    This function has been adapted from Black 24.10.0.

    """
    try:
        resolved_path = _cached_resolve(path)
    except OSError:
        return True
    try:
        resolved_path.relative_to(root)
    except ValueError:
        return True
    return False


def _path_is_excluded(
    normalized_path: str,
    pattern: re.Pattern[str] | None,
) -> bool:
    """Return whether the path is excluded by the pattern.

    This function has been adapted from Black 24.10.0.

    """
    match = pattern.search(normalized_path) if pattern else None
    return bool(match and match.group(0))


def _gen_python_files(
    paths: Iterable[Path],
    root: Path,
    exclude: re.Pattern[str],
    extend_exclude: re.Pattern[str] | None,
    force_exclude: re.Pattern[str] | None,
) -> Iterator[Path]:
    """Generate all files under ``path`` whose paths are not excluded.

    This function has been adapted from Black 24.10.0.

    """
    if not root.is_absolute():
        message = f"`root` must be absolute, not {root}"
        raise ValueError(message)
    for child in paths:
        if not child.is_absolute():
            message = f"`child` must be absolute, not {child}"
            raise ValueError(message)
        root_relative_path = child.relative_to(root).as_posix()

        # Then ignore with `--exclude` `--extend-exclude` and `--force-exclude` options.
        root_relative_path = f"/{root_relative_path}"
        if child.is_dir():
            root_relative_path = f"{root_relative_path}/"

        if any(
            _path_is_excluded(root_relative_path, x)
            for x in [exclude, extend_exclude, force_exclude]
        ) or _resolves_outside_root_or_cannot_stat(child, root):
            continue

        if child.is_dir():
            yield from _gen_python_files(
                child.iterdir(), root, exclude, extend_exclude, force_exclude
            )

        elif child.is_file():
            include_match = DEFAULT_INCLUDE_RE.search(root_relative_path)
            if include_match:
                yield child


def filter_python_files(
    paths: Collection[Path],  # pylint: disable=unsubscriptable-object
    root: Path,
    formatter: BaseFormatter,
) -> set[Path]:
    """Get Python files and explicitly listed files not excluded by Black's config.

    :param paths: Relative file/directory paths from CWD to Python sources
    :param root: A common root directory for all ``paths``
    :param formatter: The code re-formatter which provides the configuration containing
                      the exclude options
    :return: Paths of files which should be reformatted according to
             ``black_config``, relative to ``root``.

    """
    # Split input paths into directories (which need recursion) and direct files
    directories, files = set(), set()
    for p in paths:
        # Convert all input paths to absolute paths for consistent handling
        path = p.resolve()
        if path.is_dir():
            directories.add(path)
        else:
            files.add(path)

    # Recursively walk directories to find Python files, applying exclusion patterns.
    # Get all Python files from directories that match our criteria:
    # - Pass formatter's exclude/extend-exclude/force-exclude patterns
    # - Match Python file extensions (.py, .pyi, .ipynb)
    # - Aren't symlinks pointing outside the root
    files_from_directories = set(
        _gen_python_files(
            directories,
            root,
            formatter.get_exclude(DEFAULT_EXCLUDE_RE),
            formatter.get_extend_exclude(),
            formatter.get_force_exclude(),
        )
    )

    # Combine directly specified files with those found in directories.
    # Convert all paths to be relative to the root directory.
    return {p.resolve().relative_to(root) for p in files_from_directories | files}
