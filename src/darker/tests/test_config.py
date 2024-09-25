"""Tests for `darker.config`"""

# pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
# pylint: disable=use-dict-literal

from argparse import Namespace
from pathlib import Path

import pytest

from darker.config import OutputMode
from darkgraylib.config import ConfigurationError
from darkgraylib.testtools.helpers import raises_if_exception


@pytest.mark.kwparametrize(
    dict(diff=False, stdout=False, expect=None),
    dict(diff=False, stdout=True, expect=None),
    dict(diff=True, stdout=False, expect=None),
    dict(diff=True, stdout=True, expect=ConfigurationError),
)
def test_output_mode_validate_diff_stdout(diff, stdout, expect):
    """Validation fails only if ``--diff`` and ``--stdout`` are both enabled"""
    with raises_if_exception(expect):
        OutputMode.validate_diff_stdout(diff, stdout)


@pytest.mark.kwparametrize(
    dict(stdout=False),
    dict(stdout=False, src=["first.py"]),
    dict(stdout=False, src=["first.py", "second.py"]),
    dict(stdout=False, src=["first.py", "missing.py"]),
    dict(stdout=False, src=["missing.py"]),
    dict(stdout=False, src=["missing.py", "another_missing.py"]),
    dict(stdout=False, src=["directory"]),
    dict(stdout=True, expect=ConfigurationError),  # input file missing
    dict(stdout=True, src=["first.py"]),
    dict(  # too many input files
        stdout=True, src=["first.py", "second.py"], expect=ConfigurationError
    ),
    dict(  # too many input files (even if all but one missing)
        stdout=True, src=["first.py", "missing.py"], expect=ConfigurationError
    ),
    dict(  # input file doesn't exist
        stdout=True, src=["missing.py"], expect=ConfigurationError
    ),
    dict(  # too many input files (even if all but one missing)
        stdout=True, src=["missing.py", "another.py"], expect=ConfigurationError
    ),
    dict(  # input file required, not a directory
        stdout=True, src=["directory"], expect=ConfigurationError
    ),
    dict(stdout=False, stdin_filename="path.py"),
    dict(stdout=False, src=["first.py"], stdin_filename="path.py"),
    dict(stdout=False, src=["first.py", "second.py"], stdin_filename="path.py"),
    dict(stdout=False, src=["first.py", "missing.py"], stdin_filename="path.py"),
    dict(stdout=False, src=["missing.py"], stdin_filename="path.py"),
    dict(
        stdout=False, src=["missing.py", "another_missing.py"], stdin_filename="path.py"
    ),
    dict(stdout=False, src=["directory"], stdin_filename="path.py"),
    dict(stdout=True, stdin_filename="path.py"),
    dict(  # too many input files, here from two different command line arguments
        stdout=True,
        src=["first.py"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    dict(  # too many input files, here from two different command line arguments
        stdout=True,
        src=["first.py", "second.py"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    dict(  # too many input files, here from two different command line arguments
        stdout=True,
        src=["first.py", "missing.py"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    dict(  # too many input files (even if positional file is missing)
        stdout=True,
        src=["missing.py"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    dict(  # too many input files, here from two different command line arguments
        stdout=True,
        src=["missing.py", "another.py"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    dict(  # too many input files, here from two different command line arguments
        stdout=True,
        src=["directory"],
        stdin_filename="path.py",
        expect=ConfigurationError,
    ),
    src=[],
    stdin_filename=None,
    expect=None,
)
def test_output_mode_validate_stdout_src(
    tmp_path, monkeypatch, stdout, src, stdin_filename, expect
):
    """Validation fails only if exactly one file isn't provided for ``--stdout``"""
    monkeypatch.chdir(tmp_path)
    Path("first.py").touch()
    Path("second.py").touch()
    with raises_if_exception(expect):
        OutputMode.validate_stdout_src(src, stdin_filename, stdout=stdout)


@pytest.mark.kwparametrize(
    dict(diff=False, stdout=False, expect="NOTHING"),
    dict(diff=False, stdout=True, expect="CONTENT"),
    dict(diff=True, stdout=False, expect="DIFF"),
    dict(diff=True, stdout=True, expect=ConfigurationError),
)
def test_output_mode_from_args(diff, stdout, expect):
    """Correct output mode results from the ``--diff`` and ``stdout`` options"""
    args = Namespace()
    args.diff = diff
    args.stdout = stdout
    with raises_if_exception(expect):

        result = OutputMode.from_args(args)

        assert result == expect
