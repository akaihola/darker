"""Tests for `__main__._drop_changes_on_unedited_lines`"""

# pylint: disable=use-dict-literal

from pathlib import Path
from unittest.mock import Mock

import pytest

from darker.__main__ import _drop_changes_on_unedited_lines
from darkgraylib.utils import TextDocument


@pytest.mark.kwparametrize(
    dict(
        content=TextDocument("s =  'reformat'\n"),
        new_chunks=[(1, ("s =  'reformat'",), ('s = "reformat"',))],
    ),
    dict(
        content=TextDocument('s = "keep"\n'),
        new_chunks=[(1, ('s = "keep"',), ('s = "keep"',))],
    ),
    dict(
        content=TextDocument("""l1 = "first line"\nl2 =  'second line'\n"""),
        new_chunks=[
            (
                1,
                ('l1 = "first line"', "l2 =  'second line'"),
                ('l1 = "first line"', 'l2 = "second line"'),
            )
        ],
    ),
    dict(
        content=TextDocument(
            "# coding: iso-8859-5\n# б\x85б\x86\n", encoding="iso-8859-5"
        ),
        new_chunks=[
            (
                1,
                ("# coding: iso-8859-5", "# б\x85б\x86"),
                ("# coding: iso-8859-5", "# б\x85б\x86"),
            )
        ],
    ),
)
def test_unchanged_content(tmp_path, content, new_chunks):
    """Test that no reformats make it through for unmodified files."""
    # A mock object that always returns an empty list of changed lines
    edited_linenums_differ = Mock()
    edited_linenums_differ.revision_vs_lines = Mock(return_value=[])
    # The expected result is the same as the input content, unmodified
    expect = content

    result = _drop_changes_on_unedited_lines(
        new_chunks,
        abspath_in_rev2=tmp_path / "file.py",
        relpath_in_repo=Path("file.py"),
        edited_linenums_differ=edited_linenums_differ,
        rev2_content=content,
        rev2_isorted=content,
        has_isort_changes=False,
        has_fstring_changes=False,
    )

    assert result == expect
