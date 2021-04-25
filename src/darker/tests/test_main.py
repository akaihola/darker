from pathlib import Path
from subprocess import check_call
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest
from black import find_project_root

import darker.__main__
import darker.import_sorting
from darker.git import RevisionRange
from darker.utils import TextDocument


def test_isort_option_without_isort(tmpdir, without_isort, caplog):
    check_call(["git", "init"], cwd=tmpdir)
    with patch.object(darker.__main__, "isort", None), pytest.raises(SystemExit):

        darker.__main__.main(["--isort", str(tmpdir)])

    assert (
        "Please run `pip install 'darker[isort]'` to use the `--isort` option."
        in caplog.text
    )


@pytest.fixture
def run_isort(git_repo, monkeypatch, caplog, request):
    find_project_root.cache_clear()

    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'test1.py': 'original'}, commit='Initial commit')
    paths['test1.py'].write('changed')
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


def test_format_edited_parts_empty():
    with pytest.raises(ValueError):

        list(
            darker.__main__.format_edited_parts(
                [], RevisionRange("HEAD"), False, [], {}
            )
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
    paths["a.py"].write(newline.join(A_PY))
    paths["b.py"].write(f"print(42 ){newline}")

    result = darker.__main__.format_edited_parts(
        [Path("a.py")], RevisionRange("HEAD"), enable_isort, [], black_args
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
    paths = git_repo.add({'a.py': 'pass\n', 'b.py': 'pass\n'}, commit='Initial commit')
    paths['a.py'].write('"properly"\n"formatted"\n')
    paths['b.py'].write('"not"\n"checked"\n')

    result = list(
        darker.__main__.format_edited_parts(
            [Path("a.py")], RevisionRange("HEAD"), True, [], {}
        )
    )

    assert result == []


def test_format_edited_parts_lint(git_repo):
    """Unit test for ``format_edited_parts`` with linters"""
    paths = git_repo.add({"a.py": "pass\n"}, commit="Initial commit")
    paths["a.py"].write('"properly"\n"formatted"\n')
    with patch.object(darker.__main__, "run_linter") as run_linter:

        _ = list(
            darker.__main__.format_edited_parts(
                [Path("a.py")],
                RevisionRange("HEAD"),
                False,
                ["linter1", "linter2 command line"],
                {},
            )
        )

        assert run_linter.call_args_list == [
            call("linter1", git_repo.root, {Path("a.py")}, RevisionRange("HEAD")),
            call(
                "linter2 command line",
                git_repo.root,
                {Path("a.py")},
                RevisionRange("HEAD"),
            ),
        ]


@pytest.mark.parametrize(
    'arguments, expect_stdout, expect_a_py, expect_retval',
    [
        (['--diff'], A_PY_DIFF_BLACK, A_PY, 0),
        (['--isort'], [''], A_PY_BLACK_ISORT, 0),
        (
            ['--skip-string-normalization', '--diff'],
            A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
            A_PY,
            0,
        ),
        ([], [''], A_PY_BLACK, 0),
        (['--isort', '--diff'], A_PY_DIFF_BLACK_ISORT, A_PY, 0),
        (['--check'], [''], A_PY, 1),
        (['--check', '--diff'], A_PY_DIFF_BLACK, A_PY, 1),
        (['--check', '--isort'], [''], A_PY, 1),
        (['--check', '--diff', '--isort'], A_PY_DIFF_BLACK_ISORT, A_PY, 1),
    ],
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
    paths["a.py"].write(newline.join(A_PY))
    paths["b.py"].write("print(42 ){newline}")

    retval = darker.__main__.main(arguments + ['a.py'])

    stdout = capsys.readouterr().out.replace(str(git_repo.root), '')
    assert stdout.split("\n") == expect_stdout
    assert paths["a.py"].read("br").decode("ascii") == newline.join(expect_a_py)
    assert paths["b.py"].read("br").decode("ascii") == "print(42 ){newline}"
    assert retval == expect_retval


@pytest.mark.parametrize(
    "encoding, text", [(b"utf-8", b"touch\xc3\xa9"), (b"iso-8859-1", b"touch\xe9")]
)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_main_encoding(git_repo, encoding, text, newline):
    """Encoding and newline of the file is kept unchanged after reformatting"""
    paths = git_repo.add({"a.py": newline}, commit="Initial commit")
    edited = [b"# coding: ", encoding, newline, b's="', text, b'"', newline]
    expect = [b"# coding: ", encoding, newline, b's = "', text, b'"', newline]
    paths["a.py"].write(b"".join(edited), "wb")

    retval = darker.__main__.main(["a.py"])

    result = paths["a.py"].read("br")
    assert retval == 0
    assert result == b"".join(expect)


def test_output_diff(capsys):
    """output_diff() prints Black-style diff output"""
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
