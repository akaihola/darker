"""Unit tests for :mod:`darker.git`"""

# pylint: disable=no-member,protected-access,redefined-outer-name,use-dict-literal
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-lines

import os
from pathlib import Path
from subprocess import DEVNULL, check_call  # nosec
from textwrap import dedent  # nosec
from types import SimpleNamespace
from typing import Generator
from unittest.mock import ANY, patch

import pytest
from _pytest.fixtures import SubRequest

from darker import git
from darkgraylib.git import WORKTREE, RevisionRange
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture, branched_repo
from darkgraylib.utils import TextDocument


@pytest.mark.kwparametrize(
    dict(path="file.py", expect="file.py"),
    dict(path="subdir/file.py", expect="subdir/file.py"),
    dict(path="file.py.12345.tmp", expect="file.py"),
    dict(path="subdir/file.py.12345.tmp", expect="subdir/file.py"),
    dict(path="file.py.tmp", expect="file.py.tmp"),
    dict(path="subdir/file.py.tmp", expect="subdir/file.py.tmp"),
    dict(path="file.12345.tmp", expect="file.12345.tmp"),
    dict(path="subdir/file.12345.tmp", expect="subdir/file.12345.tmp"),
)
def test_get_path_in_repo(path, expect):
    """``get_path_in_repo`` drops two suffixes from ``.py.<HASH>.tmp``"""
    result = git.get_path_in_repo(Path(path))

    assert result == Path(expect)


@pytest.mark.kwparametrize(
    dict(path=".", create=False, expect=False),
    dict(path="main", create=True, expect=False),
    dict(path="main.c", create=True, expect=False),
    dict(path="main.py", create=True, expect=True),
    dict(path="main.py", create=False, expect=False),
    dict(path="main.pyx", create=True, expect=False),
    dict(path="main.pyi", create=True, expect=False),
    dict(path="main.pyc", create=True, expect=False),
    dict(path="main.pyo", create=True, expect=False),
    dict(path="main.js", create=True, expect=False),
)
def test_should_reformat_file(tmpdir, path, create, expect):
    """``should_reformat_file()`` only returns ``True`` for ``.py`` files which exist"""
    if create:
        (tmpdir / path).ensure()

    result = git.should_reformat_file(Path(tmpdir / path))

    assert result == expect


@pytest.mark.kwparametrize(
    dict(retval=0, expect=True),
    dict(retval=1, expect=False),
    dict(retval=2, expect=False),
)
def test_git_exists_in_revision_git_call(retval, expect):
    """``_git_exists_in_revision()`` calls Git and converts return value correctly"""
    with patch.object(git, "run") as run:
        run.return_value.returncode = retval

        result = git._git_exists_in_revision(Path("path.py"), "rev2", Path("."))

    run.assert_called_once_with(
        ["git", "cat-file", "-e", "rev2:./path.py"],
        cwd=".",
        check=False,
        stderr=DEVNULL,
        env=ANY,
    )
    assert result == expect


@pytest.fixture(scope="module")
def exists_missing_test_repo(request, tmp_path_factory):
    """Git repository fixture for exists/missing tests."""
    fixture = SimpleNamespace()
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        fixture.root = repo.root
        repo.add(
            {"x/README": "", "x/dir/a.py": "", "x/dir/sub/b.py": ""},
            commit="Add x/dir/*.py",
        )
        fixture.hash_add = repo.get_hash()
        repo.add({"x/dir/a.py": None}, commit="Delete x/dir/a.py")
        fixture.hash_del_a = repo.get_hash()
        repo.add({"x/dir/sub/b.py": None}, commit="Delete x/dir/sub/b.py")
        yield fixture


