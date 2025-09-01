"""Tests for `darker.__main__.main` and the ``--stdin-filename`` option"""

# pylint: disable=no-member,redefined-outer-name
# pylint: disable=too-many-arguments,too-many-positional-arguments,use-dict-literal

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import toml

import darker.__main__
from darkgraylib.command_line import EXIT_CODE_CMDLINE_ERROR
from darkgraylib.config import ConfigurationError
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.testtools.helpers import raises_if_exception

pytestmark = pytest.mark.usefixtures("find_project_root_cache_clear")


@pytest.fixture(scope="module")
def main_stdin_filename_repo(request, tmp_path_factory):
    """Git repository fixture for `test_main_stdin_filename`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        yield SimpleNamespace(
            root=repo.root,
            paths=repo.add(
                {"a.py": "original\n", "b.py": "original\n"}, commit="Initial commit"
            ),
        )


@pytest.mark.kwparametrize(
    dict(expect=SystemExit(EXIT_CODE_CMDLINE_ERROR)),
    dict(config_src=["a.py"], expect_a_py='modified = "a.py worktree"\n'),
    dict(config_src=["b.py"], src=["a.py"], expect_a_py='modified = "a.py worktree"\n'),
    dict(
        config_src=["b.py"],
        stdin_filename=["a.py"],
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(config_src=["a.py"], revision="..:STDIN:", expect_a_py='modified = "stdin"\n'),
    dict(
        config_src=["a.py"],
        revision="..:WORKTREE:",
        expect_a_py='modified = "a.py worktree"\n',
    ),
    dict(
        config_src=["b.py"],
        src=["a.py"],
        stdin_filename="a.py",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(
        config_src=["b.py"],
        src=["a.py"],
        revision="..:STDIN:",
        expect_a_py='modified = "stdin"\n',
    ),
    dict(
        config_src=["b.py"],
        src=["a.py"],
        revision="..:WORKTREE:",
        expect_a_py='modified = "a.py worktree"\n',
    ),
    dict(
        config_src=["b.py"],
        src=["a.py"],
        stdin_filename="a.py",
        revision="..:STDIN:",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(
        config_src=["b.py"],
        src=["a.py"],
        stdin_filename="a.py",
        revision="..:WORKTREE:",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(src=["a.py"], expect_a_py='modified = "a.py worktree"\n'),
    dict(
        src=["a.py"],
        stdin_filename="a.py",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(
        src=["a.py"],
        revision="..:STDIN:",
        expect_a_py='modified = "stdin"\n',
    ),
    dict(
        src=["a.py"],
        revision="..:WORKTREE:",
        expect_a_py='modified = "a.py worktree"\n',
    ),
    dict(
        src=["a.py"],
        stdin_filename="a.py",
        revision="..:STDIN:",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(
        src=["a.py"],
        stdin_filename="a.py",
        revision="..:WORKTREE:",
        expect=ConfigurationError(
            "No Python source files are allowed when using the `stdin-filename` option"
        ),
    ),
    dict(stdin_filename="a.py", expect_a_py='modified = "stdin"\n'),
    dict(
        stdin_filename="a.py", revision="..:STDIN:", expect_a_py='modified = "stdin"\n'
    ),
    dict(src=["-"], stdin_filename="a.py", expect_a_py='modified = "stdin"\n'),
    dict(
        src=["-"],
        stdin_filename="a.py",
        revision="..:STDIN:",
        expect_a_py='modified = "stdin"\n',
    ),
    dict(
        stdin_filename="a.py",
        revision="..:WORKTREE:",
        expect=ValueError(
            "With --stdin-filename, rev2 in ..:WORKTREE: must be ':STDIN:', not"
            " ':WORKTREE:'"
        ),
    ),
    dict(revision="..:STDIN:", expect=SystemExit(EXIT_CODE_CMDLINE_ERROR)),
    dict(revision="..:WORKTREE:", expect=SystemExit(EXIT_CODE_CMDLINE_ERROR)),
    config_src=None,
    src=[],
    stdin_filename=None,
    revision=None,
    expect=0,
    expect_a_py="original\n",
)
@pytest.mark.parametrize("formatter", [[], ["--formatter=black"], ["--formatter=ruff"]])
def test_main_stdin_filename(
    main_stdin_filename_repo: SimpleNamespace,
    config_src: list[str] | None,
    src: list[str],
    stdin_filename: str | None,
    revision: str | None,
    expect: int,
    expect_a_py: str,
    formatter: list[str],
) -> None:
    """Tests for `darker.__main__.main` and the ``--stdin-filename`` option"""
    repo = main_stdin_filename_repo
    repo.paths["a.py"].write_text("modified  = 'a.py worktree'")
    repo.paths["b.py"].write_text("modified  = 'b.py worktree'")
    configuration = (
        {} if config_src is None else {"tool": {"darker": {"src": config_src}}}
    )
    (repo.root / "pyproject.toml").write_text(toml.dumps(configuration))
    arguments = src[:]
    if stdin_filename is not None:
        arguments.insert(0, f"--stdin-filename={stdin_filename}")
    if revision is not None:
        arguments.insert(0, f"--revision={revision}")
    with patch.object(
        darker.__main__.sys,  # type: ignore[attr-defined]
        "stdin",
        Mock(buffer=BytesIO(b"modified  = 'stdin'")),
    ), raises_if_exception(expect):
        # end of test setup

        retval = darker.__main__.main([*formatter, *arguments])

        assert retval == expect
        assert repo.paths["a.py"].read_text() == expect_a_py
        assert repo.paths["b.py"].read_text() == "modified  = 'b.py worktree'"
