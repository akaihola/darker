"""Unit tests for Black compatible formatter plugins."""

# pylint: disable=use-dict-literal

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from darker.formatters import ruff_formatter
from darker.formatters.black_formatter import BlackFormatter
from darker.formatters.ruff_formatter import RuffFormatter
from darkgraylib.testtools.helpers import raises_or_matches
from darkgraylib.utils import TextDocument


@pytest.mark.parametrize(
    "formatter_setup",
    [(BlackFormatter, "-"), (BlackFormatter, "_"), (RuffFormatter, "-")],
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
    dict(config_lines=[r"include = '\.pyi$'"], expect={}),
    config_path=None,
)
def test_read_config_black_and_ruff(
    tmpdir, formatter_setup, config_path, config_lines, expect
):
    """``read_config()`` reads Black and Ruff config correctly from a TOML file."""
    formatter_class, option_name_delimiter = formatter_setup
    # For Black, we test both hyphen and underscore delimited option names
    config = "\n".join(  # pylint: disable=duplicate-code
        line.replace("-", option_name_delimiter) for line in config_lines
    )
    tmpdir = Path(tmpdir)
    src = tmpdir / "src.py"
    toml = tmpdir / (config_path or "pyproject.toml")
    section = formatter_class.config_section
    toml.write_text(f"[{section}]\n{config}\n")
    with raises_or_matches(expect, []):
        formatter = formatter_class()
        args = Namespace()
        args.config = config_path and str(toml)
        if config_path:
            expect["config"] = str(toml)

        # pylint: disable=duplicate-code
        formatter.read_config((str(src),), args)

        assert formatter.config == expect


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run(formatter_class, encoding, newline):
    """Running formatter through their plugin ``run`` method gives correct results."""
    src = TextDocument.from_lines(
        [f"# coding: {encoding}", "print ( 'touché' )"],
        encoding=encoding,
        newline=newline,
    )

    result = formatter_class().run(src, Path("a.py"))

    assert result.lines == (
        f"# coding: {encoding}",
        'print("touché")',
    )
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.parametrize(
    "formatter_setup",
    [
        (BlackFormatter, "darker.formatters.black_wrapper.format_str"),
        (RuffFormatter, "darker.formatters.ruff_formatter._ruff_format_stdin"),
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_always_uses_unix_newlines(formatter_setup, newline):
    """Content is always passed to Black and Ruff with Unix newlines."""
    formatter_class, formatter_func_name = formatter_setup
    src = TextDocument.from_str(f"print ( 'touché' ){newline}")
    with patch(formatter_func_name) as formatter_func:
        formatter_func.return_value = 'print("touché")\n'

        _ = formatter_class().run(src, Path("a.py"))

    (formatter_func_call,) = formatter_func.call_args_list
    assert formatter_func_call.args[0] == "print ( 'touché' )\n"


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
@pytest.mark.parametrize(
    ("src_content", "expect"),
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
def test_run_all_whitespace_input(formatter_class, src_content, expect):
    """All-whitespace files are reformatted correctly."""
    src = TextDocument.from_str(src_content)

    result = formatter_class().run(src, Path("a.py"))

    assert result.string == expect


@pytest.mark.kwparametrize(
    dict(formatter_config={}, expect=[]),
    dict(formatter_config={"line_length": 80}, expect=["--line-length=80"]),
)
def test_run_configuration(formatter_config, expect):
    """`RuffFormatter.run` passes correct configuration to Ruff."""
    src = TextDocument.from_str("import  os\n")
    with patch.object(ruff_formatter, "_ruff_format_stdin") as format_stdin:
        format_stdin.return_value = "import os\n"
        formatter = RuffFormatter()
        formatter.config = formatter_config

        formatter.run(src, Path("a.py"))

        format_stdin.assert_called_once_with(
            "import  os\n",
            Path("a.py"),
            ['--config=lint.ignore=["ISC001"]', *expect],
        )
