from argparse import ArgumentParser
from difflib import SequenceMatcher
from pathlib import Path
from pprint import pprint
from typing import Generator, Iterable, List, Tuple

import git
from black import FileMode, assert_equivalent, format_str
from whatthepatch import parse_patch


def get_edited_new_line_numbers(patch: str) -> Generator[int, None, None]:
    try:
        patchset = next(parse_patch(patch))
    except StopIteration:
        return
    for change in patchset.changes:
        if change.new and not change.old:
            # Generate 0-based line numbers for edited lines from `git diff`
            yield change.new - 1


def get_file_edit_linenums(path: Path) -> Generator[int, None, None]:
    repo = git.Repo(path, search_parent_directories=True)
    yield from get_edited_new_line_numbers(repo.git.diff(path))


def choose_edited_lines(
    black_chunks: Iterable[Tuple[int, int, List[str], List[str]]],
    edited_line_numbers: List[int],
) -> Generator[List[str], None, None]:
    for i1, i2, old_lines, new_lines in black_chunks:
        if any(i1 <= linenum < i2 for linenum in edited_line_numbers):
            yield new_lines
        else:
            yield old_lines


def run_black(src: Path) -> Tuple[List[str], List[str]]:
    src_contents = src.read_text()
    dst_contents = format_str(src_contents, mode=FileMode())
    return src_contents.splitlines(), dst_contents.splitlines()


def diff_opcodes(
    src_lines: List[str], dst_lines: List[str]
) -> List[Tuple[str, int, int, int, int]]:
    s = SequenceMatcher(None, src_lines, dst_lines)
    opcodes = s.get_opcodes()
    return opcodes


def opcodes_to_chunks(
    opcodes: List[Tuple[str, int, int, int, int]],
    src_lines: List[str],
    dst_lines: List[str],
) -> Generator[Tuple[int, int, List[str], List[str]], None, None]:
    # Make sure every other opcode is an 'equal' tag
    assert all(
        (tag1 == "equal") != (tag2 == "equal")
        for (tag1, _, _, _, _), (tag2, _, _, _, _) in zip(opcodes[:-1], opcodes[1:])
    ), opcodes

    for tag, i1, i2, j1, j2 in opcodes:
        yield i1, i2, src_lines[i1:i2], dst_lines[j1:j2]


def get_black_diff(
    src: Path,
) -> Generator[Tuple[int, int, List[str], List[str]], None, None]:
    src_lines, dst_lines = run_black(src)
    opcodes = diff_opcodes(src_lines, dst_lines)
    return opcodes_to_chunks(opcodes, src_lines, dst_lines)


def reformat(path: Path) -> None:
    edited_line_numbers: List[int] = list(get_file_edit_linenums(path))
    black_patch = list(get_black_diff(path))
    changes: List[List[str]] = list(
        choose_edited_lines(black_patch, edited_line_numbers)
    )
    new_content = "".join(f"{line}\n" for chunk in changes for line in chunk)
    old_content: str = path.read_text()
    try:
        assert_equivalent(old_content, new_content)
    except AssertionError:
        _debug_dump(black_patch, old_content)
        print(new_content)
        raise
    path.write_text(new_content)


def _debug_dump(
    black_patch: List[Tuple[int, int, List[str], List[str]]], old_content
) -> None:
    pprint(black_patch)
    pprint(
        [(linenum + 1, line) for linenum, line in enumerate(old_content.splitlines())]
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("src", nargs="+")
    args = parser.parse_args()
    for path in args.src:
        reformat(Path(path))


if __name__ == "__main__":
    main()
