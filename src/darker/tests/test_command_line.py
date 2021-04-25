import re
from importlib import reload
from pathlib import Path
from textwrap import dedent
from unittest.mock import DEFAULT, Mock, call, patch

import pytest
import toml

import darker.help
from darker import black_diff
from darker.__main__ import main
from darker.command_line import make_argument_parser, parse_command_line
from darker.git import RevisionRange
from darker.tests.helpers import filter_dict, raises_if_exception
from darker.utils import TextDocument, joinlines

pytestmark = pytest.mark.usefixtures("find_project_root_cache_clear")


@pytest.mark.parametrize("require_src, expect", [(False, []), (True, SystemExit)])
def test_make_argument_parser(require_src, expect):
    """Parser from ``make_argument_parser()`` fails if src required but not provided"""
    parser = make_argument_parser(require_src)
    with raises_if_exception(expect):

        args = parser.parse_args([])

        assert args.src == expect


@pytest.fixture
def darker_help_output(capsys):
    """Test for ``--help`` option output"""
    # Make sure the description is re-rendered since its content depends on whether
    # isort is installed or not:
    reload(darker.help)
    with pytest.raises(SystemExit):
        parse_command_line(["--help"])
    return re.sub(r'\s+', ' ', capsys.readouterr().out)


@pytest.mark.parametrize(
    "config, argv, expect",
    [
        (None, [], SystemExit),
        (
            None,
            ["file.py"],
            {"src": ["file.py"]},
        ),
        (
            {"src": ["file.py"]},
            [],
            {"src": ["file.py"]},
        ),
        (
            {"src": ["file.py"]},
            ["file.py"],
            {"src": ["file.py"]},
        ),
        (
            {"src": ["file1.py"]},
            ["file2.py"],
            {"src": ["file2.py"]},
        ),
    ],
)
def test_parse_command_line_config_src(
    tmpdir,
    monkeypatch,
    config,
    argv,
    expect,
):
    """The ``src`` positional argument from config and cmdline is handled correctly"""
    monkeypatch.chdir(tmpdir)
    if config is not None:
        toml.dump({"tool": {"darker": config}}, tmpdir / "pyproject.toml")
    with raises_if_exception(expect):

        args, effective_cfg, modified_cfg = parse_command_line(argv)

        assert filter_dict(args.__dict__, "src") == expect
        assert filter_dict(effective_cfg, "src") == expect
        assert filter_dict(modified_cfg, "src") == expect


