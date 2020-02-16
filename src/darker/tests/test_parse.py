import pytest

from darker.__main__ import choose_edited_lines, get_edited_new_line_numbers
from darker.tests.example_3_lines import CHANGE_SECOND_LINE


def test_get_edited_line_numbers():
    result = list(get_edited_new_line_numbers(CHANGE_SECOND_LINE))
    assert result == [1]


@pytest.mark.parametrize(
    "edited_line_numbers, expect",
    [
        (
            [],
            [
                ["original first line"],
                ["original second line"],
                ["original third line"],
            ],
        ),
        (
            [0],
            [
                ["original first line"],
                ["original second line"],
                ["original third line"],
            ],
        ),
        (
            [1],
            [
                ["original first line"],
                ["changed second line"],
                ["original third line"],
            ],
        ),
        (
            [2],
            [
                ["original first line"],
                ["original second line"],
                ["original third line"],
            ],
        ),
        (
            [0, 1],
            [
                ["original first line"],
                ["changed second line"],
                ["original third line"],
            ],
        ),
    ],
)
def test_choose_edited_lines(edited_line_numbers, expect):
    black_chunks = [
        (0, 1, ["original first line"], ["original first line"]),
        (1, 2, ["original second line"], ["changed second line"]),
        (2, 3, ["original third line"], ["original third line"]),
    ]
    result = list(choose_edited_lines(black_chunks, edited_line_numbers))
    assert result == expect
