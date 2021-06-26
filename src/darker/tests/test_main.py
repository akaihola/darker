"""Unit tests for :mod:`darker.__main__`"""

# pylint: disable=unused-argument

import logging
import os
import re
from argparse import ArgumentError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from black import find_project_root

import darker.__main__
import darker.import_sorting
from darker.git import WORKTREE, RevisionRange
from darker.tests.helpers import isort_present
from darker.utils import TextDocument, joinlines
from darker.verification import NotEquivalentError


def test_isort_option_without_isort(git_repo, caplog):
    """Without isort, provide isort install instructions and error"""
    with isort_present(False), patch.object(
        darker.__main__, "isort", None
    ), pytest.raises(SystemExit):

        darker.__main__.main(["--isort", "."])

    assert (
        "Please run `pip install 'darker[isort]'` to use the `--isort` option."
        in caplog.text
    )


@pytest.fixture
def run_isort(git_repo, monkeypatch, caplog, request):
    find_project_root.cache_clear()

    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'test1.py': 'original'}, commit='Initial commit')
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


@pytest.mark.parametrize(
    "run_isort, isort_args",
    [((), {}), (("--line-length", "120"), {"line_length": 120})],
    indirect=["run_isort"],
)
def test_isort_option_with_isort_calls_sortimports(tmpdir, run_isort, isort_args):
    run_isort.isort_code.assert_called_once_with(
        code="changed", settings_path=str(tmpdir), **isort_args
    )


A_PY = ["import sys", "import os", "print( '42')", ""]
A_PY_BLACK = ["import sys", "import os", "", 'print("42")', ""]
A_PY_BLACK_UNNORMALIZE = ("import sys", "import os", "", "print('42')", "")
A_PY_BLACK_ISORT = ["import os", "import sys", "", 'print("42")', ""]

A_PY_DIFF_BLACK = [
    '--- a.py',
    '+++ a.py',
    '@@ -1,3 +1,4 @@',
    ' import sys',
    ' import os',
    "-print( '42')",
    '+',
    '+print("42")',
    '',
]

A_PY_DIFF_BLACK_NO_STR_NORMALIZE = [
    '--- a.py',
    '+++ a.py',
    '@@ -1,3 +1,4 @@',
    ' import sys',
    ' import os',
    "-print( '42')",
    '+',
    "+print('42')",
    '',
]

A_PY_DIFF_BLACK_ISORT = [
    '--- a.py',
    '+++ a.py',
    '@@ -1,3 +1,4 @@',
    '+import os',
    ' import sys',
    '-import os',
    "-print( '42')",
    '+',
    '+print("42")',
    '',
]


