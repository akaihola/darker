"""Unit tests for `darker.__main__._reformat_and_flynt_single_file`."""

# pylint: disable=no-member,redefined-outer-name
# pylint: disable=too-many-arguments,too-many-positional-arguments,use-dict-literal

from pathlib import Path
from textwrap import dedent

import pytest

from darker.__main__ import _reformat_and_flynt_single_file
from darker.config import Exclusions
from darker.formatters.black_formatter import BlackFormatter
from darker.formatters.ruff_formatter import RuffFormatter
from darker.git import EditedLinenumsDiffer
from darkgraylib.git import RevisionRange
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.utils import TextDocument


@pytest.fixture(scope="module")
def reformat_and_flynt_single_file_repo(request, tmp_path_factory):
    """Git repository fixture for `test_reformat_and_flynt_single_file`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        repo.add(
            {"file.py": "import  original\nprint( original )\n"},
            commit="Initial commit",
        )
        yield repo


@pytest.mark.kwparametrize(
    dict(),
    dict(relative_path="file.py.12345.tmp"),
    dict(
        rev2_content="import  modified\n\nprint( original )\n",
        rev2_isorted="import  modified\n\nprint( original )\n",
        expect="import modified\n\nprint( original )\n",
    ),
    dict(
        rev2_content="import  original\n\nprint(modified )\n",
        rev2_isorted="import  original\n\nprint(modified )\n",
        expect="import  original\n\nprint(modified)\n",
    ),
    dict(
        rev2_content="import  original\n\nprint('{}'.format(original.foo) )\n",
        rev2_isorted="import  original\n\nprint('{}'.format(original.foo) )\n",
        expect='import  original\n\nprint(f"{original.foo}")\n',
    ),
    dict(
        rev2_content="import  original\n\nprint('{}'.format(original.foo) )\n",
        rev2_isorted="import  original\n\nprint('{}'.format(original.foo) )\n",
        exclusions=Exclusions(flynt={"file.py"}),
        expect='import  original\n\nprint("{}".format(original.foo))\n',
    ),
    dict(
        relative_path="file.py.12345.tmp",
        rev2_content="import  modified\n\nprint( original )\n",
        rev2_isorted="import  modified\n\nprint( original )\n",
        expect="import modified\n\nprint( original )\n",
    ),
    dict(
        relative_path="file.py.12345.tmp",
        rev2_content="import  original\n\nprint(modified )\n",
        rev2_isorted="import  original\n\nprint(modified )\n",
        expect="import  original\n\nprint(modified)\n",
    ),
    relative_path="file.py",
    rev2_content="import  original\nprint( original )\n",
    rev2_isorted="import  original\nprint( original )\n",
    exclusions=Exclusions(),
    expect="import  original\nprint( original )\n",
)
@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_reformat_and_flynt_single_file(
    reformat_and_flynt_single_file_repo,
    relative_path,
    rev2_content,
    rev2_isorted,
    exclusions,
    expect,
    formatter_class,
):
    """Test for `_reformat_and_flynt_single_file`."""
    repo = reformat_and_flynt_single_file_repo
    result = _reformat_and_flynt_single_file(
        repo.root,
        Path(relative_path),
        Path("file.py"),
        exclusions,
        EditedLinenumsDiffer(repo.root, RevisionRange(rev1="HEAD", rev2=":WORKTREE")),
        TextDocument(rev2_content),
        TextDocument(rev2_isorted),
        has_isort_changes=False,
        formatter=formatter_class(),
    )

    assert result.string == expect


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_blacken_and_flynt_single_file_common_ancestor(git_repo, formatter_class):
    """`_blacken_and_flynt_single_file` diffs to common ancestor of ``rev1...rev2``."""
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
    revrange = RevisionRange.parse_with_common_ancestor(
        "master...", git_repo.root, stdin_mode=False
    )

    result = _reformat_and_flynt_single_file(
        git_repo.root,
        Path("a.py"),
        Path("a.py"),
        Exclusions(),
        EditedLinenumsDiffer(git_repo.root, revrange),
        rev2_content=worktree,
        rev2_isorted=worktree,
        has_isort_changes=False,
        formatter=formatter_class(),
    )

    assert result.lines == (
        "a = 1  # changed",
        "",
        "b=2",
        "",
        "print(a + b)  # changed",
    )


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_reformat_single_file_docstring(git_repo, formatter_class):
    """`_blacken_and_flynt_single_file()` handles docstrings as one contiguous block."""
    initial = dedent(
        '''\
        def docstring_func():
            """
        originally unindented

            originally indented
            """
        '''
    )
    modified = dedent(
        '''\
        def docstring_func():
            """
        originally unindented

            modified and still indented
            """
        '''
    )
    expect = dedent(
        '''\
        def docstring_func():
            """
            originally unindented

                modified and still indented
            """
        '''
    )
    paths = git_repo.add({"a.py": initial}, commit="Initial commit")
    paths["a.py"].write_text(modified)
    revrange = RevisionRange.parse_with_common_ancestor(
        "HEAD..", git_repo.root, stdin_mode=False
    )

    result = _reformat_and_flynt_single_file(
        git_repo.root,
        Path("a.py"),
        Path("a.py"),
        Exclusions(),
        EditedLinenumsDiffer(git_repo.root, revrange),
        rev2_content=TextDocument.from_str(modified),
        rev2_isorted=TextDocument.from_str(modified),
        has_isort_changes=False,
        formatter=formatter_class(),
    )

    assert result.lines == tuple(expect.splitlines())
