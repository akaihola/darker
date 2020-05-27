from pathlib import Path
from textwrap import dedent

import pytest

from darker.git_diff import (
    GitDiffResult,
    get_edit_chunks,
    get_edit_chunks_for_one_file,
    get_edit_linenums,
)
from darker.tests.git_diff_example_output import CHANGE_SECOND_LINE, TWO_FILES_CHANGED
from darker.utils import Buf


def test_get_edit_linenums():
    diff_result = GitDiffResult(CHANGE_SECOND_LINE.encode("ascii"), ["git", "diff"])
    ((path, chunks),) = list(get_edit_linenums(diff_result))
    assert path == Path("test1.py")
    assert chunks == [2]


def test_get_edit_chunks_for_one_file():
    lines = Buf(
        dedent(
            """\
            @@ -2,1 +2,1 @@
            -original second line
            +changed second line
            """
        ).encode("ascii")
    )
    result = list(get_edit_chunks_for_one_file(lines))
    assert result == [(2, 3)]


def test_get_edit_chunks_one_file():
    diff_result = GitDiffResult(CHANGE_SECOND_LINE.encode("ascii"), ["git", "diff"])
    path, chunks = next(get_edit_chunks(diff_result))
    assert path == Path("test1.py")
    assert chunks == [(2, 3)]


def test_get_edit_chunks_two_files():
    diff_result = GitDiffResult(TWO_FILES_CHANGED.encode("ascii"), ["git", "diff"])
    paths_and_chunks = get_edit_chunks(diff_result)
    path, chunks = next(paths_and_chunks)
    assert path == Path("src/darker/git_diff.py")
    assert chunks == [(104, 108)]
    path, chunks = next(paths_and_chunks)
    assert path == Path("src/darker/tests/git_diff_example_output.py")
    assert chunks == [(30, 34)]


def test_get_edit_chunks_empty():
    gen = get_edit_chunks(GitDiffResult(b"", ["git", "diff"]))
    with pytest.raises(StopIteration):
        next(gen)
