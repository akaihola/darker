"""Unit tests for :mod:`darker.__main__`"""

# pylint: disable=no-member,too-many-locals,use-implicit-booleaness-not-comparison
# pylint: disable=protected-access,redefined-outer-name,use-dict-literal,
# pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument

import random
import re
import string
import sys
from argparse import ArgumentError
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run  # nosec
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import darker.__main__
import darker.import_sorting
from darker.git import EditedLinenumsDiffer
from darker.help import LINTING_GUIDE
from darker.terminal import output
from darker.tests.examples import A_PY, A_PY_BLACK, A_PY_BLACK_FLYNT, A_PY_BLACK_ISORT
from darker.tests.helpers import black_present, unix_and_windows_newline_repos
from darker.tests.test_fstring import FLYNTED_SOURCE, MODIFIED_SOURCE, ORIGINAL_SOURCE
from darkgraylib.git import RevisionRange
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.testtools.highlighting_helpers import BLUE, CYAN, RESET, WHITE, YELLOW
from darkgraylib.utils import WINDOWS, TextDocument, joinlines

pytestmark = pytest.mark.usefixtures(
    "find_project_root_cache_clear", "load_toml_cache_clear"
)


def randomword(length: int) -> str:
    """Create a random string of lowercase letters of a given length."""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _i in range(length))  # nosec


def _replace_diff_timestamps(text, replacement="<timestamp>"):
    return re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d\d\d\d", replacement, text)


A_PY_DIFF_BLACK = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    " import sys",
    " import os",
    "-print( '{}'.format('42'))",
    "+",
    '+print("{}".format("42"))',
]

A_PY_DIFF_BLACK_NO_STR_NORMALIZE = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    " import sys",
    " import os",
    "-print( '{}'.format('42'))",
    "+",
    "+print('{}'.format('42'))",
]

A_PY_DIFF_BLACK_ISORT = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    "+import os",
    " import sys",
    "-import os",
    "-print( '{}'.format('42'))",
    "+",
    '+print("{}".format("42"))',
]

A_PY_DIFF_BLACK_FLYNT = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    " import sys",
    " import os",
    "-print( '{}'.format('42'))",
    "+",
    '+print("42")',
]


@pytest.fixture(scope="module")
def main_repo(request, tmp_path_factory):
    """Create Git repositories to test `darker.__main__.main`."""
    fixture = {}
    with unix_and_windows_newline_repos(request, tmp_path_factory) as repos:
        for newline, repo in repos.items():
            paths = repo.add(
                {"subdir/a.py": newline, "b.py": newline}, commit="Initial commit"
            )
            fixture[newline] = SimpleNamespace(root=repo.root, paths=paths)
        yield fixture


