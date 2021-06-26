from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from darker import black_diff
from darker.black_diff import BlackArgs, read_black_config, run_black
from darker.utils import TextDocument


@pytest.mark.parametrize(
    "config_path, config_lines, expect",
    [
        (None, ['line-length = 79'], {'line_length': 79}),
        ("custom.toml", ['line-length = 99'], {'line_length': 99}),
        (
            "custom.toml",
            ['skip-string-normalization = true'],
            {'skip_string_normalization': True},
        ),
        (
            "custom.toml",
            ['skip-string-normalization = false'],
            {'skip_string_normalization': False},
        ),
        ("custom.toml", ["target-version = ['py37']"], {}),
        ("custom.toml", ["include = '\\.pyi$'"], {}),
        ("custom.toml", ["exclude = '\\.pyx$'"], {}),
    ],
)
def test_black_config(tmpdir, config_path, config_lines, expect):
    tmpdir = Path(tmpdir)
    src = tmpdir / "src.py"
    toml = tmpdir / (config_path or "pyproject.toml")

    toml.write_text("[tool.black]\n{}\n".format('\n'.join(config_lines)))

    config = read_black_config(src, config_path and str(toml))
    assert config == expect


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_black(tmpdir, encoding, newline):
    """Running Black through its Python internal API gives correct results"""
    src = TextDocument.from_lines(
        [f"# coding: {encoding}", "print ( 'touché' )"],
        encoding=encoding,
        newline=newline,
    )

    result = run_black(Path(tmpdir / "src.py"), src, BlackArgs())

    assert result.lines == (
        f"# coding: {encoding}",
        'print("touché")',
    )
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_black_always_uses_unix_newlines(tmpdir, newline):
    """Content is always passed to Black with Unix newlines"""
    src = TextDocument.from_str(f"print ( 'touché' ){newline}")
    with patch.object(black_diff, "format_str") as format_str:
        format_str.return_value = 'print("touché")\n'

        _ = run_black(Path(tmpdir / "src.py"), src, BlackArgs())

    format_str.assert_called_once_with("print ( 'touché' )\n", mode=ANY)
