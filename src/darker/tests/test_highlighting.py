"""Unit tests for :mod:`darker.highlighting`"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pygments.token import Token

from darker.command_line import parse_command_line
from darker.highlighting import colorize, lexers, should_use_color


@pytest.mark.parametrize(
    "params",
    [
        "                                                         ",
        "                                            tty          ",
        "                                 --no-color              ",
        "                                 --no-color tty          ",
        "                                    --color              ",
        "                                    --color tty          ",
        "                     PY_COLORS=0                         ",
        "                     PY_COLORS=0            tty          ",
        "                     PY_COLORS=0 --no-color              ",
        "                     PY_COLORS=0 --no-color tty          ",
        "                     PY_COLORS=0    --color              ",
        "                     PY_COLORS=0    --color tty          ",
        "                     PY_COLORS=1                         ",
        "                     PY_COLORS=1            tty          ",
        "                     PY_COLORS=1 --no-color              ",
        "                     PY_COLORS=1 --no-color tty          ",
        "                     PY_COLORS=1    --color              ",
        "                     PY_COLORS=1    --color tty          ",
        "         color=false                                     ",
        "         color=false                        tty          ",
        "         color=false             --no-color              ",
        "         color=false             --no-color tty          ",
        "         color=false                --color              ",
        "         color=false                --color tty          ",
        "         color=false PY_COLORS=0                         ",
        "         color=false PY_COLORS=0            tty          ",
        "         color=false PY_COLORS=0 --no-color              ",
        "         color=false PY_COLORS=0 --no-color tty          ",
        "         color=false PY_COLORS=0    --color              ",
        "         color=false PY_COLORS=0    --color tty          ",
        "         color=false PY_COLORS=1                         ",
        "         color=false PY_COLORS=1            tty          ",
        "         color=false PY_COLORS=1 --no-color              ",
        "         color=false PY_COLORS=1 --no-color tty          ",
        "         color=false PY_COLORS=1    --color              ",
        "         color=false PY_COLORS=1    --color tty          ",
        "         color=true                                      ",
        "         color=true                         tty          ",
        "         color=true              --no-color              ",
        "         color=true              --no-color tty          ",
        "         color=true                 --color              ",
        "         color=true                 --color tty          ",
        "         color=true  PY_COLORS=0                         ",
        "         color=true  PY_COLORS=0            tty          ",
        "         color=true  PY_COLORS=0 --no-color              ",
        "         color=true  PY_COLORS=0 --no-color tty          ",
        "         color=true  PY_COLORS=0    --color              ",
        "         color=true  PY_COLORS=0    --color tty          ",
        "         color=true  PY_COLORS=1                         ",
        "         color=true  PY_COLORS=1            tty          ",
        "         color=true  PY_COLORS=1 --no-color              ",
        "         color=true  PY_COLORS=1 --no-color tty          ",
        "         color=true  PY_COLORS=1    --color              ",
        "         color=true  PY_COLORS=1    --color tty          ",
        "pygments                                                 ",
        "pygments                                    tty USE_COLOR",
        "pygments                         --no-color              ",
        "pygments                         --no-color tty          ",
        "pygments                            --color     USE_COLOR",
        "pygments                            --color tty USE_COLOR",
        "pygments             PY_COLORS=0                         ",
        "pygments             PY_COLORS=0            tty          ",
        "pygments             PY_COLORS=0 --no-color              ",
        "pygments             PY_COLORS=0 --no-color tty          ",
        "pygments             PY_COLORS=0    --color     USE_COLOR",
        "pygments             PY_COLORS=0    --color tty USE_COLOR",
        "pygments             PY_COLORS=1                USE_COLOR",
        "pygments             PY_COLORS=1            tty USE_COLOR",
        "pygments             PY_COLORS=1 --no-color              ",
        "pygments             PY_COLORS=1 --no-color tty          ",
        "pygments             PY_COLORS=1    --color     USE_COLOR",
        "pygments             PY_COLORS=1    --color tty USE_COLOR",
        "pygments color=false                                     ",
        "pygments color=false                        tty          ",
        "pygments color=false             --no-color              ",
        "pygments color=false             --no-color tty          ",
        "pygments color=false                --color     USE_COLOR",
        "pygments color=false                --color tty USE_COLOR",
        "pygments color=false PY_COLORS=0                         ",
        "pygments color=false PY_COLORS=0            tty          ",
        "pygments color=false PY_COLORS=0 --no-color              ",
        "pygments color=false PY_COLORS=0 --no-color tty          ",
        "pygments color=false PY_COLORS=0    --color     USE_COLOR",
        "pygments color=false PY_COLORS=0    --color tty USE_COLOR",
        "pygments color=false PY_COLORS=1                USE_COLOR",
        "pygments color=false PY_COLORS=1            tty USE_COLOR",
        "pygments color=false PY_COLORS=1 --no-color              ",
        "pygments color=false PY_COLORS=1 --no-color tty          ",
        "pygments color=false PY_COLORS=1    --color     USE_COLOR",
        "pygments color=false PY_COLORS=1    --color tty USE_COLOR",
        "pygments color=true                             USE_COLOR",
        "pygments color=true                         tty USE_COLOR",
        "pygments color=true              --no-color              ",
        "pygments color=true              --no-color tty          ",
        "pygments color=true                 --color     USE_COLOR",
        "pygments color=true                 --color tty USE_COLOR",
        "pygments color=true  PY_COLORS=0                         ",
        "pygments color=true  PY_COLORS=0            tty          ",
        "pygments color=true  PY_COLORS=0 --no-color              ",
        "pygments color=true  PY_COLORS=0 --no-color tty          ",
        "pygments color=true  PY_COLORS=0    --color     USE_COLOR",
        "pygments color=true  PY_COLORS=0    --color tty USE_COLOR",
        "pygments color=true  PY_COLORS=1                USE_COLOR",
        "pygments color=true  PY_COLORS=1            tty USE_COLOR",
        "pygments color=true  PY_COLORS=1 --no-color              ",
        "pygments color=true  PY_COLORS=1 --no-color tty          ",
        "pygments color=true  PY_COLORS=1    --color     USE_COLOR",
        "pygments color=true  PY_COLORS=1    --color tty USE_COLOR",
    ],
)
def test_should_use_color(tmp_path: Path, params: str) -> None:
    """Color output is used only if correct configuration options are in place"""
    modules = sys.modules.copy()
    if "pygments " not in params:
        del modules["darker.highlighting"]
        # cause an ImportError for `import pygments`:
        modules["pygments"] = None  # type: ignore[assignment]
    with (tmp_path / "pyproject.toml").open("w") as pyproject:
        print("[tool.darker]", file=pyproject)
        if " color=true " in params:
            print("color = true", file=pyproject)
        if " color=false " in params:
            print("color = false", file=pyproject)
    env = {}
    if " PY_COLORS=0 " in params:
        env["PY_COLORS"] = "0"
    if " PY_COLORS=1 " in params:
        env["PY_COLORS"] = "1"
    argv = [str(tmp_path / "dummy.py")]
    if " --color " in params:
        argv.insert(0, "--color")
    if " --no-color " in params:
        argv.insert(0, "--no-color")
    with patch.dict(os.environ, env, clear=True):
        _, config, _ = parse_command_line(argv)
    with patch.dict(sys.modules, modules, clear=True), patch(
        "sys.stdout.isatty", Mock(return_value=" tty " in params)
    ):

        result = should_use_color(config["color"])

    expect = " USE_COLOR" in params
    assert result == expect


def test_colorize_with_no_color():
    """``colorize()`` does nothing when Pygments isn't available"""
    result = colorize("print(42)", "python", use_color=False)

    assert result == "print(42)"


