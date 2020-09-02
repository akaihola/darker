"""Picking of original or reformatted chunks based on edits

The :func:`choose_lines` function should be fed with
a list of line numbers which were edited after the last commit,
plus output from :func:`darker.black_diff.opcodes_to_chunks`.
It reconstructs the Python source code file from chunks
while choosing either the original or reformatted version of each chunk.
The original is chosen if no edited line number falls on original chunk lines,
and the reformatted if an edit was seen on any of the lines in the chunk.

Example::

    >>> reconstruction = choose_lines(
    ...     [ ( 1,                        # chunk starts on line 1 in original content
    ...         ['original line 1',
    ...          'original line 2'],
    ...         ['reformatted lines 1-2']
    ...       ),
    ...       ( 3,                        # chunk starts on line 3 in original content
    ...         ['original line 3',
    ...          'original line 4'],
    ...         ['reformatted lines 3-4']
    ...       )
    ...      ],
    ...      [2]                          # only line 2 was edited since last commit
    ... )
    >>> list(reconstruction)
    ['reformatted lines 1-2', 'original line 3', 'original line 4']

"""

import logging
from typing import Generator, Iterable, List

from darker.utils import DiffChunk

logger = logging.getLogger(__name__)


def _any_item_in_range(items: List[int], start: int, length: int) -> bool:
    """Return ``True`` if any item falls inside the slice ``[start : start + length]``

    If ``length == 0``, add one to make sure an edit at the position of an inserted
    chunk causes the reformatted version to be chosen for that chunk.

    """
    end = start + (length or 1) - 1
    has_edits = any(start <= n <= end for n in items)
    line_range = f'line {start}' if end == start else f'lines {start}-{end}'
    if has_edits:
        logger.debug("Found edits on %s", line_range)
    else:
        logger.debug("Found no edits on %s", line_range)
    return has_edits


def choose_lines(
    black_chunks: Iterable[DiffChunk],
    edit_linenums: List[int],
) -> Generator[str, None, None]:
    """Choose formatted chunks for edited areas, original chunks for non-edited"""
    for original_lines_offset, original_lines, formatted_lines in black_chunks:
        chunk_has_edits = _any_item_in_range(
            edit_linenums, original_lines_offset, len(original_lines)
        )
        if chunk_has_edits:
            choice = (
                "unmodified" if formatted_lines == original_lines else "reformatted"
            )
            chosen_lines = formatted_lines
        else:
            choice = 'original'
            chosen_lines = original_lines
        logger.debug(
            'Using %s %s %s at line %s',
            len(chosen_lines),
            choice,
            'line' if len(chosen_lines) == 1 else 'lines',
            original_lines_offset,
        )
        yield from chosen_lines
