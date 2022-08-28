"""Unit tests for :mod:`darker.git`"""

# pylint: disable=redefined-outer-name,protected-access,too-many-arguments

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, check_call  # nosec
from textwrap import dedent  # nosec
from typing import List, Union
from unittest.mock import call, patch

import pytest

from darker import git
from darker.tests.conftest import GitRepoFixture
from darker.tests.helpers import raises_or_matches
from darker.utils import GIT_DATEFORMAT, TextDocument


def test_tmp_path_sanity(tmp_path):
    """Make sure Pytest temporary directories aren't inside a Git repository"""
    try:
        result = git._git_check_output_lines(
            ["rev-parse", "--absolute-git-dir"], tmp_path, exit_on_error=False
        )
    except CalledProcessError as exc_info:
        if exc_info.returncode != 128 or not exc_info.stderr.startswith(
            "fatal: not a git repository"
        ):
            raise
    else:
        output = "\n".join(result)
        raise AssertionError(
            f"Temporary directory {tmp_path} for tests is not clean."
            f" There is a Git directory in {output}"
        )


@pytest.mark.parametrize(
    "revision_range, expect",
    [
        ("", None),
        ("..", ("", "..", "")),
        ("...", ("", "...", "")),
        ("a..", ("a", "..", "")),
        ("a...", ("a", "...", "")),
        ("a..b", ("a", "..", "b")),
        ("a...b", ("a", "...", "b")),
        ("..b", ("", "..", "b")),
        ("...b", ("", "...", "b")),
    ],
)
def test_commit_range_re(revision_range, expect):
    """Test for ``COMMIT_RANGE_RE``"""
    match = git.COMMIT_RANGE_RE.match(revision_range)
    if expect is None:
        assert match is None
    else:
        assert match is not None
        assert match.groups() == expect


def test_worktree_symbol():
    """Test for the ``WORKTREE`` symbol"""
    assert git.WORKTREE == ":WORKTREE:"


def test_git_get_mtime_at_commit():
    """darker.git.git_get_mtime_at_commit()"""
    with patch.object(git, "_git_check_output_lines"):
        git._git_check_output_lines.return_value = ["1609104839"]  # type: ignore

        result = git.git_get_mtime_at_commit(
            Path("dummy path"), "dummy revision", Path("dummy cwd")
        )
        assert result == "2020-12-27 21:33:59.000000 +0000"


@pytest.mark.kwparametrize(
    dict(
        revision=":WORKTREE:",
        expect_lines=("new content",),
        expect_mtime=lambda: datetime(2001, 9, 9, 1, 46, 40),
    ),
    dict(
        revision="HEAD",
        expect_lines=("modified content",),
        expect_mtime=datetime.utcnow,
    ),
    dict(
        revision="HEAD^",
        expect_lines=("original content",),
        expect_mtime=datetime.utcnow,
    ),
    dict(revision="HEAD~2", expect_lines=(), expect_mtime=False),
)
def test_git_get_content_at_revision(git_repo, revision, expect_lines, expect_mtime):
    """darker.git.git_get_content_at_revision()"""
    git_repo.add({"my.txt": "original content"}, commit="Initial commit")
    paths = git_repo.add({"my.txt": "modified content"}, commit="Initial commit")
    paths["my.txt"].write_bytes(b"new content")
    os.utime(paths["my.txt"], (1000000000, 1000000000))

    result = git.git_get_content_at_revision(
        Path("my.txt"), revision, cwd=Path(git_repo.root)
    )

    assert result.lines == expect_lines
    if expect_mtime:
        mtime_then = datetime.strptime(result.mtime, GIT_DATEFORMAT)
        difference = expect_mtime() - mtime_then
        assert timedelta(0) <= difference < timedelta(seconds=6)
    else:
        assert result.mtime == ""
    assert result.encoding == "utf-8"


@pytest.mark.parametrize(
    "revision_range, expect",
    [
        ("", ("HEAD", ":WORKTREE:", False)),
        ("HEAD", ("HEAD", ":WORKTREE:", False)),
        ("a", ("a", ":WORKTREE:", True)),
        ("a..", ("a", ":WORKTREE:", False)),
        ("a...", ("a", ":WORKTREE:", True)),
        ("..HEAD", ("HEAD", "HEAD", False)),
        ("...HEAD", ("HEAD", "HEAD", True)),
        ("a..HEAD", ("a", "HEAD", False)),
        ("a...HEAD", ("a", "HEAD", True)),
        ("a..b", ("a", "b", False)),
        ("a...b", ("a", "b", True)),
    ],
)
def test_revisionrange_parse(revision_range, expect):
    """Test for :meth:`RevisionRange.parse`"""
    result = git.RevisionRange._parse(revision_range)

    assert result == expect


