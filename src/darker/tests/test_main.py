from pathlib import Path
from subprocess import check_call
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import darker.__main__
import darker.import_sorting
from darker.tests.git_diff_example_output import CHANGE_SECOND_LINE


def test_isort_option_without_isort(tmpdir, without_isort, caplog):
    check_call(["git", "init"], cwd=tmpdir)
    with patch.object(darker.__main__, "SortImports", None), pytest.raises(SystemExit):

        darker.__main__.main(["--isort", str(tmpdir)])

    assert (
        "Please run `pip install 'darker[isort]'` to use the `--isort` option."
        in caplog.text
    )


@pytest.fixture
def run_isort(tmpdir, monkeypatch, caplog):
    monkeypatch.chdir(tmpdir)
    check_call(["git", "init"], cwd=tmpdir)
    with patch.multiple(
        darker.__main__,
        run_black=Mock(return_value=([], [])),
        git_diff_name_only=Mock(return_value=[Path(tmpdir / 'test1.py')]),
    ), patch("darker.import_sorting.SortImports"):
        darker.__main__.main(["--isort", "./test1.py"])
        return SimpleNamespace(
            SortImports=darker.import_sorting.SortImports, caplog=caplog
        )


def test_isort_option_with_isort(run_isort):
    assert "Please run" not in run_isort.caplog.text


def test_isort_option_with_isort_calls_sortimports(run_isort):
    run_isort.SortImports.assert_called_once_with(
        str(Path.cwd() / "test1.py"),
        force_grid_wrap=0,
        include_trailing_comma=True,
        line_length=88,
        multi_line_output=3,
        use_parentheses=True,
    )
