"""Tests for :mod:`darker.fstring`"""

# pylint: disable=protected-access
# pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument

from importlib import reload
from pathlib import Path

import pytest

import darker.fstring
from darker.git import EditedLinenumsDiffer
from darker.tests.helpers import flynt_present
from darkgraylib.git import RevisionRange
from darkgraylib.utils import TextDocument, joinlines

ORIGINAL_SOURCE = ("'{}'.format(x)", "#", "'{0}'.format(42)")
MODIFIED_SOURCE = ("'{}'.format( x)", "#", "'{0}'.format( 42)")
FLYNTED_SOURCE = ("f'{x}'", "#", "f'{42}'")


@pytest.mark.parametrize("present", [True, False])
def test_fstring_importable_with_and_without_flynt(present):
    """Make sure ``import darker.fstring`` works with and without ``flynt``"""
    try:
        with flynt_present(present):

            # Import when `flynt` has been removed temporarily
            reload(darker.fstring)
    finally:
        # Re-import after restoring `flynt` so other tests won't be affected
        reload(darker.fstring)


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_apply_flynt_exclude(git_repo, encoding, newline):
    """Encoding and newline are intact after Flynt fstringification"""
    git_repo.add({"test1.py": joinlines(ORIGINAL_SOURCE, newline)}, commit="Initial")
    edited_linenums_differ = EditedLinenumsDiffer(
        git_repo.root, RevisionRange("HEAD", ":WORKTREE:")
    )
    src = Path("test1.py")
    content_ = TextDocument.from_lines(
        MODIFIED_SOURCE, encoding=encoding, newline=newline
    )

    result = darker.fstring.apply_flynt(content_, src, edited_linenums_differ)

    assert result.lines == FLYNTED_SOURCE
    assert result.encoding == encoding
    assert result.newline == newline
