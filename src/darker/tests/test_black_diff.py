from pathlib import Path

import pytest

from darker.black_diff import BlackArgs, read_black_config, run_black


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


def test_run_black(tmpdir):
    src_contents = "print ( '42' )\n"

    result = run_black(Path(tmpdir / "src.py"), src_contents, BlackArgs())

    assert result == ['print("42")']
