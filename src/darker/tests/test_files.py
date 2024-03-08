import io
from contextlib import redirect_stderr
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from darker import files


class BlackTestCase(TestCase):
    @patch("darker.files.find_user_pyproject_toml")
    def test_find_pyproject_toml(self, find_user_pyproject_toml: MagicMock) -> None:
        find_user_pyproject_toml.side_effect = RuntimeError()

        with redirect_stderr(io.StringIO()) as stderr:
            result = files.find_pyproject_toml(
                path_search_start=(str(Path.cwd().root),)
            )

        assert result is None
        err = stderr.getvalue()
        assert "Ignoring user configuration" in err
