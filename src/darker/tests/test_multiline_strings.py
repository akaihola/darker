"""Tests for `darker.multiline_strings`"""

import pytest

from darker import multiline_strings
from darker.utils import TextDocument


def test_get_multiline_string_ranges():
    """`get_multiline_string_ranges()` identifies multi-line strings correctly"""
    content = TextDocument.from_lines(
        [
            "'single-quoted string'",  # (line 1)
            "f'single-quoted f-string'",
            "r'single-quoted raw string'",
            "rf'single-quoted raw f-string'",
            "b'single-quoted bytestring'",  # (line 5)
            "rb'single-quoted raw bytestring'",
            "'''triple-single-quoted one-line string'''",
            "f'''triple-single-quoted one-line f-string'''",
            "r'''triple-single-quoted one-line raw string'''",
            "rf'''triple-single-quoted one-line raw f-string'''",  # (line 10)
            "b'''triple-single-quoted one-line bytestring'''",
            "rb'''triple-single-quoted one-line raw bytestring'''",
            "'''triple-single-quoted",  # line 13
            "   two-line string'''",
            "f'''triple-single-quoted",  # line 15
            "    two-line f-string'''",
            "r'''triple-single-quoted",  # line 17
            "    two-line raw string'''",
            "rf'''triple-single-quoted",  # line 19
            "     two-line raw f-string'''",
            "b'''triple-single-quoted",  # line 21
            "    two-line bytestring'''",
            "rb'''triple-single-quoted",  # line 23
            "     two-line raw bytestring'''",
            '"double-quoted string"',  # (line 25)
            'f"double-quoted f-string"',
            'r"double-quoted raw string"',
            'rf"double-quoted raw f-string"',
            'b"double-quoted bytestring"',
            'rb"double-quoted raw bytestring"',  # (line 30)
            '"""triple-double-quoted one-line string"""',
            'f"""triple-double-quoted one-line f-string"""',
            'r"""triple-double-quoted one-line raw string"""',
            'rf"""triple-double-quoted one-line raw f-string"""',
            'b"""triple-double-quoted one-line bytestring"""',  # (line 35)
            'rb"""triple-double-quoted one-line raw bytestring"""',
            '"""triple-double-quoted',  # line 37
            '   two-line string"""',
            'f"""triple-double-quoted',  # line 39
            '    two-line f-string"""',
            'r"""triple-double-quoted',  # line 41
            '    two-line raw string"""',
            'rf"""triple-double-quoted',  # line 43
            '     two-line raw f-string"""',
            'b"""triple-double-quoted',  # line 45
            '    two-line bytestring"""',
            'rb"""triple-double-quoted',  # line 47
            '     two-line raw bytestring"""',
            '"""triple-',  # line 49
            "   double-",
            "   quoted",
            "   six-",
            "   line",
            '   string"""',  # line 54
        ]
    )

    result = multiline_strings.get_multiline_string_ranges(content)

    assert result == [
        # 1-based, end-exclusive
        (13, 15),
        (15, 17),
        (17, 19),
        (19, 21),
        (21, 23),
        (23, 25),
        (37, 39),
        (39, 41),
        (41, 43),
        (43, 45),
        (45, 47),
        (47, 49),
        (49, 55),
    ]


# End-exclusive
TEST_RANGES = [(2, 2), (5, 6), (9, 11), (14, 17)]


@pytest.mark.kwparametrize(
    # `(start, end)` and `ranges` are end-exclusive
    dict(start=0, end=0, ranges=[], expect=None),
    dict(start=0, end=42, ranges=[], expect=None),
    dict(start=0, end=0, ranges=TEST_RANGES, expect=None),
    dict(start=1, end=2, ranges=TEST_RANGES, expect=None),
    dict(start=2, end=2, ranges=TEST_RANGES, expect=None),
    dict(start=1, end=3, ranges=TEST_RANGES, expect=(2, 2)),
    dict(start=2, end=3, ranges=TEST_RANGES, expect=None),
    dict(start=3, end=3, ranges=TEST_RANGES, expect=None),
    dict(start=4, end=5, ranges=TEST_RANGES, expect=None),
    dict(start=5, end=5, ranges=TEST_RANGES, expect=None),
    dict(start=4, end=6, ranges=TEST_RANGES, expect=(5, 6)),
    dict(start=5, end=6, ranges=TEST_RANGES, expect=(5, 6)),
    dict(start=6, end=6, ranges=TEST_RANGES, expect=None),
    dict(start=4, end=7, ranges=TEST_RANGES, expect=(5, 6)),
    dict(start=5, end=7, ranges=TEST_RANGES, expect=(5, 6)),
    dict(start=6, end=7, ranges=TEST_RANGES, expect=None),
    dict(start=10, end=10, ranges=TEST_RANGES, expect=(9, 11)),
    dict(start=10, end=11, ranges=TEST_RANGES, expect=(9, 11)),
    dict(start=10, end=12, ranges=TEST_RANGES, expect=(9, 11)),
    dict(start=11, end=11, ranges=TEST_RANGES, expect=None),
    dict(start=11, end=12, ranges=TEST_RANGES, expect=None),
    dict(start=12, end=12, ranges=TEST_RANGES, expect=None),
    dict(start=10, end=19, ranges=TEST_RANGES, expect=(9, 17)),
)
def test_find_overlap(start, end, ranges, expect):
    """`find_overlap()` finds the enclosing range for overlapping ranges"""
    result = multiline_strings.find_overlap(start, end, ranges)

    assert result == expect