def git_call(cmd, encoding=None):
    """Returns a mocked call to git"""
    return call(
        cmd.split(),
        cwd=str(Path("/path")),
        encoding=encoding,
        stderr=PIPE,
        env={"LC_ALL": "C", "PATH": os.environ["PATH"]},
    )


@pytest.mark.kwparametrize(
    dict(
        revision=":WORKTREE:",
        expect_textdocument_calls=[call.from_file(Path("/path/my.txt"))],
    ),
    dict(
        revision="HEAD",
        expect_git_calls=[
            git_call("git show HEAD:./my.txt"),
            git_call("git log -1 --format=%ct HEAD -- my.txt", encoding="utf-8"),
        ],
        expect_textdocument_calls=[
            call.from_bytes(b"1627107028", mtime="2021-07-24 06:10:28.000000 +0000")
        ],
    ),
    dict(
        revision="HEAD^",
        expect_git_calls=[
            git_call("git show HEAD^:./my.txt"),
            git_call("git log -1 --format=%ct HEAD^ -- my.txt", encoding="utf-8"),
        ],
        expect_textdocument_calls=[
            call.from_bytes(b"1627107028", mtime="2021-07-24 06:10:28.000000 +0000")
        ],
    ),
    dict(
        revision="master",
        expect_git_calls=[
            git_call("git show master:./my.txt"),
            git_call("git log -1 --format=%ct master -- my.txt", encoding="utf-8"),
        ],
        expect_textdocument_calls=[
            call.from_bytes(b"1627107028", mtime="2021-07-24 06:10:28.000000 +0000")
        ],
    ),
    expect_git_calls=[],
)
def test_git_get_content_at_revision_obtain_file_content(
    revision, expect_git_calls, expect_textdocument_calls
):
    """``git_get_content_at_revision`` calls Git or reads files based on revision"""
    with patch("darker.git.check_output") as check_output, patch(
        "darker.git.TextDocument"
    ) as text_document_class:
        # this dummy value acts both as a dummy Unix timestamp for the file as well as
        # the contents of the file:
        check_output.return_value = b"1627107028"

        git.git_get_content_at_revision(Path("my.txt"), revision, Path("/path"))

        assert check_output.call_args_list == expect_git_calls
        assert text_document_class.method_calls == expect_textdocument_calls


@pytest.mark.kwparametrize(
    dict(revrange="HEAD", expect="HEAD..:WORKTREE:"),
    dict(revrange="{initial}", expect="{initial}..:WORKTREE:"),
    dict(revrange="{initial}..", expect="{initial}..:WORKTREE:"),
    dict(revrange="{initial}..HEAD", expect="{initial}..HEAD"),
    dict(revrange="{initial}..feature", expect="{initial}..feature"),
    dict(revrange="{initial}...", expect="{initial}..:WORKTREE:"),
    dict(revrange="{initial}...HEAD", expect="{initial}..HEAD"),
    dict(revrange="{initial}...feature", expect="{initial}..feature"),
    dict(revrange="master", expect="{initial}..:WORKTREE:"),
    dict(revrange="master..", expect="master..:WORKTREE:"),
    dict(revrange="master..HEAD", expect="master..HEAD"),
    dict(revrange="master..feature", expect="master..feature"),
    dict(revrange="master...", expect="{initial}..:WORKTREE:"),
    dict(revrange="master...HEAD", expect="{initial}..HEAD"),
    dict(revrange="master...feature", expect="{initial}..feature"),
)
def test_revisionrange_parse_with_common_ancestor(git_repo, revrange, expect):
    """``_git_get_old_revision()`` gets common ancestor using Git when necessary"""
    git_repo.add({"a": "i"}, commit="Initial commit")
    initial = git_repo.get_hash()
    git_repo.add({"a": "m"}, commit="in master")
    master = git_repo.get_hash()
    git_repo.create_branch("feature", initial)
    git_repo.add({"a": "f"}, commit="in feature")

    result = git.RevisionRange.parse_with_common_ancestor(
        revrange.format(initial=initial), git_repo.root
    )

    rev1, rev2 = expect.format(initial=initial, master=master).split("..")
    assert result.rev1 == rev1
    assert result.rev2 == rev2


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
    if create:
        (tmpdir / path).ensure()

    result = git.should_reformat_file(Path(tmpdir / path))

    assert result == expect