@pytest.mark.parametrize(
    "text, lexer, use_color, expect",
    [
        (
            "except RuntimeError:",
            "python",
            True,
            {"\x1b[34mexcept\x1b[39;49;00m \x1b[36mRuntimeError\x1b[39;49;00m:"},
        ),
        ("except RuntimeError:", "python", False, {"except RuntimeError:"}),
        ("a = 1", "python", True, {"a = \x1b[34m1\x1b[39;49;00m"}),
        ("a = 1\n", "python", True, {"a = \x1b[34m1\x1b[39;49;00m\n"}),
        (
            "- a\n+ b\n",
            "diff",
            True,
            {
                # Pygments 2.4.0:
                "\x1b[31;01m- a\x1b[39;49;00m\n\x1b[32m+ b\x1b[39;49;00m\n",
                # Pygments 2.10.0:
                "\x1b[91m- a\x1b[39;49;00m\n\x1b[32m+ b\x1b[39;49;00m\n",
                # Pygments 2.11.2:
                "\x1b[91m- a\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n"
                + "\x1b[32m+ b\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n",
            },
        ),
        (
            "- a\n+ b\n",
            "diff",
            False,
            {"- a\n+ b\n"},
        ),
    ],
)
def test_colorize(text, lexer, use_color, expect):
    """``colorize()`` produces correct highlighted terminal output"""
    result = colorize(text, lexer, use_color)

    assert result in expect


@pytest.mark.parametrize(
    "text, expect",
    [
        (
            "path/to/file.py:42:",
            [
                (0, Token.Literal.String, "path/to/file.py"),
                (15, Token.Text, ":"),
                (16, Token.Literal.Number, "42"),
                (18, Token.Text, ":"),
                (19, Token.Literal.Number, ""),
            ],
        ),
        (
            "path/to/file.py:42:43:",
            [
                (0, Token.Literal.String, "path/to/file.py"),
                (15, Token.Text, ":"),
                (16, Token.Literal.Number, "42"),
                (18, Token.Text, ":"),
                (19, Token.Literal.Number, "43"),
                (21, Token.Text, ":"),
                (22, Token.Literal.Number, ""),
            ],
        ),
    ],
)
def test_location_lexer(text, expect):
    """Linter "path:linenum:colnum:" prefixes are lexed correctly"""
    location_lexer = lexers.LocationLexer()

    result = list(location_lexer.get_tokens_unprocessed(text))

    assert result == expect


