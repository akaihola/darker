"""Unit tests for `darker.command_line` and `darker.__main__`."""

# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=no-member,redefined-outer-name,unused-argument,use-dict-literal

from __future__ import annotations

import os
import re
from importlib import reload
from pathlib import Path
from textwrap import dedent
from unittest.mock import DEFAULT, Mock, call, patch

import pytest
import toml
from black import FileMode, TargetVersion

import darker.help
from darker.__main__ import main
from darker.command_line import make_argument_parser, parse_command_line
from darker.config import Exclusions
from darker.formatters.black_formatter import BlackFormatter
from darker.tests.helpers import flynt_present, isort_present
from darkgraylib.config import ConfigurationError
from darkgraylib.git import RevisionRange
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.testtools.helpers import raises_if_exception
from darkgraylib.utils import TextDocument, joinlines

# Clear LRU caches for `find_project_root()` and `_load_toml()` before each test
pytestmark = pytest.mark.usefixtures(
    "find_project_root_cache_clear", "load_toml_cache_clear"
)


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
        expect_value=("flynt", False),
        expect_config=("flynt", False),
        expect_modified=("flynt", ...),
    ),
    dict(
        argv=["-f", "."],
        expect_value=("flynt", True),
        expect_config=("flynt", True),
        expect_modified=("flynt", True),
    ),
    dict(
        argv=["--flynt", "."],
        expect_value=("flynt", True),
        expect_config=("flynt", True),
        expect_modified=("flynt", True),
    ),
    dict(
        argv=["."],
        expect_value=("lint", []),
        expect_config=("lint", []),
        expect_modified=("lint", ...),
    ),
    dict(
        argv=["-L", "dummy", "."],
        expect_value=("lint", ["dummy"]),
        expect_config=("lint", ["dummy"]),
        expect_modified=("lint", ["dummy"]),
    ),
    dict(
        argv=["--lint", "dummy", "-L", "foobar", "."],
        expect_value=("lint", ["dummy", "foobar"]),
        expect_config=("lint", ["dummy", "foobar"]),
        expect_modified=("lint", ["dummy", "foobar"]),
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
        argv=["--target-version", "py37", "."],
        expect_value=("target_version", "py37"),
        expect_config=("target_version", "py37"),
        expect_modified=("target_version", "py37"),
    ),
    dict(
        argv=["--formatter", "black", "."],
        expect_value=("formatter", "black"),
        expect_config=("formatter", "black"),
        expect_modified=("formatter", ...),
    ),
    dict(
        argv=["--formatter=black", "."],
        expect_value=("formatter", "black"),
        expect_config=("formatter", "black"),
        expect_modified=("formatter", ...),
    ),
    dict(
        argv=["--formatter", "none", "."],
        expect_value=("formatter", "none"),
        expect_config=("formatter", "none"),
        expect_modified=("formatter", "none"),
    ),
    dict(
        argv=["--formatter=none", "."],
        expect_value=("formatter", "none"),
        expect_config=("formatter", "none"),
        expect_modified=("formatter", "none"),
    ),
    dict(
        argv=["--formatter", "rustfmt", "."],
        expect_value=SystemExit,
        expect_config=None,
        expect_modified=None,
    ),
    dict(
        argv=["--formatter=rustfmt", "."],
        expect_value=SystemExit,
        expect_config=None,
        expect_modified=None,
    ),
    dict(
        argv=["--target-version", "py39", "."],
        expect_value=("target_version", "py39"),
        expect_config=("target_version", "py39"),
        expect_modified=("target_version", "py39"),
    ),
    dict(
        argv=["--target-version", "py37", "--target-version", "py39", "."],
        expect_value=("target_version", "py39"),
        expect_config=("target_version", "py39"),
        expect_modified=("target_version", "py39"),
    ),
    dict(
        argv=["--target-version", "py39", "--target-version", "py37", "."],
        expect_value=("target_version", "py37"),
        expect_config=("target_version", "py37"),
        expect_modified=("target_version", "py37"),
    ),
    dict(
        argv=["--target-version", "py39,py37", "."],
        expect_value=SystemExit,
        expect_config=None,
        expect_modified=None,
    ),
    dict(
        argv=["--preview", "."],
        expect_value=("preview", True),
        expect_config=("preview", True),
        expect_modified=("preview", True),
    ),
    environ={},
)
def test_parse_command_line(
    tmp_path, monkeypatch, argv, environ, expect_value, expect_config, expect_modified
):
    """``parse_command_line()`` parses options correctly"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dummy.py").touch()
    (tmp_path / "my.cfg").touch()
    (tmp_path / "subdir_with_config").mkdir()
    (tmp_path / "subdir_with_config" / "pyproject.toml").touch()
    with patch.dict(os.environ, environ, clear=True), raises_if_exception(
        expect_value
    ) as expect_exception:

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


@pytest.mark.kwparametrize(
    dict(config={}, expect_warn=set()),
    dict(config={"diff": True}, expect_warn=set()),
    dict(config={"stdout": True}, expect_warn=set()),
    dict(config={"check": True}, expect_warn=set()),
    dict(config={"isort": True}, expect_warn=set()),
    dict(config={"flynt": True}, expect_warn=set()),
    dict(
        config={"lint": ["dummy"]},
        expect_warn={
            "Baseline linting has been moved to the Graylint package. Please remove the"
            " `lint =` option from your configuration file.",
        },
    ),
    dict(config={"line_length": 88}, expect_warn=set()),
    dict(config={"target_version": "py37"}, expect_warn=set()),
    dict(
        config={
            "diff": True,
            "stdout": False,
            "check": True,
            "isort": True,
            "lint": ["dummy"],
            "line_length": 88,
            "target_version": "py37",
        },
        expect_warn={
            "Baseline linting has been moved to the Graylint package. Please remove the"
            " `lint =` option from your configuration file.",
        },
    ),
)
def test_parse_command_line_deprecated_option(
    tmp_path, monkeypatch, config, expect_warn
):
    """`parse_command_line` warns about deprecated configuration options."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(toml.dumps({"tool": {"darker": config}}))
    with patch("darker.command_line.warnings.warn") as warn:

        parse_command_line(["-"])

    assert {c.args[0] for c in warn.call_args_list} == expect_warn


