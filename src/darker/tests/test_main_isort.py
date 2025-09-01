"""Tests for the ``--isort`` option of the ``darker`` command-line interface."""

# pylint: disable=no-member,redefined-outer-name,unused-argument,use-dict-literal

from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import darker.__main__
import darker.import_sorting
from darker.exceptions import MissingPackageError
from darker.formatters import black_formatter
from darker.tests.helpers import isort_present
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.utils import TextDocument

# Need to clear Black's `find_project_root` cache between tests
pytestmark = pytest.mark.usefixtures("find_project_root_cache_clear")


@pytest.fixture(scope="module")
def isort_repo(request, tmp_path_factory):
    """Git repository fixture for `test_isort_option_with_isort*`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        paths = repo.add({"test1.py": "original"}, commit="Initial commit")
        paths["test1.py"].write_bytes(b"changed")
        yield repo


def test_isort_option_without_isort(isort_repo):
    """Without isort, provide isort install instructions and error."""
    # The `git_repo` fixture ensures test is not run in the Darker repository clone in
    # CI builds. It helps avoid a NixOS test issue.
    with isort_present(present=False), patch.object(
        darker.__main__,
        "isort",
        None,
    ), pytest.raises(MissingPackageError) as exc_info:

        darker.__main__.main(["--isort", "."])

    assert (
        str(exc_info.value)
        == "Please run `pip install darker[isort]` to use the `--isort` option."
    )


@pytest.fixture()
def run_isort(isort_repo, make_temp_copy, monkeypatch, caplog, request):
    """Fixture for running Darker with requested arguments and a patched `isort`.

    Provides an `run_isort.isort_code` mock object which allows checking whether and how
    the `isort.code()` function was called.

    """
    with make_temp_copy(isort_repo.root) as root:
        monkeypatch.chdir(root)
        args = getattr(request, "param", ())
        isorted_code = "import os; import sys;"
        blacken_code = "import os\nimport sys\n"
        patch_run_black_ctx = patch.object(
            black_formatter.BlackFormatter,
            "run",
            return_value=TextDocument(blacken_code),
        )
        with patch_run_black_ctx, patch(
            "darker.import_sorting.isort_code"
        ) as isort_code:
            isort_code.return_value = isorted_code
            darker.__main__.main(["--isort", "./test1.py", *args])
            return SimpleNamespace(
                isort_code=isort_code,
                caplog=caplog,
                root=root,
            )


def test_isort_option_with_isort(run_isort):
    """Doesn't prompt to install ``isort`` if it's already installed."""
    assert "Please run" not in run_isort.caplog.text


@pytest.mark.kwparametrize(
    dict(run_isort=(), isort_args={}),
    dict(run_isort=("--line-length", "120"), isort_args={"line_length": 120}),
    indirect=["run_isort"],
)
def test_isort_option_with_isort_calls_sortimports(run_isort, isort_args):
    """Relevant config options are passed from command line to ``isort``."""
    run_isort.isort_code.assert_called_once_with(
        code="changed",
        file_path=run_isort.root / "test1.py",
        settings_path=str(run_isort.root),
        **isort_args,
    )


def test_isort_respects_skip_glob(tmp_path):
    """Test that Darker respects isort's skip_glob setting."""
    # Create a pyproject.toml file with isort skip_glob configuration
    configuration = dedent(
        """
        [tool.isort]
        skip_glob = ['*/conf/settings/*']
        filter_files = true
        """
    )
    (tmp_path / "pyproject.toml").write_text(configuration)
    # Create a file that should be skipped
    settings_dir = tmp_path / "conf" / "settings"
    settings_dir.mkdir(parents=True)
    backoffice_py = settings_dir / "backoffice.py"
    backoffice_py.write_text("import sys\nimport os\n")

    # Run darker with --isort
    darker.__main__.main(["--isort", str(settings_dir / "backoffice.py")])

    assert backoffice_py.read_text() == "import sys\nimport os\n"
