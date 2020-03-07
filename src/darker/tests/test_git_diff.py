from pathlib import Path
from textwrap import dedent

import pytest

from darker.git_diff import (
    get_edit_chunks,
    get_edit_chunks_for_one_file,
    get_edit_linenums,
)
from darker.tests.example_3_lines import CHANGE_SECOND_LINE, TWO_FILES_CHANGED
from darker.utils import Buf


def test_get_edit_linenums():
    ((path, chunks),) = list(get_edit_linenums(CHANGE_SECOND_LINE.encode("ascii")))
    assert path == Path("test1.txt")
    assert list(chunks) == [2]


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
    path, chunks = next(get_edit_chunks(CHANGE_SECOND_LINE.encode("ascii")))
    assert path == Path("test1.txt")
    assert list(chunks) == [(2, 3)]


def test_get_edit_chunks_two_files():
    paths_and_chunks = get_edit_chunks(TWO_FILES_CHANGED.encode("ascii"))
    path, chunks = next(paths_and_chunks)
    assert path == Path("src/darker/git_diff.py")
    assert list(chunks) == [(104, 108)]
    path, chunks = next(paths_and_chunks)
    assert path == Path("src/darker/tests/example_3_lines.py")
    assert list(chunks) == [(30, 34)]


def test_get_edit_chunks_empty():
    gen = get_edit_chunks(b"")
    with pytest.raises(StopIteration):
        next(gen)
