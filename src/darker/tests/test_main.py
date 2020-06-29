from pathlib import Path
from subprocess import check_call
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import darker.__main__
import darker.import_sorting


def test_isort_option_without_isort(tmpdir, without_isort, caplog):
    check_call(["git", "init"], cwd=tmpdir)
    with patch.object(darker.__main__, "SortImports", None), pytest.raises(SystemExit):

        darker.__main__.main(["--isort", str(tmpdir)])

    assert (
        "Please run `pip install 'darker[isort]'` to use the `--isort` option."
        in caplog.text
    )


@pytest.fixture
def run_isort(tmpdir, monkeypatch, caplog):
    monkeypatch.chdir(tmpdir)
    check_call(["git", "init"], cwd=tmpdir)
    with patch.multiple(
        darker.__main__,
        run_black=Mock(return_value=([], [])),
        git_diff_name_only=Mock(return_value=[Path(tmpdir / 'test1.py')]),
    ), patch("darker.import_sorting.SortImports"):
        darker.__main__.main(["--isort", "./test1.py"])
        return SimpleNamespace(
            SortImports=darker.import_sorting.SortImports, caplog=caplog
        )


def test_isort_option_with_isort(run_isort):
    assert "Please run" not in run_isort.caplog.text


def test_isort_option_with_isort_calls_sortimports(run_isort):
    run_isort.SortImports.assert_called_once_with(
        str(Path.cwd() / "test1.py"),
        force_grid_wrap=0,
        include_trailing_comma=True,
        line_length=88,
        multi_line_output=3,
        use_parentheses=True,
        quiet=True,
    )


def test_format_edited_parts_empty():
    with pytest.raises(ValueError):

        darker.__main__.format_edited_parts([], False, {}, True)


def test_format_edited_parts_isort_print_diff():
    with pytest.raises(NotImplementedError):

        darker.__main__.format_edited_parts([Path('test.py')], True, {}, True)


A_PY = ['import sys', 'import os', "print( '42')", '']
A_PY_BLACK = ['import sys', 'import os', '', 'print("42")', '']
A_PY_BLACK_ISORT = ['import os', 'import sys', '', 'print("42")', '']

A_PY_DIFF_BLACK = [
    '--- /a.py',
    '+++ /a.py',
    '@@ -1,3 +1,4 @@',
    '',
    ' import sys',
    ' import os',
    "-print( '42')",
    '+',
    '+print("42")',
    '',
]

A_PY_DIFF_BLACK_NO_STR_NORMALIZE = [
    '--- /a.py',
    '+++ /a.py',
    '@@ -1,3 +1,4 @@',
    '',
    ' import sys',
    ' import os',
    "-print( '42')",
    '+',
    "+print('42')",
    '',
]


@pytest.mark.parametrize(
    'srcs, isort, black_args, print_diff, expect_stdout, expect_a_py',
    [
        (['a.py'], False, {}, True, A_PY_DIFF_BLACK, A_PY),
        (['a.py'], True, {}, False, [''], A_PY_BLACK_ISORT),
        (
            ['a.py'],
            False,
            {'skip_string_normalization': True},
            True,
            A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
            A_PY,
        ),
        (['a.py'], False, {}, False, [''], A_PY_BLACK),
    ],
)
def test_format_edited_parts(
    git_repo,
    monkeypatch,
    capsys,
    srcs,
    isort,
    black_args,
    print_diff,
    expect_stdout,
    expect_a_py,
):
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({'a.py': '\n', 'b.py': '\n'}, commit='Initial commit')
    paths['a.py'].write('\n'.join(A_PY))
    paths['b.py'].write('print(42 )\n')
    darker.__main__.format_edited_parts(
        [Path(src) for src in srcs], isort, black_args, print_diff
    )
    stdout = capsys.readouterr().out.replace(str(git_repo.root), '')
    assert stdout.split('\n') == expect_stdout
    assert paths['a.py'].readlines(cr=False) == expect_a_py
    assert paths['b.py'].readlines(cr=False) == ['print(42 )', '']
