"""Unit tests for :mod:`darker.highlighting`"""

# pylint: disable=too-many-arguments,redefined-outer-name,unused-argument

import os
import sys
from pathlib import Path
from typing import Dict, Generator, List
from unittest.mock import Mock, patch

import pytest
from _pytest.fixtures import SubRequest
from pygments.token import Token

from darker.command_line import parse_command_line
from darker.highlighting import colorize, lexers, should_use_color


@pytest.fixture(params=["", "color = false", "color = true"])
def pyproject_toml_color(
    request: SubRequest, tmp_path: Path
) -> Generator[None, None, None]:
    """Parametrized fixture for the ``color =`` option in ``pyproject.toml``

    Creates three versions of ``pyproject.toml`` in ``tmp_path`` for a test function:

    Without the ``color =`` option::

        [tool.darker]

    With color turned off::

        [tool.darker]
        color = false

    With color turned on::

        [tool.darker]
        color = true

    :param request: The Pytest ``request`` object
    :param tmp_path: A temporary directory created by Pytest
    :yield: The ``color =`` option line in ``pyproject.toml``, or an empty string

    """
    with (tmp_path / "pyproject.toml").open("w") as pyproject_toml:
        print(f"[tool.darker]\n{request.param}\n", file=pyproject_toml)

    yield request.param


@pytest.fixture(params=[False, True])
def tty(request: SubRequest) -> Generator[None, None, None]:
    """Parametrized fixture for patching `sys.stdout.isatty`

    Patches `sys.stdout.isatty` to return either `False` or `True`.

    :param request: The Pytest ``request`` object
    :yield: The patched `False` or `True` return value for `sys.stdout.isatty`

    """
    with patch("sys.stdout.isatty", Mock(return_value=request.param)):

        yield request.param


@pytest.fixture(params=[{}, {"NO_COLOR": "foo"}])
def env_no_color(request: SubRequest) -> Generator[None, None, None]:
    """Parametrized fixture for patching ``NO_COLOR``

    Patches the environment with or without the ``NO_COLOR`` environment variable

    :param request: The Pytest ``request`` object
    :yield: The patched items in the environment

    """
    with patch.dict(os.environ, request.param):

        yield request.param


@pytest.fixture(params=[{}, {"PY_COLORS": "0"}, {"PY_COLORS": "1"}])
def env_py_colors(request: SubRequest) -> Generator[None, None, None]:
    """Parametrized fixture for patching ``PY_COLORS``

    Patches the environment with or without the ``PY_COLORS`` environment variable

    :param request: The Pytest ``request`` object
    :yield: The patched items in the environment

    """
    with patch.dict(os.environ, request.param):

        yield request.param


@pytest.mark.parametrize("cmdline", [[], ["--no-color"], ["--color"]])
def test_should_use_color_no_pygments(
    tmp_path: Path,
    pyproject_toml_color: str,
    env_no_color: Dict[str, str],
    env_py_colors: Dict[str, str],
    cmdline: List[str],
    tty: bool,
) -> None:
    """Color output is never used if `pygments` is not installed"""
    argv = cmdline + [str(tmp_path / "dummy.py")]
    _, config, _ = parse_command_line(argv)
    mods = sys.modules.copy()
    del mods["darker.highlighting"]
    # cause an ImportError for `import pygments`:
    mods["pygments"] = None  # type: ignore[assignment]
    with patch.dict(sys.modules, mods, clear=True):

        result = should_use_color(config["color"])

    assert result is False


@pytest.mark.kwparametrize(
    dict(cmdline="--no-color", expect=False),
    dict(cmdline="--color", expect=True),
)
def test_should_use_color_pygments_and_command_line_argument(
    tmp_path: Path,
    pyproject_toml_color: str,
    env_no_color: Dict[str, str],
    env_py_colors: Dict[str, str],
    cmdline: str,
    expect: bool,
    tty: bool,
) -> None:
    """--color / --no-color determines highlighting if `pygments` is installed"""
    argv = [cmdline, str(tmp_path / "dummy.py")]
    _, config, _ = parse_command_line(argv)

    result = should_use_color(config["color"])

    assert result == expect


@pytest.mark.kwparametrize(
    dict(env_py_colors_={"PY_COLORS": "0"}, expect=False),
    dict(env_py_colors_={"PY_COLORS": "1"}, expect=True),
)
def test_should_use_color_pygments_and_py_colors(
    tmp_path: Path,
    pyproject_toml_color: str,
    env_no_color: Dict[str, str],
    env_py_colors_: Dict[str, str],
    expect: bool,
    tty: bool,
) -> None:
    """PY_COLORS determines highlighting when `pygments` installed and no cmdline args

    These tests are set up so that it appears as if
    - ``pygments`` is installed
    - there is no ``--color`` or `--no-color`` command line option

    """
    with patch.dict(os.environ, env_py_colors_, clear=True):
        _, config, _ = parse_command_line([str(tmp_path / "dummy.py")])

    result = should_use_color(config["color"])

    assert result == expect


@pytest.mark.parametrize(
    "params, expect",
    [
        # for the expected value, for readability, strings are used instead of booleans
        ("                            ", ""),
        ("                         tty", "should_use_color() == True"),
        ("color=false                 ", ""),
        ("color=false              tty", ""),
        ("color=true                  ", "should_use_color() == True"),
        ("color=true               tty", "should_use_color() == True"),
        ("            NO_COLOR=foo    ", ""),
        ("            NO_COLOR=foo tty", ""),
        ("color=false NO_COLOR=foo    ", ""),
        ("color=false NO_COLOR=foo tty", ""),
        ("color=true  NO_COLOR=foo    ", ""),
        ("color=true  NO_COLOR=foo tty", ""),
    ],
)
def test_should_use_color_pygments(tmp_path: Path, params: str, expect: str) -> None:
    """Color output is enabled only if correct configuration options are in place

    These tests are set up so that it appears as if
    - ``pygments`` is installed
    - there is no ``--color`` or `--no-color`` command line option
    - the ``PY_COLORS`` environment variable isn't set to ``0`` or ``1``

    """
    with (tmp_path / "pyproject.toml").open("w") as pyproject:
        print("[tool.darker]", file=pyproject)
        if params.startswith("color="):
            print(params.split()[0], file=pyproject)
    env = {}
    if " NO_COLOR=foo " in params:
        env["NO_COLOR"] = "foo"
    with patch.dict(os.environ, env, clear=True):
        _, config, _ = parse_command_line([str(tmp_path / "dummy.py")])
    with patch("sys.stdout.isatty", Mock(return_value=params.endswith(" tty"))):

        result = should_use_color(config["color"])

    assert result == (expect == "should_use_color() == True")


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
