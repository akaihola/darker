from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Generator, List

import git
import intervals as I
from black import FileMode, assert_equivalent, diff, format_str
from whatthepatch import parse_patch
from whatthepatch.apply import apply_diff
from whatthepatch.exceptions import HunkApplyException
from whatthepatch.patch import Change, diffobj


def get_edited_new_line_numbers(patch: str) -> Generator[int, None, None]:
    try:
        patchset = next(parse_patch(patch))
    except StopIteration:
        return
    for change in patchset.changes:
        if change.new and not change.old:
            yield change.new


def get_file_edit_linenums(path):
    repo = git.Repo(path, search_parent_directories=True)
    yield from get_edited_new_line_numbers(repo.git.diff(path))


def choose_edited_lines(
    black_patch: diffobj, edited_line_numbers: List[int]
) -> Generator[Change, None, None]:
    def reset_chunk():
        nonlocal chunk_changes, chunk_interval
        chunk_changes = []
        chunk_interval = I.empty()

    def emit_chunk():
        nonlocal chunk_interval, chunk_changes
        if any(linenum in chunk_interval for linenum in edited_line_numbers):
            yield from chunk_changes
        reset_chunk()

    chunk_changes = chunk_interval = None
    reset_chunk()

    for black_change in black_patch.changes:
        if black_change.old and black_change.new:
            # It's an unchanged line. Emit lines from collected chunk
            # if any of its lines have been edited.
            yield from emit_chunk()
            yield black_change
        else:
            chunk_changes.append(black_change)
            if black_change.old:
                chunk_interval = chunk_interval.replace(
                    I.CLOSED,
                    lambda lower: lower if lower < I.inf else black_change.old,
                    lambda upper: upper if upper > -I.inf else black_change.old + 1,
                    I.OPEN,
                    ignore_inf=False,
                )
    yield from emit_chunk()


def get_black_diff(src: Path) -> str:
    src_contents = src.read_text()
    dst_contents = format_str(src_contents, mode=FileMode())
    then = datetime.utcfromtimestamp(src.stat().st_mtime)
    now = datetime.utcnow()
    src_name = f"{src}\t{then} +0000"
    dst_name = f"{src}\t{now} +0000"
    return diff(src_contents, dst_contents, src_name, dst_name)


def reformat(path: Path) -> None:
    edited_line_numbers: List[int] = list(get_file_edit_linenums(path))
    black_diff = get_black_diff(path)
    try:
        black_patch: diffobj = next(parse_patch(black_diff))
    except StopIteration:
        return
    changes: List[Change] = list(choose_edited_lines(black_patch, edited_line_numbers))
    filtered_diff = diffobj(black_patch.header, changes, black_patch.text)
    old_content: str = path.read_text()
    try:
        new_lines = apply_diff(filtered_diff, old_content)
    except HunkApplyException:
        _debug_dump(filtered_diff, old_content)
        raise
    new_content = "".join(f"{line}\n" for line in new_lines)
    try:
        assert_equivalent(old_content, new_content)
    except AssertionError:
        _debug_dump(filtered_diff, old_content)
        print(new_content)
        raise
    path.write_text(new_content)


def _debug_dump(filtered_diff, old_content):
    pprint([tuple(c) for c in filtered_diff.changes])
    pprint(
        [(linenum + 1, line) for linenum, line in enumerate(old_content.splitlines())]
    )


def main():
    parser = ArgumentParser()
    parser.add_argument("src", nargs="+")
    args = parser.parse_args()
    for path in args.src:
        reformat(Path(path))


if __name__ == "__main__":
    main()