@pytest.mark.kwparametrize(
    dict(cmd=[], exit_on_error=True, expect_template=CalledProcessError(1, "")),
    dict(
        cmd=["status", "-sb"],
        exit_on_error=True,
        expect_template=[
            "## branch",
            "A  add_index.py",
            "D  del_index.py",
            " D del_worktree.py",
            "A  mod_index.py",
            "?? add_worktree.py",
            "?? mod_worktree.py",
        ],
    ),
    dict(
        cmd=["diff"],
        exit_on_error=True,
        expect_template=[
            "diff --git a/del_worktree.py b/del_worktree.py",
            "deleted file mode 100644",
            "index 94f3610..0000000",
            "--- a/del_worktree.py",
            "+++ /dev/null",
            "@@ -1 +0,0 @@",
            "-original",
            "\\ No newline at end of file",
        ],
    ),
    dict(
        cmd=["merge-base", "master"],
        exit_on_error=True,
        expect_template=CalledProcessError(129, ""),
    ),
    dict(
        cmd=["merge-base", "master", "HEAD"],
        exit_on_error=True,
        expect_template=["<hash of branch point>"],
    ),
    dict(
        cmd=["show", "missing.file"],
        exit_on_error=True,
        expect_template=SystemExit(123),
    ),
    dict(
        cmd=["show", "missing.file"],
        exit_on_error=False,
        expect_template=CalledProcessError(128, ""),
    ),
)
def test_git_check_output_lines(branched_repo, cmd, exit_on_error, expect_template):
    """Unit test for :func:`_git_check_output_lines`"""
    if isinstance(expect_template, BaseException):
        expect: Union[List[str], BaseException] = expect_template
    else:
        replacements = {"<hash of branch point>": branched_repo.get_hash("master^")}
        expect = [replacements.get(line, line) for line in expect_template]
    with raises_or_matches(expect, ["returncode", "code"]) as check:

        check(git._git_check_output_lines(cmd, branched_repo.root, exit_on_error))


@pytest.mark.kwparametrize(
    dict(
        cmd=["show", "{initial}:/.file2"],
        exit_on_error=True,
        expect_exc=SystemExit,
        expect_log=(
            r"ERROR    darker\.git:git\.py:\d+ fatal: "
            r"[pP]ath '/\.file2' does not exist in '{initial}'\n$"
        ),
    ),
    dict(
        cmd=["show", "{initial}:/.file2"],
        exit_on_error=False,
        expect_exc=CalledProcessError,
    ),
    dict(
        cmd=["non-existing", "command"],
        exit_on_error=True,
        expect_exc=CalledProcessError,
        expect_stderr="git: 'non-existing' is not a git command. See 'git --help'.\n",
    ),
    dict(
        cmd=["non-existing", "command"],
        exit_on_error=False,
        expect_exc=CalledProcessError,
    ),
    expect_stderr="",
    expect_log=r"$",
)
def test_git_check_output_lines_stderr_and_log(
    git_repo, capfd, caplog, cmd, exit_on_error, expect_exc, expect_stderr, expect_log
):
    """Git non-existing file error is logged and suppressed from stderr"""
    git_repo.add({"file1": "file1"}, commit="Initial commit")
    initial = git_repo.get_hash()[:7]
    git_repo.add({"file2": "file2"}, commit="Second commit")
    capfd.readouterr()  # flush captured stdout and stderr
    cmdline = [s.format(initial=initial) for s in cmd]
    with pytest.raises(expect_exc):

        git._git_check_output_lines(cmdline, git_repo.root, exit_on_error)

    outerr = capfd.readouterr()
    assert outerr.out == ""
    assert outerr.err == expect_stderr
    expect_log_re = expect_log.format(initial=initial)
    assert re.match(expect_log_re, caplog.text), repr(caplog.text)


def test_git_get_content_at_revision_stderr(git_repo, capfd, caplog):
    """No stderr or log output from ``git_get_content_at_revision`` for missing file"""
    git_repo.add({"file1": "file1"}, commit="Initial commit")
    initial = git_repo.get_hash()[:7]
    git_repo.add({"file2": "file2"}, commit="Second commit")
    capfd.readouterr()  # flush captured stdout and stderr

    result = git.git_get_content_at_revision(Path("file2"), initial, git_repo.root)

    assert result == TextDocument()
    outerr = capfd.readouterr()
    assert outerr.out == ""
    assert outerr.err == ""
    assert caplog.text == ""


