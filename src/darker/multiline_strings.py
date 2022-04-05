"""Helper functions for dealing with reformatting multi-line strings"""

from tokenize import STRING, tokenize
from typing import List, Optional, Sequence, Tuple

from darker.utils import TextDocument


def get_multiline_string_ranges(content: TextDocument) -> List[Tuple[int, int]]:
    """Return the line ranges of multi-line strings found in the given Python source

    The returned data is 1-based, end-exclusive. In other words, each item is a 1-based
    ``(start, end)`` tuple, ``end`` being the line number following the last line of the
    multi-line string.

    :return: Line number ranges of multi-line strings

    """
    readline = (f"{line}\n".encode(content.encoding) for line in content.lines).__next__
    return [
        (t.start[0], t.end[0] + 1)
        for t in tokenize(readline)
        if t.type == STRING and t.end[0] > t.start[0]
    ]


def find_overlap(
    start: int, end: int, ranges: Sequence[Tuple[int, int]]
) -> Optional[Tuple[int, int]]:
    """Return the convex hull of given ranges which overlap with given start and end

    `start..end` must be end-exclusive.

    :param start: The first line of the range to find overlaps for.
    :param end: The first line after the range to find overlaps for.
    :param ranges: The ranges to scan when looking for an overlap with `(start, end)`.
                   End-exclusive, and either 0- or 1-based as long as similarly based as
                   `(start, end)`.
    :return: The convex hull, i.e. range from start of first until the end of last range
             which overlap with the given `(start, end)` range

    """
    overlap: Optional[Tuple[int, int]] = None
    for range_start, range_end in ranges:
        if end <= range_start:
            break
        if start < range_end:
            if overlap:
                overlap = (
                    overlap[0],  # pylint: disable=unsubscriptable-object
                    range_end,
                )
            else:
                overlap = range_start, range_end
    return overlap
