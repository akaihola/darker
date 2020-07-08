from pathlib import Path
from subprocess import check_call
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from black import find_project_root

import darker.__main__
import darker.import_sorting


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
        darker.__main__, run_black=Mock(return_value=[]), verify_ast_unchanged=Mock(),
    ), patch("darker.import_sorting.isort.code"):
        darker.__main__.main(["--isort", "./test1.py", *args])
        return SimpleNamespace(
            isort_code=darker.import_sorting.isort.code, caplog=caplog
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

        list(darker.__main__.format_edited_parts([], "HEAD", False, [], {}))


A_PY = ['import sys', 'import os', "print( '42')", '']
A_PY_BLACK = ['import sys', 'import os', '', 'print("42")', '']
A_PY_BLACK_UNNORMALIZE = ['import sys', 'import os', '', "print('42')", '']
A_PY_BLACK_ISORT = ['import os', 'import sys', '', 'print("42")', '']

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
)
def test_format_edited_parts(git_repo, monkeypatch, enable_isort, black_args, expect):
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'a.py': '\n', 'b.py': '\n'}, commit='Initial commit')
    paths['a.py'].write('\n'.join(A_PY))
    paths['b.py'].write('print(42 )\n')

    changes = list(
        darker.__main__.format_edited_parts(
            [Path("a.py")], "HEAD", enable_isort, [], black_args
        )
    )

    expect_changes = [(paths['a.py'], '\n'.join(A_PY), '\n'.join(expect), expect[:-1])]
    assert changes == expect_changes


def test_format_edited_parts_all_unchanged(git_repo, monkeypatch):
    """``format_edited_parts()`` yields nothing if no reformatting was needed"""
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'a.py': 'pass\n', 'b.py': 'pass\n'}, commit='Initial commit')
    paths['a.py'].write('"properly"\n"formatted"\n')
    paths['b.py'].write('"not"\n"checked"\n')

    result = list(
        darker.__main__.format_edited_parts([Path("a.py")], "HEAD", True, [], {})
    )

    assert result == []


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
def test_main(
    git_repo, monkeypatch, capsys, arguments, expect_stdout, expect_a_py, expect_retval
):  # pylint: disable=too-many-arguments
    """Main function outputs diffs and modifies files correctly"""
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'a.py': '\n', 'b.py': '\n'}, commit='Initial commit')
    paths['a.py'].write('\n'.join(A_PY))
    paths['b.py'].write('print(42 )\n')

    retval = darker.__main__.main(arguments + ['a.py'])

    stdout = capsys.readouterr().out.replace(str(git_repo.root), '')
    assert stdout.split('\n') == expect_stdout
    assert paths['a.py'].readlines(cr=False) == expect_a_py
    assert paths['b.py'].readlines(cr=False) == ['print(42 )', '']
    assert retval == expect_retval


def test_output_diff(capsys):
    """output_diff() prints Black-style diff output"""
    darker.__main__.print_diff(
        Path('a.py'),
        'unchanged\nremoved\nkept 1\n2\n3\n4\n5\n6\n7\nchanged\n',
        ['inserted', 'unchanged', 'kept 1', '2', '3', '4', '5', '6', '7', 'Changed'],
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