@pytest.fixture(scope="module")
def encodings_repo(tmp_path_factory):
    """Create an example Git repository using various encodings for the same file"""
    tmpdir = tmp_path_factory.mktemp("branched_repo")
    git_repo = GitRepoFixture.create_repository(tmpdir)
    # Commit without an encoding cookie, defaults to utf-8
    git_repo.add({"file.py": "darker = 'plus foncé'\n"}, commit="Default encoding")
    git_repo.create_tag("default")
    # Commit without an encoding cookie but with a utf-8 signature
    content = "darker = 'plus foncé'\n".encode("utf-8-sig")
    git_repo.add({"file.py": content}, commit="utf-8-sig")
    git_repo.create_tag("utf-8-sig")
    # Commit with an iso-8859-1 encoding cookie
    content = "# coding: iso-8859-1\ndarker = 'plus foncé'\n".encode("iso-8859-1")
    git_repo.add({"file.py": content}, commit="iso-8859-1")
    git_repo.create_tag("iso-8859-1")
    # Commit with a utf-8 encoding cookie
    content = "# coding: utf-8\npython = 'パイソン'\n".encode()
    git_repo.add({"file.py": content}, commit="utf-8")
    git_repo.create_tag("utf-8")
    # Current worktree content (not committed) with a shitfjs encoding cookie
    content = "# coding: shiftjis\npython = 'パイソン'\n".encode("shiftjis")
    git_repo.add({"file.py": content})
    return git_repo


@pytest.mark.kwparametrize(
    dict(commit="default", encoding="utf-8", lines=("darker = 'plus foncé'",)),
    dict(commit="utf-8-sig", encoding="utf-8-sig", lines=("darker = 'plus foncé'",)),
    dict(
        commit="iso-8859-1",
        encoding="iso-8859-1",
        lines=("# coding: iso-8859-1", "darker = 'plus foncé'"),
    ),
    dict(
        commit="utf-8", encoding="utf-8", lines=("# coding: utf-8", "python = 'パイソン'")
    ),
    dict(
        commit=":WORKTREE:",
        encoding="shiftjis",
        lines=("# coding: shiftjis", "python = 'パイソン'"),
    ),
)
def test_git_get_content_at_revision_encoding(encodings_repo, commit, encoding, lines):
    """Git file is loaded using its historical encoding"""
    result = git.git_get_content_at_revision(
        Path("file.py"), commit, encodings_repo.root
    )
    assert result.encoding == encoding
    assert result.lines == lines


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
        ["git", "cat-file", "-e", "rev2:path.py"],
        cwd=".",
        check=False,
        stderr=DEVNULL,
        env={"LC_ALL": "C", "PATH": os.environ["PATH"]},
    )
    assert result == expect


@pytest.mark.kwparametrize(
    dict(rev2="{add}", path="dir/a.py", expect=True),
    dict(rev2="{add}", path="dir/b.py", expect=True),
    dict(rev2="{add}", path="dir/", expect=True),
    dict(rev2="{add}", path="dir", expect=True),
    dict(rev2="{del_a}", path="dir/a.py", expect=False),
    dict(rev2="{del_a}", path="dir/b.py", expect=True),
    dict(rev2="{del_a}", path="dir/", expect=True),
    dict(rev2="{del_a}", path="dir", expect=True),
    dict(rev2="HEAD", path="dir/a.py", expect=False),
    dict(rev2="HEAD", path="dir/b.py", expect=False),
    dict(rev2="HEAD", path="dir/", expect=False),
    dict(rev2="HEAD", path="dir", expect=False),
)
def test_git_exists_in_revision(git_repo, rev2, path, expect):
    """``_get_exists_in_revision()`` detects file/dir existence correctly"""
    git_repo.add({"dir/a.py": "", "dir/b.py": ""}, commit="Add dir/*.py")
    add = git_repo.get_hash()
    git_repo.add({"dir/a.py": None}, commit="Delete dir/a.py")
    del_a = git_repo.get_hash()
    git_repo.add({"dir/b.py": None}, commit="Delete dir/b.py")

    result = git._git_exists_in_revision(
        Path(path), rev2.format(add=add, del_a=del_a), git_repo.root
    )

    assert result == expect


