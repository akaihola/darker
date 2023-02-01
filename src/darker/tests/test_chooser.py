"""Unit tests for `darker.chooser`"""

# pylint: disable=use-dict-literal

import pytest

from darker.chooser import choose_lines


@pytest.mark.kwparametrize(
    dict(edited_line_numbers=[], expect_second_line="original second line"),
    dict(edited_line_numbers=[0], expect_second_line="original second line"),
    dict(edited_line_numbers=[1], expect_second_line="changed second line"),
    dict(edited_line_numbers=[2], expect_second_line="original second line"),
    dict(edited_line_numbers=[0, 1], expect_second_line="changed second line"),
)
def test_choose_lines(edited_line_numbers, expect_second_line):
    """``choose_lines()`` picks new versions of lines if touching edited line numbers"""
    black_chunks = [
        (0, ("original first line",), ("original first line",)),
        (1, ("original second line",), ("changed second line",)),
        (2, ("original third line",), ("original third line",)),
    ]

    result = list(choose_lines(black_chunks, edited_line_numbers))

    expect = ["original first line", expect_second_line, "original third line"]
    assert result == expect
