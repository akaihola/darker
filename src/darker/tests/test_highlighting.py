"""Unit tests for :mod:`darker.highlighting`"""

# pylint: disable=too-many-arguments,redefined-outer-name,unused-argument
# pylint: disable=protected-access

import os
import sys
from pathlib import Path
from shlex import shlex
from typing import Dict, Generator
from unittest.mock import patch

import pytest
from _pytest.fixtures import SubRequest
from pygments.token import Token

from darker.command_line import parse_command_line
from darker.highlighting import colorize, lexers, should_use_color


@pytest.fixture(scope="module")
def module_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fixture for creating a module-scope temporary directory

    :param tmp_path_factory: The temporary path factory fixture from Pytest
    :return: The created directory path

    """
    return tmp_path_factory.mktemp("test_highlighting")


def unset_our_env_vars():
    """Unset the environment variables used in this test module"""
    os.environ.pop("PY_COLORS", None)
    os.environ.pop("NO_COLOR", None)
    os.environ.pop("FORCE_COLOR", None)


@pytest.fixture(scope="module", autouse=True)
def clean_environ():
    """Fixture for clearing unwanted environment variables

    The ``NO_COLOR`` and ``PY_COLORS`` environment variables are tested in this module,
    so we need to ensure they aren't already set.

    In all `os.environ` patching, we use our own low-level custom code instead of
    `unittest.mock.patch.dict` for performance reasons.

    """
    old = os.environ
    os.environ = old.copy()  # type: ignore  # noqa: B003
    unset_our_env_vars()

    yield

    os.environ = old  # noqa: B003


@pytest.fixture(params=["", "color = false", "color = true"])
def pyproject_toml_color(
    request: SubRequest, module_tmp_path: Path
) -> Generator[None, None, None]:
    """Parametrized fixture for the ``color =`` option in ``pyproject.toml``

    Creates three versions of ``pyproject.toml`` in ``module_tmp_path`` for a test
    function:

    Without the ``color =`` option::

        [tool.darker]

    With color turned off::

        [tool.darker]
        color = false

    With color turned on::

        [tool.darker]
        color = true

    :param request: The Pytest ``request`` object
    :param module_tmp_path: A temporary directory created by Pytest
    :yield: The ``color =`` option line in ``pyproject.toml``, or an empty string

    """
    pyproject_toml_path = module_tmp_path / "pyproject.toml"
    with pyproject_toml_path.open("w") as pyproject_toml:
        print(f"[tool.darker]\n{request.param}\n", file=pyproject_toml)

    yield request.param

    pyproject_toml_path.unlink()


@pytest.fixture(params=["", "tty"])
def tty(request: SubRequest) -> Generator[bool, None, None]:
    """Parametrized fixture for patching `sys.stdout.isatty`

    Patches `sys.stdout.isatty` to return either `False` or `True`. The parameter values
    are strings and not booleans in order to improve readability of parametrized tests.
    Custom patching for performance.

    :param request: The Pytest ``request`` object
    :yield: The patched `False` or `True` return value for `sys.stdout.isatty`

    """
    old_isatty = sys.stdout.isatty
    is_a_tty: bool = request.param == "tty"
    sys.stdout.isatty = lambda: is_a_tty  # type: ignore[assignment]

    yield is_a_tty

    sys.stdout.isatty = old_isatty  # type: ignore[assignment]


def _parse_environment_variables(definitions: str) -> Dict[str, str]:
    """Parse a ``"<var1>=<val1> <var2>=<val2>"`` formatted string into a dictionary

    :param definitions: The string to parse
    :return: The parsed dictionary

    """
    return dict(item.split("=") for item in shlex(definitions, punctuation_chars=" "))


@pytest.fixture(params=["", "NO_COLOR=", "NO_COLOR=foo"])
def env_no_color(request: SubRequest) -> Generator[Dict[str, str], None, None]:
    """Parametrized fixture for patching ``NO_COLOR``

    This fixture must come before `config_from_env_and_argv` in test function
    signatures.

    Patches the environment with or without the ``NO_COLOR`` environment variable. The
    environment is expressed as a space-separated string to improve readability of
    parametrized tests.

    :param request: The Pytest ``request`` object
    :yield: The patched items in the environment

    """
    os.environ.update(_parse_environment_variables(request.param))
    yield request.param
    unset_our_env_vars()


@pytest.fixture(params=["", "FORCE_COLOR=", "FORCE_COLOR=foo"])
def env_force_color(request: SubRequest) -> Generator[Dict[str, str], None, None]:
    """Parametrized fixture for patching ``FORCE_COLOR``

    This fixture must come before `config_from_env_and_argv` in test function
    signatures.

    Patches the environment with or without the ``FORCE_COLOR`` environment variable.
    The environment is expressed as a space-separated string to improve readability of
    parametrized tests.

    :param request: The Pytest ``request`` object
    :yield: The patched items in the environment

    """
    os.environ.update(_parse_environment_variables(request.param))
    yield request.param
    unset_our_env_vars()


@pytest.fixture(params=["", "PY_COLORS=0", "PY_COLORS=1"])
def env_py_colors(request: SubRequest) -> Generator[Dict[str, str], None, None]:
    """Parametrized fixture for patching ``PY_COLORS``

    This fixture must come before `config_from_env_and_argv` in test function
    signatures.

    Patches the environment with or without the ``PY_COLORS`` environment variable. The
    environment is expressed as a space-separated string to improve readability of
    parametrized tests.

    :param request: The Pytest ``request`` object
    :yield: The patched items in the environment

    """
    os.environ.update(_parse_environment_variables(request.param))
    yield request.param
    unset_our_env_vars()


@pytest.fixture
def uninstall_pygments() -> Generator[None, None, None]:
    """Fixture for uninstalling ``pygments`` temporarily"""
    mods = sys.modules.copy()
    del mods["darker.highlighting"]
    # cause an ImportError for `import pygments`:
    mods["pygments"] = None  # type: ignore[assignment]
    with patch.dict(sys.modules, mods, clear=True):

        yield


config_cache = {}


@pytest.fixture(params=[[], ["--no-color"], ["--color"]])
def config_from_env_and_argv(
    request: SubRequest, module_tmp_path: Path
) -> Generator[bool, None, None]:
    """Parametrized fixture for the ``--color`` / ``--no-color`` arguments

    Yields ``color`` configuration boolean values resulting from the current environment
    variables and a command line
    - with no color argument,
    - with the ``--color`` argument, and
    - with the ``--no--color`` argument.

    The ``NO_COLOR`` and ``PY_COLORS`` environment variables affect the resulting
    configuration, and must precede `config_from_env_and_argv` in test function
    signatures (if they are being used).

    :param request: The Pytest ``request`` object
    :param module_tmp_path: A temporary directory created by Pytest
    :yield: The list of arguments for the Darker command line

    """
    argv = request.param + [str(module_tmp_path / "dummy.py")]
    cache_key = (
        tuple(request.param),
        os.getenv("NO_COLOR"),
        os.getenv("FORCE_COLOR"),
        os.getenv("PY_COLORS"),
        (module_tmp_path / "pyproject.toml").read_bytes(),
    )
    if cache_key not in config_cache:
        _, config, _ = parse_command_line(argv)
        config_cache[cache_key] = config["color"]
    yield config_cache[cache_key]


def test_should_use_color_no_pygments(
    uninstall_pygments: None,
    pyproject_toml_color: str,
    env_no_color: str,
    env_force_color: str,
    env_py_colors: str,
    config_from_env_and_argv: bool,
    tty: bool,
) -> None:
    """Color output is never used if `pygments` is not installed

    All combinations of ``pyproject.toml`` options, environment variables and command
    line options affecting syntax highlighting are tested without `pygments`.

    """
    result = should_use_color(config_from_env_and_argv)

    assert result is False


@pytest.mark.parametrize(
    "config_from_env_and_argv, expect",
    [(["--no-color"], False), (["--color"], True)],
    indirect=["config_from_env_and_argv"],
)
def test_should_use_color_pygments_and_command_line_argument(
    pyproject_toml_color: str,
    env_no_color: str,
    env_force_color: str,
    env_py_colors: str,
    config_from_env_and_argv: bool,
    expect: bool,
    tty: bool,
) -> None:
    """--color / --no-color determines highlighting if `pygments` is installed

    All combinations of ``pyproject.toml`` options, environment variables and command
    line options affecting syntax highlighting are tested with `pygments` installed.

    """
    result = should_use_color(config_from_env_and_argv)

    assert result == expect


@pytest.mark.parametrize(
    "env_py_colors, expect",
    [("PY_COLORS=0", False), ("PY_COLORS=1", True)],
    indirect=["env_py_colors"],
)
@pytest.mark.parametrize("config_from_env_and_argv", [[]], indirect=True)
def test_should_use_color_pygments_and_py_colors(
    pyproject_toml_color: str,
    env_no_color: str,
    env_force_color: str,
    env_py_colors: str,
    config_from_env_and_argv: bool,
    tty: bool,
    expect: bool,
) -> None:
    """PY_COLORS determines highlighting when `pygments` installed and no cmdline args

    These tests are set up so that it appears as if
    - ``pygments`` is installed
    - there is no ``--color`` or `--no-color`` command line option

    All combinations of ``pyproject.toml`` options and environment variables affecting
    syntax highlighting are tested.

    """
    result = should_use_color(config_from_env_and_argv)

    assert result == expect


@pytest.mark.parametrize(
    "env_no_color, env_force_color, expect",
    [
        ("            ", "FORCE_COLOR=   ", "should_use_color() == True"),
        ("            ", "FORCE_COLOR=foo", "should_use_color() == True"),
        ("NO_COLOR=   ", "FORCE_COLOR=   ", "                          "),
        ("NO_COLOR=   ", "FORCE_COLOR=foo", "                          "),
        ("NO_COLOR=foo", "FORCE_COLOR=   ", "                          "),
        ("NO_COLOR=foo", "FORCE_COLOR=foo", "                          "),
    ],
    indirect=["env_no_color", "env_force_color"],
)
@pytest.mark.parametrize("config_from_env_and_argv", [[]], indirect=True)
def test_should_use_color_no_color_force_color(
    pyproject_toml_color: str,
    env_no_color: str,
    env_force_color: str,
    config_from_env_and_argv: bool,
    tty: bool,
    expect: str,
) -> None:
    """NO_COLOR/FORCE_COLOR determine highlighting in absence of PY_COLORS/cmdline args

    These tests are set up so that it appears as if
    - ``pygments`` is installed
    - the ``PY_COLORS`` environment variable is unset
    - there is no ``--color`` or `--no-color`` command line option

    All combinations of ``pyproject.toml`` options, ``NO_COLOR``, ``FORCE_COLOR`` and
    `sys.stdout.isatty` are tested.

    """
    result = should_use_color(config_from_env_and_argv)

    assert result == (expect == "should_use_color() == True")


@pytest.mark.parametrize("config_from_env_and_argv", [[]], indirect=True)
@pytest.mark.parametrize(
    "pyproject_toml_color, tty, expect",
    [
        # for readability, padded strings are used for parameters and the expectation
        ("             ", "   ", "                          "),
        ("             ", "tty", "should_use_color() == True"),
        ("color = false", "   ", "                          "),
        ("color = false", "tty", "                          "),
        ("color = true ", "   ", "should_use_color() == True"),
        ("color = true ", "tty", "should_use_color() == True"),
    ],
    indirect=["pyproject_toml_color", "tty"],
)
def test_should_use_color_pygments(
    pyproject_toml_color: str,
    tty: bool,
    config_from_env_and_argv: bool,
    expect: str,
) -> None:
    """Color output is enabled only if correct configuration options are in place

    These tests are set up so that it appears as if
    - ``pygments`` is installed (required for running the tests)
    - there is no ``--color`` or `--no-color`` command line option
    - the ``PY_COLORS`` environment variable isn't set to ``0`` or ``1`` (cleared by
      the auto-use ``clear_environ`` fixture)

    This test exercises the remaining combinations of ``pyproject.toml`` options and
    environment variables affecting syntax highlighting.

    """
    result = should_use_color(config_from_env_and_argv)

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