@pytest.mark.kwparametrize(
    dict(rev2="{add}", expect=set()),
    dict(rev2="{del_a}", expect={Path("dir/a.py")}),
    dict(rev2="HEAD", expect={Path("dir"), Path("dir/a.py"), Path("dir/b.py")}),
)
def test_get_missing_at_revision(git_repo, rev2, expect):
    """``get_missing_at_revision()`` returns missing files/directories correctly"""
    git_repo.add({"dir/a.py": "", "dir/b.py": ""}, commit="Add dir/*.py")
    add = git_repo.get_hash()
    git_repo.add({"dir/a.py": None}, commit="Delete dir/a.py")
    del_a = git_repo.get_hash()
    git_repo.add({"dir/b.py": None}, commit="Delete dir/b.py")

    result = git.get_missing_at_revision(
        {Path("dir"), Path("dir/a.py"), Path("dir/b.py")},
        rev2.format(add=add, del_a=del_a),
        git_repo.root,
    )

    assert result == expect


def test_get_missing_at_revision_worktree(git_repo):
    """``get_missing_at_revision()`` returns missing work tree files/dirs correctly"""
    paths = git_repo.add({"dir/a.py": "", "dir/b.py": ""}, commit="Add dir/*.py")
    paths["dir/a.py"].unlink()
    paths["dir/b.py"].unlink()

    result = git.get_missing_at_revision(
        {Path("dir"), Path("dir/a.py"), Path("dir/b.py")}, git.WORKTREE, git_repo.root
    )

    assert result == {Path("dir/a.py"), Path("dir/b.py")}


def test_git_diff_name_only(git_repo):
    """``_git_diff_name_only()`` only returns paths of modified files"""
    git_repo.add({"a.py": "a", "b.py": "b", "c.py": "c"}, commit="Initial commit")
    first = git_repo.get_hash()
    git_repo.add({"a.py": "A", "b.dy": "B"}, commit="only a.py modified")
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
def test_git_get_modified_python_files(git_repo, modify_paths, paths, expect):
    """Tests for `darker.git.git_get_modified_python_files()`"""
    root = Path(git_repo.root)
    git_repo.add(
        {
            "a.py": "original",
            "b.py": "original",
            "c/d.py": "original",
            "c/e.js": "original",
            "d/f/g.py": "original",
        },
        commit="Initial commit",
    )
    for path, content in modify_paths.items():
        absolute_path = git_repo.root / path
        if content is None:
            absolute_path.unlink()
        else:
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_path.write_bytes(content.encode("ascii"))
    revrange = git.RevisionRange("HEAD", ":WORKTREE:")

    result = git.git_get_modified_python_files(
        {root / p for p in paths}, revrange, cwd=root
    )

    assert result == {Path(p) for p in expect}


