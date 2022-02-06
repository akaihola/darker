"""Unit tests for `darker.black_diff`"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import ANY, patch

import pytest
import regex

from darker import black_diff
from darker.black_diff import (
    BlackConfig,
    filter_python_files,
    read_black_config,
    run_black,
)
from darker.utils import TextDocument


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


@pytest.mark.kwparametrize(
    dict(
        config_path=None, config_lines=["line-length = 79"], expect={"line_length": 79}
    ),
    dict(
        config_path="custom.toml",
        config_lines=["line-length = 99"],
        expect={"line_length": 99},
    ),
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
    dict(config_lines=["target-version = ['py37']"], expect={}),
    dict(config_lines=[r"include = '\.pyi$'"], expect={}),
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
def test_black_config(tmpdir, config_path, config_lines, expect):
    tmpdir = Path(tmpdir)
    src = tmpdir / "src.py"
    toml = tmpdir / (config_path or "pyproject.toml")
    toml.write_text("[tool.black]\n{}\n".format("\n".join(config_lines)))

    config = read_black_config((str(src),), config_path and str(toml))

    assert config == expect


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
    """``filter_python_files()`` skips excluded files correctly"""
    monkeypatch.chdir(tmp_path)
    names = {
        Path(name)
        for name in {
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
        }
    }
    paths = {tmp_path / name for name in names}
    for path in paths:
        path.touch()
    black_config = BlackConfig(
        {
            "exclude": regex.compile(exclude) if exclude else None,
            "extend_exclude": regex.compile(extend_exclude) if extend_exclude else None,
            "force_exclude": regex.compile(force_exclude) if force_exclude else None,
        }
    )
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

    result = filter_python_files({Path(".")} | explicit, tmp_path, black_config)

    expect_paths = {tmp_path / f"{path}.py" for path in expect} | {
        tmp_path / p for p in explicit
    }
    assert result == expect_paths


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_black(encoding, newline):
    """Running Black through its Python internal API gives correct results"""
    src = TextDocument.from_lines(
        [f"# coding: {encoding}", "print ( 'touché' )"],
        encoding=encoding,
        newline=newline,
    )

    result = run_black(src, BlackConfig())

    assert result.lines == (
        f"# coding: {encoding}",
        'print("touché")',
    )
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_black_always_uses_unix_newlines(newline):
    """Content is always passed to Black with Unix newlines"""
    src = TextDocument.from_str(f"print ( 'touché' ){newline}")
    with patch.object(black_diff, "format_str") as format_str:
        format_str.return_value = 'print("touché")\n'

        _ = run_black(src, BlackConfig())

    format_str.assert_called_once_with("print ( 'touché' )\n", mode=ANY)


def test_run_black_ignores_excludes():
    """Black's exclude configuration is ignored by ``run_black()``"""
    src = TextDocument.from_str("a=1\n")

    result = run_black(
        src,
        BlackConfig(
            {
                "exclude": regex.compile(r".*"),
                "extend_exclude": regex.compile(r".*"),
                "force_exclude": regex.compile(r".*"),
            }
        ),
    )

    assert result.string == "a = 1\n"


@pytest.mark.parametrize(
    "src_content, expect",
    [
        ("", ""),
        ("\n", "\n"),
        ("\r\n", "\r\n"),
        (" ", ""),
        ("\t", ""),
        (" \t", ""),
        (" \t\n", "\n"),
        (" \t\r\n", "\r\n"),
    ],
)
def test_run_black_all_whitespace_input(src_content, expect):
    """All-whitespace files are reformatted correctly"""
    src = TextDocument.from_str(src_content)

    result = run_black(src, BlackConfig())

    assert result.string == expect
