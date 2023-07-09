"""Tests for `darker.multiline_strings`"""

# pylint: disable=use-dict-literal

import pytest

from darker import multiline_strings
from darkgraylib.utils import TextDocument


def test_get_multiline_string_ranges():
    """`get_multiline_string_ranges()` identifies multi-line strings correctly"""
    content = TextDocument.from_lines(
        line
        for _, line in [
            # Dummy line numbers added to ease debugging of failures
            (1, "'single-quoted string'"),
            (2, "f'single-quoted f-string'"),
            (3, "r'single-quoted raw string'"),
            (4, "rf'single-quoted raw f-string'"),
            (5, "b'single-quoted bytestring'"),
            (6, "rb'single-quoted raw bytestring'"),
            (7, "'''triple-single-quoted one-line string'''"),
            (8, "f'''triple-single-quoted one-line f-string'''"),
            (9, "r'''triple-single-quoted one-line raw string'''"),
            (10, "rf'''triple-single-quoted one-line raw f-string'''"),
            (11, "b'''triple-single-quoted one-line bytestring'''"),
            (12, "rb'''triple-single-quoted one-line raw bytestring'''"),
            (13, "'''triple-single-quoted"),
            (14, "   two-line string'''"),
            (15, "f'''triple-single-quoted"),
            (16, "    two-line f-string'''"),
            (17, "r'''triple-single-quoted"),
            (18, "    two-line raw string'''"),
            (19, "rf'''triple-single-quoted"),
            (20, "     two-line raw f-string'''"),
            (21, "b'''triple-single-quoted"),
            (22, "    two-line bytestring'''"),
            (23, "rb'''triple-single-quoted"),
            (24, "     two-line raw bytestring'''"),
            (25, '"double-quoted string"'),
            (26, 'f"double-quoted f-string"'),
            (27, 'r"double-quoted raw string"'),
            (28, 'rf"double-quoted raw f-string"'),
            (29, 'b"double-quoted bytestring"'),
            (30, 'rb"double-quoted raw bytestring"'),
            (31, '"""triple-double-quoted one-line string"""'),
            (32, 'f"""triple-double-quoted one-line f-string"""'),
            (33, 'r"""triple-double-quoted one-line raw string"""'),
            (34, 'rf"""triple-double-quoted one-line raw f-string"""'),
            (35, 'b"""triple-double-quoted one-line bytestring"""'),
            (36, 'rb"""triple-double-quoted one-line raw bytestring"""'),
            (37, '"""triple-double-quoted'),
            (38, '   two-line string"""'),
            (39, 'f"""triple-double-quoted'),
            (40, '    two-line f-string"""'),
            (41, 'r"""triple-double-quoted'),
            (42, '    two-line raw string"""'),
            (43, 'rf"""triple-double-quoted'),
            (44, '     two-line raw f-string"""'),
            (45, 'b"""triple-double-quoted'),
            (46, '    two-line bytestring"""'),
            (47, 'rb"""triple-double-quoted'),
            (48, '     two-line raw bytestring"""'),
            (49, '"""triple-'),
            (50, "   double-"),
            (51, "   quoted"),
            (52, "   six-"),
            (53, "   line"),
            (54, '   string"""'),
        ]
    )

    result = list(multiline_strings.get_multiline_string_ranges(content))

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