@pytest.fixture(scope="module")
def branched_repo(tmp_path_factory):
    """Create an example Git repository with a master branch and a feature branch

    The history created is::

        . worktree
        . index
        * branch
        | * master
        |/
        * Initial commit

    """
    tmpdir = tmp_path_factory.mktemp("branched_repo")
    git_repo = GitRepoFixture.create_repository(tmpdir)
    git_repo.add(
        {
            "del_master.py": "original",
            "del_branch.py": "original",
            "del_index.py": "original",
            "del_worktree.py": "original",
            "mod_master.py": "original",
            "mod_branch.py": "original",
            "mod_both.py": "original",
            "mod_same.py": "original",
            "keep.py": "original",
        },
        commit="Initial commit",
    )
    branch_point = git_repo.get_hash()
    git_repo.add(
        {
            "del_master.py": None,
            "add_master.py": "master",
            "mod_master.py": "master",
            "mod_both.py": "master",
            "mod_same.py": "same",
        },
        commit="master",
    )
    git_repo.create_branch("branch", branch_point)
    git_repo.add(
        {
            "del_branch.py": None,
            "mod_branch.py": "branch",
            "mod_both.py": "branch",
            "mod_same.py": "same",
        },
        commit="branch",
    )
    git_repo.add(
        {"del_index.py": None, "add_index.py": "index", "mod_index.py": "index"}
    )
    (git_repo.root / "del_worktree.py").unlink()
    (git_repo.root / "add_worktree.py").write_bytes(b"worktree")
    (git_repo.root / "mod_worktree.py").write_bytes(b"worktree")
    return git_repo


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
            "del_master.py",
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
            "del_master.py",
            "mod_master.py",
            "mod_both.py",
            "mod_branch.py",
        },
    ),
    dict(
        _description="from master to branch, excluding worktree and index",
        revrange="master..branch",
        expect={
            "del_master.py",
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
    _description, branched_repo, revrange, expect
):
    """Test for :func:`darker.git.git_get_modified_python_files` with revision range"""
    result = git.git_get_modified_python_files(
        [Path(branched_repo.root)],
        git.RevisionRange.parse_with_common_ancestor(revrange, branched_repo.root),
        Path(branched_repo.root),
    )

    assert {path.name for path in result} == expect


@pytest.mark.kwparametrize(
    dict(
        environ={},
        expect_rev1="HEAD",
        expect_rev2=":WORKTREE:",
        expect_use_common_ancestor=False,
    ),
    dict(
        environ={"PRE_COMMIT_FROM_REF": "old"},
        expect_rev1="HEAD",
        expect_rev2=":WORKTREE:",
        expect_use_common_ancestor=False,
    ),
    dict(
        environ={"PRE_COMMIT_TO_REF": "new"},
        expect_rev1="HEAD",
        expect_rev2=":WORKTREE:",
        expect_use_common_ancestor=False,
    ),
    dict(
        environ={"PRE_COMMIT_FROM_REF": "old", "PRE_COMMIT_TO_REF": "new"},
        expect_rev1="old",
        expect_rev2="new",
        expect_use_common_ancestor=True,
    ),
)
def test_revisionrange_parse_pre_commit(
    environ, expect_rev1, expect_rev2, expect_use_common_ancestor
):
    """RevisionRange._parse(':PRE-COMMIT:') gets the range from environment variables"""
    with patch.dict(os.environ, environ):

        result = git.RevisionRange._parse(":PRE-COMMIT:")

        assert result == (expect_rev1, expect_rev2, expect_use_common_ancestor)


edited_linenums_differ_cases = pytest.mark.kwparametrize(
    dict(context_lines=0, expect=[3, 7]),
    dict(context_lines=1, expect=[2, 3, 4, 6, 7, 8]),
    dict(context_lines=2, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
    dict(context_lines=3, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
)


@edited_linenums_differ_cases
def test_edited_linenums_differ_compare_revisions(git_repo, context_lines, expect):
    """Tests for EditedLinenumsDiffer.revision_vs_worktree()"""
    paths = git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
    paths["a.py"].write_bytes(b"1\n2\nthree\n4\n5\n6\nseven\n8\n")
    revrange = git.RevisionRange("HEAD", ":WORKTREE:")
    differ = git.EditedLinenumsDiffer(git_repo.root, revrange)

    linenums = differ.compare_revisions(Path("a.py"), context_lines)

    assert linenums == expect


@edited_linenums_differ_cases
def test_edited_linenums_differ_revision_vs_lines(git_repo, context_lines, expect):
    """Tests for EditedLinenumsDiffer.revision_vs_lines()"""
    git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
    content = TextDocument.from_lines(["1", "2", "three", "4", "5", "6", "seven", "8"])
    revrange = git.RevisionRange("HEAD", ":WORKTREE:")
    differ = git.EditedLinenumsDiffer(git_repo.root, revrange)

    linenums = differ.revision_vs_lines(Path("a.py"), content, context_lines)

    assert linenums == expect


@pytest.mark.kwparametrize(
    dict(context_lines=0, expect=[1, 3, 4, 5, 6, 8]),
    dict(context_lines=1, expect=[1, 2, 3, 4, 5, 6, 7, 8]),
)
def test_edited_linenums_differ_revision_vs_lines_multiline_strings(
    git_repo, context_lines, expect
):
    """Tests for EditedLinenumsDiffer.revision_vs_lines() with multi-line strings"""
    git_repo.add(
        {
            "a.py": dedent(
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
        },
        commit="Initial commit",
    )
    content = TextDocument.from_lines(
        [
            "CHANGED",
            "keep",
            "'''CHANGED FIRST,",
            "keep second",
            "and third,",
            "CHANGED FOURTH LINE OF MULTILINE'''",
            "keep",
            "CHANGED",
        ]
    )
    revrange = git.RevisionRange("HEAD", ":WORKTREE:")
    differ = git.EditedLinenumsDiffer(git_repo.root, revrange)

    linenums = differ.revision_vs_lines(Path("a.py"), content, context_lines)

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
