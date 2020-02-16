from whatthepatch import apply_diff
from whatthepatch.patch import diffobj, parse_patch

from darker.tests.example_3_lines import CHANGE_SECOND_LINE, ORIGINAL


def test_apply():
    diff = next(parse_patch(CHANGE_SECOND_LINE))  # type: diffobj
    old_content = ORIGINAL
    new_content = apply_diff(diff, old_content)
    assert new_content == [
        "original first linex",
        "changed second line",
        "original third line",
    ]


def test_apply_partial():
    diff = next(parse_patch(CHANGE_SECOND_LINE))  # type: diffobj
    del diff.changes[1:3]
    old_content = ORIGINAL
    new_content = apply_diff(diff, old_content)
    assert new_content == [
        'original first line',
        'original second line',
        'original third line',
    ]