def test_parse_command_line_unknown_conffile_option(tmp_path, monkeypatch):
    """`parse_command_line` warns about deprecated configuration options."""
    monkeypatch.chdir(tmp_path)
    config = {"unknown": "value", "preview": "true"}
    (tmp_path / "pyproject.toml").write_text(toml.dumps({"tool": {"darker": config}}))
    with pytest.raises(
        ConfigurationError,
        match=r"Invalid \[tool.darker\] keys in pyproject.toml: preview, unknown",
    ):

        parse_command_line(["-"])


@pytest.mark.kwparametrize(
    dict(config={}),
    dict(config={"diff": True}),
    dict(config={"stdout": True}),
    dict(config={"check": True}),
    dict(config={"isort": True}),
    dict(config={"lint": ["pylint"]}),
    dict(
        config={"skip_string_normalization": True},
        expect=ConfigurationError(
            "Please move the `skip_string_normalization` option from the [tool.darker]"
            " section to the [tool.black] section in your `pyproject.toml` file.",
        ),
    ),
    dict(
        config={"skip_magic_trailing_comma": True},
        expect=ConfigurationError(
            "Please move the `skip_magic_trailing_comma` option from the [tool.darker]"
            " section to the [tool.black] section in your `pyproject.toml` file.",
        ),
    ),
    dict(config={"line_length": 88}),
    dict(config={"target_version": "py37"}),
    dict(
        config={
            "diff": True,
            "stdout": False,
            "check": True,
            "isort": True,
            "lint": ["pylint"],
            "skip_string_normalization": True,
            "skip_magic_trailing_comma": True,
            "line_length": 88,
            "target_version": "py37",
        },
        expect=ConfigurationError(
            "Please move the `skip_magic_trailing_comma` option from the [tool.darker]"
            " section to the [tool.black] section in your `pyproject.toml` file. Please"
            " move the `skip_string_normalization` option from the [tool.darker]"
            " section to the [tool.black] section in your `pyproject.toml` file.",
        ),
    ),
    expect=None,
)
def test_parse_command_line_removed_option(tmp_path, monkeypatch, config, expect):
    """`parse_command_line` fails if old removed options are used."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(toml.dumps({"tool": {"darker": config}}))
    with raises_if_exception(expect):

        parse_command_line(["-"])


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

        assert (
            "Please run `pip install darker[isort]` to enable "
            not in get_darker_help_output(capsys)
        )


def test_help_description_without_flynt_package(capsys):
    """``darker --help`` description shows how to add ``flynt`` if it's not present"""
    with flynt_present(False):

        assert (
            "Please run `pip install darker[flynt]` to enable converting old literal "
            "string formatting to f-strings" in get_darker_help_output(capsys)
        )


