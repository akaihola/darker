import re
from pathlib import Path
from textwrap import dedent
from unittest.mock import call, patch

import pytest

from darker import black_diff
from darker.__main__ import main
from darker.command_line import parse_command_line


@pytest.fixture
def darker_help_output(capsys):
    with pytest.raises(SystemExit):
        parse_command_line(["--help"])
    return re.sub(r'\s+', ' ', capsys.readouterr().out)


def test_help_description_without_isort_package(without_isort, darker_help_output):
    assert (
        "Please run `pip install 'darker[isort]'` to enable sorting of import "
        "definitions" in darker_help_output
    )


def test_help_isort_option_without_isort_package(without_isort, darker_help_output):
    assert (
        "Please run `pip install 'darker[isort]'` to enable usage of this option."
        in darker_help_output
    )


def test_help_with_isort_package(with_isort, darker_help_output):
    assert "Please run" not in darker_help_output


@pytest.mark.parametrize(
    "options, expect",
    [
        ([], call()),
        (['-c', 'black.cfg'], call(line_length=81, string_normalization=True)),
        (['--config', 'black.cfg'], call(line_length=81, string_normalization=True)),
        (['-S'], call(string_normalization=False)),
        (['--skip-string-normalization'], call(string_normalization=False)),
        (['-l', '90'], call(line_length=90)),
        (['--line-length', '90'], call(line_length=90)),
        (['-c', 'black.cfg', '-S'], call(line_length=81, string_normalization=False)),
        (
            ['-c', 'black.cfg', '-l', '90'],
            call(line_length=90, string_normalization=True),
        ),
        (['-l', '90', '-S'], call(line_length=90, string_normalization=False)),
        (
            ['-c', 'black.cfg', '-l', '90', '-S'],
            call(line_length=90, string_normalization=False),
        ),
    ],
)
def test_black_options(monkeypatch, tmpdir, git_repo, options, expect):
    monkeypatch.chdir(tmpdir)
    (tmpdir / 'pyproject.toml').write("[tool.black]\n")
    (tmpdir / 'black.cfg').write(
        dedent(
            """
            [tool.black]
            line-length = 81
            skip-string-normalization = false
            """
        )
    )
    added_files = git_repo.add(
        {"main.py": 'print("Hello World!")\n'}, commit="Initial commit"
    )
    added_files["main.py"].write('print ("Hello World!")\n')
    with patch.object(black_diff, 'Mode', wraps=black_diff.Mode) as Mode:

        main(options + [str(path) for path in added_files.values()])

    _, expect_args, expect_kwargs = expect
    Mode.assert_called_once_with(*expect_args, **expect_kwargs)


@pytest.mark.parametrize(
    'options, expect',
    [
        (['a.py'], ({Path('a.py')}, False, {}, False, False)),
        (['--isort', 'a.py'], ({Path('a.py')}, True, {}, False, False)),
        (
            ['--config', 'my.cfg', 'a.py'],
            ({Path('a.py')}, False, {'config': 'my.cfg'}, False, False),
        ),
        (
            ['--line-length', '90', 'a.py'],
            ({Path('a.py')}, False, {'line_length': 90}, False, False),
        ),
        (
            ['--skip-string-normalization', 'a.py'],
            ({Path('a.py')}, False, {'skip_string_normalization': True}, False, False),
        ),
        (['--diff', 'a.py'], ({Path('a.py')}, False, {}, True, False)),
    ],
)
def test_options(options, expect):
    with patch('darker.__main__.format_edited_parts') as format_edited_parts:

        retval = main(options)

    format_edited_parts.assert_called_once_with(*expect)
    assert retval == 0


@pytest.mark.parametrize(
    'check, all_unchanged, expect_retval',
    [(False, True, 0), (False, False, 0), (True, True, 0), (True, False, 1)],
)
def test_main_retval(check, all_unchanged, expect_retval):
    """main() return value is correct based on --check and the need to reformat files"""
    with patch("darker.__main__.format_edited_parts") as format_edited_parts:
        format_edited_parts.return_value = all_unchanged
        check_arg_maybe = ['--check'] if check else []

        retval = main(check_arg_maybe + ['a.py'])

    assert retval == expect_retval
