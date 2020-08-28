import pytest

from darker.config import TomlArrayLinesEncoder


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
