"""Helper functions for working with files and directories."""

import inspect
from pathlib import Path
from typing import Collection, Optional, Set, Tuple

from black import (
    DEFAULT_EXCLUDES,
    DEFAULT_INCLUDES,
    Report,
    err,
    find_user_pyproject_toml,
    gen_python_files,
    re_compile_maybe_verbose,
)

from darker.formatters.formatter_config import BlackConfig
from darkgraylib.files import find_project_root


def find_pyproject_toml(path_search_start: Tuple[str, ...]) -> Optional[str]:
    """Find the absolute filepath to a pyproject.toml if it exists"""
    path_project_root = find_project_root(path_search_start)
    path_pyproject_toml = path_project_root / "pyproject.toml"
    if path_pyproject_toml.is_file():
        return str(path_pyproject_toml)

    try:
        path_user_pyproject_toml = find_user_pyproject_toml()
        return (
            str(path_user_pyproject_toml)
            if path_user_pyproject_toml.is_file()
            else None
        )
    except (PermissionError, RuntimeError) as e:
        # We do not have access to the user-level config directory, so ignore it.
        err(f"Ignoring user configuration directory due to {e!r}")
        return None


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
    :return: Paths of files which should be reformatted according to
             ``black_config``, relative to ``root``.

    """
    sig = inspect.signature(gen_python_files)
    # those two exist and are required in black>=21.7b1.dev9
    kwargs = {"verbose": False, "quiet": False} if "verbose" in sig.parameters else {}
    # `gitignore=` was replaced with `gitignore_dict=` in black==22.10.1.dev19+gffaaf48
    for param in sig.parameters:
        if param == "gitignore":
            kwargs[param] = None  # type: ignore[assignment]
        elif param == "gitignore_dict":
            kwargs[param] = {}  # type: ignore[assignment]
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
            **kwargs,  # type: ignore[arg-type]
        )
    )
    return {p.resolve().relative_to(root) for p in files_from_directories | files}


DEFAULT_EXCLUDE_RE = re_compile_maybe_verbose(DEFAULT_EXCLUDES)
DEFAULT_INCLUDE_RE = re_compile_maybe_verbose(DEFAULT_INCLUDES)
