"""Unit tests for `darker.formatters.ruff_formatter`."""

# pylint: disable=redefined-outer-name

from subprocess import run  # nosec
from textwrap import dedent
from unittest.mock import patch

import pytest

from darker.formatters import ruff_formatter


def test_get_supported_target_versions():
    """`ruff_formatter._get_supported_target_versions` runs Ruff, gets py versions."""
    with patch.object(ruff_formatter, "run") as run_mock:
        run_mock.return_value.stdout = dedent(
            """
            Default value: "py38"
            Type: "py37" | "py38" | "py39" | "py310" | "py311" | "py312"
            Example usage:
            """
        )

        # pylint: disable=protected-access
        result = ruff_formatter._get_supported_target_versions()  # noqa: SLF001

    assert result == {
        (3, 7): "py37",
        (3, 8): "py38",
        (3, 9): "py39",
        (3, 10): "py310",
        (3, 11): "py311",
        (3, 12): "py312",
    }


@pytest.fixture
def ruff():
    """Make a Ruff call and return the `subprocess.CompletedProcess` instance."""
    cmdline = [
        "ruff",
        "format",
        "--force-exclude",  # apply `exclude =` from conffile even with stdin
        "--stdin-filename=myfile.py",  # allow to match exclude patterns
        '--config=lint.ignore=["ISC001"]',
        "-",
    ]
    return run(  # noqa: S603  # nosec
        cmdline, input="print( 1)\n", capture_output=True, check=False, text=True
    )


def test_ruff_returncode(ruff):
    """A basic Ruff subprocess call returns a zero returncode."""
    assert ruff.returncode == 0


def test_ruff_stderr(ruff):
    """A basic Ruff subprocess call prints nothing on standard error."""
    assert ruff.stderr == ""


def test_ruff_stdout(ruff):
    """A basic Ruff subprocess call prints the reformatted file on standard output."""
    assert ruff.stdout == "print(1)\n"
