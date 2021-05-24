"""Unit tests for :mod:`darker.utils`"""

import logging
import os
from pathlib import Path
from textwrap import dedent

import pytest

from darker.utils import (
    TextDocument,
    debug_dump,
    detect_newline,
    get_common_root,
    get_path_ancestry,
    joinlines,
)


@pytest.mark.kwparametrize(
    dict(string="", expect="\n"),
    dict(string="\n", expect="\n"),
    dict(string="\r\n", expect="\r\n"),
    dict(string="one line\n", expect="\n"),
    dict(string="one line\r\n", expect="\r\n"),
    dict(string="first line\nsecond line\n", expect="\n"),
    dict(string="first line\r\nsecond line\r\n", expect="\r\n"),
    dict(string="first unix\nthen windows\r\n", expect="\n"),
    dict(string="first windows\r\nthen unix\n", expect="\r\n"),
)
def test_detect_newline(string, expect):
    """``detect_newline()`` gives correct results"""
    result = detect_newline(string)

    assert result == expect


def test_debug_dump(caplog, capsys):
    """darker.utils.debug_dump()"""
    caplog.set_level(logging.DEBUG)
    debug_dump([(1, ("black",), ("chunks",))], [2, 3])
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


def test_get_common_root_empty():
    """``get_common_root()`` raises a ``ValueError`` if ``paths`` argument is empty"""
    with pytest.raises(ValueError):

        get_common_root([])


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
    "textdocument, expect",
    [
        (TextDocument(), "utf-8"),
        (TextDocument(encoding="utf-8"), "utf-8"),
        (TextDocument(encoding="utf-16"), "utf-16"),
        (TextDocument.from_str(""), "utf-8"),
        (TextDocument.from_str("", encoding="utf-8"), "utf-8"),
        (TextDocument.from_str("", encoding="utf-16"), "utf-16"),
        (TextDocument.from_lines([]), "utf-8"),
        (TextDocument.from_lines([], encoding="utf-8"), "utf-8"),
        (TextDocument.from_lines([], encoding="utf-16"), "utf-16"),
    ],
)
def test_textdocument_set_encoding(textdocument, expect):
    """TextDocument.encoding is correct from each constructor"""
    assert textdocument.encoding == expect


@pytest.mark.parametrize(
    "textdocument, expect",
    [
        (TextDocument(), ""),
        (TextDocument(lines=["zéro", "un"]), "zéro\nun\n"),
        (TextDocument(lines=["zéro", "un"], newline="\n"), "zéro\nun\n"),
        (TextDocument(lines=["zéro", "un"], newline="\r\n"), "zéro\r\nun\r\n"),
    ],
)
def test_textdocument_string(textdocument, expect):
    """TextDocument.string respects the newline setting"""
    assert textdocument.string == expect


@pytest.mark.parametrize(
    "encoding, newline, expect",
    [
        ("utf-8", "\n", b"z\xc3\xa9ro\nun\n"),
        ("iso-8859-1", "\n", b"z\xe9ro\nun\n"),
        ("utf-8", "\r\n", b"z\xc3\xa9ro\r\nun\r\n"),
        ("iso-8859-1", "\r\n", b"z\xe9ro\r\nun\r\n"),
    ],
)
def test_textdocument_encoded_string(encoding, newline, expect):
    """TextDocument.encoded_string uses correct encoding and newline"""
    textdocument = TextDocument(
        lines=["zéro", "un"], encoding=encoding, newline=newline
    )

    assert textdocument.encoded_string == expect


@pytest.mark.parametrize(
    "textdocument, expect",
    [
        (TextDocument(), ()),
        (TextDocument(string="zéro\nun\n"), ("zéro", "un")),
        (TextDocument(string="zéro\nun\n", newline="\n"), ("zéro", "un")),
        (TextDocument(string="zéro\r\nun\r\n", newline="\r\n"), ("zéro", "un")),
    ],
)
def test_textdocument_lines(textdocument, expect):
    """TextDocument.lines is correct after parsing a string with different newlines"""
    assert textdocument.lines == expect


