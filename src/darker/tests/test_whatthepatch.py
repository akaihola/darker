from pprint import pprint

from whatthepatch import apply_diff
from whatthepatch.patch import parse_patch, diffobj

from darker.tests.example_3_lines import ORIGINAL, CHANGE_SECOND_LINE


def test_apply():
    diff = next(parse_patch(CHANGE_SECOND_LINE))  # type: diffobj
    old_content = ORIGINAL
    new_content = apply_diff(diff, old_content)
    assert new_content == ['original first line',
                           'changed second line',
                           'original third line']


def test_apply_partial():
    diff = next(parse_patch(CHANGE_SECOND_LINE))  # type: diffobj
    del diff.changes[1:3]
    old_content = ORIGINAL
    new_content = apply_diff(diff, old_content)
    assert new_content == ['original first line',
                           'original second line',
                           'original third line']
