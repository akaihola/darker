"""Unit tests for :func:`darker.__main__._reformat_single_file`"""

# pylint: disable=protected-access

from pathlib import Path
from textwrap import dedent

import darker.__main__
from darker.git import EditedLinenumsDiffer, RevisionRange
from darker.utils import TextDocument


def test_reformat_single_file_common_ancestor(git_repo):
    """``_reformat_single_file()`` compares to the common ancestor of ``rev1...rev2``"""
    a_py_initial = dedent(
        """\
        a=1

        b=2

        print( a+b )
        """
    )
    a_py_master = dedent(
        """\
        a=1           # every

        b=2           # line

        print( a+b )  # changed
        """
    )
    a_py_feature = dedent(
        """\
        a= 1  # changed

        b=2

        print( a+b )
        """
    )
    a_py_worktree = dedent(
        """\
        a= 1  # changed

        b=2

        print(a+b )  # changed
        """
    )
    git_repo.add({"a.py": a_py_initial}, commit="Initial commit")
    initial = git_repo.get_hash()
    git_repo.add({"a.py": a_py_master}, commit="on master")
    git_repo.create_branch("feature", initial)
    git_repo.add({"a.py": a_py_feature}, commit="on feature")
    worktree = TextDocument.from_str(a_py_worktree)

    result = darker.__main__._reformat_single_file(
        git_repo.root,
        Path("a.py"),
        Path("a.py"),
        EditedLinenumsDiffer(
            git_repo.root,
            RevisionRange.parse_with_common_ancestor("master...", git_repo.root),
        ),
        rev2_content=worktree,
        rev2_isorted=worktree,
        enable_isort=False,
        black_config={},
    )

    assert result.lines == (
        "a = 1  # changed",
        "",
        "b=2",
        "",
        "print(a + b)  # changed",
    )
