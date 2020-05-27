from pathlib import Path
from textwrap import dedent

import pytest

from darker.git_diff import (
    GitDiffParseError,
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


@pytest.mark.parametrize(
    "git_diff_lines",
    [[], ["diff --git path_a path_b", "index ", "--- path_a", "+++ path_a"]],
)
def test_get_edit_chunks_empty_output(git_diff_lines):
    git_diff_result = GitDiffResult(
        "".join(f"{line}\n" for line in git_diff_lines).encode("ascii"),
        ["git", "diff"],
    )
    result = list(get_edit_chunks(git_diff_result))
    assert result == []


@pytest.mark.parametrize(
    "first_line",
    ["diff --git ", "diff --git path_a", "diff --git path_a path_b path_c"],
)
def test_get_edit_chunks_cant_parse(first_line):
    output = f"{first_line}\n"
    git_diff_result = GitDiffResult(output.encode("ascii"), ["git", "diff"])
    with pytest.raises(GitDiffParseError) as exc:
        list(get_edit_chunks(git_diff_result))
    assert str(exc.value) == f"Can't parse '{first_line}'"


@pytest.mark.parametrize(
    "git_diff_lines, expect",
    [
        (["first line doesn't have diff --git"], "diff --git ",),
        (
            ["diff --git path_a path_b", "second line doesn't have old mode"],
            "old mode ",
        ),
        (
            [
                "diff --git path_a path_b",
                "old mode ",
                "third line doesn't have new mode",
            ],
            "new mode ",
        ),
        (
            [
                "diff --git path_a path_b",
                "old mode ",
                "new mode ",
                "fourth line doesn't have index",
            ],
            "index ",
        ),
        (
            [
                "diff --git path_a path_b",
                "index ",
                "third line doesn't have --- path_a",
            ],
            "--- path_a",
        ),
        (
            [
                "diff --git path_a path_b",
                "index ",
                "--- path_a",
                "fourth line doesn't have +++ path_a",
            ],
            "+++ path_a",
        ),
    ],
)
def test_get_edit_chunks_unexpected_line(git_diff_lines, expect):
    git_diff_result = GitDiffResult(
        "".join(f"{line}\n" for line in git_diff_lines).encode("ascii"),
        ["git", "diff"],
    )
    with pytest.raises(GitDiffParseError) as exc:
        list(get_edit_chunks(git_diff_result))
    expect_exception_message = (
        f"Expected an '{expect}' line, got '{git_diff_lines[-1]}' from 'git diff'"
    )
    assert str(exc.value) == expect_exception_message


@pytest.mark.parametrize(
    "git_diff_lines",
    [
        ["diff --git path_a path_b"],
        ["diff --git path_a path_b", "old mode "],
        ["diff --git path_a path_b", "old mode ", "new mode "],
        ["diff --git path_a path_b", "old mode ", "new mode ", "index "],
        ["diff --git path_a path_b", "index "],
        ["diff --git path_a path_b", "index ", "--- path_a"],
    ],
)
def test_get_edit_chunks_unexpected_end(git_diff_lines):
    git_diff_result = GitDiffResult(
        "".join(f"{line}\n" for line in git_diff_lines).encode("ascii"),
        ["git", "diff"],
    )
    with pytest.raises(GitDiffParseError) as exc:
        list(get_edit_chunks(git_diff_result))
    assert str(exc.value) == "Unexpected end of output from 'git diff'"
