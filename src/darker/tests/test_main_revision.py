"""Unit tests for the ``--revision`` argument in `darker.main`"""

# pylint: disable=no-member,redefined-outer-name
# pylint: disable=too-many-arguments,too-many-positional-arguments,use-dict-literal

import pytest

from darker.__main__ import main
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.testtools.helpers import raises_if_exception

# The following test is a bit dense, so some explanation is due.
#
# A Git repository with 3 commits is created. Python files with one line of code
# ("ORIGINAL=1") are added, modified or deleted in each commit. An abbreviated number is
# used for each commit in the test code:
# - 2: HEAD~2          add 4 files
# - 1: HEAD~1 (HEAD^)  add 2 files, delete 1 file, keep 1 file, modify 2 files
# - 0: HEAD~0 (HEAD)   delete 1 file, modify 1 file, keep 4 files
#
# In each test case, all of the 6 files are overwritten in the working tree with given
# content.
#
# `darker --diff --revision <rev>` is called and the diff captured from stdout.
#
# Each case is gets as parameters:
# - the `<rev>` argument – which Git revision to compare to
# - `worktree_content` – the content to write to all the 6 known Python files
# - `expect` – a list of files expected to appear in `darker --diff`
#
# The Python file names tell the history of the file with a list of actions:
# +2 - added in HEAD~2
# +1 - added in HEAD^
# -1 - deleted in HEAD^
# M1 - modified in HEAD^
# -0 - deleted in HEAD
# M0 - modified in HEAD
#
# So e.g. the test case `HEAD~2`, `ORIGINAL=1` tells us that when `ORIGINAL=1` is
# written to all Python files and `darker --diff --revision HEAD~2` is called, the diff
# indicates reformatting in
# - +1.py – the file which was added in HEAD^
# - +1M0.py – the file added in HEAD^ and overwritten in HEAD (with `MODIFIED=1`)
# All other files are missing from the diff since their content was the same as now
# (`ORIGINAL=1`) at HEAD~2.


@pytest.fixture(scope="module")
def revision_files(request, tmp_path_factory):
    """Git repository fixture for testing `--revision`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        # 2: HEAD~2:
        paths = repo.add(
            {
                "+2.py": "ORIGINAL=1\n",
                "+2M1.py": "ORIGINAL=1\n",
                "+2-1.py": "ORIGINAL=1\n",
                "+2M1-0.py": "ORIGINAL=1\n",
            },
            commit="First commit",
        )
        # 1: HEAD~1 i.e. HEAD^
        paths.update(
            repo.add(
                {
                    "+2M1.py": "MODIFIED=1\n",
                    "+1.py": "ORIGINAL=1\n",
                    "+1M0.py": "ORIGINAL=1\n",
                    "+2-1.py": None,
                    "+2M1-0.py": "MODIFIED=1\n",
                },
                commit="Second commit",
            )
        )
        # 0: HEAD~0 i.e. HEAD:
        repo.add(
            {"+1M0.py": "MODIFIED=1\n", "+2M1-0.py": None},
            commit="Third commit",
        )
        yield paths


@pytest.mark.kwparametrize(
    dict(
        revision="",
        worktree_content=b"USERMOD=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="",
        worktree_content=b"ORIGINAL=1\n",
        expect={"+1M0", "+2-1", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="",
        worktree_content=b"MODIFIED=1\n",
        expect={"+1", "+2-1", "+2", "+2M1-0"},
    ),
    dict(
        revision="HEAD",
        worktree_content=b"USERMOD=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="HEAD",
        worktree_content=b"ORIGINAL=1\n",
        expect={"+1M0", "+2-1", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="HEAD",
        worktree_content=b"MODIFIED=1\n",
        expect={"+1", "+2-1", "+2", "+2M1-0"},
    ),
    dict(
        revision="HEAD^",
        worktree_content=b"USERMOD=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="HEAD^",
        worktree_content=b"USERMOD=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="HEAD^",
        worktree_content=b"ORIGINAL=1\n",
        expect={"+2-1", "+2M1-0", "+2M1"},
    ),
    dict(
        revision="HEAD^",
        worktree_content=b"MODIFIED=1\n",
        expect={"+1", "+1M0", "+2-1", "+2"},
    ),
    dict(
        revision="HEAD~2",
        worktree_content=b"USERMOD=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    # These are empty because git diff reports these are renamed files.
    # We only care about added or modified files. See PR #454
    dict(revision="HEAD~2", worktree_content=b"ORIGINAL=1\n", expect=set()),
    dict(
        revision="HEAD~2",
        worktree_content=b"MODIFIED=1\n",
        expect={"+1", "+1M0", "+2-1", "+2", "+2M1-0", "+2M1"},
    ),
    dict(revision="HEAD~3", worktree_content=b"USERMOD=1\n", expect=SystemExit),
)
def test_revision(revision_files, capsys, revision, worktree_content, expect):
    """``--diff`` with ``--revision`` reports correct files as modified"""
    # Working tree:
    for path in revision_files.values():
        path.write_bytes(worktree_content)
    arguments = ["--diff", "--revision", revision, "."]

    with raises_if_exception(expect):
        main(arguments)

        modified_files = {
            line.split("\t")[0][4:-3]
            for line in capsys.readouterr().out.splitlines()
            if line.startswith("+++ ")
        }
        assert modified_files == expect