@pytest.mark.parametrize(
    "argv, expect_value, expect_config, expect_modified",
    [
        (["."], ("src", ["."]), ("src", ["."]), ("src", ["."])),
        (
            ["."],
            ("revision", "HEAD"),
            ("revision", "HEAD"),
            ("revision", ...),
        ),
        (
            ["-rmaster", "."],
            ("revision", "master"),
            ("revision", "master"),
            ("revision", "master"),
        ),
        (
            ["--revision", "HEAD", "."],
            ("revision", "HEAD"),
            ("revision", "HEAD"),
            ("revision", ...),
        ),
        (["."], ("diff", False), ("diff", False), ("diff", ...)),
        (["--diff", "."], ("diff", True), ("diff", True), ("diff", True)),
        (["."], ("check", False), ("check", False), ("check", ...)),
        (["--check", "."], ("check", True), ("check", True), ("check", True)),
        (["."], ("isort", False), ("isort", False), ("isort", ...)),
        (["-i", "."], ("isort", True), ("isort", True), ("isort", True)),
        (["--isort", "."], ("isort", True), ("isort", True), ("isort", True)),
        (["."], ("lint", []), ("lint", []), ("lint", ...)),
        (
            ["-L", "pylint", "."],
            ("lint", ["pylint"]),
            ("lint", ["pylint"]),
            ("lint", ["pylint"]),
        ),
        (
            ["--lint", "flake8", "-L", "mypy", "."],
            ("lint", ["flake8", "mypy"]),
            ("lint", ["flake8", "mypy"]),
            ("lint", ["flake8", "mypy"]),
        ),
        (["."], ("config", None), ("config", None), ("config", ...)),
        (
            ["-c", "my.cfg", "."],
            ("config", "my.cfg"),
            ("config", "my.cfg"),
            ("config", "my.cfg"),
        ),
        (
            ["--config=my.cfg", "."],
            ("config", "my.cfg"),
            ("config", "my.cfg"),
            ("config", "my.cfg"),
        ),
        (["."], ("log_level", 30), ("log_level", "WARNING"), ("log_level", ...)),
        (
            ["-v", "."],
            ("log_level", 20),
            ("log_level", "INFO"),
            ("log_level", "INFO"),
        ),
        (
            ["--verbose", "-v", "."],
            ("log_level", 10),
            ("log_level", "DEBUG"),
            ("log_level", "DEBUG"),
        ),
        (
            ["-q", "."],
            ("log_level", 40),
            ("log_level", "ERROR"),
            ("log_level", "ERROR"),
        ),
        (
            ["--quiet", "-q", "."],
            ("log_level", 50),
            ("log_level", "CRITICAL"),
            ("log_level", "CRITICAL"),
        ),
        (
            ["."],
            ("skip_string_normalization", None),
            ("skip_string_normalization", None),
            ("skip_string_normalization", ...),
        ),
        (
            ["-S", "."],
            ("skip_string_normalization", True),
            ("skip_string_normalization", True),
            ("skip_string_normalization", True),
        ),
        (
            ["--skip-string-normalization", "."],
            ("skip_string_normalization", True),
            ("skip_string_normalization", True),
            ("skip_string_normalization", True),
        ),
        (
            ["--no-skip-string-normalization", "."],
            ("skip_string_normalization", False),
            ("skip_string_normalization", False),
            ("skip_string_normalization", False),
        ),
        (
            ["."],
            ("line_length", None),
            ("line_length", None),
            ("line_length", ...),
        ),
        (
            ["-l=88", "."],
            ("line_length", 88),
            ("line_length", 88),
            ("line_length", 88),
        ),
        (
            ["--line-length", "99", "."],
            ("line_length", 99),
            ("line_length", 99),
            ("line_length", 99),
        ),
    ],
)
def test_parse_command_line(
    tmpdir, monkeypatch, argv, expect_value, expect_config, expect_modified
):
    monkeypatch.chdir(tmpdir)
    args, effective_cfg, modified_cfg = parse_command_line(argv)

    arg_name, expect_arg_value = expect_value
    assert getattr(args, arg_name) == expect_arg_value

    option, expect_config_value = expect_config
    if expect_config_value is ...:
        assert option not in effective_cfg
    else:
        assert effective_cfg[option] == expect_config_value

    modified_option, expect_modified_value = expect_modified
    if expect_modified_value is ...:
        assert modified_option not in modified_cfg
    else:
        assert modified_cfg[modified_option] == expect_modified_value


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
    "config, options, expect",
    [
        ([], [], call()),
        ([], ['--skip-string-normalization'], call(string_normalization=False)),
        ([], ['--no-skip-string-normalization'], call(string_normalization=True)),
        (['skip_string_normalization = false'], [], call(string_normalization=True)),
        (
            ['skip_string_normalization = false'],
            ['--skip-string-normalization'],
            call(string_normalization=False),
        ),
        (
            ['skip_string_normalization = false'],
            ['--no-skip-string-normalization'],
            call(string_normalization=True),
        ),
        (['skip_string_normalization = true'], [], call(string_normalization=False)),
        (
            ['skip_string_normalization = true'],
            ['--skip-string-normalization'],
            call(string_normalization=False),
        ),
        (
            ['skip_string_normalization = true'],
            ['--no-skip-string-normalization'],
            call(string_normalization=True),
        ),
    ],
)
def test_black_options_skip_string_normalization(git_repo, config, options, expect):
    """Black string normalization config and cmdline option are combined correctly"""
    added_files = git_repo.add(
        {"main.py": "foo", "pyproject.toml": joinlines(["[tool.black]"] + config)},
        commit="Initial commit",
    )
    added_files["main.py"].write("bar")
    mode_class_mock = Mock(wraps=black_diff.Mode)
    # Speed up tests by mocking `format_str` to skip running Black
    format_str = Mock(return_value="bar")
    with patch.multiple(black_diff, Mode=mode_class_mock, format_str=format_str):

        main(options + [str(path) for path in added_files.values()])

    assert mode_class_mock.call_args_list == [expect]


@pytest.mark.parametrize(
    'options, expect',
    [
        (["a.py"], ({Path("a.py")}, RevisionRange("HEAD"), False, [], {})),
        (["--isort", "a.py"], ({Path("a.py")}, RevisionRange("HEAD"), True, [], {})),
        (
            ["--config", "my.cfg", "a.py"],
            ({Path("a.py")}, RevisionRange("HEAD"), False, [], {"config": "my.cfg"}),
        ),
        (
            ["--line-length", "90", "a.py"],
            ({Path("a.py")}, RevisionRange("HEAD"), False, [], {"line_length": 90}),
        ),
        (
            ["--skip-string-normalization", "a.py"],
            (
                {Path("a.py")},
                RevisionRange("HEAD"),
                False,
                [],
                {"skip_string_normalization": True},
            ),
        ),
        (["--diff", "a.py"], ({Path("a.py")}, RevisionRange("HEAD"), False, [], {})),
    ],
)
def test_options(tmpdir, monkeypatch, options, expect):
    """The main engine is called with correct parameters based on the command line

    Executed in a clean directory so Darker's own ``pyproject.toml`` doesn't interfere.

    """
    monkeypatch.chdir(tmpdir)
    (tmpdir / "my.cfg").write("")
    with patch('darker.__main__.format_edited_parts') as format_edited_parts:

        retval = main(options)

    format_edited_parts.assert_called_once_with(*expect)
    assert retval == 0


@pytest.mark.parametrize(
    'check, changes, expect_retval',
    [(False, False, 0), (False, True, 0), (True, False, 0), (True, True, 1)],
)
def test_main_retval(check, changes, expect_retval):
    """main() return value is correct based on --check and the need to reformat files"""
    format_edited_parts = Mock()
    format_edited_parts.return_value = (
        [
            (
                Path("/dummy.py"),
                TextDocument.from_lines(["old"]),
                TextDocument.from_lines(["new"]),
            )
        ]
        if changes
        else []
    )
    check_arg_maybe = ['--check'] if check else []
    with patch.multiple(
        'darker.__main__', format_edited_parts=format_edited_parts, modify_file=DEFAULT
    ):

        retval = main(check_arg_maybe + ['a.py'])

    assert retval == expect_retval
