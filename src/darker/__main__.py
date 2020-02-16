from argparse import ArgumentParser
from difflib import SequenceMatcher
from pathlib import Path
from pprint import pprint
from subprocess import check_output
from typing import Generator, Iterable, List, Tuple

from black import FileMode, assert_equivalent, format_str


def git_diff_u0(path: Path) -> bytes:
    """Run ``git diff -U0 <path>`` on the given path, and return the output"""
    return check_output(["git", "diff", "-U0", path], cwd=str(path.parent))


def get_edit_linenums(patch: bytes) -> Generator[int, None, None]:
    """Yield changed line numbers in Git diff to-file

    The patch must be in ``git diff -U0`` format, and only contain differences for a
    single file.

    """
    git_diff_lines = patch.split(b"\n")
    assert git_diff_lines[0].startswith(b"diff --git ")
    assert git_diff_lines[1].startswith(b"index ")
    assert git_diff_lines[2].startswith(b"--- a/")
    assert git_diff_lines[3].startswith(b"+++ b/")
    for line in git_diff_lines[4:]:
        assert not line.startswith((b"diff --git ", b"index "))
        if not line or line.startswith((b"+", b"-")):
            continue
        assert line.startswith(b"@@ ")
        start_str, *length_str = line.split()[2].split(b",")
        start_linenum = int(start_str) - 1
        length = int(length_str[0]) if length_str else 1
        yield from range(start_linenum, start_linenum + length)


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
    return SequenceMatcher(None, src_lines, dst_lines, autojunk=False).get_opcodes()


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
        yield i1, src_lines[i1:i2], dst_lines[j1:j2]


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


def _debug_dump(
    black_chunks: List[Tuple[int, List[str], List[str]]],
    old_content: str,
    new_content: str,
    edited_linenums: List[int],
) -> None:
    """Print debug output. This is used in case of an unexpected failure."""
    print(edited_linenums)
    pprint(black_chunks)
    pprint(
        [(linenum + 1, line) for linenum, line in enumerate(old_content.splitlines())]
    )
    print(new_content)


def joinlines(lines: List[str]) -> str:
    """Join a list of lines back, adding a linefeed after each line

    This is the reverse of ``str.splitlines()``.

    """
    return "".join(f"{line}\n" for line in lines)


def check(
    edited_to_file_lines: List[str],
    reformatted_str: str,
    black_chunks: List[Tuple[int, List[str], List[str]]],
    edited_linenums: List[int],
):
    """Verify that source code parses to the same AST before and after reformat"""
    edited_to_file_str = joinlines(edited_to_file_lines)
    try:
        assert_equivalent(edited_to_file_str, reformatted_str)
    except AssertionError:
        _debug_dump(black_chunks, edited_to_file_str, reformatted_str, edited_linenums)
        raise


def apply_black_on_edited_lines(src: Path) -> None:
    """Apply black formatting to chunks with edits since the last commit

    1. do a ``git diff -U0 <path>``
    2. extract line numbers in the edited to-file for changed lines
    3. run black on the contents of the edited to-file
    4. get a diff between the edited to-file and the reformatted content
    5. convert the diff into chunks, keeping original and reformatted content for each
       chunk
    6. choose reformatted content for each chunk if there were any changed lines inside
       the chunk in the edited to-file, or choose the chunk's original contents if no
       edits were done in that chunk
    7. concatenate all chosen chunks
    8. verify that the resulting reformatted source code parses to an identical AST as
       the original edited to-file
    9. write the reformatted source back to the original file

    """
    git_diff_output = git_diff_u0(src)
    edited_linenums = list(get_edit_linenums(git_diff_output))
    edited, formatted = run_black(src)
    opcodes = diff_and_get_opcodes(edited, formatted)
    black_chunks = list(opcodes_to_chunks(opcodes, edited, formatted))
    chosen_lines: List[str] = list(choose_lines(black_chunks, edited_linenums))
    result_str = joinlines(chosen_lines)
    check(edited, result_str, black_chunks, edited_linenums)
    src.write_text(result_str)


def main() -> None:
    """Parse the command line and apply black formatting for each source file"""
    parser = ArgumentParser()
    parser.add_argument("src", nargs="+")
    args = parser.parse_args()
    for path in args.src:
        apply_black_on_edited_lines(Path(path))


if __name__ == "__main__":
    main()
