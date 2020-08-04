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

        darker.__main__.format_edited_parts([], False, {}, True, False)


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

A_PY_DIFF_BLACK_ISORT = [
    '--- /a.py',
    '+++ /a.py',
    '@@ -1,3 +1,4 @@',
    '',
    '+import os',
    ' import sys',
    '-import os',
    "-print( '42')",
    '+',
    '+print("42")',
    '',
]


@pytest.mark.parametrize(
    'isort, black_args, print_diff, expect_stdout, expect_a_py',
    [
        (False, {}, True, A_PY_DIFF_BLACK, A_PY),
        (True, {}, False, [''], A_PY_BLACK_ISORT,),
        (
            False,
            {'skip_string_normalization': True},
            True,
            A_PY_DIFF_BLACK_NO_STR_NORMALIZE,
            A_PY,
        ),
        (False, {}, False, [''], A_PY_BLACK),
        (True, {}, True, A_PY_DIFF_BLACK_ISORT, A_PY,),
    ],
)
def test_format_edited_parts(
    git_repo,
    monkeypatch,
    capsys,
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
        [Path('a.py')], isort, black_args, print_diff, False
    )
    stdout = capsys.readouterr().out.replace(str(git_repo.root), '')
    assert stdout.split('\n') == expect_stdout
    assert paths['a.py'].readlines(cr=False) == expect_a_py
    assert paths['b.py'].readlines(cr=False) == ['print(42 )', '']
