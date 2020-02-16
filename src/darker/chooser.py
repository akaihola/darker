"""Picking of original or reformatted chunks based on edits"""

from typing import Generator, Iterable, List, Tuple


def any_edit_falls_inside(items: List[int], start: int, length: int) -> bool:
    """Return ``True`` if any item falls inside the slice [start:start + length]

    If ``length == 0``, add one to make sure an edit at the position of an inserted
    chunk causes the reformatted version to be chosen for that chunk.

    """
    return any(start <= n < start + (length or 1) for n in items)


def choose_lines(
    black_chunks: Iterable[Tuple[int, List[str], List[str]]], edit_linenums: List[int],
) -> Generator[str, None, None]:
    """Choose formatted chunks for edited areas, original chunks for non-edited"""
    for original_lines_offset, original_lines, formatted_lines in black_chunks:
        chunk_has_edits = any_edit_falls_inside(
            edit_linenums, original_lines_offset, len(original_lines)
        )
        chosen_lines = formatted_lines if chunk_has_edits else original_lines
        yield from chosen_lines
