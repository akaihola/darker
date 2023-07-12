"""Tests for `darker.__main__.main` and the ``--stdin-filename`` option"""

# pylint: disable=too-many-arguments,use-dict-literal

from io import BytesIO
from typing import List, Optional
from unittest.mock import Mock, patch

import pytest
import toml

import darker.__main__
from darker.tests.helpers import raises_if_exception
from darkgraylib.config import ConfigurationError
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture

pytestmark = pytest.mark.usefixtures("find_project_root_cache_clear")


@pytest.mark.kwparametrize(
    dict(expect=SystemExit(2)),
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
    dict(revision="..:STDIN:", expect=SystemExit(2)),
    dict(revision="..:WORKTREE:", expect=SystemExit(2)),
    config_src=None,
    src=[],
    stdin_filename=None,
    revision=None,
    expect=0,
    expect_a_py="original\n",
)
def test_main_stdin_filename(
    git_repo: GitRepoFixture,
    config_src: Optional[List[str]],
    src: List[str],
    stdin_filename: Optional[str],
    revision: Optional[str],
    expect: int,
    expect_a_py: str,
) -> None:
    """Tests for `darker.__main__.main` and the ``--stdin-filename`` option"""
    if config_src is not None:
        configuration = {"tool": {"darker": {"src": config_src}}}
        git_repo.add({"pyproject.toml": toml.dumps(configuration)})
    paths = git_repo.add(
        {"a.py": "original\n", "b.py": "original\n"}, commit="Initial commit"
    )
    paths["a.py"].write_text("modified  = 'a.py worktree'")
    paths["b.py"].write_text("modified  = 'b.py worktree'")
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

        retval = darker.__main__.main(arguments)

        assert retval == expect
        assert paths["a.py"].read_text() == expect_a_py
        assert paths["b.py"].read_text() == "modified  = 'b.py worktree'"
