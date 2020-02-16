import pytest

from darker.chooser import choose_lines


@pytest.mark.parametrize(
    "edited_line_numbers, expect",
    [
        ([], ["original first line", "original second line", "original third line"],),
        ([0], ["original first line", "original second line", "original third line"],),
        ([1], ["original first line", "changed second line", "original third line"],),
        ([2], ["original first line", "original second line", "original third line"],),
        (
            [0, 1],
            ["original first line", "changed second line", "original third line"],
        ),
    ],
)
def test_choose_edited_lines(edited_line_numbers, expect):
    black_chunks = [
        (0, ["original first line"], ["original first line"]),
        (1, ["original second line"], ["changed second line"]),
        (2, ["original third line"], ["original third line"]),
    ]
    result = list(choose_lines(black_chunks, edited_line_numbers))
    assert result == expect
