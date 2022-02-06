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
from typing import Generator, List, Tuple

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
    assert all(
        (tag1 == "equal") != (tag2 == "equal")
        for (tag1, _, _, _, _), (tag2, _, _, _, _) in zip(opcodes[:-1], opcodes[1:])
    ), opcodes


def opcodes_to_edit_linenums(
    opcodes: List[Tuple[str, int, int, int, int]], context_lines: int
) -> Generator[int, None, None]:
    """Convert diff opcodes to line numbers of edited lines in the destination file

    :param opcodes: The diff opcodes to convert
    :param context_lines: The number of lines before and after an edited line to mark
                          edited as well

    """
    if not opcodes:
        return
    _validate_opcodes(opcodes)
    prev_chunk_end = 1
    _tag, _i1, _i2, _j1, end = opcodes[-1]
    for tag, _i1, _i2, j1, j2 in opcodes:
        if tag != "equal":
            chunk_end = min(j2 + 1 + context_lines, end + 1)
            yield from range(max(j1 + 1 - context_lines, prev_chunk_end), chunk_end)
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
    for tag, i1, i2, j1, j2 in opcodes:
        yield i1 + 1, src.lines[i1:i2], dst.lines[j1:j2]


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