def test_help_flynt_option_without_flynt_package(capsys):
    """``--flynt`` option help text shows how to install `flynt`` if it's not present"""
    with flynt_present(False):

        assert (
            "Please run `pip install darker[flynt]` to enable usage of this option."
            in get_darker_help_output(capsys)
        )


def test_help_with_flynt_package(capsys):
    """``darker --help`` omits ``flynt`` installation instructions if it is installed"""
    with flynt_present(True):

        assert (
            "Please run `pip install darker[flynt]` to enable "
            not in get_darker_help_output(capsys)
        )


@pytest.fixture(scope="module")
def black_options_files(request, tmp_path_factory):
    """Fixture for the `test_black_options` test."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        (repo.root / "pyproject.toml").write_bytes(b"[tool.black]\n")
        (repo.root / "black.cfg").write_text(
            dedent(
                """
                [tool.black]
                line-length = 81
                skip-string-normalization = false
                target-version = 'py38'
                """
            )
        )
        yield repo.add({"main.py": 'print("Hello World!")\n'}, commit="Initial commit")


@pytest.mark.kwparametrize(
    dict(options=[], expect=call()),
    dict(
        options=["-c", "black.cfg"],
        expect=call(
            line_length=81,
            string_normalization=True,
            target_versions={TargetVersion.PY38},
        ),
    ),
    dict(
        options=["--config", "black.cfg"],
        expect=call(
            line_length=81,
            string_normalization=True,
            target_versions={TargetVersion.PY38},
        ),
    ),
    dict(options=["-S"], expect=call(string_normalization=False)),
    dict(
        options=["--skip-string-normalization"], expect=call(string_normalization=False)
    ),
    dict(options=["-l", "90"], expect=call(line_length=90)),
    dict(options=["--line-length", "90"], expect=call(line_length=90)),
    dict(
        options=["-c", "black.cfg", "-S"],
        expect=call(
            line_length=81,
            string_normalization=False,
            target_versions={TargetVersion.PY38},
        ),
    ),
    dict(
        options=["-c", "black.cfg", "-l", "90"],
        expect=call(
            line_length=90,
            string_normalization=True,
            target_versions={TargetVersion.PY38},
        ),
    ),
    dict(
        options=["-l", "90", "-S"],
        expect=call(line_length=90, string_normalization=False),
    ),
    dict(
        options=["-c", "black.cfg", "-l", "90", "-S"],
        expect=call(
            line_length=90,
            string_normalization=False,
            target_versions={TargetVersion.PY38},
        ),
    ),
    dict(options=["-t", "py39"], expect=call(target_versions={TargetVersion.PY39})),
    dict(
        options=["--target-version", "py39"],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        options=["-c", "black.cfg", "-t", "py39"],
        expect=call(
            line_length=81,
            string_normalization=True,
            target_versions={TargetVersion.PY39},
        ),
    ),
    dict(
        options=["-t", "py39", "-S"],
        expect=call(string_normalization=False, target_versions={TargetVersion.PY39}),
    ),
    dict(
        options=["-c", "black.cfg", "-t", "py39", "-S"],
        expect=call(
            line_length=81,
            string_normalization=False,
            target_versions={TargetVersion.PY39},
        ),
    ),
    dict(
        options=["--preview"],
        expect=call(
            preview=True,
        ),
    ),
)
def test_black_options(black_options_files, options, expect):
    """Black options from the command line are passed correctly to Black."""
    # The Git repository set up by the module-scope `black_options_repo` fixture is
    # shared by all test cases. The "main.py" file modified by the test run needs to be
    # reset to its original content before the next test case.
    black_options_files["main.py"].write_bytes(b'print ("Hello World!")\n')
    with patch(
        "darker.formatters.black_wrapper.FileMode", wraps=FileMode
    ) as file_mode_class:
        # end of test setup, now call the function under test

        main(options + [str(path) for path in black_options_files.values()])

    assert black_options_files["main.py"].read_bytes() == b'print("Hello World!")\n'
    _, expect_args, expect_kwargs = expect
    file_mode_class.assert_called_once_with(*expect_args, **expect_kwargs)


@pytest.fixture(scope="module")
def black_config_file_and_options_files(request, tmp_path_factory):
    """Git repository fixture for the `test_black_config_file_and_options` test."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        repo_files = repo.add(
            {"main.py": "foo", "pyproject.toml": "* placeholder, will be overwritten"},
            commit="Initial commit",
        )
        repo_files["main.py"].write_bytes(b"a = [1, 2,]")
        yield repo_files


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
    dict(
        config=[],
        options=["--skip-magic-trailing-comma"],
        expect=call(magic_trailing_comma=False),
    ),
    dict(
        config=["skip_magic_trailing_comma = false"],
        options=[],
        expect=call(magic_trailing_comma=True),
    ),
    dict(
        config=["skip_magic_trailing_comma = true"],
        options=[],
        expect=call(magic_trailing_comma=False),
    ),
    dict(
        config=[],
        options=["--target-version", "py39"],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        config=["target-version = 'py39'"],
        options=[],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        config=["target_version = ['py39']"],
        options=[],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        config=["target-version = 'py38'"],
        options=["--target-version", "py39"],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        config=["target-version = ['py38']"],
        options=["-t", "py39"],
        expect=call(target_versions={TargetVersion.PY39}),
    ),
    dict(
        config=["preview = true"],
        options=[],
        expect=call(preview=True),
    ),
    dict(
        config=["preview = false"],
        options=["--preview"],
        expect=call(preview=True),
    ),
    dict(
        config=["preview = true"],
        options=["--preview"],
        expect=call(preview=True),
    ),
)
def test_black_config_file_and_options(
    black_config_file_and_options_files, config, options, expect
):
    """Black configuration file and command line options are combined correctly"""
    repo_files = black_config_file_and_options_files
    repo_files["pyproject.toml"].write_text(joinlines(["[tool.black]", *config]))
    mode_class_mock = Mock(wraps=FileMode)
    # Speed up tests by mocking `format_str` to skip running Black
    format_str = Mock(return_value="a = [1, 2,]")
    with patch("darker.formatters.black_wrapper.FileMode", mode_class_mock), patch(
        "black.format_str", format_str
    ):
        # end of test setup, now call the function under test

        main(options + [str(path) for path in repo_files.values()])

    assert mode_class_mock.call_args_list == [expect]


