"""Diff text and get line numbers of changes or chunks of original and changed content

The functions in this module implement

- diffing text files, returning opcodes
- turning opcodes into a list of line numbers of changed lines
- turning opcodes into chunks of original and modified text

In our case, we run a diff between original and user-edited source code.
Another diff is done between user-edited and Black-reformatted source code
as returned by :func:`black.black_diff.run_black_for_content`.

    >>> src = TextDocument.from_lines(
    ...     [
    ...         'for i in range(5): print(i)',
    ...         'print("done")'
    ...     ]
    ... )

    >>> dst = TextDocument.from_lines(
    ...     [
    ...         'for i in range(5):',
    ...         '    print(i)',
    ...         'print("done")'
    ...     ]
    ... )

:func:`diff_and_get_opcodes`.
divides a diff between the original and reformatted content
into alternating chunks of
intact (represented by the 'equal' tag) and
modified ('delete', 'replace' or 'insert' tag) lines.
Each chunk is an opcode represented by the tag and the corresponding 0-based line ranges
in the original and reformatted content, e.g.::

    >>> opcodes = diff_and_get_opcodes(src, dst)
    >>> len(opcodes)
    2
    >>> opcodes[0]  # split 'for' loop into two lines
    ('replace', 0, 1, 0, 2)
    >>> opcodes[1]  # keep 'print("done")' as such
    ('equal', 1, 2, 2, 3)

:func:`opcodes_to_chunks` picks the lines
from original and reformatted content for each opcode.
It combines line content with the 1-based line offset in the original content, e.g.::

    >>> chunks = list(opcodes_to_chunks(opcodes, src, dst))
    >>> len(chunks)
    2
    >>> chunks[0]  # (<offset in orig content>, <original lines>, <reformatted lines>)
    (1, ('for i in range(5): print(i)',), ('for i in range(5):', '    print(i)'))
    >>> chunks[1]
    (2, ('print("done")',), ('print("done")',))

By concatenating the second items in these tuples, i.e. original lines,
the original file can be reconstructed.

By concatenating the third items, i.e. reformatted lines,
the complete output from Black can be reconstructed.

By concatenating and choosing either the second or third item,
a mixed result with only selected regions reformatted can be reconstructed.

"""

import logging
from difflib import SequenceMatcher
from typing import Generator, List, Sequence, Tuple

from darker.multiline_strings import find_overlap
from darker.utils import DiffChunk, TextDocument

logger = logging.getLogger(__name__)


def diff_and_get_opcodes(
    src: TextDocument, dst: TextDocument
) -> List[Tuple[str, int, int, int, int]]:
    """Return opcodes and line numbers for chunks in the diff of two lists of strings

    The opcodes are 5-tuples for each chunk with

    - the tag of the operation ('equal', 'delete', 'replace' or 'insert')
    - the number of the first line in the chunk in the from-file
    - the number of the last line in the chunk in the from-file
    - the number of the first line in the chunk in the to-file
    - the number of the last line in the chunk in the to-file

    Line numbers are zero based.

    """
    matcher = SequenceMatcher(None, src.lines, dst.lines, autojunk=False)
    opcodes = matcher.get_opcodes()
    logger.debug(
        "Diff between edited and reformatted has %s opcode%s",
        len(opcodes),
        "s" if len(opcodes) > 1 else "",
    )
    return opcodes


def _validate_opcodes(opcodes: List[Tuple[str, int, int, int, int]]) -> None:
    """Make sure every other opcode is an 'equal' tag"""
    if not all(
        (tag1 == "equal") != (tag2 == "equal")
        for (tag1, _, _, _, _), (tag2, _, _, _, _) in zip(opcodes[:-1], opcodes[1:])
    ):
        raise ValueError(f"Unexpected opcodes in {opcodes!r}")


def opcodes_to_edit_linenums(
    opcodes: List[Tuple[str, int, int, int, int]],
    context_lines: int,
    multiline_string_ranges: Sequence[Tuple[int, int]],
) -> Generator[int, None, None]:
    """Convert diff opcodes to line numbers of edited lines in the destination file

    On top of a straight mapping from line ranges to individual line numbers, this
    function extends each diff opcode line range
    - upwards and downwards for as many lines as determined by ``context_lines``
    - to make sure the range covers any multiline strings completely

    :param opcodes: The diff opcodes to convert. 0-based, end-exclusive.
    :param context_lines: The number of lines before and after an edited line to mark
                          edited as well
    :param multiline_string_ranges: Line ranges of multi-line strings. 1-based,
                                    end-exclusive.
    :return: Generates a list of integer 1-based line numbers

    """
    if not opcodes:
        return
    _validate_opcodes(opcodes)

    # Calculate the last line number beyond which we won't extend with extra context
    # lines
    _tag, _i1, _i2, _j1, last_opcode_end = opcodes[-1]
    _, last_multiline_string_end = (
        multiline_string_ranges[-1] if multiline_string_ranges else (None, 0)
    )
    lastline = max(last_opcode_end + 1, last_multiline_string_end)

    prev_chunk_end = 1
    for tag, _i1, _i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        chunk_start = j1 + 1 - context_lines
        chunk_end = j2 + 1 + context_lines
        multiline_string_range = find_overlap(
            chunk_start, chunk_end, multiline_string_ranges
        )
        if multiline_string_range:
            chunk_start = min(chunk_start, multiline_string_range[0])
            chunk_end = max(chunk_end, multiline_string_range[1])
        yield from range(max(chunk_start, prev_chunk_end), min(chunk_end, lastline))
        prev_chunk_end = chunk_end


def opcodes_to_chunks(
    opcodes: List[Tuple[str, int, int, int, int]],
    src: TextDocument,
    dst: TextDocument,
) -> Generator[DiffChunk, None, None]:
    """Convert each diff opcode to a line number and original plus modified lines

    Each chunk is a 3-tuple with

    - the 1-based number of the first line in the chunk in the from-file
    - the original lines of the chunk in the from-file
    - the modified lines of the chunk in the to-file

    Based on this, the patch can be constructed by choosing either original or modified
    lines for each chunk and concatenating them together.

    """
    _validate_opcodes(opcodes)
    for _tag, src_start, src_end, dst_start, dst_end in opcodes:
        yield src_start + 1, src.lines[src_start:src_end], dst.lines[dst_start:dst_end]


def diff_chunks(src: TextDocument, dst: TextDocument) -> List[DiffChunk]:
    """Diff two documents and return the list of chunks in the diff

    Each chunk is a 3-tuple::

        (
            linenum: int,
            old_lines: List[str],
            new_lines: List[str],
        )

    ``old_lines`` and ``new_lines`` may be

    - identical to indicate a chunk with no changes,
    - of the same length but different items to indicate some modified lines, or
    - of different lengths to indicate removed or inserted lines.

    For the return value ``retval``, the following always holds::

        retval[n + 1][0] == retval[n][0] + len(retval[n][old_lines])

    """
    opcodes = diff_and_get_opcodes(src, dst)
    return list(opcodes_to_chunks(opcodes, src, dst))