@pytest.mark.parametrize(
    "formatter_arguments", [[], ["--formatter=black"], ["--formatter=ruff"]]
)
@pytest.mark.kwparametrize(
    dict(arguments=["--diff"], expect_stdout=A_PY_DIFF_BLACK),
    dict(arguments=["--isort"], expect_a_py=A_PY_BLACK_ISORT),
    dict(arguments=["--flynt"], expect_a_py=A_PY_BLACK_FLYNT),
    dict(
        arguments=["--skip-string-normalization", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
    ),
    dict(arguments=[], expect_a_py=A_PY_BLACK, expect_retval=0),
    dict(arguments=["--isort", "--diff"], expect_stdout=A_PY_DIFF_BLACK_ISORT),
    dict(arguments=["--flynt", "--diff"], expect_stdout=A_PY_DIFF_BLACK_FLYNT),
    dict(arguments=["--check"], expect_a_py=A_PY, expect_retval=1),
    dict(
        arguments=["--check", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK,
        expect_retval=1,
    ),
    dict(arguments=["--check", "--isort"], expect_retval=1),
    dict(arguments=["--check", "--flynt"], expect_retval=1),
    dict(
        arguments=["--check", "--diff", "--isort"],
        expect_stdout=A_PY_DIFF_BLACK_ISORT,
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--diff", "--flynt"],
        expect_stdout=A_PY_DIFF_BLACK_FLYNT,
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--lint", "dummy"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=["", *LINTING_GUIDE.lstrip().splitlines()],
        expect_retval=1,
    ),
    dict(
        arguments=["--diff", "--lint", "dummy"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=[*A_PY_DIFF_BLACK, "", *LINTING_GUIDE.lstrip().splitlines()],
        expect_retval=0,
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           exclude = 'a.py'
           [tool.ruff.format]
           exclude = ['a.py']
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           exclude = 'a.py'
           [tool.ruff.format]
           exclude = ['a.py']
           """,
        expect_stdout=[],
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           extend_exclude = 'a.py'
           [tool.ruff]
           extend-exclude = ['a.py']
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           extend_exclude = 'a.py'
           [tool.ruff]
           extend-exclude = ['a.py']
           """,
        expect_stdout=[],
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           force_exclude = 'a.py'
           [tool.ruff.format]
           exclude = ['a.py']
           [tool.ruff]
           force-exclude = true  # redundant, always passed to ruff anyway
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           force_exclude = 'a.py'
           [tool.ruff.format]
           exclude = ['a.py']
           [tool.ruff]
           force-exclude = true  # redundant, always passed to ruff anyway
           """,
        expect_stdout=[],
    ),
    dict(
        arguments=["--diff"],
        expect_stdout=A_PY_DIFF_BLACK,
        root_as_cwd=False,
    ),
    # for all test cases, by default there's no output, `a.py` stays unmodified, and the
    # return value is a zero:
    pyproject_toml="",
    expect_stdout=[],
    expect_a_py=A_PY,
    expect_retval=0,
    root_as_cwd=True,
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_main(
    main_repo,
    monkeypatch,
    capsys,
    formatter_arguments,
    arguments,
    newline,
    pyproject_toml,
    expect_stdout,
    expect_a_py,
    expect_retval,
    root_as_cwd,
    tmp_path_factory,
):
    """Main function outputs diffs and modifies files correctly"""
    repo = main_repo[newline]
    if root_as_cwd:
        cwd = repo.root
        pwd = Path("")
    else:
        cwd = tmp_path_factory.mktemp("not_a_git_repo")
        pwd = repo.root
    monkeypatch.chdir(cwd)
    (repo.root / "pyproject.toml").write_text(dedent(pyproject_toml))
    repo.paths["subdir/a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    repo.paths["b.py"].write_bytes(f"print(42 ){newline}".encode("ascii"))

    retval = darker.__main__.main(
        [*formatter_arguments, *arguments, str(pwd / "subdir")]
    )

    stdout = capsys.readouterr().out.replace(str(repo.root), "")
    diff_output = stdout.splitlines(False)
    if expect_stdout:
        if "--diff" in arguments:
            assert "\t" in diff_output[0], diff_output[0]
            diff_output[0], old_mtime = diff_output[0].split("\t", 1)
            assert old_mtime.endswith(" +0000")
            assert "\t" in diff_output[1], diff_output[1]
            diff_output[1], new_mtime = diff_output[1].split("\t", 1)
            assert new_mtime.endswith(" +0000")
            assert all("\t" not in line for line in diff_output[2:])
        else:
            assert all("\t" not in line for line in diff_output)
    assert diff_output == expect_stdout
    assert repo.paths["subdir/a.py"].read_bytes().decode("ascii") == newline.join(
        expect_a_py
    )
    assert repo.paths["b.py"].read_bytes().decode("ascii") == f"print(42 ){newline}"
    assert retval == expect_retval


@pytest.mark.parametrize("formatter", [[], ["--formatter=black"], ["--formatter=ruff"]])
def test_main_in_plain_directory(tmp_path, capsys, formatter):
    """Darker works also in a plain directory tree"""
    subdir_a = tmp_path / "subdir_a"
    subdir_c = tmp_path / "subdir_b/subdir_c"
    subdir_a.mkdir()
    subdir_c.mkdir(parents=True)
    (subdir_a / "non-python file.txt").write_text("not  reformatted\n")
    (subdir_a / "python file.py").write_text("import  sys, os\nprint('ok')")
    (subdir_c / "another python file.py").write_text("a  =5")

    retval = darker.__main__.main(
        [*formatter, "--diff", "--check", "--isort", "--lint", "dummy", str(tmp_path)],
    )

    assert retval == 1
    output = capsys.readouterr().out
    output = _replace_diff_timestamps(output)
    assert (
        output
        == dedent(
            """\
            --- subdir_a/python file.py	<timestamp> +0000
            +++ subdir_a/python file.py	<timestamp> +0000
            @@ -1,2 +1,4 @@
            -import  sys, os
            -print('ok')
            +import os
            +import sys
            +
            +print("ok")
            --- subdir_b/subdir_c/another python file.py	<timestamp> +0000
            +++ subdir_b/subdir_c/another python file.py	<timestamp> +0000
            @@ -1 +1 @@
            -a  =5
            +a = 5
            """,
        )
        + LINTING_GUIDE
    )


@pytest.mark.parametrize("formatter", [[], ["--formatter=black"], ["--formatter=ruff"]])
@pytest.mark.parametrize(
    "encoding, text", [(b"utf-8", b"touch\xc3\xa9"), (b"iso-8859-1", b"touch\xe9")]
)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_main_encoding(git_repo, formatter, encoding, text, newline):
    """Encoding and newline of the file is kept unchanged after reformatting"""
    paths = git_repo.add({"a.py": newline.decode("ascii")}, commit="Initial commit")
    edited = [b"# coding: ", encoding, newline, b's="', text, b'"', newline]
    expect = [b"# coding: ", encoding, newline, b's = "', text, b'"', newline]
    paths["a.py"].write_bytes(b"".join(edited))

    retval = darker.__main__.main([*formatter, "a.py"])

    result = paths["a.py"].read_bytes()
    assert retval == 0
    assert result == b"".join(expect)


def test_main_historical(git_repo):
    """Stop if rev2 isn't the working tree and no ``--diff`` or ``--check`` provided"""
    with pytest.raises(ArgumentError):

        darker.__main__.main(["--revision=foo..bar", "."])


@pytest.fixture(scope="module")
def main_historical_ok_repo(request, tmp_path_factory):
    """Git repository fixture for `test_main_historical_ok`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        repo.add({"README": "first"}, commit="Initial commit")
        initial = repo.get_hash()
        repo.add({"README": "second"}, commit="Second commit")
        second = repo.get_hash()

        yield SimpleNamespace(root=repo.root, hash_initial=initial, hash_second=second)


@pytest.mark.parametrize("arguments", [["--diff"], ["--check"], ["--diff", "--check"]])
@pytest.mark.parametrize("src", [".", "foo/..", "{repo_root}"])
def test_main_historical_ok(main_historical_ok_repo, arguments, src):
    """Runs ok for repository root with rev2 specified and ``--diff`` or ``--check``"""
    repo = main_historical_ok_repo
    revision_arg = f"--revision={repo.hash_initial}..{repo.hash_second}"

    darker.__main__.main([*arguments, revision_arg, src.format(repo_root=repo.root)])


def test_main_pre_commit_head(git_repo, monkeypatch):
    """Warn if run by pre-commit, rev2=HEAD and no ``--diff`` or ``--check`` provided"""
    git_repo.add({"a.py": "original = 1"}, commit="Add a.py")
    initial = git_repo.get_hash()
    git_repo.add({"a.py": "modified  = 2"}, commit="Modify a.py")
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", initial)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "HEAD")
    with pytest.warns(
        UserWarning,
        match=re.escape(
            "Darker was called by pre-commit, comparing HEAD to an older commit."
            " As an experimental feature, allowing overwriting of files."
            " See https://github.com/akaihola/darker/issues/180 for details."
        ),
    ):

        result = darker.__main__.main(["--revision=:PRE-COMMIT:", "a.py"])

    assert result == 0


def test_main_historical_pre_commit(git_repo, monkeypatch):
    """Stop if run by pre-commit, rev2 older than HEAD and no ``--diff``/``--check``"""
    git_repo.add({"README.txt": ""}, commit="Initial commit")
    initial = git_repo.get_hash()
    git_repo.add({"a.py": "original"}, commit="Add a.py")
    older_commit = git_repo.get_hash()
    git_repo.add({"a.py": "modified"}, commit="Modify a.py")
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", initial)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", older_commit)
    with pytest.raises(
        ArgumentError,
        match=(
            re.escape(
                f"Can't write reformatted files for revision {older_commit!r}."
                " Either --diff or --check must be used."
            )
        ),
    ):

        darker.__main__.main(["--revision=:PRE-COMMIT:", "a.py"])


@pytest.mark.parametrize("formatter", [[], ["--formatter=black"], ["--formatter=ruff"]])
def test_main_vscode_tmpfile(git_repo, capsys, formatter):
    """Main function handles VSCode `.py.<HASH>.tmp` files correctly"""
    _ = git_repo.add(
        {"a.py": "print ( 'reformat me' ) \n"},
        commit="Initial commit",
    )
    (git_repo.root / "a.py.hash.tmp").write_text("print ( 'reformat me now' ) \n")

    retval = darker.__main__.main([*formatter, "--diff", "a.py.hash.tmp"])

    assert retval == 0
    outerr = capsys.readouterr()
    assert outerr.err == ""
    stdout = _replace_diff_timestamps(outerr.out.replace(str(git_repo.root), ""))
    diff_output = stdout.splitlines(False)
    assert diff_output == [
        "--- a.py.hash.tmp\t<timestamp> +0000",
        "+++ a.py.hash.tmp\t<timestamp> +0000",
        "@@ -1 +1 @@",
        "-print ( 'reformat me now' ) ",
        '+print("reformat me now")',
    ]


def test_print_diff(tmp_path, capsys):
    """print_diff() prints Black-style diff output with 5 lines of context"""
    Path(tmp_path / "a.py").write_text("dummy\n", encoding="utf-8")
    darker.__main__.print_diff(
        Path(tmp_path / "a.py"),
        TextDocument.from_lines(
            [
                "unchanged",
                "removed",
                "kept 1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "changed",
            ],
            mtime="2020-10-08 19:16:22.146405 +0000",
        ),
        TextDocument.from_lines(
            [
                "inserted",
                "unchanged",
                "kept 1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "Changed",
            ],
            mtime="2020-10-08 19:21:09.005501 +0000",
        ),
        root=tmp_path,
        use_color=False,
    )

    assert capsys.readouterr().out.splitlines() == [
        "--- a.py\t2020-10-08 19:16:22.146405 +0000",
        "+++ a.py\t2020-10-08 19:21:09.005501 +0000",
        "@@ -1,7 +1,7 @@",
        "+inserted",
        " unchanged",
        "-removed",
        " kept 1",
        " 2",
        " 3",
        " 4",
        " 5",
        "@@ -9,6 +9,6 @@",
        " 7",
        " 8",
        " 9",
        " 10",
        " 11",
        "-changed",
        "+Changed",
    ]


@pytest.fixture(scope="module")
def maybe_flynt_single_file_repo(request, tmp_path_factory):
    """Git repository fixture for `test_maybe_flynt_single_file`."""
    with unix_and_windows_newline_repos(request, tmp_path_factory) as repos:
        for newline, repo in repos.items():
            repo.add(
                {"test1.py": joinlines(ORIGINAL_SOURCE, newline)}, commit="Initial"
            )
        yield repos


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.kwparametrize(
    dict(exclude=set(), expect=FLYNTED_SOURCE),
    dict(exclude={"**/*"}, expect=MODIFIED_SOURCE),
)
def test_maybe_flynt_single_file(
    maybe_flynt_single_file_repo, encoding, newline, exclude, expect
):
    """Flynt skipped if path matches exclusion patterns, encoding and newline intact"""
    repo = maybe_flynt_single_file_repo[newline]
    edited_linenums_differ = EditedLinenumsDiffer(
        repo.root, RevisionRange("HEAD", ":WORKTREE:")
    )  # pylint: disable=duplicate-code
    src = Path("test1.py")
    content_ = TextDocument.from_lines(
        MODIFIED_SOURCE, encoding=encoding, newline=newline
    )

    result = darker.__main__._maybe_flynt_single_file(
        src, exclude, edited_linenums_differ, content_
    )

    assert result.lines == expect
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.kwparametrize(
    dict(new_content=TextDocument(), expect=b""),
    dict(new_content=TextDocument(lines=["touché"]), expect=b"touch\xc3\xa9\n"),
    dict(
        new_content=TextDocument(lines=["touché"], newline="\r\n"),
        expect=b"touch\xc3\xa9\r\n",
    ),
    dict(
        new_content=TextDocument(lines=["touché"], encoding="iso-8859-1"),
        expect=b"touch\xe9\n",
    ),
)
def test_modify_file(tmp_path, new_content, expect):
    """Encoding and newline are respected when writing a text file on disk"""
    path = tmp_path / "test.py"

    darker.__main__.modify_file(path, new_content)

    result = path.read_bytes()
    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        new_content=TextDocument(lines=['print("foo")']),
        use_color=False,
        expect=('print("foo")\n',),
    ),
    dict(
        new_content=TextDocument(lines=['print("foo")']),
        use_color=False,
        expect=('print("foo")\n',),
    ),
    dict(
        new_content=TextDocument(lines=['print("foo")']),
        use_color=True,
        expect=(
            f'{CYAN}print{RESET}({YELLOW}"{RESET}foo{YELLOW}"{RESET})\n',
            f'{CYAN}print{RESET}({YELLOW}"{RESET}{YELLOW}foo{RESET}{YELLOW}"{RESET})\n',
            # Pygments >=2.4.x, <2.14.0
            f'{BLUE}print{RESET}({YELLOW}"{RESET}foo{YELLOW}"{RESET})\n',
            f'{BLUE}print{RESET}({YELLOW}"{RESET}{YELLOW}foo{RESET}{YELLOW}"{RESET})\n',
            # Pygments 2.14.0, variant 1:
            f'{CYAN}print{RESET}({YELLOW}"{RESET}foo{YELLOW}"{RESET}){WHITE}{RESET}\n',
            # Pygments 2.17.2
            f'{CYAN}print{RESET}({YELLOW}"{RESET}{YELLOW}foo{RESET}{YELLOW}"{RESET})'
            f"{WHITE}{RESET}\n",
        ),
    ),
)
def test_print_source(new_content, use_color, expect, capsys):
    """Highlight is applied only if specified, final newline is handled correctly."""
    darker.__main__.print_source(new_content, use_color=use_color)

    assert capsys.readouterr().out in expect


def test_stdout_path_resolution(git_repo, capsys):
    """When using ``--stdout``, file paths are resolved correctly"""
    git_repo.add({"src/menu.py": "print ( 'foo' )\n"})

    result = darker.__main__.main(["--stdout", "./src/menu.py"])

    assert result == 0
    assert capsys.readouterr().out == 'print("foo")\n'


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_stdout_newlines(git_repo, capsysbinary, newline):
    """When using ``--stdout``, newlines are not duplicated.

    See: https://github.com/akaihola/darker/issues/604

    The `git_repo` fixture is used to ensure that the test doesn't run in the Darker
    repository clone in CI. It helps avoid the Git error message
    "fatal: Not a valid object name origin/master" in the NixOS CI tests.

    """
    if WINDOWS and sys.version_info < (3, 10):
        # See https://bugs.python.org/issue38671
        Path("new-file.py").touch()
    code = f"import collections{newline}import sys{newline}".encode()
    with patch("sys.stdin.buffer.read", return_value=code):

        result = darker.__main__.main(
            ["--stdout", "--isort", "--stdin-filename=new-file.py", "-"],
        )

    assert result == 0
    assert capsysbinary.readouterr().out == code


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_stdout_newlines_subprocess(git_repo, newline):
    """When using ``--stdout``, newlines are not duplicated.

    See: https://github.com/akaihola/darker/issues/604

    The `git_repo` fixture is used to ensure that the test doesn't run in the Darker
    repository clone in CI. It helps avoid the Git error message
    "fatal: Not a valid object name origin/master" in the NixOS CI tests.

    """
    if WINDOWS and sys.version_info < (3, 10):
        # See https://bugs.python.org/issue38671
        Path("new-file.py").touch()
    code = f"import collections{newline}import sys{newline}".encode()
    try:

        darker_subprocess = run(  # nosec
            ["darker", "--stdout", "--isort", "--stdin-filename=new-file.py", "-"],
            input=code,
            stdout=PIPE,
            check=True,
        )

    except CalledProcessError as e:
        if e.stdout:
            output(e.stdout, end="\n")
        if e.stderr:
            output(e.stderr, end="\n")
        raise
    assert darker_subprocess.stdout == code


def test_long_command_length(git_repo):
    """Large amount of changed files does not break Git invocation even on Windows"""
    # For PR #542 - large character count for changed files
    # on windows breaks subprocess
    # Need to exceed 32762 characters
    files = {}
    path = "src"
    for _f in range(0, 4):
        # Of course windows limits the path length too
        path = f"{path}/{randomword(30)}"

    for _d in range(0, 210):
        files[f"{path}/{randomword(30)}.py"] = randomword(10)

    git_repo.add(files, commit="Add all the files")
    result = darker.__main__.main(["--diff", "--check", "src"])
    assert result == 0


@pytest.fixture(scope="module")
def formatter_none_repo(git_repo_m):
    """Create a Git repo with a single file to test a formatter that does nothing."""
    files = git_repo_m.add({"file1.py": "# old content\n"}, commit="Initial")
    files["file1.py"].write_text(
        dedent(
            """
            import sys, os
            print ( 'untouched unformatted code' )
            """
        )
    )
    return files


@pytest.mark.parametrize("has_black", [False, True])
def test_formatter_none(has_black, formatter_none_repo):
    """The dummy formatter works regardless of whether Black is installed or not."""
    with black_present(present=has_black):
        argv = ["--formatter=none", "--isort", "file1.py"]

        result = darker.__main__.main(argv)

    assert result == 0
    expect = dedent(
        """
        import os
        import sys

        print ( 'untouched unformatted code' )
        """
    )
    assert formatter_none_repo["file1.py"].read_text() == expect