@pytest.mark.kwparametrize(
    dict(cwd=".", rev2="{add}", path="x/dir/a.py", expect=True),
    dict(cwd=".", rev2="{add}", path="x/dir/sub/b.py", expect=True),
    dict(cwd=".", rev2="{add}", path="x/dir/", expect=True),
    dict(cwd=".", rev2="{add}", path="x/dir", expect=True),
    dict(cwd=".", rev2="{add}", path="x/dir/sub", expect=True),
    dict(cwd=".", rev2="{del_a}", path="x/dir/a.py", expect=False),
    dict(cwd=".", rev2="{del_a}", path="x/dir/sub/b.py", expect=True),
    dict(cwd=".", rev2="{del_a}", path="x/dir/", expect=True),
    dict(cwd=".", rev2="{del_a}", path="x/dir", expect=True),
    dict(cwd=".", rev2="{del_a}", path="x/dir/sub", expect=True),
    dict(cwd=".", rev2="HEAD", path="x/dir/a.py", expect=False),
    dict(cwd=".", rev2="HEAD", path="x/dir/sub/b.py", expect=False),
    dict(cwd=".", rev2="HEAD", path="x/dir/", expect=False),
    dict(cwd=".", rev2="HEAD", path="x/dir", expect=False),
    dict(cwd=".", rev2="HEAD", path="x/dir/sub", expect=False),
    dict(cwd="x", rev2="{add}", path="dir/a.py", expect=True),
    dict(cwd="x", rev2="{add}", path="dir/sub/b.py", expect=True),
    dict(cwd="x", rev2="{add}", path="dir/", expect=True),
    dict(cwd="x", rev2="{add}", path="dir", expect=True),
    dict(cwd="x", rev2="{add}", path="dir/sub", expect=True),
    dict(cwd="x", rev2="{del_a}", path="dir/a.py", expect=False),
    dict(cwd="x", rev2="{del_a}", path="dir/sub/b.py", expect=True),
    dict(cwd="x", rev2="{del_a}", path="dir/", expect=True),
    dict(cwd="x", rev2="{del_a}", path="dir", expect=True),
    dict(cwd="x", rev2="{del_a}", path="dir/sub", expect=True),
    dict(cwd="x", rev2="HEAD", path="dir/a.py", expect=False),
    dict(cwd="x", rev2="HEAD", path="dir/sub/b.py", expect=False),
    dict(cwd="x", rev2="HEAD", path="dir/", expect=False),
    dict(cwd="x", rev2="HEAD", path="dir", expect=False),
    dict(cwd="x", rev2="HEAD", path="dir/sub", expect=False),
)
def test_git_exists_in_revision(
    exists_missing_test_repo, monkeypatch, cwd, rev2, path, expect
):
    """``_get_exists_in_revision()`` detects file/dir existence correctly"""
    repo = exists_missing_test_repo
    monkeypatch.chdir(cwd)

    result = git._git_exists_in_revision(
        Path(path),
        rev2.format(add=repo.hash_add, del_a=repo.hash_del_a),
        repo.root / "x/dir/sub",
    )

    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        paths={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
        rev2="{add}",
        expect=set(),
    ),
    dict(
        paths={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
        rev2="{del_a}",
        expect={"x/dir/a.py"},
    ),
    dict(
        paths={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
        rev2="HEAD",
        expect={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
    ),
    dict(
        paths={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
        rev2=":WORKTREE:",
        expect={"x/dir", "x/dir/a.py", "x/dir/sub", "x/dir/sub/b.py"},
    ),
    dict(
        paths={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
        cwd="x",
        rev2="{add}",
        expect=set(),
    ),
    dict(
        paths={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
        cwd="x",
        rev2="{del_a}",
        expect={"dir/a.py"},
    ),
    dict(
        paths={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
        cwd="x",
        rev2="HEAD",
        expect={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
    ),
    dict(
        paths={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
        cwd="x",
        rev2=":WORKTREE:",
        expect={"dir", "dir/a.py", "dir/sub", "dir/sub/b.py"},
    ),
    cwd=".",
    git_cwd=".",
)
def test_get_missing_at_revision(
    exists_missing_test_repo, monkeypatch, paths, cwd, git_cwd, rev2, expect
):
    """``get_missing_at_revision()`` returns missing files/directories correctly"""
    repo = exists_missing_test_repo
    monkeypatch.chdir(repo.root / cwd)

    result = git.get_missing_at_revision(
        {Path(p) for p in paths},
        rev2.format(add=repo.hash_add, del_a=repo.hash_del_a),
        repo.root / git_cwd,
    )

    assert result == {Path(p) for p in expect}


def test_get_missing_at_revision_worktree(git_repo):
    """``get_missing_at_revision()`` returns missing work tree files/dirs correctly"""
    paths = git_repo.add({"dir/a.py": "", "dir/b.py": ""}, commit="Add dir/*.py")
    paths["dir/a.py"].unlink()
    paths["dir/b.py"].unlink()

    result = git.get_missing_at_revision(
        {Path("dir"), Path("dir/a.py"), Path("dir/b.py")}, WORKTREE, git_repo.root
    )

    assert result == {Path("dir/a.py"), Path("dir/b.py")}


def test_git_diff_name_only(git_repo):
    """``_git_diff_name_only()`` includes added/modified, skips renamed/moved files."""
    git_repo.add({"a.py": "a", "b.py": "b", "c.py": "c"}, commit="Initial commit")
    first = git_repo.get_hash()
    git_repo.add({"a.py": "A", "b.dy": "B"}, commit="only a.py modified")
    git_repo.rename("c.py", "x.py", commit="rename c.py to x.py")

    second = git_repo.get_hash()

    result = git._git_diff_name_only(
        first, second, {Path("a.py"), Path("c.py"), Path("Z.py")}, git_repo.root
    )

    assert result == {Path("a.py")}


def test_git_ls_files_others(git_repo):
    """``_git_ls_files_others()`` only returns paths of untracked non-ignored files"""
    git_repo.add(
        {
            "tracked.py": "tracked",
            "tracked.ignored": "tracked",
            ".gitignore": "*.ignored",
        },
        commit="Initial commit",
    )
    (git_repo.root / "untracked.py").write_text("untracked")
    (git_repo.root / "untracked.ignored").write_text("untracked")

    result = git._git_ls_files_others(
        {
            Path("tracked.py"),
            Path("tracked.ignored"),
            Path("untracked.py"),
            Path("untracked.ignored"),
            Path("missing.py"),
            Path("missing.ignored"),
        },
        git_repo.root,
    )

    assert result == {Path("untracked.py")}


@pytest.fixture(scope="module")
def git_get_modified_python_files_repo(request, tmp_path_factory):
    """Git repository fixture for `test_git_get_modified_python_files`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        repo.add(
            {
                "a.py": "original",
                "b.py": "original",
                "c/d.py": "original",
                "c/e.js": "original",
                "d/f/g.py": "original",
            },
            commit="Initial commit",
        )
        yield repo


@pytest.mark.kwparametrize(
    dict(paths=["a.py"], expect=[]),
    dict(expect=[]),
    dict(modify_paths={"a.py": "new"}, expect=["a.py"]),
    dict(modify_paths={"a.py": "new"}, paths=["b.py"], expect=[]),
    dict(modify_paths={"a.py": "new"}, paths=["a.py", "b.py"], expect=["a.py"]),
    dict(
        modify_paths={"c/d.py": "new"}, paths=["c/d.py", "d/f/g.py"], expect=["c/d.py"]
    ),
    dict(modify_paths={"c/e.js": "new"}, paths=["c/e.js"], expect=[]),
    dict(modify_paths={"a.py": "original"}, paths=["a.py"], expect=[]),
    dict(modify_paths={"a.py": None}, paths=["a.py"], expect=[]),
    dict(modify_paths={"h.py": "untracked"}, paths=["h.py"], expect=["h.py"]),
    dict(paths=["h.py"], expect=[]),
    modify_paths={},
    paths=[],
)
def test_git_get_modified_python_files(
    git_get_modified_python_files_repo, modify_paths, paths, expect, make_temp_copy
):
    """Tests for `darker.git.git_get_modified_python_files()`"""
    with make_temp_copy(git_get_modified_python_files_repo.root) as root:
        for path, content in modify_paths.items():
            absolute_path = root / path
            if content is None:
                absolute_path.unlink()
            else:
                absolute_path.parent.mkdir(parents=True, exist_ok=True)
                absolute_path.write_bytes(content.encode("ascii"))
        revrange = RevisionRange("HEAD", ":WORKTREE:")

        result = git.git_get_modified_python_files(
            {root / p for p in paths}, revrange, repo_root=root
        )

    assert result == {Path(p) for p in expect}


@pytest.fixture(scope="module")
def git_get_modified_python_files_revision_range_repo(
    request: SubRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[GitRepoFixture, None, None]:
    """Fixture for a Git repository with multiple commits and branches."""
    yield from branched_repo(request, tmp_path_factory)


@pytest.mark.kwparametrize(
    dict(
        _description="from latest commit in branch to worktree and index",
        revrange="HEAD",
        expect={"add_index.py", "add_worktree.py", "mod_index.py", "mod_worktree.py"},
    ),
    dict(
        _description="from initial commit to worktree and index on branch (implicit)",
        revrange="master",
        expect={
            "mod_both.py",
            "mod_same.py",
            "mod_branch.py",
            "add_index.py",
            "mod_index.py",
            "add_worktree.py",
            "mod_worktree.py",
        },
    ),
    dict(
        _description="from initial commit to worktree and index on branch",
        revrange="master...",
        expect={
            "mod_both.py",
            "mod_same.py",
            "mod_branch.py",
            "add_index.py",
            "mod_index.py",
            "add_worktree.py",
            "mod_worktree.py",
        },
    ),
    dict(
        _description="from master to worktree and index on branch",
        revrange="master..",
        expect={
            "mod_master.py",
            "mod_both.py",
            "mod_branch.py",
            "add_index.py",
            "mod_index.py",
            "add_worktree.py",
            "mod_worktree.py",
        },
    ),
    dict(
        _description=(
            "from master to last commit on branch," " excluding worktree and index"
        ),
        revrange="master..HEAD",
        expect={
            "mod_master.py",
            "mod_both.py",
            "mod_branch.py",
        },
    ),
    dict(
        _description="from master to branch, excluding worktree and index",
        revrange="master..branch",
        expect={
            "mod_master.py",
            "mod_both.py",
            "mod_branch.py",
        },
    ),
    dict(
        _description=(
            "from initial commit to last commit on branch,"
            " excluding worktree and index"
        ),
        revrange="master...HEAD",
        expect={"mod_both.py", "mod_same.py", "mod_branch.py"},
    ),
    dict(
        _description="from initial commit to previous commit on branch",
        revrange="master...branch",
        expect={"mod_both.py", "mod_same.py", "mod_branch.py"},
    ),
)
def test_git_get_modified_python_files_revision_range(
    _description,  # noqa: PT019
    git_get_modified_python_files_revision_range_repo,
    revrange,
    expect,
):
    """Test for :func:`darker.git.git_get_modified_python_files` with revision range"""
    repo = git_get_modified_python_files_revision_range_repo
    result = git.git_get_modified_python_files(
        [Path(repo.root)],
        RevisionRange.parse_with_common_ancestor(revrange, repo.root, stdin_mode=False),
        Path(repo.root),
    )

    assert {path.name for path in result} == expect


edited_linenums_differ_cases = pytest.mark.kwparametrize(
    dict(context_lines=0, expect=[3, 7]),
    dict(context_lines=1, expect=[2, 3, 4, 6, 7, 8]),
    dict(context_lines=2, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
    dict(context_lines=3, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
)


@pytest.fixture(scope="module")
def edited_linenums_differ_revisions_repo(request, tmp_path_factory):
    """Git repository fixture for `git.EditedLinenumsDiffer` tests."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        paths = repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
        yield SimpleNamespace(root=repo.root, paths=paths)


@edited_linenums_differ_cases
def test_edited_linenums_differ_compare_revisions(
    edited_linenums_differ_revisions_repo, context_lines, expect
):
    """Tests for EditedLinenumsDiffer.revision_vs_worktree()"""
    repo = edited_linenums_differ_revisions_repo
    repo.paths["a.py"].write_bytes(b"1\n2\nthree\n4\n5\n6\nseven\n8\n")
    revrange = RevisionRange("HEAD", ":WORKTREE:")
    differ = git.EditedLinenumsDiffer(repo.root, revrange)

    linenums = differ.compare_revisions(Path("a.py"), context_lines)

    assert linenums == expect


@edited_linenums_differ_cases
def test_edited_linenums_differ_revision_vs_lines(
    edited_linenums_differ_revisions_repo, context_lines, expect
):
    """Tests for EditedLinenumsDiffer.revision_vs_lines()"""
    repo = edited_linenums_differ_revisions_repo
    content = TextDocument.from_lines(["1", "2", "three", "4", "5", "6", "seven", "8"])
    revrange = RevisionRange("HEAD", ":WORKTREE:")
    differ = git.EditedLinenumsDiffer(repo.root, revrange)

    linenums = differ.revision_vs_lines(Path("a.py"), content, context_lines)

    assert linenums == expect


@pytest.fixture(scope="module")
def edited_linenums_differ_revision_vs_lines_multiline_strings_repo(
    request, tmp_path_factory
):
    """Fixture for `test_edited_linenums_differ_revision_vs_lines_multiline_strings`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        a_py_content = dedent(
            """\
            change\n
            keep\n
            '''change first,\n
            keep second\n
            and third,\n
            change fourth line of multiline'''\n
            keep\n
            change\n
            """
        )
        repo.add({"a.py": a_py_content}, commit="Initial commit")
        content_lines = [
            "CHANGED",
            "keep",
            "'''CHANGED FIRST,",
            "keep second",
            "and third,",
            "CHANGED FOURTH LINE OF MULTILINE'''",
            "keep",
            "CHANGED",
        ]
        content = TextDocument.from_lines(content_lines)
        revrange = RevisionRange("HEAD", ":WORKTREE:")
        differ = git.EditedLinenumsDiffer(repo.root, revrange)
        yield SimpleNamespace(content=content, differ=differ)


@pytest.mark.kwparametrize(
    dict(context_lines=0, expect=[1, 3, 4, 5, 6, 8]),
    dict(context_lines=1, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
)
def test_edited_linenums_differ_revision_vs_lines_multiline_strings(
    edited_linenums_differ_revision_vs_lines_multiline_strings_repo,
    context_lines,
    expect,
):
    """Tests for `git.EditedLinenumsDiffer.revision_vs_lines`, multi-line strings."""
    fixture = edited_linenums_differ_revision_vs_lines_multiline_strings_repo

    linenums = fixture.differ.revision_vs_lines(
        Path("a.py"), fixture.content, context_lines
    )

    assert linenums == expect


def test_local_gitconfig_ignored_by_gitrepofixture(tmp_path):
    """Tests that ~/.gitconfig is ignored when running darker's git tests"""
    (tmp_path / "HEAD").write_text("ref: refs/heads/main")

    # Note: once we decide to drop support for git < 2.28, the HEAD file
    # creation above can be removed, and setup can simplify to
    # check_call("git config --global init.defaultBranch main".split())
    check_call(  # nosec
        "git config --global init.templateDir".split() + [str(tmp_path)],
        env={"HOME": str(tmp_path), "PATH": os.environ["PATH"]},
    )
    root = tmp_path / "repo"
    root.mkdir()
    git_repo = GitRepoFixture.create_repository(root)
    assert git_repo.get_branch() == "master"
