"""Helper functions for dealing with reformatting multi-line strings"""

from tokenize import STRING, tokenize
from typing import List, Optional, Sequence, Tuple

from darker.utils import TextDocument


def get_multiline_string_ranges(content: TextDocument) -> List[Tuple[int, int]]:
    """Return the line ranges of multi-line strings found in the given Python source

    Each item is a 1-based ``(start, end)`` tuple, ``end`` being the line number
    following the last line of the multi-line string.

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
    """Return the first of the given ranges which overlaps with given start and end

    :return: The first overlapping range

    """
    for range_start, range_end in ranges:
        if start < range_end and end > range_start:
            return range_start, range_end
    return None
