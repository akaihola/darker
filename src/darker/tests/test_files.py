"""Test for the `darker.files` module."""

# pylint: disable=use-dict-literal

from pathlib import Path

import pytest

from darker import files


@pytest.mark.kwparametrize(
    dict(start="only_pyproject/subdir", expect="only_pyproject/pyproject.toml"),
    dict(start="only_git/subdir", expect=None),
    dict(start="git_and_pyproject/subdir", expect="git_and_pyproject/pyproject.toml"),
)
def test_find_pyproject_toml(tmp_path: Path, start: str, expect: str) -> None:
    """Test `files.find_pyproject_toml` with no user home directory."""
    (tmp_path / "only_pyproject").mkdir()
    (tmp_path / "only_pyproject" / "pyproject.toml").touch()
    (tmp_path / "only_pyproject" / "subdir").mkdir()
    (tmp_path / "only_git").mkdir()
    (tmp_path / "only_git" / ".git").mkdir()
    (tmp_path / "only_git" / "subdir").mkdir()
    (tmp_path / "git_and_pyproject").mkdir()
    (tmp_path / "git_and_pyproject" / ".git").mkdir()
    (tmp_path / "git_and_pyproject" / "pyproject.toml").touch()
    (tmp_path / "git_and_pyproject" / "subdir").mkdir()

    result = files.find_pyproject_toml(path_search_start=(str(tmp_path / start),))

    if not expect:
        assert result is None
    else:
        assert result == str(tmp_path / expect)
