"""Unit tests for :mod:`darker.__main__`"""

# pylint: disable=unused-argument,too-many-arguments,use-dict-literal,protected-access

import logging
import re
from argparse import ArgumentError
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

import darker.__main__
import darker.import_sorting
import darker.linting
from darker.config import Exclusions
from darker.exceptions import MissingPackageError
from darker.git import WORKTREE, EditedLinenumsDiffer, RevisionRange
from darker.tests.helpers import isort_present
from darker.utils import TextDocument, joinlines
from darker.verification import NotEquivalentError


def _replace_diff_timestamps(text, replacement="<timestamp>"):
    return re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d\d\d\d", replacement, text)


def test_isort_option_without_isort(git_repo, caplog):
    """Without isort, provide isort install instructions and error"""
    with isort_present(False), patch.object(
        darker.__main__, "isort", None
    ), pytest.raises(MissingPackageError) as exc_info:

        darker.__main__.main(["--isort", "."])

    assert (
        str(exc_info.value)
        == "Please run `pip install darker[isort]` to use the `--isort` option."
    )


@pytest.fixture
def run_isort(git_repo, monkeypatch, caplog, request, find_project_root_cache_clear):
    """Fixture for running Darker with requested arguments and a patched `isort`

    Provides an `run_isort.isort_code` mock object which allows checking whether and how
    the `isort.code()` function was called.

    """
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({"test1.py": "original"}, commit="Initial commit")
    paths["test1.py"].write_bytes(b"changed")
    args = getattr(request, "param", ())
    isorted_code = "import os; import sys;"
    blacken_code = "import os\nimport sys\n"
    patch_run_black_ctx = patch.object(
        darker.__main__, "run_black", return_value=TextDocument(blacken_code)
    )
    with patch_run_black_ctx, patch("darker.import_sorting.isort_code") as isort_code:
        isort_code.return_value = isorted_code
        darker.__main__.main(["--isort", "./test1.py", *args])
        return SimpleNamespace(
            isort_code=darker.import_sorting.isort_code, caplog=caplog
        )


def test_isort_option_with_isort(run_isort):
    assert "Please run" not in run_isort.caplog.text


@pytest.mark.kwparametrize(
    dict(run_isort=(), isort_args={}),
    dict(run_isort=("--line-length", "120"), isort_args={"line_length": 120}),
    indirect=["run_isort"],
)
def test_isort_option_with_isort_calls_sortimports(tmpdir, run_isort, isort_args):
    run_isort.isort_code.assert_called_once_with(
        code="changed", settings_path=str(tmpdir), **isort_args
    )


A_PY = ["import sys", "import os", "print( '42')", ""]
A_PY_ISORT = ["import os", "import sys", "", "print( '42')", ""]
A_PY_BLACK = ["import sys", "import os", "", 'print("42")', ""]
A_PY_BLACK_UNNORMALIZE = ("import sys", "import os", "", "print('42')", "")
A_PY_BLACK_ISORT = ["import os", "import sys", "", 'print("42")', ""]

A_PY_DIFF_BLACK = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    " import sys",
    " import os",
    "-print( '42')",
    "+",
    '+print("42")',
]

A_PY_DIFF_BLACK_NO_STR_NORMALIZE = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    " import sys",
    " import os",
    "-print( '42')",
    "+",
    "+print('42')",
]

A_PY_DIFF_BLACK_ISORT = [
    "--- a.py",
    "+++ a.py",
    "@@ -1,3 +1,4 @@",
    "+import os",
    " import sys",
    "-import os",
    "-print( '42')",
    "+",
    '+print("42")',
]