@pytest.mark.parametrize(
    'enable_isort, black_args, expect',
    [
        (False, {}, A_PY_BLACK),
        (True, {}, A_PY_BLACK_ISORT),
        (False, {'skip_string_normalization': True}, A_PY_BLACK_UNNORMALIZE),
    ],
    ids=["black", "black_isort", "black_unnormalize"],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_format_edited_parts(git_repo, enable_isort, black_args, newline, expect):
    """Correct reformatting and import sorting changes are produced"""
    paths = git_repo.add({"a.py": newline, "b.py": newline}, commit="Initial commit")
    paths["a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes("print(42 ){newline}".encode("ascii"))

    result = darker.__main__.format_edited_parts(
        Path(git_repo.root),
        [Path("a.py")],
        RevisionRange("HEAD"),
        enable_isort,
        black_args,
    )

    changes = [
        (path, worktree_content.string, chosen.string, chosen.lines)
        for path, worktree_content, chosen in result
    ]
    expect_changes = [
        (paths["a.py"], newline.join(A_PY), newline.join(expect), tuple(expect[:-1]))
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
                black_args={},
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
        black_args={},
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
        black_args={},
    )

    assert list(result) == [(paths["a.py"], a_py[x[0]], a_py[x[1]]) for x in expect]


@pytest.mark.kwparametrize(
    dict(
        arguments=["--diff"],
        expect_stdout=A_PY_DIFF_BLACK,
    ),
    dict(
        arguments=["--isort"],
        expect_a_py=A_PY_BLACK_ISORT,
    ),
    dict(
        arguments=["--skip-string-normalization", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
    ),
    dict(arguments=[], expect_stdout=[""], expect_a_py=A_PY_BLACK, expect_retval=0),
    dict(
        arguments=["--isort", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK_ISORT,
    ),
    dict(arguments=["--check"], expect_stdout=[""], expect_a_py=A_PY, expect_retval=1),
    dict(
        arguments=["--check", "--diff"],
        expect_stdout=A_PY_DIFF_BLACK,
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--isort"],
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--diff", "--isort"],
        expect_stdout=A_PY_DIFF_BLACK_ISORT,
        expect_retval=1,
    ),
    dict(
        arguments=["--check", "--lint", "echo a.py:1: message"],
        expect_stdout=["a.py:1: message /a.py", ""],
        expect_retval=1,
    ),
    dict(
        arguments=["--diff", "--lint", "echo a.py:1: message"],
        expect_stdout=A_PY_DIFF_BLACK[:-1] + ["a.py:1: message /a.py", ""],
    ),
    # for all test cases, by default there's no output, `a.py` stays unmodified, and the
    # return value is a zero:
    expect_stdout=[""],
    expect_a_py=A_PY,
    expect_retval=0,
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_main(
    git_repo,
    monkeypatch,
    capsys,
    arguments,
    newline,
    expect_stdout,
    expect_a_py,
    expect_retval,
):  # pylint: disable=too-many-arguments
    """Main function outputs diffs and modifies files correctly"""
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({"a.py": newline, "b.py": newline}, commit="Initial commit")
    paths["a.py"].write_bytes(newline.join(A_PY).encode("ascii"))
    paths["b.py"].write_bytes("print(42 ){newline}".encode("ascii"))

    retval = darker.__main__.main(arguments + ['a.py'])

    stdout = capsys.readouterr().out.replace(str(git_repo.root), '')
    assert stdout.replace(os.sep, "/").split("\n") == expect_stdout
    assert paths["a.py"].read_bytes().decode("ascii") == newline.join(expect_a_py)
    assert paths["b.py"].read_bytes().decode("ascii") == "print(42 ){newline}"
    assert retval == expect_retval


@pytest.mark.parametrize(
    "encoding, text", [(b"utf-8", b"touch\xc3\xa9"), (b"iso-8859-1", b"touch\xe9")]
)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_main_encoding(git_repo, encoding, text, newline):
    """Encoding and newline of the file is kept unchanged after reformatting"""
    paths = git_repo.add({"a.py": newline.decode("ascii")}, commit="Initial commit")
    edited = [b"# coding: ", encoding, newline, b's="', text, b'"', newline]
    expect = [b"# coding: ", encoding, newline, b's = "', text, b'"', newline]
    paths["a.py"].write_bytes(b"".join(edited))

    retval = darker.__main__.main(["a.py"])

    result = paths["a.py"].read_bytes()
    assert retval == 0
    assert result == b"".join(expect)


def test_main_historical():
    """Stop if rev2 isn't the working tree and no ``--diff`` or ``--check`` provided"""
    with pytest.raises(ArgumentError):

        darker.__main__.main(["--revision=foo..bar"])


def test_output_diff(tmp_path, monkeypatch, capsys):
    """output_diff() prints Black-style diff output"""
    monkeypatch.chdir(tmp_path)
    Path("a.py").write_text("dummy\n")
    darker.__main__.print_diff(
        Path('a.py'),
        TextDocument.from_lines(
            ["unchanged", "removed", "kept 1", "2", "3", "4", "5", "6", "7", "changed"]
        ),
        TextDocument.from_lines(
            ["inserted", "unchanged", "kept 1", "2", "3", "4", "5", "6", "7", "Changed"]
        ),
    )

    assert capsys.readouterr().out.splitlines() == [
        '--- a.py',
        '+++ a.py',
        '@@ -1,5 +1,5 @@',
        '+inserted',
        ' unchanged',
        '-removed',
        ' kept 1',
        ' 2',
        ' 3',
        '@@ -7,4 +7,4 @@',
        ' 5',
        ' 6',
        ' 7',
        '-changed',
        '+Changed',
    ]


@pytest.mark.parametrize(
    "new_content, expect",
    [
        (TextDocument(), b""),
        (TextDocument(lines=["touché"]), b"touch\xc3\xa9\n"),
        (TextDocument(lines=["touché"], newline="\r\n"), b"touch\xc3\xa9\r\n"),
        (TextDocument(lines=["touché"], encoding="iso-8859-1"), b"touch\xe9\n"),
    ],
)
def test_modify_file(tmp_path, new_content, expect):
    """Encoding and newline are respected when writing a text file on disk"""
    path = tmp_path / "test.py"

    darker.__main__.modify_file(path, new_content)

    result = path.read_bytes()
    assert result == expect
