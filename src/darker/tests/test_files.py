"""Test for the `darker.files` module."""

import io
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, patch

from darker import files


@patch("darker.files.find_user_pyproject_toml")
def test_find_pyproject_toml(find_user_pyproject_toml: MagicMock) -> None:
    """Test `files.find_pyproject_toml` with no user home directory."""
    find_user_pyproject_toml.side_effect = RuntimeError()
    with redirect_stderr(io.StringIO()) as stderr:
        # end of test setup

        result = files.find_pyproject_toml(path_search_start=(str(Path.cwd().root),))

    assert result is None
    err = stderr.getvalue()
    assert "Ignoring user configuration" in err
