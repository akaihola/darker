"""Unit tests for Ruff related parts of `darker.command_line`."""

# pylint: disable=no-member,redefined-outer-name,unused-argument,use-dict-literal

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from darker.__main__ import main
from darker.formatters import ruff_formatter
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture


@pytest.fixture(scope="module")
def ruff_options_files(request, tmp_path_factory):
    """Fixture for the `ruff_black_options` test."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        (repo.root / "pyproject.toml").write_bytes(b"[tool.ruff]\n")
        (repo.root / "ruff.cfg").write_text(
            dedent(
                """
                [tool.ruff]
                line-length = 81
                skip-string-normalization = false
                target-version = 'py38'
                """
            )
        )
        yield repo.add({"main.py": 'print("Hello World!")\n'}, commit="Initial commit")


@pytest.mark.kwparametrize(
    dict(options=[]),
    dict(options=["-c", "ruff.cfg"], expect_opts=["--line-length=81"]),
    dict(options=["--config", "ruff.cfg"], expect_opts=["--line-length=81"]),
    dict(
        options=["-S"],
        expect_opts=['--config=format.quote-style="preserve"'],
    ),
    dict(
        options=["--skip-string-normalization"],
        expect_opts=['--config=format.quote-style="preserve"'],
    ),
    dict(options=["-l", "90"], expect_opts=["--line-length=90"]),
    dict(options=["--line-length", "90"], expect_opts=["--line-length=90"]),
    dict(
        options=["-c", "ruff.cfg", "-S"],
        expect_opts=["--line-length=81", '--config=format.quote-style="preserve"'],
    ),
    dict(
        options=["-c", "ruff.cfg", "-l", "90"],
        expect_opts=["--line-length=90"],
    ),
    dict(
        options=["-l", "90", "-S"],
        expect_opts=["--line-length=90", '--config=format.quote-style="preserve"'],
    ),
    dict(
        options=["-c", "ruff.cfg", "-l", "90", "-S"],
        expect_opts=["--line-length=90", '--config=format.quote-style="preserve"'],
    ),
    dict(options=["-t", "py39"], expect_opts=["--target-version=py39"]),
    dict(options=["--target-version", "py39"], expect_opts=["--target-version=py39"]),
    dict(
        options=["-c", "ruff.cfg", "-t", "py39"],
        expect_opts=["--line-length=81", "--target-version=py39"],
    ),
    dict(
        options=["-t", "py39", "-S"],
        expect_opts=[
            "--target-version=py39",
            '--config=format.quote-style="preserve"',
        ],
    ),
    dict(
        options=["-c", "ruff.cfg", "-t", "py39", "-S"],
        expect_opts=[
            "--line-length=81",
            "--target-version=py39",
            '--config=format.quote-style="preserve"',
        ],
    ),
    dict(options=["--preview"], expect_opts=["--preview"]),
    expect_opts=[],
)
def test_ruff_options(monkeypatch, ruff_options_files, options, expect_opts):
    """Ruff options from the command line are passed correctly to Ruff."""
    ruff_options_files["main.py"].write_bytes(b'print ("Hello World!")\n')
    with patch.object(ruff_formatter, "_ruff_format_stdin") as format_stdin:
        format_stdin.return_value = 'print("Hello World!")\n'

        main([*options, "--formatter=ruff", str(ruff_options_files["main.py"])])

    format_stdin.assert_called_once_with(
        'print ("Hello World!")\n',
        Path("main.py"),
        ['--config=lint.ignore=["ISC001"]', *expect_opts],
    )
