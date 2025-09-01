"""Unit tests for `darker.black_formatter`"""

# pylint: disable=too-many-arguments,too-many-positional-arguments,use-dict-literal

import re
import sys
from argparse import Namespace
from dataclasses import dataclass, field
from importlib import reload
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import regex
from black import Mode, TargetVersion

import darker.formatters.black_formatter
from darker.exceptions import DependencyError
from darker.files import DEFAULT_EXCLUDE_RE, filter_python_files
from darker.formatters import create_formatter
from darker.formatters.black_formatter import BlackFormatter
from darker.tests.helpers import black_present
from darkgraylib.config import ConfigurationError
from darkgraylib.testtools.helpers import raises_or_matches
from darkgraylib.utils import TextDocument

if sys.version_info >= (3, 11):
    try:
        import tomllib
    except ImportError:
        # Help users on older alphas
        if not TYPE_CHECKING:
            import tomli as tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from darker.formatters.formatter_config import BlackCompatibleConfig


@dataclass
class RegexEquality:
    """Compare equality to either `re.Pattern` or `regex.Pattern`"""

    pattern: str
    flags: int = field(default=re.UNICODE)

    def __eq__(self, other):
        return (
            other.pattern == self.pattern
            and other.flags & 0x1FF == re.compile(self.pattern).flags | self.flags
        )


@pytest.mark.parametrize("present", [True, False])
def test_formatters_black_importable_with_and_without_isort(present):
    """Ensure `darker.formatters.black_formatter` imports with/without ``black``."""
    try:
        with black_present(present=present):
            # end of test setup, now import the module

            # Import when `black` has been removed temporarily
            reload(darker.formatters.black_formatter)

    finally:
        # Re-import after restoring `black` so other tests won't be affected
        reload(darker.formatters.black_formatter)


def test_formatter_without_black(caplog):
    """`BlackFormatter` logs warnings with instructions if `black` is not installed."""
    args = Namespace()
    args.config = None
    formatter = create_formatter("black")
    with black_present(present=False), pytest.raises(
        DependencyError, match="^Can't find the Black package$"
    ):
        # end of test setup, now exercise the Black formatter

        formatter.read_config((), args)

    assert [
        record.msg for record in caplog.records if record.levelname == "WARNING"
    ] == [
        # warning 1:
        "Since Darker 3.0.0, Black is no longer installed by default. "
        "To re-format code using Black, install it using e.g."
        " `pip install 'darker[black]'` or `pip install black`",
        # warning 2:
        "To use a different formatter or no formatter, select it on the command line"
        " (e.g. `--formatter=ruff`) or configuration (e.g. `formatter=none`)",
    ]


@pytest.mark.parametrize("option_name_delimiter", ["-", "_"])
@pytest.mark.kwparametrize(
    dict(
        config_lines=["skip-string-normalization = true"],
        expect={"skip_string_normalization": True},
    ),
    dict(
        config_lines=["skip-string-normalization = false"],
        expect={"skip_string_normalization": False},
    ),
    dict(
        config_lines=["skip-magic-trailing-comma = true"],
        expect={"skip_magic_trailing_comma": True},
    ),
    dict(
        config_lines=["skip-magic-trailing-comma = false"],
        expect={"skip_magic_trailing_comma": False},
    ),
    dict(config_lines=["target-version ="], expect=tomllib.TOMLDecodeError()),
    dict(config_lines=["target-version = false"], expect=ConfigurationError()),
    dict(config_lines=["target-version = 'py37'"], expect={"target_version": (3, 7)}),
    dict(
        config_lines=["target-version = ['py37']"],
        expect={"target_version": {(3, 7)}},
    ),
    dict(
        config_lines=["target-version = ['py39']"],
        expect={"target_version": {(3, 9)}},
    ),
    dict(
        config_lines=["target-version = ['py37', 'py39']"],
        expect={"target_version": {(3, 7), (3, 9)}},
    ),
    dict(
        config_lines=["target-version = ['py39', 'py37']"],
        expect={"target_version": {(3, 9), (3, 7)}},
    ),
    dict(
        config_lines=[r"exclude = '\.pyx$'"],
        expect={"exclude": RegexEquality("\\.pyx$")},
    ),
    dict(
        config_lines=["extend-exclude = '''", r"^/setup\.py", r"|^/dummy\.py", "'''"],
        expect={
            "extend_exclude": RegexEquality(
                "(?x)^/setup\\.py\n|^/dummy\\.py\n", re.VERBOSE
            )
        },
    ),
    dict(
        config_lines=["force-exclude = '''", r"^/setup\.py", r"|\.pyc$", "'''"],
        expect={"force_exclude": RegexEquality("(?x)^/setup\\.py\n|\\.pyc$\n")},
    ),
    config_path=None,
)
def test_read_config(tmpdir, option_name_delimiter, config_path, config_lines, expect):
    """``read_config()`` reads Black config correctly from a TOML file."""
    # Test both hyphen and underscore delimited option names
    config = "\n".join(
        line.replace("-", option_name_delimiter) for line in config_lines
    )
    tmpdir = Path(tmpdir)
    src = tmpdir / "src.py"
    toml = tmpdir / (config_path or "pyproject.toml")
    toml.write_text(f"[tool.black]\n{config}\n")
    with raises_or_matches(expect, []):
        formatter = BlackFormatter()
        args = Namespace()
        args.config = config_path and str(toml)
        if config_path:
            expect["config"] = str(toml)

        formatter.read_config((str(src),), args)

        assert formatter.config == expect


