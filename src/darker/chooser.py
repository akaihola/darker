"""Picking of original or reformatted chunks based on edits"""

import logging
from typing import Generator, Iterable, List, Tuple

logger = logging.getLogger(__name__)


def any_edit_falls_inside(items: List[int], start: int, length: int) -> bool:
    """Return ``True`` if any item falls inside the slice [start:start + length]

    If ``length == 0``, add one to make sure an edit at the position of an inserted
    chunk causes the reformatted version to be chosen for that chunk.

    """
    end = start + (length or 1) - 1
    has_edits = any(start <= n <= end for n in items)
    line_range = f'line {start}' if end == start else f'lines {start}-{end}'
    if has_edits:
        logger.info('Found edits on %s', line_range)
    else:
        logger.info('Found no edits on %s', line_range)
    return has_edits


def choose_lines(
    black_chunks: Iterable[Tuple[int, List[str], List[str]]], edit_linenums: List[int],
) -> Generator[str, None, None]:
    """Choose formatted chunks for edited areas, original chunks for non-edited"""
    for original_lines_offset, original_lines, formatted_lines in black_chunks:
        chunk_has_edits = any_edit_falls_inside(
            edit_linenums, original_lines_offset, len(original_lines)
        )
        if chunk_has_edits:
            choice = 'reformatted'
            chosen_lines = formatted_lines
        else:
            choice = 'original'
            chosen_lines = original_lines
        logger.info(
            'Using %s %s %s at line %s',
            len(chosen_lines),
            choice,
            'line' if len(chosen_lines) == 1 else 'lines',
            original_lines_offset,
        )
        yield from chosen_lines
