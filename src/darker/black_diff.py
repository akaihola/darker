"""Turn Python code into chunks of original and re-formatted code

The functions in this module implement three steps
for converting a file with Python source code into a list of chunks.
From these chunks, the same file can be reconstructed
while choosing whether each chunk should be taken from the original untouched file
or from the version reformatted with Black.

First, :func:`run_black` uses Black to reformat the contents of a given file.
Original and reformatted lines are returned e.g.::

    (
        [
            'for i in range(5): print(i)',
            'print("done")'
        ],
        [
            'for i in range(5):',
             '    print(i)',
             'print("done")'
        ]
    )

The output of :func:`run_black` should then be fed into :func:`diff_and_get_opcodes`.
It divides a diff between the original and reformatted content
into alternating chunks of
intact (represented by the 'equal' tag) and
modified ('delete', 'replace' or 'insert' tag) lines.
Each chunk is an opcode represented by the tag and the corresponding 0-based line ranges
in the original and reformatted content, e.g.::

    [
        ('replace', 0, 1, 0, 2),  # split for loop into two lines
        ('equal', 1, 2, 2, 3)     # keep print("done") as such
    ]

Finally, :func:`opcodes_to_chunks` picks the lines
from original and reformatted content for each opcode.
It combines line content with the 1-based line offset in the original content, e.g.::

    [(
         1,                                # original line offset
         ['for i in range(5): print(i)'],  # original line
         ['for i in range(5):',            # reformatted lines
          '    print(i)']
     ),
     (
         2,                                # original line offset
         ['print("done")'],                # original line
         ['print("done")']                 # (identical) reformatted line
     )]

By concatenating the second items in these tuples, i.e. original lines,
the original file can be reconstructed.

By concatenating the third items, i.e. reformatted lines,
the complete output from Black can be reconstructed.

By concatenating and choosing either the second or third item,
a mixed result with only selected regions reformatted can be reconstructed.

"""

import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Generator, List, Tuple

from black import FileMode, format_str

logger = logging.getLogger(__name__)


def run_black(src: Path) -> Tuple[List[str], List[str]]:
    """Run the black formatter for the contents of the given Python file

    Return lines of the original file as well as the formatted content.

    """
    src_contents = src.read_text()
    dst_contents = format_str(src_contents, mode=FileMode())
    return src_contents.splitlines(), dst_contents.splitlines()


def diff_and_get_opcodes(
    src_lines: List[str], dst_lines: List[str]
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
    matcher = SequenceMatcher(None, src_lines, dst_lines, autojunk=False)
    opcodes = matcher.get_opcodes()
    logger.info(
        "Diff between edited and reformatted has %s opcode%s",
        len(opcodes),
        "s" if len(opcodes) > 1 else "",
    )
    return opcodes


def opcodes_to_chunks(
    opcodes: List[Tuple[str, int, int, int, int]],
    src_lines: List[str],
    dst_lines: List[str],
) -> Generator[Tuple[int, List[str], List[str]], None, None]:
    """Convert each diff opcode to a line number and original plus modified lines

    Each chunk is a 3-tuple with

    - the 1-based number of the first line in the chunk in the from-file
    - the original lines of the chunk in the from-file
    - the modified lines of the chunk in the to-file

    Based on this, the patch can be constructed by choosing either original or modified
    lines for each chunk and concatenating them together.

    """
    # Make sure every other opcode is an 'equal' tag
    assert all(
        (tag1 == "equal") != (tag2 == "equal")
        for (tag1, _, _, _, _), (tag2, _, _, _, _) in zip(opcodes[:-1], opcodes[1:])
    ), opcodes

    for tag, i1, i2, j1, j2 in opcodes:
        yield i1 + 1, src_lines[i1:i2], dst_lines[j1:j2]