@pytest.mark.kwparametrize(
    dict(
        expect={
            "none",
            "exclude",
            "extend",
            "force",
            "exclude+extend",
            "exclude+force",
            "extend+force",
            "exclude+extend+force",
        }
    ),
    dict(exclude="exclude", expect={"none", "extend", "force", "extend+force"}),
    dict(extend_exclude="extend", expect={"none", "exclude", "force", "exclude+force"}),
    dict(force_exclude="force", expect={"none", "exclude", "extend", "exclude+extend"}),
    dict(exclude="exclude", extend_exclude="extend", expect={"none", "force"}),
    dict(exclude="exclude", force_exclude="force", expect={"none", "extend"}),
    dict(extend_exclude="extend", force_exclude="force", expect={"none", "exclude"}),
    dict(
        exclude="exclude",
        extend_exclude="extend",
        force_exclude="force",
        expect={"none"},
    ),
    exclude=None,
    extend_exclude=None,
    force_exclude=None,
)
def test_filter_python_files(
    tmp_path, monkeypatch, exclude, extend_exclude, force_exclude, expect
):
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    """``filter_python_files()`` skips excluded files correctly"""
    monkeypatch.chdir(tmp_path)
    names = {
        Path(name)
        for name in [
            "none.py",
            "exclude.py",
            "extend.py",
            "force.py",
            "exclude+extend.py",
            "exclude+force.py",
            "extend+force.py",
            "exclude+extend+force.py",
            "none+explicit.py",
            "exclude+explicit.py",
            "extend+explicit.py",
            "force+explicit.py",
            "exclude+extend+explicit.py",
            "exclude+force+explicit.py",
            "extend+force+explicit.py",
            "exclude+extend+force+explicit.py",
        ]
    }
    paths = {tmp_path / name for name in names}
    for path in paths:
        path.touch()
    black_config: BlackCompatibleConfig = {
        "exclude": regex.compile(exclude) if exclude else DEFAULT_EXCLUDE_RE,
        "extend_exclude": regex.compile(extend_exclude) if extend_exclude else None,
        "force_exclude": regex.compile(force_exclude) if force_exclude else None,
    }
    explicit = {
        Path("none+explicit.py"),
        Path("exclude+explicit.py"),
        Path("extend+explicit.py"),
        Path("force+explicit.py"),
        Path("exclude+extend+explicit.py"),
        Path("exclude+force+explicit.py"),
        Path("extend+force+explicit.py"),
        Path("exclude+extend+force+explicit.py"),
    }
    formatter = BlackFormatter()
    formatter.config = black_config

    result = filter_python_files({Path()} | explicit, tmp_path, formatter)

    expect_paths = {Path(f"{path}.py") for path in expect} | explicit
    assert result == expect_paths


def test_run_ignores_excludes():
    """Black's exclude configuration is ignored by `BlackFormatter.run`."""
    src = TextDocument.from_str("a=1\n")
    formatter = BlackFormatter()
    formatter.config = {
        "exclude": regex.compile(r".*"),
        "extend_exclude": regex.compile(r".*"),
        "force_exclude": regex.compile(r".*"),
    }

    result = formatter.run(src, Path("a.py"))

    assert result.string == "a = 1\n"


@pytest.mark.kwparametrize(
    dict(black_config={}),
    dict(
        black_config={"target_version": (3, 7)},
        expect_target_versions={TargetVersion.PY37},
    ),
    dict(
        black_config={"target_version": (3, 9)},
        expect_target_versions={TargetVersion.PY39},
    ),
    dict(
        black_config={"target_version": {(3, 7)}},
        expect_target_versions={TargetVersion.PY37},
    ),
    dict(
        black_config={"target_version": {(3, 9)}},
        expect_target_versions={TargetVersion.PY39},
    ),
    dict(
        black_config={"target_version": {(3, 7), (3, 9)}},
        expect_target_versions={TargetVersion.PY37, TargetVersion.PY39},
    ),
    dict(
        black_config={"target_version": {(3, 9), (3, 7)}},
        expect_target_versions={TargetVersion.PY37, TargetVersion.PY39},
    ),
    dict(
        black_config={"target_version": False},
        expect=ConfigurationError(),
    ),
    dict(
        black_config={"target_version": {False}},
        expect=ConfigurationError(),
    ),
    dict(black_config={"line_length": 80}, expect_line_length=80),
    dict(
        black_config={"skip_string_normalization": False},
        expect_string_normalization=True,
    ),
    dict(
        black_config={"skip_string_normalization": True},
        expect_string_normalization=False,
    ),
    dict(
        black_config={"skip_magic_trailing_comma": False},
        expect_magic_trailing_comma=True,
    ),
    dict(
        black_config={"skip_magic_trailing_comma": True},
        expect_magic_trailing_comma=False,
    ),
    expect=TextDocument.from_str("import os\n"),
    expect_target_versions=set(),
    expect_line_length=88,
    expect_string_normalization=True,
    expect_magic_trailing_comma=True,
)
def test_run_configuration(
    black_config,
    expect,
    expect_target_versions,
    expect_line_length,
    expect_string_normalization,
    expect_magic_trailing_comma,
):
    """`BlackFormatter.run` passes correct configuration to Black."""
    src = TextDocument.from_str("import  os\n")
    with patch(
        "darker.formatters.black_wrapper.format_str"
    ) as format_str, raises_or_matches(expect, []) as check:
        format_str.return_value = "import os\n"
        formatter = BlackFormatter()
        formatter.config = black_config

        check(formatter.run(src, Path("a.py")))

        assert format_str.call_count == 1
        mode = format_str.call_args[1]["mode"]
        assert mode == Mode(
            target_versions=expect_target_versions,
            line_length=expect_line_length,
            string_normalization=expect_string_normalization,
            magic_trailing_comma=expect_magic_trailing_comma,
        )