@pytest.mark.parametrize(
    "text, expect",
    [
        (
            "  no coverage:     a = 1",
            [
                (0, Token.Literal.String, "  no coverage: "),
                (15, Token.Text, "    "),
                (19, Token.Name, "a"),
                (20, Token.Text, " "),
                (21, Token.Operator, "="),
                (22, Token.Text, " "),
                (23, Token.Literal.Number.Integer, "1"),
            ],
        ),
        (
            "C000 python(code) = not(highlighted)",
            [
                (0, Token.Error, "C000"),
                (4, Token.Literal.String, " "),
                (5, Token.Literal.String, "python(code)"),
                (17, Token.Literal.String, " "),
                (18, Token.Literal.String, "="),
                (19, Token.Literal.String, " "),
                (20, Token.Literal.String, "not(highlighted)"),
            ],
        ),
        (
            "C0000 Unused argument not highlighted",
            [
                (0, Token.Error, "C0000"),
                (5, Token.Literal.String, " "),
                (6, Token.Literal.String, "Unused argument "),
                (22, Token.Literal.String, "not"),
                (25, Token.Literal.String, " "),
                (26, Token.Literal.String, "highlighted"),
            ],
        ),
        (
            "E000 Unused variable not highlighted",
            [
                (0, Token.Error, "E000"),
                (4, Token.Literal.String, " "),
                (5, Token.Literal.String, "Unused variable "),
                (21, Token.Literal.String, "not"),
                (24, Token.Literal.String, " "),
                (25, Token.Literal.String, "highlighted"),
            ],
        ),
        (
            "E0000 Returning python_expression - is highlighted",
            [
                (0, Token.Error, "E0000"),
                (5, Token.Literal.String, " "),
                (6, Token.Literal.String, "Returning "),
                (16, Token.Name, "python_expression"),
                (33, Token.Literal.String, " "),
                (34, Token.Literal.String, "-"),
                (35, Token.Literal.String, " "),
                (36, Token.Literal.String, "is"),
                (38, Token.Literal.String, " "),
                (39, Token.Literal.String, "highlighted"),
            ],
        ),
        (
            "F000 Unused python_expression_highlighted",
            [
                (0, Token.Error, "F000"),
                (4, Token.Literal.String, " "),
                (5, Token.Literal.String, "Unused "),
                (12, Token.Name, "python_expression_highlighted"),
            ],
        ),
        (
            "F0000 Base type PythonClassHighlighted whatever",
            [
                (0, Token.Error, "F0000"),
                (5, Token.Literal.String, " "),
                (6, Token.Literal.String, "Base type "),
                (16, Token.Name, "PythonClassHighlighted"),
                (38, Token.Literal.String, " "),
                (39, Token.Literal.String, "whatever"),
            ],
        ),
        (
            "N000 imported from python.module.highlighted",
            [
                (0, Token.Error, "N000"),
                (4, Token.Literal.String, " "),
                (5, Token.Literal.String, "imported from "),
                (19, Token.Name, "python"),
                (25, Token.Operator, "."),
                (26, Token.Name, "module"),
                (32, Token.Operator, "."),
                (33, Token.Name, "highlighted"),
            ],
        ),
        (
            "N0000 (message-identifier) not-highlighted-in-the-middle",
            [
                (0, Token.Error, "N0000"),
                (5, Token.Literal.String, " "),
                (6, Token.Literal.String, "(message-identifier)"),
                (26, Token.Literal.String, " "),
                (27, Token.Literal.String, "not-highlighted-in-the-middle"),
            ],
        ),
        (
            "W000 at-the-end-highlight (message-identifier)",
            [
                (0, Token.Error, "W000"),
                (4, Token.Literal.String, " "),
                (5, Token.Literal.String, "at-the-end-highlight"),
                (25, Token.Literal.String, " "),
                (26, Token.Literal.String, "("),
                (27, Token.Error, "message-identifier"),
                (45, Token.Literal.String, ")"),
            ],
        ),
        (
            "W0000 four-digit-warning",
            [
                (0, Token.Error, "W0000"),
                (5, Token.Literal.String, " "),
                (6, Token.Literal.String, "four-digit-warning"),
            ],
        ),
        (
            "E00 two-digit-message-id-not-highlighted",
            [
                (0, Token.Text, ""),
                (0, Token.Literal.String, "E00"),
                (3, Token.Literal.String, " "),
                (4, Token.Literal.String, "two-digit-message-id-not-highlighted"),
            ],
        ),
        (
            "E00000 five-digit-message-id-not-highlighted",
            [
                (0, Token.Text, ""),
                (0, Token.Literal.String, "E00000"),
                (6, Token.Literal.String, " "),
                (7, Token.Literal.String, "five-digit-message-id-not-highlighted"),
            ],
        ),
    ],
)
def test_description_lexer(text, expect):
    """The description parts of linter output are lexed correctly"""
    description_lexer = lexers.DescriptionLexer()

    result = list(description_lexer.get_tokens_unprocessed(text))

    assert result == expect
