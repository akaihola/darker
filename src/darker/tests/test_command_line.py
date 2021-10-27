# pylint: disable=too-many-arguments,too-many-locals

"""Unit tests for :mod:`darker.command_line` and :mod:`darker.__main__`"""

import re
from argparse import ArgumentError
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
from darker.config import ConfigurationError
from darker.git import RevisionRange
from darker.tests.helpers import filter_dict, isort_present, raises_if_exception
from darker.utils import TextDocument, joinlines

pytestmark = pytest.mark.usefixtures("find_project_root_cache_clear")


@pytest.mark.kwparametrize(
    dict(require_src=False, expect=[]), dict(require_src=True, expect=SystemExit)
)
def test_make_argument_parser(require_src, expect):
    """Parser from ``make_argument_parser()`` fails if src required but not provided"""
    parser = make_argument_parser(require_src)
    with raises_if_exception(expect):

        args = parser.parse_args([])

        assert args.src == expect


def get_darker_help_output(capsys):
    """Test for ``--help`` option output"""
    # Make sure the description is re-rendered since its content depends on whether
    # isort is installed or not:
    reload(darker.help)
    with pytest.raises(SystemExit):
        parse_command_line(["--help"])
    return re.sub(r"\s+", " ", capsys.readouterr().out)


@pytest.mark.kwparametrize(
    dict(config=None, argv=[], expect=SystemExit),
    dict(
        config=None,
        argv=["file.py"],
        expect={"src": ["file.py"]},
    ),
    dict(
        config={"src": ["file.py"]},
        argv=[],
        expect={"src": ["file.py"]},
    ),
    dict(
        config={"src": ["file.py"]},
        argv=["file.py"],
        expect={"src": ["file.py"]},
    ),
    dict(
        config={"src": ["file1.py"]},
        argv=["file2.py"],
        expect={"src": ["file2.py"]},
    ),
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
        assert filter_dict(dict(effective_cfg), "src") == expect
        assert filter_dict(dict(modified_cfg), "src") == expect


@pytest.mark.kwparametrize(
    dict(
        argv=["."],
        expect_value=("src", ["."]),
        expect_config=("src", ["."]),
        expect_modified=("src", ["."]),
    ),
    dict(
        argv=["."],
        expect_value=("revision", "HEAD"),
        expect_config=("revision", "HEAD"),
        expect_modified=("revision", ...),
    ),
    dict(
        argv=["-rmaster", "."],
        expect_value=("revision", "master"),
        expect_config=("revision", "master"),
        expect_modified=("revision", "master"),
    ),
    dict(
        argv=["--revision", "HEAD", "."],
        expect_value=("revision", "HEAD"),
        expect_config=("revision", "HEAD"),
        expect_modified=("revision", ...),
    ),
    dict(
        argv=["."],
        expect_value=("diff", False),
        expect_config=("diff", False),
        expect_modified=("diff", ...),
    ),
    dict(
        argv=["--diff", "."],
        expect_value=("diff", True),
        expect_config=("diff", True),
        expect_modified=("diff", True),
    ),
    dict(
        argv=["."],
        expect_value=("stdout", False),
        expect_config=("stdout", False),
        expect_modified=("stdout", ...),
    ),
    dict(
        argv=["--stdout", "dummy.py"],
        expect_value=("stdout", True),
        expect_config=("stdout", True),
        expect_modified=("stdout", True),
    ),
    dict(
        argv=["--diff", "--stdout", "dummy.py"],
        expect_value=ConfigurationError,
        expect_config=ConfigurationError,
        expect_modified=ConfigurationError,
    ),
    dict(
        argv=["."],
        expect_value=("check", False),
        expect_config=("check", False),
        expect_modified=("check", ...),
    ),
    dict(
        argv=["--check", "."],
        expect_value=("check", True),
        expect_config=("check", True),
        expect_modified=("check", True),
    ),
    dict(
        argv=["."],
        expect_value=("isort", False),
        expect_config=("isort", False),
        expect_modified=("isort", ...),
    ),
    dict(
        argv=["-i", "."],
        expect_value=("isort", True),
        expect_config=("isort", True),
        expect_modified=("isort", True),
    ),
    dict(
        argv=["--isort", "."],
        expect_value=("isort", True),
        expect_config=("isort", True),
        expect_modified=("isort", True),
    ),
    dict(
        argv=["."],
        expect_value=("lint", []),
        expect_config=("lint", []),
        expect_modified=("lint", ...),
    ),
    dict(
        argv=["-L", "pylint", "."],
        expect_value=("lint", ["pylint"]),
        expect_config=("lint", ["pylint"]),
        expect_modified=("lint", ["pylint"]),
    ),
    dict(
        argv=["--lint", "flake8", "-L", "mypy", "."],
        expect_value=("lint", ["flake8", "mypy"]),
        expect_config=("lint", ["flake8", "mypy"]),
        expect_modified=("lint", ["flake8", "mypy"]),
    ),
    dict(
        argv=["."],
        expect_value=("config", None),
        expect_config=("config", None),
        expect_modified=("config", ...),
    ),
    dict(
        argv=["-c", "my.cfg", "."],
        expect_value=("config", "my.cfg"),
        expect_config=("config", "my.cfg"),
        expect_modified=("config", "my.cfg"),
    ),
    dict(
        argv=["--config=my.cfg", "."],
        expect_value=("config", "my.cfg"),
        expect_config=("config", "my.cfg"),
        expect_modified=("config", "my.cfg"),
    ),
    dict(
        argv=["."],
        expect_value=("log_level", 30),
        expect_config=("log_level", "WARNING"),
        expect_modified=("log_level", ...),
    ),
    dict(
        argv=["-v", "."],
        expect_value=("log_level", 20),
        expect_config=("log_level", "INFO"),
        expect_modified=("log_level", "INFO"),
    ),
    dict(
        argv=["--verbose", "-v", "."],
        expect_value=("log_level", 10),
        expect_config=("log_level", "DEBUG"),
        expect_modified=("log_level", "DEBUG"),
    ),
    dict(
        argv=["-q", "."],
        expect_value=("log_level", 40),
        expect_config=("log_level", "ERROR"),
        expect_modified=("log_level", "ERROR"),
    ),
    dict(
        argv=["--quiet", "-q", "."],
        expect_value=("log_level", 50),
        expect_config=("log_level", "CRITICAL"),
        expect_modified=("log_level", "CRITICAL"),
    ),
    dict(
        argv=["."],
        expect_value=("skip_string_normalization", None),
        expect_config=("skip_string_normalization", None),
        expect_modified=("skip_string_normalization", ...),
    ),
    dict(
        argv=["-S", "."],
        expect_value=("skip_string_normalization", True),
        expect_config=("skip_string_normalization", True),
        expect_modified=("skip_string_normalization", True),
    ),
    dict(
        argv=["--skip-string-normalization", "."],
        expect_value=("skip_string_normalization", True),
        expect_config=("skip_string_normalization", True),
        expect_modified=("skip_string_normalization", True),
    ),
    dict(
        argv=["--no-skip-string-normalization", "."],
        expect_value=("skip_string_normalization", False),
        expect_config=("skip_string_normalization", False),
        expect_modified=("skip_string_normalization", False),
    ),
    dict(
        argv=["--skip-magic-trailing-comma", "."],
        expect_value=("skip_magic_trailing_comma", True),
        expect_config=("skip_magic_trailing_comma", True),
        expect_modified=("skip_magic_trailing_comma", True),
    ),
    dict(
        argv=["."],
        expect_value=("line_length", None),
        expect_config=("line_length", None),
        expect_modified=("line_length", ...),
    ),
    dict(
        argv=["-l=88", "."],
        expect_value=("line_length", 88),
        expect_config=("line_length", 88),
        expect_modified=("line_length", 88),
    ),
    dict(
        argv=["--line-length", "99", "."],
        expect_value=("line_length", 99),
        expect_config=("line_length", 99),
        expect_modified=("line_length", 99),
    ),
    dict(
        # this is accepted as a path, but would later fail if a file or directory with
        # that funky name doesn't exist
        argv=["--suspicious path"],
        expect_value=("src", ["--suspicious path"]),
        expect_config=("src", ["--suspicious path"]),
        expect_modified=("src", ["--suspicious path"]),
    ),
    dict(
        argv=["valid/path", "another/valid/path"],
        expect_value=("src", ["valid/path", "another/valid/path"]),
        expect_config=("src", ["valid/path", "another/valid/path"]),
        expect_modified=("src", ["valid/path", "another/valid/path"]),
    ),
)
def test_parse_command_line(
    tmp_path, monkeypatch, argv, expect_value, expect_config, expect_modified
):
    """``parse_command_line()`` parses options correctly"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dummy.py").touch()
    with raises_if_exception(expect_value) as expect_exception:

        args, effective_cfg, modified_cfg = parse_command_line(argv)

    if not expect_exception:
        arg_name, expect_arg_value = expect_value
        assert getattr(args, arg_name) == expect_arg_value

        option, expect_config_value = expect_config
        if expect_config_value is ...:
            assert option not in effective_cfg
        else:
            assert effective_cfg[option] == expect_config_value  # type: ignore

        modified_option, expect_modified_value = expect_modified
        if expect_modified_value is ...:
            assert modified_option not in modified_cfg
        else:
            assert (
                modified_cfg[modified_option] == expect_modified_value  # type: ignore
            )


def test_help_description_without_isort_package(capsys):
    """``darker --help`` description shows how to add ``isort`` if it's not present"""
    with isort_present(False):

        assert (
            "Please run `pip install darker[isort]` to enable sorting of import "
            "definitions" in get_darker_help_output(capsys)
        )


def test_help_isort_option_without_isort_package(capsys):
    """``--isort`` option help text shows how to install `isort`` if it's not present"""
    with isort_present(False):

        assert (
            "Please run `pip install darker[isort]` to enable usage of this option."
            in get_darker_help_output(capsys)
        )


def test_help_with_isort_package(capsys):
    """``darker --help`` omits ``isort`` installation instructions if it is installed"""
    with isort_present(True):

        assert "Please run" not in get_darker_help_output(capsys)


@pytest.mark.kwparametrize(
    dict(options=[], expect=call()),
    dict(
        options=["-c", "black.cfg"],
        expect=call(line_length=81, string_normalization=True),
    ),
    dict(
        options=["--config", "black.cfg"],
        expect=call(line_length=81, string_normalization=True),
    ),
    dict(options=["-S"], expect=call(string_normalization=False)),
    dict(
        options=["--skip-string-normalization"], expect=call(string_normalization=False)
    ),
    dict(options=["-l", "90"], expect=call(line_length=90)),
    dict(options=["--line-length", "90"], expect=call(line_length=90)),
    dict(
        options=["-c", "black.cfg", "-S"],
        expect=call(line_length=81, string_normalization=False),
    ),
    dict(
        options=["-c", "black.cfg", "-l", "90"],
        expect=call(line_length=90, string_normalization=True),
    ),
    dict(
        options=["-l", "90", "-S"],
        expect=call(line_length=90, string_normalization=False),
    ),
    dict(
        options=["-c", "black.cfg", "-l", "90", "-S"],
        expect=call(line_length=90, string_normalization=False),
    ),
)
def test_black_options(monkeypatch, tmpdir, git_repo, options, expect):
    """Black options from the command line are passed correctly to Black"""
    monkeypatch.chdir(tmpdir)
    (tmpdir / "pyproject.toml").write("[tool.black]\n")
    (tmpdir / "black.cfg").write(
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
    added_files["main.py"].write_bytes(b'print ("Hello World!")\n')
    with patch.object(black_diff, "Mode", wraps=black_diff.Mode) as file_mode_class:

        main(options + [str(path) for path in added_files.values()])

    _, expect_args, expect_kwargs = expect
    file_mode_class.assert_called_once_with(*expect_args, **expect_kwargs)


@pytest.mark.kwparametrize(
    dict(config=[], options=[], expect=call()),
    dict(
        config=[],
        options=["--skip-string-normalization"],
        expect=call(string_normalization=False),
    ),
    dict(
        config=[],
        options=["--no-skip-string-normalization"],
        expect=call(string_normalization=True),
    ),
    dict(
        config=["skip_string_normalization = false"],
        options=[],
        expect=call(string_normalization=True),
    ),
    dict(
        config=["skip_string_normalization = false"],
        options=["--skip-string-normalization"],
        expect=call(string_normalization=False),
    ),
    dict(
        config=["skip_string_normalization = false"],
        options=["--no-skip-string-normalization"],
        expect=call(string_normalization=True),
    ),
    dict(
        config=["skip_string_normalization = true"],
        options=[],
        expect=call(string_normalization=False),
    ),
    dict(
        config=["skip_string_normalization = true"],
        options=["--skip-string-normalization"],
        expect=call(string_normalization=False),
    ),
    dict(
        config=["skip_string_normalization = true"],
        options=["--no-skip-string-normalization"],
        expect=call(string_normalization=True),
    ),
)
def test_black_options_skip_string_normalization(git_repo, config, options, expect):
    """Black string normalization config and cmdline option are combined correctly"""
    added_files = git_repo.add(
        {"main.py": "foo", "pyproject.toml": joinlines(["[tool.black]"] + config)},
        commit="Initial commit",
    )
    added_files["main.py"].write_bytes(b"bar")
    mode_class_mock = Mock(wraps=black_diff.Mode)
    # Speed up tests by mocking `format_str` to skip running Black
    format_str_to_lines = Mock(return_value=["bar"])
    with patch.multiple(
        black_diff, Mode=mode_class_mock, format_str_to_lines=format_str_to_lines
    ):

        main(options + [str(path) for path in added_files.values()])

    assert mode_class_mock.call_args_list == [expect]


@pytest.mark.parametrize(
    "config, options, expect",
    [
        ([], [], call()),
        ([], ["--skip-magic-trailing-comma"], call(magic_trailing_comma=False)),
        (["skip_magic_trailing_comma = false"], [], call(magic_trailing_comma=True)),
        (["skip_magic_trailing_comma = true"], [], call(magic_trailing_comma=False)),
    ],
)
def test_black_options_skip_magic_trailing_comma(git_repo, config, options, expect):
    """Black string normalization config and cmdline option are combined correctly"""
    added_files = git_repo.add(
        {"main.py": "foo", "pyproject.toml": joinlines(["[tool.black]"] + config)},
        commit="Initial commit",
    )
    added_files["main.py"].write_bytes(b"a = [1, 2,]")
    mode_class_mock = Mock(wraps=black_diff.Mode)
    # Speed up tests by mocking `format_str` to skip running Black
    format_str_to_lines = Mock(return_value=["a = [1, 2,]"])
    with patch.multiple(
        black_diff, Mode=mode_class_mock, format_str_to_lines=format_str_to_lines
    ):

        main(options + [str(path) for path in added_files.values()])

    assert mode_class_mock.call_args_list == [expect]


@pytest.mark.kwparametrize(
    dict(
        options=["a.py"],
        # Expected arguments to the `format_edited_parts()` call.
        # `Path("git_root")` will be replaced with the temporary Git repository root:
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            False,
            {},
        ),
    ),
    dict(
        options=["--isort", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            True,
            {},
        ),
    ),
    dict(
        options=["--config", "my.cfg", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            False,
            {"config": "my.cfg"},
        ),
    ),
    dict(
        options=["--line-length", "90", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            False,
            {"line_length": 90},
        ),
    ),
    dict(
        options=["--skip-string-normalization", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            False,
            {"skip_string_normalization": True},
        ),
    ),
    dict(
        options=["--diff", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            set(),
            RevisionRange("HEAD", ":WORKTREE:"),
            False,
            {},
        ),
    ),
)
def test_options(git_repo, options, expect):
    """The main engine is called with correct parameters based on the command line

    Executed in a clean directory so Darker's own ``pyproject.toml`` doesn't interfere.

    """
    paths = git_repo.add(
        {"a.py": "1\n", "b.py": "2\n", "my.cfg": ""}, commit="Initial commit"
    )
    paths["a.py"].write_bytes(b"one\n")
    with patch('darker.__main__.format_edited_parts') as format_edited_parts:

        retval = main(options)

    expect = (Path(git_repo.root), expect[1]) + expect[2:]
    format_edited_parts.assert_called_once_with(*expect, report_unmodified=False)
    assert retval == 0


@pytest.mark.kwparametrize(
    dict(check=False, changes=False, lintfail=False),
    dict(check=False, changes=False, lintfail=True, expect_retval=1),
    dict(check=False, changes=True, lintfail=False),
    dict(check=False, changes=True, lintfail=True, expect_retval=1),
    dict(check=True, changes=False, lintfail=False),
    dict(check=True, changes=True, lintfail=True, expect_retval=1),
    expect_retval=0,
)
def test_main_retval(git_repo, check, changes, lintfail, expect_retval):
    """main() return value is correct based on --check, reformatting and linters"""
    git_repo.add({"a.py": ""}, commit="Initial commit")
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
    run_linters = Mock(return_value=lintfail)
    check_arg_maybe = ["--check"] if check else []
    with patch.multiple(
        "darker.__main__",
        format_edited_parts=format_edited_parts,
        modify_file=DEFAULT,
        run_linters=run_linters,
    ):

        retval = main(check_arg_maybe + ["a.py"])

    assert retval == expect_retval


def test_main_missing_in_worktree(git_repo):
    """An ``ArgumentError`` is raised if given file is not found on disk"""
    paths = git_repo.add({"a.py": ""}, commit="Add a.py")
    paths["a.py"].unlink()

    with pytest.raises(
        ArgumentError,
        match=re.escape(
            "argument PATH: Error: Path(s) 'a.py' do not exist in the working tree"
        ),
    ):

        main(["a.py"])


def test_main_missing_in_revision(git_repo):
    """An ``ArgumentError`` is raised if given file didn't exist in rev2"""
    paths = git_repo.add({"a.py": ""}, commit="Add a.py")
    git_repo.add({"a.py": None}, commit="Delete a.py")
    paths["a.py"].touch()

    with pytest.raises(
        ArgumentError,
        match=re.escape("argument PATH: Error: Path(s) 'a.py' do not exist in HEAD"),
    ):

        main(["--diff", "--revision", "..HEAD", "a.py"])