@pytest.mark.kwparametrize(
    dict(
        isort_exclude={"**/*"},
        expect=[A_PY_BLACK],
    ),
    dict(
        expect=[A_PY_BLACK_ISORT],
    ),
    dict(
        black_config={"skip_string_normalization": True},
        isort_exclude={"**/*"},
        expect=[A_PY_BLACK_UNNORMALIZE],
    ),
    dict(
        black_exclude={Path("a.py")},
        isort_exclude={"**/*"},
        expect=[],
    ),
    dict(
        black_exclude={Path("a.py")},
        expect=[A_PY_ISORT],
    ),
    black_config={},
    black_exclude=set(),
    isort_exclude=set(),
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_format_edited_parts(
    git_repo, black_config, black_exclude, isort_exclude, newline, expect
):
    """Correct reformatting and import sorting changes are produced

    Black reformatting is done even if a file is excluded in Black configuration.
    File exclusion is done in Darker before calling
    :func:`~darker.__main__.format_edited_parts`.

    """
    paths = git_repo.add({"a.py": newline, "b.py": newline}, commit="Initial commit")
    paths["a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes(f"print(42 ){newline}".encode("ascii"))

    result = darker.__main__.format_edited_parts(
        Path(git_repo.root),
        {Path("a.py")},
        Exclusions(black=black_exclude, isort=isort_exclude),
        RevisionRange("HEAD", ":WORKTREE:"),
        black_config,
        report_unmodified=False,
    )

    changes = [
        (path, worktree_content.string, chosen.string, chosen.lines)
        for path, worktree_content, chosen in result
    ]
    expect_changes = [
        (
            paths["a.py"],
            newline.join(A_PY),
            newline.join(expect_lines),
            tuple(expect_lines[:-1]),
        )
        for expect_lines in expect
    ]
    assert changes == expect_changes


def test_format_edited_parts_all_unchanged(git_repo, monkeypatch):
    """``format_edited_parts()`` yields nothing if no reformatting was needed"""
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({"a.py": "pass\n", "b.py": "pass\n"}, commit="Initial commit")
    paths["a.py"].write_bytes(b'"properly"\n"formatted"\n')
    paths["b.py"].write_bytes(b'"not"\n"checked"\n')

    result = list(
        darker.__main__.format_edited_parts(
            Path(git_repo.root),
            {Path("a.py"), Path("b.py")},
            Exclusions(black=set(), isort=set()),
            RevisionRange("HEAD", ":WORKTREE:"),
            {},
            report_unmodified=False,
        )
    )

    assert result == []


def test_format_edited_parts_ast_changed(git_repo, caplog):
    """``darker.__main__.format_edited_parts()`` when reformatting changes the AST"""
    caplog.set_level(logging.DEBUG, logger="darker.__main__")
    paths = git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
    paths["a.py"].write_bytes(b"8\n7\n6\n5\n4\n3\n2\n1\n")
    mock_ctx = patch.object(
        darker.verification.ASTVerifier, "is_equivalent_to_baseline", return_value=False
    )
    with mock_ctx, pytest.raises(NotEquivalentError):
        _ = list(
            darker.__main__.format_edited_parts(
                git_repo.root,
                {Path("a.py")},
                Exclusions(black=set(), isort={"**/*"}),
                RevisionRange("HEAD", ":WORKTREE:"),
                black_config={},
                report_unmodified=False,
            )
        )
    a_py = str(paths["a.py"])
    main = "darker.__main__:__main__.py"
    log = [
        line
        for line in re.sub(r":\d+", "", caplog.text).splitlines()
        if " lines of context " in line
    ]
    assert log == [
        f"DEBUG    {main} AST verification of {a_py} with 0 lines of context failed",
        f"DEBUG    {main} Trying with 5 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 5 lines of context failed",
        f"DEBUG    {main} Trying with 7 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 7 lines of context failed",
        f"DEBUG    {main} Trying with 8 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 8 lines of context failed",
    ]


def test_format_edited_parts_isort_on_already_formatted(git_repo):
    """An already correctly formatted file after ``isort`` is simply skipped"""
    before = [
        "import a",
        "import b",
        "",
        "a.foo()",
        "b.bar()",
    ]
    after = [
        "import b",
        "",
        "b.bar()",
    ]
    paths = git_repo.add({"a.py": joinlines(before)}, commit="Initial commit")
    paths["a.py"].write_text(joinlines(after))

    result = darker.__main__.format_edited_parts(
        git_repo.root,
        {Path("a.py")},
        Exclusions(black=set(), isort=set()),
        RevisionRange("HEAD", ":WORKTREE:"),
        black_config={},
        report_unmodified=False,
    )

    assert list(result) == []


@pytest.mark.kwparametrize(
    dict(rev1="HEAD^", rev2="HEAD", expect=[]),
    dict(rev1="HEAD^", rev2=WORKTREE, expect=[(":WORKTREE:", "reformatted")]),
    dict(rev1="HEAD", rev2=WORKTREE, expect=[(":WORKTREE:", "reformatted")]),
)
def test_format_edited_parts_historical(git_repo, rev1, rev2, expect):
    """``format_edited_parts()`` is correct for different commit pairs"""
    a_py = {
        "HEAD^": TextDocument.from_lines(
            [
                "import a",
                "from b import bar, foo",
                "",
                "a.foo()",
                "bar()",
            ]
        ),
        "HEAD": TextDocument.from_lines(
            [
                "from b import bar, foo",
                "",
                "bar()",
            ]
        ),
        ":WORKTREE:": TextDocument.from_lines(
            [
                "from b import foo, bar",
                "",
                "bar( )",
            ]
        ),
        "reformatted": TextDocument.from_lines(
            [
                "from b import bar, foo",
                "",
                "bar()",
            ]
        ),
    }
    paths = git_repo.add({"a.py": a_py["HEAD^"].string}, commit="Initial commit")
    git_repo.add({"a.py": a_py["HEAD"].string}, commit="Modified a.py")
    paths["a.py"].write_text(a_py[":WORKTREE:"].string)

    result = darker.__main__.format_edited_parts(
        git_repo.root,
        {Path("a.py")},
        Exclusions(black=set(), isort=set()),
        RevisionRange(rev1, rev2),
        black_config={},
        report_unmodified=False,
    )

    assert list(result) == [(paths["a.py"], a_py[x[0]], a_py[x[1]]) for x in expect]


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
    rev1="HEAD",
    rev2=":WORKTREE",
    rev2_content="import  original\nprint( original )\n",
    rev2_isorted="import  original\nprint( original )\n",
    enable_isort=False,
    black_config={},
    expect="import  original\nprint( original )\n",
)
def test_blacken_single_file(
    git_repo,
    relative_path,
    rev1,
    rev2,
    rev2_content,
    rev2_isorted,
    enable_isort,
    black_config,
    expect,
):
    """Test for ``_blacken_single_file``"""
    git_repo.add(
        {"file.py": "import  original\nprint( original )\n"}, commit="Initial commit"
    )
    result = darker.__main__._blacken_single_file(
        git_repo.root,
        Path(relative_path),
        Path("file.py"),
        EditedLinenumsDiffer(git_repo.root, RevisionRange(rev1, rev2)),
        TextDocument(rev2_content),
        TextDocument(rev2_isorted),
        enable_isort,
        black_config,
    )

    assert result.string == expect


@pytest.mark.kwparametrize(
    dict(arguments=["--diff"], expect_stdout=A_PY_DIFF_BLACK),
    dict(arguments=["--isort"], expect_a_py=A_PY_BLACK_ISORT),
    dict(
        arguments=["--skip-string-normalization", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
    ),
    dict(arguments=[], expect_a_py=A_PY_BLACK, expect_retval=0),
    dict(arguments=["--isort", "--diff"], expect_stdout=A_PY_DIFF_BLACK_ISORT),
    dict(arguments=["--check"], expect_a_py=A_PY, expect_retval=1),
    dict(
        arguments=["--check", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK,
        expect_retval=1,
    ),
    dict(arguments=["--check", "--isort"], expect_retval=1),
    dict(
        arguments=["--check", "--diff", "--isort"],
        expect_stdout=A_PY_DIFF_BLACK_ISORT,
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--lint", "echo subdir/a.py:1: message"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=["", f"subdir/a.py:1: message {Path('/subdir/a.py')}"],
        expect_retval=1,
    ),
    dict(
        arguments=["--diff", "--lint", "echo subdir/a.py:1: message"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=A_PY_DIFF_BLACK
        + ["", f"subdir/a.py:1: message {Path('/subdir/a.py')}"],
        expect_retval=1,
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           exclude = 'a.py'
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           exclude = 'a.py'
           """,
        expect_stdout=[],
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           extend_exclude = 'a.py'
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           extend_exclude = 'a.py'
           """,
        expect_stdout=[],
    ),
    dict(
        arguments=[],
        pyproject_toml="""
           [tool.black]
           force_exclude = 'a.py'
           """,
        expect_a_py=A_PY,
    ),
    dict(
        arguments=["--diff"],
        pyproject_toml="""
           [tool.black]
           force_exclude = 'a.py'
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
    git_repo,
    monkeypatch,
    capsys,
    find_project_root_cache_clear,
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
    if root_as_cwd:
        cwd = git_repo.root
        pwd = Path("")
    else:
        cwd = tmp_path_factory.mktemp("not_a_git_repo")
        pwd = git_repo.root
    monkeypatch.chdir(cwd)
    paths = git_repo.add(
        {
            "pyproject.toml": dedent(pyproject_toml),
            "subdir/a.py": newline,
            "b.py": newline,
        },
        commit="Initial commit",
    )
    paths["subdir/a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes(f"print(42 ){newline}".encode("ascii"))

    retval = darker.__main__.main(arguments + [str(pwd / "subdir")])

    stdout = capsys.readouterr().out.replace(str(git_repo.root), "")
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
    assert paths["subdir/a.py"].read_bytes().decode("ascii") == newline.join(
        expect_a_py
    )
    assert paths["b.py"].read_bytes().decode("ascii") == f"print(42 ){newline}"
    assert retval == expect_retval


def test_main_in_plain_directory(tmp_path, capsys):
    """Darker works also in a plain directory tree"""
    subdir_a = tmp_path / "subdir_a"
    subdir_c = tmp_path / "subdir_b/subdir_c"
    subdir_a.mkdir()
    subdir_c.mkdir(parents=True)
    (subdir_a / "non-python file.txt").write_text("not  reformatted\n")
    (subdir_a / "python file.py").write_text("import  sys, os\nprint('ok')")
    (subdir_c / "another python file.py").write_text("a  =5")
    with patch.object(darker.linting, "run_linter") as run_linter:

        retval = darker.__main__.main(
            ["--diff", "--check", "--isort", "--lint", "my-linter", str(tmp_path)]
        )

    assert retval == 1
    assert run_linter.call_args_list == [
        call(
            "my-linter",
            tmp_path,
            {
                Path("subdir_a/python file.py"),
                Path("subdir_b/subdir_c/another python file.py"),
            },
            RevisionRange(rev1="HEAD", rev2=":WORKTREE:"),
            False,
        )
    ]
    output = capsys.readouterr().out
    output = _replace_diff_timestamps(output)
    assert output == dedent(
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
        """
    )


@pytest.mark.parametrize(
    "encoding, text", [(b"utf-8", b"touch\xc3\xa9"), (b"iso-8859-1", b"touch\xe9")]
)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_main_encoding(
    git_repo, find_project_root_cache_clear, encoding, text, newline
):
    """Encoding and newline of the file is kept unchanged after reformatting"""
    paths = git_repo.add({"a.py": newline.decode("ascii")}, commit="Initial commit")
    edited = [b"# coding: ", encoding, newline, b's="', text, b'"', newline]
    expect = [b"# coding: ", encoding, newline, b's = "', text, b'"', newline]
    paths["a.py"].write_bytes(b"".join(edited))

    retval = darker.__main__.main(["a.py"])

    result = paths["a.py"].read_bytes()
    assert retval == 0
    assert result == b"".join(expect)


def test_main_historical(git_repo):
    """Stop if rev2 isn't the working tree and no ``--diff`` or ``--check`` provided"""
    with pytest.raises(ArgumentError):

        darker.__main__.main(["--revision=foo..bar", "."])


@pytest.mark.parametrize("arguments", [["--diff"], ["--check"], ["--diff", "--check"]])
@pytest.mark.parametrize("src", [".", "foo/..", "{git_repo_root}"])
def test_main_historical_ok(git_repo, arguments, src):
    """Runs ok for repository root with rev2 specified and ``--diff`` or ``--check``"""
    git_repo.add({"README": "first"}, commit="Initial commit")
    initial = git_repo.get_hash()
    git_repo.add({"README": "second"}, commit="Second commit")
    second = git_repo.get_hash()

    darker.__main__.main(
        arguments
        + [f"--revision={initial}..{second}", src.format(git_repo_root=git_repo.root)]
    )


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
                f"Can't write reformatted files for revision '{older_commit}'."
                " Either --diff or --check must be used."
            )
        ),
    ):

        darker.__main__.main(["--revision=:PRE-COMMIT:", "a.py"])


def test_main_vscode_tmpfile(git_repo, capsys):
    """Main function handles VSCode `.py.<HASH>.tmp` files correctly"""
    _ = git_repo.add(
        {"a.py": "print ( 'reformat me' ) \n"},
        commit="Initial commit",
    )
    (git_repo.root / "a.py.hash.tmp").write_text("print ( 'reformat me now' ) \n")

    retval = darker.__main__.main(["--diff", "a.py.hash.tmp"])

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
            '\x1b[36mprint\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00mfoo'
            + '\x1b[33m"\x1b[39;49;00m)\n',
            '\x1b[36mprint\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00m\x1b[33mfoo'
            + '\x1b[39;49;00m\x1b[33m"\x1b[39;49;00m)\n',
            # Pygments 2.4.x:
            '\x1b[34mprint\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00mfoo'
            + '\x1b[33m"\x1b[39;49;00m)\n',
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
