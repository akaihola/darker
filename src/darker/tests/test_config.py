"""Tests for `darker.config`"""

# pylint: disable=unused-argument

import os
import re
from argparse import ArgumentParser, Namespace
from pathlib import Path
from textwrap import dedent

import pytest

from darker.config import (
    ConfigurationError,
    DarkerConfig,
    OutputMode,
    TomlArrayLinesEncoder,
    dump_config,
    get_effective_config,
    get_modified_config,
    load_config,
    replace_log_level_name,
)
from darker.tests.helpers import raises_if_exception


@pytest.mark.kwparametrize(
    dict(list_value=[], expect="[\n]"),
    dict(list_value=["one value"], expect='[\n    "one value",\n]'),
    dict(list_value=["two", "values"], expect='[\n    "two",\n    "values",\n]'),
    dict(
        list_value=[
            "a",
            "dozen",
            "short",
            "string",
            "values",
            "in",
            "the",
            "list",
            "of",
            "strings",
            "to",
            "format",
        ],
        expect=(
            '[\n    "a",\n    "dozen",\n    "short",\n    "string",\n    "values"'
            ',\n    "in",\n    "the",\n    "list",\n    "of",\n    "strings"'
            ',\n    "to",\n    "format",\n]'
        ),
    ),
)
def test_toml_array_lines_encoder(list_value, expect):
    result = TomlArrayLinesEncoder().dump_list(list_value)

    assert result == expect


@pytest.mark.kwparametrize(
    dict(log_level=0, expect="NOTSET"),
    dict(log_level=10, expect="DEBUG"),
    dict(log_level=20, expect="INFO"),
    dict(log_level=30, expect="WARNING"),
    dict(log_level=40, expect="ERROR"),
    dict(log_level=50, expect="CRITICAL"),
    dict(log_level="DEBUG", expect=10),
    dict(log_level="INFO", expect=20),
    dict(log_level="WARNING", expect=30),
    dict(log_level="WARN", expect=30),
    dict(log_level="ERROR", expect=40),
    dict(log_level="CRITICAL", expect=50),
    dict(log_level="FOOBAR", expect="Level FOOBAR"),
)
def test_replace_log_level_name(log_level, expect):
    config = DarkerConfig() if log_level is None else DarkerConfig(log_level=log_level)
    replace_log_level_name(config)

    assert config["log_level"] == expect


@pytest.mark.kwparametrize(
    dict(diff=False, stdout=False, expect=None),
    dict(diff=False, stdout=True, expect=None),
    dict(diff=True, stdout=False, expect=None),
    dict(diff=True, stdout=True, expect=ConfigurationError),
)
def test_output_mode_validate_diff_stdout(diff, stdout, expect):
    """Validation fails only if ``--diff`` and ``--stdout`` are both enabled"""
    with raises_if_exception(expect):
        OutputMode.validate_diff_stdout(diff, stdout)


@pytest.mark.kwparametrize(
    dict(stdout=False, src=[], expect=None),
    dict(stdout=False, src=["first.py"], expect=None),
    dict(stdout=False, src=["first.py", "second.py"], expect=None),
    dict(stdout=False, src=["first.py", "missing.py"], expect=None),
    dict(stdout=False, src=["missing.py"], expect=None),
    dict(stdout=False, src=["missing.py", "another_missing.py"], expect=None),
    dict(stdout=False, src=["directory"], expect=None),
    dict(stdout=True, src=[], expect=ConfigurationError),
    dict(stdout=True, src=["first.py"], expect=None),
    dict(stdout=True, src=["first.py", "second.py"], expect=ConfigurationError),
    dict(stdout=True, src=["first.py", "missing.py"], expect=ConfigurationError),
    dict(stdout=True, src=["missing.py"], expect=ConfigurationError),
    dict(stdout=True, src=["missing.py", "another.py"], expect=ConfigurationError),
    dict(stdout=True, src=["directory"], expect=ConfigurationError),
)
def test_output_mode_validate_stdout_src(tmp_path, monkeypatch, stdout, expect, src):
    """Validation fails only if exactly one file isn't provided for ``--stdout``"""
    monkeypatch.chdir(tmp_path)
    Path("first.py").touch()
    Path("second.py").touch()
    with raises_if_exception(expect):

        OutputMode.validate_stdout_src(stdout, src)