@pytest.fixture(scope="module")
def options_repo(request, tmp_path_factory):
    """Git repository fixture for the `test_options` test."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        paths = repo.add(
            {"a.py": "1\n", "b.py": "2\n", "my.cfg": ""}, commit="Initial commit"
        )
        paths["a.py"].write_bytes(b"one\n")
        yield repo


@pytest.mark.kwparametrize(
    dict(
        options=["a.py"],
        # Expected arguments to the `format_edited_parts()` call.
        # `Path("git_root")` will be replaced with the temporary Git repository root:
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {},
        ),
    ),
    dict(
        options=["--isort", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {},
        ),
    ),
    dict(
        options=["--flynt", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {},
        ),
    ),
    dict(
        options=["--config", "my.cfg", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {"config": "my.cfg"},
        ),
    ),
    dict(
        options=["--line-length", "90", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {"line_length": 90},
        ),
    ),
    dict(
        options=["--skip-string-normalization", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {"skip_string_normalization": True},
        ),
    ),
    dict(
        options=["--diff", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {},
        ),
    ),
    dict(
        options=["--target-version", "py39", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {"target_version": {(3, 9)}},
        ),
    ),
    dict(
        options=["--preview", "a.py"],
        expect=(
            Path("git_root"),
            {Path("a.py")},
            Exclusions(isort={"**/*"}, flynt={"**/*"}),
            RevisionRange("HEAD", ":WORKTREE:"),
            {"preview": True},
        ),
    ),
)
def test_options(options_repo, monkeypatch, options, expect):
    """The main engine is called with correct parameters based on the command line

    Executed in a clean directory so Darker's own ``pyproject.toml`` doesn't interfere.

    """
    with patch('darker.__main__.format_edited_parts') as format_edited_parts:
        monkeypatch.chdir(options_repo.root)

        retval = main(options)

    expect_formatter = BlackFormatter()
    expect_formatter.config = expect[4]
    actual_formatter = format_edited_parts.call_args.args[4]
    assert actual_formatter.config == expect_formatter.config
    expect = (Path(options_repo.root), expect[1]) + expect[2:4] + (expect_formatter,)
    format_edited_parts.assert_called_once_with(
        *expect, report_unmodified=False, workers=1
    )
    assert retval == 0


@pytest.fixture(scope="module")
def main_retval_repo(request, tmp_path_factory):
    """Git repository fixture for the `test_main_retval` test."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        repo.add({"a.py": ""}, commit="Initial commit")
        yield


