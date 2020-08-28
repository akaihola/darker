import pytest

from darker.config import TomlArrayLinesEncoder, replace_log_level_name


@pytest.mark.parametrize(
    "list_value, expect",
    [
        ([], "[\n]"),
        (["one value"], '[\n    "one value",\n]'),
        (["two", "values"], '[\n    "two",\n    "values",\n]'),
        (
            [
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
            '[\n    "a",\n    "dozen",\n    "short",\n    "string",\n    "values"'
            ',\n    "in",\n    "the",\n    "list",\n    "of",\n    "strings"'
            ',\n    "to",\n    "format",\n]',
        ),
    ],
)
def test_toml_array_lines_encoder(list_value, expect):
    result = TomlArrayLinesEncoder().dump_list(list_value)

    assert result == expect


@pytest.mark.parametrize(
    "log_level, expect",
    [
        (0, "NOTSET"),
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARNING"),
        (40, "ERROR"),
        (50, "CRITICAL"),
        ("DEBUG", 10),
        ("INFO", 20),
        ("WARNING", 30),
        ("WARN", 30),
        ("ERROR", 40),
        ("CRITICAL", 50),
        ("FOOBAR", "Level FOOBAR"),
    ],
)
def test_replace_log_level_name(log_level, expect):
    if log_level is None:
        config = {}
    else:
        config = {"log_level": log_level}

    replace_log_level_name(config)

    assert config["log_level"] == expect
