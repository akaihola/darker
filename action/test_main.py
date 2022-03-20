import re
import sys
from contextlib import contextmanager
from pathlib import Path
from runpy import run_module
from subprocess import PIPE, STDOUT, CompletedProcess
from types import SimpleNamespace
from typing import Dict, Generator
from unittest.mock import ANY, Mock, call, patch

import pytest

# pylint: disable=redefined-outer-name,unused-argument


class SysExitCalled(Exception):
    """Mock exception to catch a call to `sys.exit`"""


@pytest.fixture
def run_main_env() -> Dict[str, str]:
    """By default, call `main.py` with just `GITHUB_ACTION_PATH` in the environment"""
    return {}


@contextmanager
def patch_main(
    tmp_path: Path,
    run_main_env: Dict[str, str],
    pip_returncode: int = 0,
) -> Generator[SimpleNamespace, None, None]:
    """Patch `subprocess.run`, `sys.exit` and environment variables

    :param tmp_path: Path to use for the `GITHUB_ACTION_PATH` environment variable
    :param run_main_env: [description]
    :yield: An object with `.subprocess.run` and `.sys.exit` mock objects

    """

    def run(args, **kwargs):
        returncode = pip_returncode if args[1:3] == ["-m", "pip"] else 0
        return CompletedProcess(args, returncode, stdout="", stderr="")

    run_mock = Mock(wraps=run)
    exit_ = Mock(side_effect=SysExitCalled)
    with patch("subprocess.run", run_mock), patch("sys.exit", exit_), patch.dict(
        "os.environ", {"GITHUB_ACTION_PATH": str(tmp_path), **run_main_env}
    ):

        yield SimpleNamespace(
            subprocess=SimpleNamespace(run=run_mock), sys=SimpleNamespace(exit=exit_)
        )


@pytest.fixture
def main_patch(
    tmp_path: Path, run_main_env: Dict[str, str]
) -> Generator[SimpleNamespace, None, None]:
    with patch_main(tmp_path, run_main_env) as run_main_fixture:
        yield run_main_fixture


def test_creates_virtualenv(tmp_path, main_patch):
    """The GitHub action creates a virtualenv for Darker"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[0] == call(
        [sys.executable, "-m", "venv", str(tmp_path / ".darker-env")],
        check=True,
    )


@pytest.mark.kwparametrize(
    dict(run_main_env={}, expect=["darker[isort]"]),
    dict(run_main_env={"INPUT_VERSION": "1.5.0"}, expect=["darker[isort]==1.5.0"]),
    dict(
        run_main_env={"INPUT_LINT": "pylint"},
        expect=["darker[isort]", "pylint"],
    ),
    dict(
        run_main_env={"INPUT_LINT": "pylint,flake8"},
        expect=["darker[isort]", "pylint", "flake8"],
    ),
    dict(
        run_main_env={"INPUT_LINT": "  flake8  "},
        expect=["darker[isort]", "flake8"],
    ),
    dict(
        run_main_env={"INPUT_LINT": "  flake8  ,  pylint  "},
        expect=["darker[isort]", "flake8", "pylint"],
    ),
)
def test_installs_packages(tmp_path, main_patch, run_main_env, expect):
    """Darker, isort and linters are installed in the virtualenv using pip"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[1] == call(
        [
            str(tmp_path / ".darker-env" / "bin" / "python"),
            "-m",
            "pip",
            "install",
        ]
        + expect,
        check=False,
        stdout=PIPE,
        stderr=STDOUT,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "linters", ["foo", "  foo  ", "foo,bar", "  foo  ,  bar  ", "pylint,foo"]
)
def test_wont_install_unknown_packages(tmp_path, linters):
    """Non-whitelisted linters raise an exception"""
    with patch_main(tmp_path, {"INPUT_LINT": linters}) as main_patch, pytest.raises(
        RuntimeError,
        match=re.escape("'foo' is not supported as a linter by the GitHub Action"),
    ):

        run_module("main")

    # only virtualenv `run` called, `pip` and `darker` not called
    (venv_create,) = main_patch.subprocess.run.call_args_list
    assert venv_create == call([ANY, "-m", "venv", ANY], check=True)
    assert not main_patch.sys.exit.called


@pytest.mark.kwparametrize(
    dict(env={"INPUT_SRC": "."}, expect=["--revision", "HEAD^", "."]),
    dict(
        env={"INPUT_SRC": "subdir/ myfile.py"},
        expect=["--revision", "HEAD^", "subdir/", "myfile.py"],
    ),
    dict(
        env={"INPUT_SRC": ".", "INPUT_OPTIONS": "--isort"},
        expect=["--isort", "--revision", "HEAD^", "."],
    ),
    dict(
        env={"INPUT_SRC": ".", "INPUT_REVISION": "master..."},
        expect=["--revision", "master...", "."],
    ),
    dict(
        env={"INPUT_SRC": ".", "INPUT_COMMIT_RANGE": "master..."},
        expect=["--revision", "master...", "."],
    ),
    dict(
        env={
            "INPUT_SRC": ".",
            "INPUT_REVISION": "master...",
            "INPUT_COMMIT_RANGE": "ignored",
        },
        expect=["--revision", "master...", "."],
    ),
    dict(
        env={"INPUT_SRC": ".", "INPUT_LINT": "pylint,flake8"},
        expect=["--lint", "pylint", "--lint", "flake8", "--revision", "HEAD^", "."],
    ),
    dict(
        env={
            "INPUT_SRC": "here.py there/too",
            "INPUT_OPTIONS": "--isort --verbose",
            "INPUT_REVISION": "master...",
            "INPUT_COMMIT_RANGE": "ignored",
            "INPUT_LINT": "pylint,flake8",
        },
        expect=[
            "--isort",
            "--verbose",
            "--lint",
            "pylint",
            "--lint",
            "flake8",
            "--revision",
            "master...",
            "here.py",
            "there/too",
        ],
    ),
)
def test_runs_darker(tmp_path, env, expect):
    """Configuration translates correctly into a Darker command line"""
    with patch_main(tmp_path, env) as main_patch, pytest.raises(SysExitCalled):

        run_module("main")

    darker = str(tmp_path / ".darker-env" / "bin" / "darker")
    assert darker in [c.args[0][0] for c in main_patch.subprocess.run.call_args_list]


def test_error_if_pip_fails(tmp_path, capsys):
    """Returns an error and the pip error code if pip fails"""
    with patch_main(tmp_path, {}, pip_returncode=42) as main_patch, pytest.raises(
        SysExitCalled
    ):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[-1] == call(
        [ANY, "-m", "pip", "install", "darker[isort]"],
        check=False,
        stdout=PIPE,
        stderr=STDOUT,
        encoding="utf-8",
    )
    assert (
        capsys.readouterr().out.splitlines()[-1]
        == "::error::Failed to install darker[isort]."
    )
    main_patch.sys.exit.assert_called_once_with(42)


def test_exits(main_patch):
    """A successful run exits with a zero return code"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    main_patch.sys.exit.assert_called_once_with(0)
