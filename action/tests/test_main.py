"""Tests for the GitHub Action ``main.py`` module"""

# pylint: disable=use-dict-literal

from __future__ import annotations

import sys
from contextlib import contextmanager
from runpy import run_module
from subprocess import PIPE, STDOUT, CompletedProcess  # nosec
from types import SimpleNamespace
from typing import TYPE_CHECKING, Generator
from unittest.mock import ANY, Mock, call, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# pylint: disable=redefined-outer-name,unused-argument


BIN = "Scripts" if sys.platform == "win32" else "bin"


class SysExitCalled(Exception):
    """Mock exception to catch a call to `sys.exit`"""


@pytest.fixture
def run_main_env() -> dict[str, str]:
    """By default, call `main.py` with just `GITHUB_ACTION_PATH` in the environment"""
    return {}


@contextmanager
def patch_main(
    tmp_path: Path,
    run_main_env: dict[str, str],
    pip_returncode: int = 0,
) -> Generator[SimpleNamespace]:
    """Patch `subprocess.run`, `sys.exit` and environment variables

    :param tmp_path: Path to use for the `GITHUB_ACTION_PATH` environment variable
    :param run_main_env: Additional environment for running ``main.py``
    :yield: An object with `.subprocess.run` and `.sys.exit` mock objects

    """

    def run(args, **kwargs):
        returncode = pip_returncode if args[1:3] == ["-m", "pip"] else 0
        return CompletedProcess(
            args, returncode, stdout="Output\nfrom\nDarker", stderr=""
        )

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
    tmp_path: Path,
    run_main_env: dict[str, str],
) -> Generator[SimpleNamespace]:
    """`subprocess.run, `sys.exit` and environment variables patching as Pytest fixture

    :param tmp_path: Path to use for the `GITHUB_ACTION_PATH` environment variable
    :param run_main_env: Additional environment for running ``main.py``
    :yield: An object with `.subprocess.run` and `.sys.exit` mock objects

    """
    with patch_main(tmp_path, run_main_env) as run_main_fixture:
        yield run_main_fixture


@pytest.fixture
def github_output(tmp_path: Path) -> Generator[Path]:
    """Fixture to set up a GitHub output file for the action"""
    gh_output_filepath = tmp_path / "github.output"
    with patch.dict("os.environ", {"GITHUB_OUTPUT": str(gh_output_filepath)}):

        yield gh_output_filepath


def test_creates_virtualenv(tmp_path, main_patch, github_output):
    """The GitHub action creates a virtualenv for Darker"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[0] == call(
        [sys.executable, "-m", "venv", str(tmp_path / ".darker-env")],
        check=True,
    )


@pytest.mark.kwparametrize(
    dict(run_main_env={}, expect=["darker[black,color,isort]"]),
    dict(
        run_main_env={"INPUT_VERSION": "1.5.0"},
        expect=["darker[black,color,isort]==1.5.0"],
    ),
    dict(
        run_main_env={"INPUT_VERSION": "@master"},
        expect=[
            "darker[black,color,isort]@git+https://github.com/akaihola/darker@master"
        ],
    ),
    dict(
        run_main_env={"INPUT_LINT": "dummy"},
        expect=["darker[black,color,isort]"],
    ),
    dict(
        run_main_env={"INPUT_LINT": "dummy,foobar"},
        expect=["darker[black,color,isort]"],
    ),
)
def test_installs_packages(tmp_path, main_patch, github_output, run_main_env, expect):
    """Darker, isort and linters are installed in the virtualenv using pip"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[1] == call(
        [
            str(tmp_path / ".darker-env" / BIN / "python"),
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
        env={"INPUT_SRC": ".", "INPUT_LINT": "dummy,foobar"},
        expect=["--revision", "HEAD^", "."],
    ),
    dict(
        env={"INPUT_SRC": ".", "INPUT_LINT": "dummy == 2.13.1,foobar>=3.9.2"},
        expect=["--revision", "HEAD^", "."],
    ),
    dict(
        env={
            "INPUT_SRC": "here.py there/too",
            "INPUT_OPTIONS": "--isort --verbose",
            "INPUT_REVISION": "master...",
            "INPUT_COMMIT_RANGE": "ignored",
            "INPUT_LINT": "dummy,foobar",
        },
        expect=[
            "--isort",
            "--verbose",
            "--revision",
            "master...",
            "here.py",
            "there/too",
        ],
    ),
)
def test_runs_darker(
    tmp_path: Path,
    github_output: Generator[Path],
    env: dict[str, str],
    expect: list[str],
) -> None:
    """Configuration translates correctly into a Darker command line"""
    with patch_main(tmp_path, env) as main_patch, pytest.raises(SysExitCalled):

        run_module("main")

    darker = str(tmp_path / ".darker-env" / BIN / "darker")
    # This gets the first list item of the first positional argument to the `run` call.
    (darker_call,) = (
        c.args[0]
        for c in main_patch.subprocess.run.call_args_list
        if c.args[0][0] == darker
    )
    assert darker_call[1:] == expect


def test_error_if_pip_fails(tmp_path, capsys):
    """Returns an error and the pip error code if pip fails"""
    with patch_main(tmp_path, {}, pip_returncode=42) as main_patch, pytest.raises(
        SysExitCalled
    ):

        run_module("main")

    assert main_patch.subprocess.run.call_args_list[-1] == call(
        [ANY, "-m", "pip", "install", "darker[black,color,isort]"],
        check=False,
        stdout=PIPE,
        stderr=STDOUT,
        encoding="utf-8",
    )
    assert (
        capsys.readouterr().out.splitlines()[-1]
        == "Darker::error::Failed to install darker[black,color,isort]."
    )
    main_patch.sys.exit.assert_called_once_with(42)


def test_exits(main_patch, github_output):
    """A successful run exits with a zero return code"""
    with pytest.raises(SysExitCalled):

        run_module("main")

    main_patch.sys.exit.assert_called_once_with(0)


@pytest.mark.parametrize(
    "expect_line",
    ["exitcode=0", "stdout<<DARKER_ACTION_EOF"],
)
def test_writes_github_output(main_patch, github_output, expect_line):
    """A successful run outputs a zero exit code and output from Darker."""
    with pytest.raises(SysExitCalled):

        run_module("main")

    assert expect_line in github_output.read_text().splitlines()