@pytest.mark.parametrize(
    "textdocument, expect_lines, expect_encoding, expect_newline, expect_mtime",
    [
        (TextDocument.from_str(""), (), "utf-8", "\n", ""),
        (TextDocument.from_str("", encoding="utf-8"), (), "utf-8", "\n", ""),
        (TextDocument.from_str("", encoding="iso-8859-1"), (), "iso-8859-1", "\n", ""),
        (TextDocument.from_str("a\nb\n"), ("a", "b"), "utf-8", "\n", ""),
        (TextDocument.from_str("a\r\nb\r\n"), ("a", "b"), "utf-8", "\r\n", ""),
        (TextDocument.from_str("", mtime="my mtime"), (), "utf-8", "\n", "my mtime"),
    ],
)
def test_textdocument_from_str(
    textdocument, expect_lines, expect_encoding, expect_newline, expect_mtime
):
    """TextDocument.from_str() gets correct content, encoding, newlines and mtime"""
    assert textdocument.lines == expect_lines
    assert textdocument.encoding == expect_encoding
    assert textdocument.newline == expect_newline
    assert textdocument.mtime == expect_mtime


@pytest.mark.parametrize(
    "content, expect",
    [
        (b'print("touch\xc3\xa9")\n', "utf-8"),
        (b'\xef\xbb\xbfprint("touch\xc3\xa9")\n', "utf-8-sig"),
        (b'# coding: iso-8859-1\n"touch\xe9"\n', "iso-8859-1"),
    ],
)
def test_textdocument_from_file_detect_encoding(tmp_path, content, expect):
    """TextDocument.from_file() detects the file encoding correctly"""
    path = tmp_path / "test.py"
    path.write_bytes(content)

    textdocument = TextDocument.from_file(path)

    assert textdocument.encoding == expect


@pytest.mark.parametrize(
    "content, expect", [(b'print("unix")\n', "\n"), (b'print("windows")\r\n', "\r\n")]
)
def test_textdocument_from_file_detect_newline(tmp_path, content, expect):
    """TextDocument.from_file() detects the newline character sequence correctly"""
    path = tmp_path / "test.py"
    path.write_bytes(content)

    textdocument = TextDocument.from_file(path)

    assert textdocument.newline == expect


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
        (
            TextDocument(lines=["line1", "line2"], encoding="utf-16", newline="\r\n"),
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
        (
            TextDocument("line1\r\nline2\r\n"),
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
        (
            TextDocument(mtime="some mtime"),
            "TextDocument([0 lines], mtime='some mtime')",
        ),
        (
            TextDocument(encoding="utf-8"),
            "TextDocument([0 lines])",
        ),
        (
            TextDocument(encoding="a non-default encoding"),
            "TextDocument([0 lines], encoding='a non-default encoding')",
        ),
        (
            TextDocument(newline="\n"),
            "TextDocument([0 lines])",
        ),
        (
            TextDocument(newline="a non-default newline"),
            "TextDocument([0 lines], newline='a non-default newline')",
        ),
    ],
)
def test_textdocument_repr(document, expect):
    """TextDocument.__repr__()"""
    result = document.__repr__()

    assert result == expect


@pytest.mark.parametrize(
    "document, expect",
    [
        (TextDocument(), ""),
        (TextDocument(mtime=""), ""),
        (TextDocument(mtime="dummy mtime"), "dummy mtime"),
    ],
)
def test_textdocument_mtime(document, expect):
    """TextDocument.mtime"""
    assert document.mtime == expect


def test_textdocument_from_file(tmp_path):
    """TextDocument.from_file()"""
    dummy_txt = tmp_path / "dummy.txt"
    dummy_txt.write_bytes(b"# coding: iso-8859-1\r\ndummy\r\ncontent\r\n")
    os.utime(dummy_txt, (1_000_000_000, 1_000_000_000))

    document = TextDocument.from_file(dummy_txt)

    assert document.string == "# coding: iso-8859-1\r\ndummy\r\ncontent\r\n"
    assert document.lines == ("# coding: iso-8859-1", "dummy", "content")
    assert document.encoding == "iso-8859-1"
    assert document.newline == "\r\n"
    assert document.mtime == "2001-09-09 01:46:40.000000 +0000"
