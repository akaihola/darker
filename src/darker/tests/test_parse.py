import pytest
from whatthepatch.patch import Change

from darker.__main__ import (get_edited_new_line_numbers,
                             choose_edited_lines)
from darker.tests.example_3_lines import CHANGE_SECOND_LINE


def test_get_edited_line_numbers():
    result = list(get_edited_new_line_numbers(CHANGE_SECOND_LINE))
    assert result == [2]


@pytest.mark.parametrize(
    'edited_line_numbers, expect',
    [([], [(1, 1, 'original first line', 1),
           (3, 3, 'original third line', 1)]),
     ([1], [(1, 1, 'original first line', 1),
            (3, 3, 'original third line', 1)]),
     ([2], [(1, 1, 'original first line', 1),
            (2, None, 'original second line', 1),
            (None, 2, 'changed second line', 1),
            (3, 3, 'original third line', 1)]),
     ([3], [(1, 1, 'original first line', 1),
            (3, 3, 'original third line', 1)]),
     ([1, 2], [(1, 1, 'original first line', 1),
               (2, None, 'original second line', 1),
               (None, 2, 'changed second line', 1),
               (3, 3, 'original third line', 1)]),
     ]
)
def test_choose_edited_lines(edited_line_numbers, expect):
    result = list(choose_edited_lines(CHANGE_SECOND_LINE, edited_line_numbers))
    assert [tuple(r) for r in result] == expect
