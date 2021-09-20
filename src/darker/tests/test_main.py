"""Unit tests for :mod:`darker.__main__`"""

# pylint: disable=unused-argument

import logging
import re
from argparse import ArgumentError
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from black import find_project_root

import darker.__main__
import darker.import_sorting
from darker.exceptions import MissingPackageError
from darker.git import WORKTREE, RevisionRange
from darker.tests.helpers import isort_present
from darker.utils import TextDocument, joinlines
from darker.verification import NotEquivalentError


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
def run_isort(git_repo, monkeypatch, caplog, request):
    find_project_root.cache_clear()

    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({"test1.py": "original"}, commit="Initial commit")
    paths["test1.py"].write_bytes(b"changed")
    args = getattr(request, "param", ())
    with patch.multiple(
        darker.__main__,
        run_black=Mock(return_value=TextDocument()),
        verify_ast_unchanged=Mock(),
    ), patch("darker.import_sorting.isort_code") as isort_code:
        isort_code.return_value = "dummy isort output"
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
    dict(enable_isort=False, black_config={}, expect=[A_PY_BLACK]),
    dict(enable_isort=True, black_config={}, expect=[A_PY_BLACK_ISORT]),
    dict(
        enable_isort=False,
        black_config={"skip_string_normalization": True},
        expect=[A_PY_BLACK_UNNORMALIZE],
    ),
    dict(
        enable_isort=False,
        black_config={"exclude": re.compile(r"/a\.py$")},
        expect=[],
    ),
    dict(
        enable_isort=True,
        black_config={"exclude": re.compile(r"/a\.py$")},
        expect=[A_PY_ISORT],
    ),
    dict(
        enable_isort=False,
        black_config={"extend_exclude": re.compile(r"/a\.py$")},
        expect=[],
    ),
    dict(
        enable_isort=True,
        black_config={"extend_exclude": re.compile(r"/a\.py$")},
        expect=[A_PY_ISORT],
    ),
    dict(
        enable_isort=False,
        black_config={"force_exclude": re.compile(r"/a\.py$")},
        expect=[],
    ),
    dict(
        enable_isort=True,
        black_config={"force_exclude": re.compile(r"/a\.py$")},
        expect=[A_PY_ISORT],
    ),
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_format_edited_parts(git_repo, enable_isort, black_config, newline, expect):
    """Correct reformatting and import sorting changes are produced

    Also, Black reformatting is skipped for files excluded in Black configuration

    """
    paths = git_repo.add({"a.py": newline, "b.py": newline}, commit="Initial commit")
    paths["a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes(f"print(42 ){newline}".encode("ascii"))

    result = darker.__main__.format_edited_parts(
        Path(git_repo.root),
        [Path("a.py")],
        RevisionRange("HEAD"),
        enable_isort,
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
            RevisionRange("HEAD"),
            True,
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
    with patch.object(
        darker.__main__, "verify_ast_unchanged"
    ) as verify_ast_unchanged, pytest.raises(NotEquivalentError):
        verify_ast_unchanged.side_effect = NotEquivalentError

        _ = list(
            darker.__main__.format_edited_parts(
                git_repo.root,
                [Path("a.py")],
                RevisionRange("HEAD"),
                enable_isort=False,
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
        RevisionRange("HEAD"),
        enable_isort=True,
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
        RevisionRange(rev1, rev2),
        enable_isort=True,
        black_config={},
        report_unmodified=False,
    )

    assert list(result) == [(paths["a.py"], a_py[x[0]], a_py[x[1]]) for x in expect]


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
        arguments=["--check", "--lint", "echo a.py:1: message"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=[f"a.py:1: message {Path('/a.py')}"],
        expect_retval=1,
    ),
    dict(
        arguments=["--diff", "--lint", "echo a.py:1: message"],
        # Windows compatible path assertion using `pathlib.Path()`
        expect_stdout=A_PY_DIFF_BLACK + [f"a.py:1: message {Path('/a.py')}"],
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
):  # pylint: disable=too-many-arguments
    """Main function outputs diffs and modifies files correctly"""
    if root_as_cwd:
        cwd = git_repo.root
        pwd = Path("")
    else:
        cwd = tmp_path_factory.mktemp("not_a_git_repo")
        pwd = git_repo.root
    monkeypatch.chdir(cwd)
    paths = git_repo.add(
        {"pyproject.toml": dedent(pyproject_toml), "a.py": newline, "b.py": newline},
        commit="Initial commit",
    )
    paths["a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes(f"print(42 ){newline}".encode("ascii"))

    retval = darker.__main__.main(arguments + [str(pwd / "a.py")])

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
    assert paths["a.py"].read_bytes().decode("ascii") == newline.join(expect_a_py)
    assert paths["b.py"].read_bytes().decode("ascii") == f"print(42 ){newline}"
    assert retval == expect_retval


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


def test_print_diff(tmp_path, monkeypatch, capsys):
    """print_diff() prints Black-style diff output with 5 lines of context"""
    monkeypatch.chdir(tmp_path)
    Path("a.py").write_text("dummy\n")
    darker.__main__.print_diff(
        Path("a.py"),
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