@pytest.mark.kwparametrize(
    dict(arguments=["a.py"], changes=False),
    dict(arguments=["a.py"], changes=True),
    dict(arguments=["--check", "a.py"], changes=False),
    dict(arguments=["--check", "a.py"], changes=True, expect_retval=1),
    expect_retval=0,
)
def test_main_retval(main_retval_repo, arguments, changes, expect_retval):
    """``main()`` return value is correct based on ``--check`` and reformatting."""
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
    with patch.multiple(
        "darker.__main__",
        format_edited_parts=format_edited_parts,
        modify_file=DEFAULT,
    ):

        retval = main(arguments)

    assert retval == expect_retval


def test_main_missing_in_worktree(git_repo):
    """An ``ArgumentError`` is raised if given file is not found on disk"""
    paths = git_repo.add({"a.py": ""}, commit="Add a.py")
    paths["a.py"].unlink()

    with pytest.raises(
        FileNotFoundError,
        match=re.escape("Path(s) 'a.py' do not exist in the working tree"),
    ):

        main(["a.py"])


def test_main_missing_in_revision(git_repo):
    """An ``ArgumentError`` is raised if given file didn't exist in rev2"""
    paths = git_repo.add({"a.py": ""}, commit="Add a.py")
    git_repo.add({"a.py": None}, commit="Delete a.py")
    paths["a.py"].touch()

    with pytest.raises(
        FileNotFoundError,
        match=re.escape("Path(s) 'a.py' do not exist in HEAD"),
    ):

        main(["--diff", "--revision", "..HEAD", "a.py"])
