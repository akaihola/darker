from pathlib import Path
from textwrap import dedent

import pytest

from darker.utils import (
    TextDocument,
    debug_dump,
    get_common_root,
    get_path_ancestry,
    joinlines,
)


def test_debug_dump(capsys):
    debug_dump(
        [(1, ("black",), ("chunks",))],
        TextDocument.from_str("old content"),
        TextDocument.from_str("new content"),
        [2, 3],
    )
    assert capsys.readouterr().out == (
        dedent(
            """\
            --------------------------------------------------------------------------------
             -   1 black
             +     chunks
            --------------------------------------------------------------------------------
            """
        )
    )


def test_joinlines():
    result = joinlines(("a", "b", "c"))
    assert result == "a\nb\nc\n"


def test_get_common_root(tmpdir):
    tmpdir = Path(tmpdir)
    path1 = tmpdir / "a" / "b" / "c" / "d"
    path2 = tmpdir / "a" / "e" / ".." / "b" / "f" / "g"
    path3 = tmpdir / "a" / "h" / ".." / "b" / "i"
    result = get_common_root([path1, path2, path3])
    assert result == tmpdir / "a" / "b"


def test_get_common_root_of_directory(tmpdir):
    tmpdir = Path(tmpdir)
    result = get_common_root([tmpdir])
    assert result == tmpdir


def test_get_path_ancestry_for_directory(tmpdir):
    tmpdir = Path(tmpdir)
    result = list(get_path_ancestry(tmpdir))
    assert result[-1] == tmpdir
    assert result[-2] == tmpdir.parent


def test_get_path_ancestry_for_file(tmpdir):
    tmpdir = Path(tmpdir)
    dummy = tmpdir / "dummy"
    dummy.write_text("dummy")
    result = list(get_path_ancestry(dummy))
    assert result[-1] == tmpdir
    assert result[-2] == tmpdir.parent


@pytest.mark.parametrize(
    "document1, document2, expect",
    [
        (TextDocument(lines=["foo"]), TextDocument(lines=[]), False),
        (TextDocument(lines=[]), TextDocument(lines=["foo"]), False),
        (TextDocument(lines=["foo"]), TextDocument(lines=["bar"]), False),
        (
            TextDocument(lines=["line1", "line2"]),
            TextDocument(lines=["line1", "line2"]),
            True,
        ),
        (TextDocument(lines=["foo"]), TextDocument(""), False),
        (TextDocument(lines=[]), TextDocument("foo\n"), False),
        (TextDocument(lines=["foo"]), TextDocument("bar\n"), False),
        (
            TextDocument(lines=["line1", "line2"]),
            TextDocument("line1\nline2\n"),
            True,
        ),
        (TextDocument("foo\n"), TextDocument(lines=[]), False),
        (TextDocument(""), TextDocument(lines=["foo"]), False),
        (TextDocument("foo\n"), TextDocument(lines=["bar"]), False),
        (
            TextDocument("line1\nline2\n"),
            TextDocument(lines=["line1", "line2"]),
            True,
        ),
        (TextDocument("foo\n"), TextDocument(""), False),
        (TextDocument(""), TextDocument("foo\n"), False),
        (TextDocument("foo\n"), TextDocument("bar\n"), False),
        (
            TextDocument("line1\nline2\n"),
            TextDocument("line1\nline2\n"),
            True,
        ),
        (TextDocument("foo"), "line1\nline2\n", NotImplemented),
    ],
)
def test_textdocument_eq(document1, document2, expect):
    """TextDocument.__eq__()"""
    result = document1.__eq__(document2)

    assert result == expect


@pytest.mark.parametrize(
    "document, expect",
    [
        (TextDocument(""), "TextDocument([0 lines])"),
        (TextDocument(lines=[]), "TextDocument([0 lines])"),
        (TextDocument("One line\n"), "TextDocument([1 lines])"),
        (TextDocument(lines=["One line"]), "TextDocument([1 lines])"),
        (TextDocument("Two\nlines\n"), "TextDocument([2 lines])"),
        (TextDocument(lines=["Two", "lines"]), "TextDocument([2 lines])"),
    ],
)
def test_textdocument_repr(document, expect):
    """TextDocument.__repr__()"""
    result = document.__repr__()

    assert result == expect
