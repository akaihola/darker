"""Turn Python code into chunks of original and re-formatted code

The functions in this module implement three steps
for converting a file with Python source code into a list of chunks.
From these chunks, the same file can be reconstructed
while choosing whether each chunk should be taken from the original untouched file
or from the version reformatted with Black.

In examples below, a simple two-line snippet is used.
The first line will be reformatted by Black, and the second left intact::

    >>> from unittest.mock import Mock
    >>> src = Mock()
    >>> src.read_text.return_value = '''\\
    ... for i in range(5): print(i)
    ... print("done")
    ... '''

First, :func:`run_black` uses Black to reformat the contents of a given file.
Original and reformatted lines are returned e.g.::

    >>> src_lines, dst_lines = run_black(src)
    >>> src_lines
    ['for i in range(5): print(i)',
     'print("done")']
    >>> dst_lines
    ['for i in range(5):',
     '    print(i)',
     'print("done")']

The output of :func:`run_black` should then be fed into :func:`diff_and_get_opcodes`.
It divides a diff between the original and reformatted content
into alternating chunks of
intact (represented by the 'equal' tag) and
modified ('delete', 'replace' or 'insert' tag) lines.
Each chunk is an opcode represented by the tag and the corresponding 0-based line ranges
in the original and reformatted content, e.g.::

    >>> opcodes = diff_and_get_opcodes(src_lines, dst_lines)
    >>> len(opcodes)
    2
    >>> opcodes[0]  # split 'for' loop into two lines
    ('replace', 0, 1, 0, 2)
    >>> opcodes[1]  # keep 'print("done")' as such
    ('equal', 1, 2, 2, 3)

Finally, :func:`opcodes_to_chunks` picks the lines
from original and reformatted content for each opcode.
It combines line content with the 1-based line offset in the original content, e.g.::

    >>> chunks = list(opcodes_to_chunks(opcodes, src_lines, dst_lines))
    >>> len(chunks)
    2
    >>> chunks[0]  # (<offset in orig content>, <original lines>, <reformatted lines>)
    (1,
     ['for i in range(5): print(i)'],
     ['for i in range(5):',
      '    print(i)'])
    >>> chunks[1]
    (2,
     ['print("done")'],
     ['print("done")'])

By concatenating the second items in these tuples, i.e. original lines,
the original file can be reconstructed.

By concatenating the third items, i.e. reformatted lines,
the complete output from Black can be reconstructed.

By concatenating and choosing either the second or third item,
a mixed result with only selected regions reformatted can be reconstructed.

"""

import logging
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from black import FileMode, format_str, read_pyproject_toml
from click import Command, Context, Option

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def read_black_config(src: Path, value: Optional[str]) -> Dict[str, Any]:
    """Read the black configuration from pyproject.toml"""
    command = Command("main")

    context = Context(command)
    context.params["src"] = (str(src),)

    parameter = Option(("--config",))

    read_pyproject_toml(context, parameter, value)

    return context.default_map or {}


def run_black(src: Path, config: Optional[str]) -> Tuple[List[str], List[str]]:
    """Run the black formatter for the contents of the given Python file

    Return lines of the original file as well as the formatted content.

    """
    defaults = read_black_config(src, config)
    mode = FileMode(**defaults)

    src_contents = src.read_text()
    dst_contents = format_str(src_contents, mode=mode)
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
    logger.debug(
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
