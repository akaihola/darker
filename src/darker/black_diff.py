"""Running black reformatting and getting a diff for the changes"""
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
    """Return opcodes and lines for chunks in the diff between two lists of strings

    The opcodes are 5-tuples for each chunk with

    - the tag of the operation ('equal', 'delete', 'replace' or 'insert')
    - the number of the first line in the chunk in the from-file
    - the number of the last line in the chunk in the from-file
    - the number of the first line in the chunk in the to-file
    - the number of the last line in the chunk in the to-file

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
    """Convert each diff opcode to a linenumbers and original plus modified lines

    Each chunk is a 3-tuple with

    - the number of the first line in the chunk in the from-file
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
