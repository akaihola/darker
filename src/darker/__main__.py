import io
import sys
from argparse import ArgumentParser
from contextlib import redirect_stdout
from pathlib import Path
from typing import Generator, List

import git
from black import FileMode, WriteBack, assert_equivalent, format_file_in_place

import intervals as I
from whatthepatch import parse_patch
from whatthepatch.apply import apply_diff
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


def get_black_diff(path: Path) -> str:
    captured_stdout = io.TextIOWrapper(io.BytesIO(), sys.stdout.encoding)
    with redirect_stdout(captured_stdout):
        format_file_in_place(
            src=path, fast=False, mode=FileMode(), write_back=WriteBack.DIFF,
        )
    captured_stdout.seek(0)
    black_diff = captured_stdout.read()
    return black_diff


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
    new_lines = apply_diff(filtered_diff, old_content)
    new_content = "".join(f"{line}\n" for line in new_lines)
    assert_equivalent(old_content, new_content)
    path.write_text(new_content)


def main():
    parser = ArgumentParser()
    parser.add_argument("src", nargs="+")
    args = parser.parse_args()
    for path in args.src:
        reformat(Path(path))


if __name__ == "__main__":
    main()
