"""Helper functions for dealing with reformatting multi-line strings"""
import sys
from tokenize import STRING, tokenize
from typing import Generator, Optional, Sequence, Tuple

from darkgraylib.utils import TextDocument

if sys.version_info >= (3, 12):
    from tokenize import FSTRING_END, FSTRING_START
else:
    FSTRING_START = FSTRING_END = -1


MAX_LINES_IN_FILE = 2**64  # make it very unlikely to hit this limit


def get_multiline_string_ranges(
    content: TextDocument,
) -> Generator[Tuple[int, int], None, None]:
    """Generate the line ranges of multi-line strings found in the given Python source

    The yielded data is 1-based, end-exclusive. In other words, each item is a 1-based
    ``(start, end)`` tuple, ``end`` being the line number following the last line of the
    multi-line string.

    :param content: The Python source code to scan for multi-line strings
    :return: Generates the line ranges of multi-line strings

    """
    readline = (f"{line}\n".encode(content.encoding) for line in content.lines).__next__
    token_start_line = MAX_LINES_IN_FILE
    for token in tokenize(readline):
        if token.type in {STRING, FSTRING_START}:
            token_start_line = token.start[0]
        if token.type in {STRING, FSTRING_END} and token.end[0] > token_start_line:
            yield token_start_line, token.end[0] + 1
            token_start_line = MAX_LINES_IN_FILE


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
