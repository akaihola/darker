"""Helper functions for working with files and directories."""

from typing import Optional, Tuple

from black import err, find_user_pyproject_toml

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