@pytest.mark.kwparametrize(
    dict(diff=False, stdout=False, expect="NOTHING"),
    dict(diff=False, stdout=True, expect="CONTENT"),
    dict(diff=True, stdout=False, expect="DIFF"),
    dict(diff=True, stdout=True, expect=ConfigurationError),
)
def test_output_mode_from_args(diff, stdout, expect):
    """Correct output mode results from the ``--diff`` and ``stdout`` options"""
    args = Namespace()
    args.diff = diff
    args.stdout = stdout
    with raises_if_exception(expect):

        result = OutputMode.from_args(args)

        assert result == expect


@pytest.mark.kwparametrize(
    dict(),
    dict(cwd="lvl1"),
    dict(cwd="lvl1/lvl2"),
    dict(cwd="has_git", expect={}),
    dict(cwd="has_git/lvl1", expect={}),
    dict(cwd="has_pyp", expect={"CONFIG_PATH": "has_pyp"}),
    dict(cwd="has_pyp/lvl1", expect={"CONFIG_PATH": "has_pyp"}),
    dict(srcs=["root.py"]),
    dict(srcs=["../root.py"], cwd="lvl1"),
    dict(srcs=["../root.py"], cwd="has_git"),
    dict(srcs=["../root.py"], cwd="has_pyp"),
    dict(srcs=["root.py", "lvl1/lvl1.py"]),
    dict(srcs=["../root.py", "lvl1.py"], cwd="lvl1"),
    dict(srcs=["../root.py", "../lvl1/lvl1.py"], cwd="has_git"),
    dict(srcs=["../root.py", "../lvl1/lvl1.py"], cwd="has_pyp"),
    dict(srcs=["has_pyp/pyp.py", "lvl1/lvl1.py"]),
    dict(srcs=["../has_pyp/pyp.py", "lvl1.py"], cwd="lvl1"),
    dict(srcs=["../has_pyp/pyp.py", "../lvl1/lvl1.py"], cwd="has_git"),
    dict(srcs=["pyp.py", "../lvl1/lvl1.py"], cwd="has_pyp"),
    dict(
        srcs=["has_pyp/lvl1/l1.py", "has_pyp/lvl1b/l1b.py"],
        expect={"CONFIG_PATH": "has_pyp"},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="lvl1",
        expect={"CONFIG_PATH": "has_pyp"},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="has_git",
        expect={"CONFIG_PATH": "has_pyp"},
    ),
    dict(
        srcs=["lvl1/l1.py", "lvl1b/l1b.py"],
        cwd="has_pyp",
        expect={"CONFIG_PATH": "has_pyp"},
    ),
    dict(
        srcs=["full_example/full.py"],
        expect={
            "check": True,
            "diff": True,
            "isort": True,
            "lint": ["flake8", "mypy", "pylint"],
            "log_level": 10,
            "revision": "main",
            "src": ["src", "tests"],
        },
    ),
    dict(srcs=["stdout_example/dummy.py"], expect={"stdout": True}),
    dict(confpath="c", expect={"PYP_TOML": 1}),
    dict(confpath="c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="lvl1", confpath="../c", expect={"PYP_TOML": 1}),
    dict(cwd="lvl1", confpath="../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="lvl1/lvl2", confpath="../../c", expect={"PYP_TOML": 1}),
    dict(cwd="lvl1/lvl2", confpath="../../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="has_git", confpath="../c", expect={"PYP_TOML": 1}),
    dict(cwd="has_git", confpath="../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="has_git/lvl1", confpath="../../c", expect={"PYP_TOML": 1}),
    dict(cwd="has_git/lvl1", confpath="../../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="has_pyp", confpath="../c", expect={"PYP_TOML": 1}),
    dict(cwd="has_pyp", confpath="../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(cwd="has_pyp/lvl1", confpath="../../c", expect={"PYP_TOML": 1}),
    dict(cwd="has_pyp/lvl1", confpath="../../c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(srcs=["root.py"], confpath="c", expect={"PYP_TOML": 1}),
    dict(srcs=["root.py"], confpath="c/pyproject.toml", expect={"PYP_TOML": 1}),
    dict(srcs=["../root.py"], cwd="lvl1", confpath="../c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["../root.py"],
        cwd="lvl1",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["../root.py"], cwd="has_git", confpath="../c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["../root.py"],
        cwd="has_git",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["../root.py"], cwd="has_pyp", confpath="../c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["../root.py"],
        cwd="has_pyp",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["root.py", "lvl1/lvl1.py"], confpath="c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["root.py", "lvl1/lvl1.py"],
        confpath="c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "lvl1.py"],
        cwd="lvl1",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "lvl1.py"],
        cwd="lvl1",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "../lvl1/lvl1.py"],
        cwd="has_git",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "../lvl1/lvl1.py"],
        cwd="has_git",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "../lvl1/lvl1.py"],
        cwd="has_pyp",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../root.py", "../lvl1/lvl1.py"],
        cwd="has_pyp",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["has_pyp/pyp.py", "lvl1/lvl1.py"], confpath="c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["has_pyp/pyp.py", "lvl1/lvl1.py"],
        confpath="c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/pyp.py", "lvl1.py"],
        cwd="lvl1",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/pyp.py", "lvl1.py"],
        cwd="lvl1",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/pyp.py", "../lvl1/lvl1.py"],
        cwd="has_git",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/pyp.py", "../lvl1/lvl1.py"],
        cwd="has_git",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["pyp.py", "../lvl1/lvl1.py"],
        cwd="has_pyp",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["pyp.py", "../lvl1/lvl1.py"],
        cwd="has_pyp",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["has_pyp/lvl1/l1.py", "has_pyp/lvl1b/l1b.py"],
        confpath="c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["has_pyp/lvl1/l1.py", "has_pyp/lvl1b/l1b.py"],
        confpath="c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="lvl1",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="lvl1",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="has_git",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["../has_pyp/lvl1/l1.py", "../has_pyp/lvl1b/l1b.py"],
        cwd="has_git",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["lvl1/l1.py", "lvl1b/l1b.py"],
        cwd="has_pyp",
        confpath="../c",
        expect={"PYP_TOML": 1},
    ),
    dict(
        srcs=["lvl1/l1.py", "lvl1b/l1b.py"],
        cwd="has_pyp",
        confpath="../c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["full_example/full.py"], confpath="c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["full_example/full.py"],
        confpath="c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    dict(srcs=["stdout_example/dummy.py"], confpath="c", expect={"PYP_TOML": 1}),
    dict(
        srcs=["stdout_example/dummy.py"],
        confpath="c/pyproject.toml",
        expect={"PYP_TOML": 1},
    ),
    srcs=[],
    cwd=".",
    confpath=None,
    expect={"CONFIG_PATH": "."},
)
def test_load_config(
    find_project_root_cache_clear, tmp_path, monkeypatch, srcs, cwd, confpath, expect
):
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[tool.darker]\nCONFIG_PATH = "."\n')
    (tmp_path / "lvl1/lvl2").mkdir(parents=True)
    (tmp_path / "has_git/.git").mkdir(parents=True)
    (tmp_path / "has_git/lvl1").mkdir()
    (tmp_path / "has_pyp/lvl1").mkdir(parents=True)
    (tmp_path / "has_pyp/pyproject.toml").write_text(
        '[tool.darker]\nCONFIG_PATH = "has_pyp"\n'
    )
    (tmp_path / "full_example").mkdir()
    (tmp_path / "full_example/pyproject.toml").write_text(
        dedent(
            """
            [tool.darker]
            src = [
                "src",
                "tests",
            ]
            revision = "main"
            diff = true
            check = true
            isort = true
            lint = [
                "flake8",
                "mypy",
                "pylint",
            ]
            log_level = "DEBUG"
            """
        )
    )
    (tmp_path / "stdout_example").mkdir()
    (tmp_path / "stdout_example/pyproject.toml").write_text(
        "[tool.darker]\nstdout = true\n"
    )
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "pyproject.toml").write_text("[tool.darker]\nPYP_TOML = 1\n")
    monkeypatch.chdir(tmp_path / cwd)

    result = load_config(confpath, srcs)

    assert result == expect


@pytest.mark.kwparametrize(
    dict(path=".", expect="Configuration file pyproject.toml not found"),
    dict(path="./foo.toml", expect="Configuration file ./foo.toml not found"),
    dict(
        path="empty", expect=f"Configuration file empty{os.sep}pyproject.toml not found"
    ),
    dict(
        path="empty/",
        expect=f"Configuration file empty{os.sep}pyproject.toml not found",
    ),
    dict(path="subdir/foo.toml", expect="Configuration file subdir/foo.toml not found"),
    dict(
        path="missing_dir",
        expect="Configuration file missing_dir not found",
    ),
    dict(
        path=f"missing_dir{os.sep}",
        expect=f"Configuration file missing_dir{os.sep}pyproject.toml not found",
    ),
    dict(
        path="missing_dir/foo.toml",
        expect="Configuration file missing_dir/foo.toml not found",
    ),
)
def test_load_config_explicit_path_errors(tmp_path, monkeypatch, path, expect):
    """``load_config()`` raises an error if given path is not a file"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "pyproject.toml").write_text("")
    (tmp_path / "empty").mkdir()
    with pytest.raises(ConfigurationError, match=re.escape(expect)):

        _ = load_config(path, ["."])


@pytest.mark.kwparametrize(
    dict(args=Namespace(), expect={}),
    dict(args=Namespace(one="option"), expect={"one": "option"}),
    dict(args=Namespace(log_level=10), expect={"log_level": "DEBUG"}),
    dict(
        args=Namespace(two="options", log_level=20),
        expect={"two": "options", "log_level": "INFO"},
    ),
    dict(args=Namespace(diff=True, stdout=True), expect=ConfigurationError),
)
def test_get_effective_config(args, expect):
    """``get_effective_config()`` converts command line options correctly"""
    with raises_if_exception(expect):

        result = get_effective_config(args)

        assert result == expect


@pytest.mark.kwparametrize(
    dict(args=Namespace(), expect={}),
    dict(args=Namespace(unknown="option"), expect={"unknown": "option"}),
    dict(args=Namespace(log_level=10), expect={"log_level": "DEBUG"}),
    dict(args=Namespace(names=[], int=42, string="fourty-two"), expect={"names": []}),
    dict(
        args=Namespace(names=["bar"], int=42, string="fourty-two"),
        expect={"names": ["bar"]},
    ),
    dict(
        args=Namespace(names=["foo"], int=43, string="fourty-two"), expect={"int": 43}
    ),
    dict(args=Namespace(names=["foo"], int=42, string="one"), expect={"string": "one"}),
)
def test_get_modified_config(args, expect):
    parser = ArgumentParser()
    parser.add_argument("names", nargs="*", default=["foo"])
    parser.add_argument("--int", dest="int", default=42)
    parser.add_argument("--string", default="fourty-two")
    result = get_modified_config(parser, args)

    assert result == expect


@pytest.mark.kwparametrize(
    dict(config={}, expect="[tool.darker]\n"),
    dict(config={"str": "value"}, expect='[tool.darker]\nstr = "value"\n'),
    dict(config={"int": 42}, expect="[tool.darker]\nint = 42\n"),
    dict(config={"float": 4.2}, expect="[tool.darker]\nfloat = 4.2\n"),
    dict(
        config={"list": ["foo", "bar"]},
        expect=dedent(
            """\
            [tool.darker]
            list = [
                "foo",
                "bar",
            ]
            """
        ),
    ),
    dict(
        config={
            "src": ["main.py"],
            "revision": "master",
            "diff": False,
            "stdout": False,
            "check": False,
            "isort": False,
            "lint": [],
            "config": None,
            "log_level": "DEBUG",
            "skip_string_normalization": None,
            "line_length": None,
        },
        expect=dedent(
            """\
            [tool.darker]
            src = [
                "main.py",
            ]
            revision = "master"
            diff = false
            stdout = false
            check = false
            isort = false
            lint = [
            ]
            log_level = "DEBUG"
            """
        ),
    ),
)
def test_dump_config(config, expect):
    """``dump_config()`` outputs configuration correctly in the TOML format"""
    result = dump_config(config)

    assert result == expect
