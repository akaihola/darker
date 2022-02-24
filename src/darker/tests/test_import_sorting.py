"""Tests for :mod:`darker.import_sorting`"""

# pylint: disable=unused-argument,protected-access

from importlib import reload
from pathlib import Path
from textwrap import dedent

import pytest

import darker.import_sorting
from darker.git import EditedLinenumsDiffer, RevisionRange
from darker.tests.helpers import isort_present
from darker.utils import TextDocument, joinlines

ORIGINAL_SOURCE = ("import sys", "import os", "", "print(42)")
ISORTED_SOURCE = ("import os", "import sys", "", "print(42)")


@pytest.mark.parametrize("present", [True, False])
def test_import_sorting_importable_with_and_without_isort(present):
    """Make sure ``import darker.import_sorting`` works with and without ``isort``"""
    try:
        with isort_present(present):

            # Import when `isort` has been removed temporarily
            reload(darker.import_sorting)
    finally:
        # Re-import after restoring `isort` so other tests won't be affected
        reload(darker.import_sorting)


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.kwparametrize(
    dict(content=ORIGINAL_SOURCE, expect=ORIGINAL_SOURCE),
    dict(content=("import sys", "import os"), expect=("import sys", "import os")),
    dict(
        content=("import sys", "import os", "# foo", "print(42)"),
        expect=("import sys", "import os", "# foo", "print(42)"),
    ),
    dict(
        content=("import sys", "import os", "", "print(43)"),
        expect=("import sys", "import os", "", "print(43)"),
    ),
    dict(content=("import   sys", "import os", "", "print(42)"), expect=ISORTED_SOURCE),
    dict(content=("import sys", "import   os", "", "print(42)"), expect=ISORTED_SOURCE),
)
def test_apply_isort(git_repo, encoding, newline, content, expect):
    """Imports are sorted if edits overlap them, with encoding and newline intact"""
    git_repo.add({"test1.py": joinlines(ORIGINAL_SOURCE, newline)}, commit="Initial")
    edited_linenums_differ = EditedLinenumsDiffer(
        git_repo.root, RevisionRange("HEAD", ":WORKTREE:")
    )
    src = Path("test1.py")
    content_ = TextDocument.from_lines(content, encoding=encoding, newline=newline)

    result = darker.import_sorting.apply_isort(content_, src, edited_linenums_differ)

    assert result.lines == expect
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.kwparametrize(
    dict(
        line_length=50,
        settings_file=None,
        expect=(
            "from module import (ab, cd, ef, gh, ij, kl, mn,\n"
            "                    op, qr, st, uv, wx, yz)\n"
        ),
    ),
    dict(
        line_length=50,
        settings_file="pyproject.toml",
        expect=(
            "from module import (ab, cd, ef, gh, ij, kl, mn,\n"
            "                    op, qr, st, uv, wx, yz)\n"
        ),
    ),
    dict(
        line_length=60,
        settings_file=None,
        expect=(
            "from module import (ab, cd, ef, gh, ij, kl, mn, op, qr, st,\n"
            "                    uv, wx, yz)\n"
        ),
    ),
    dict(
        line_length=60,
        settings_file="pyproject.toml",
        expect=(
            "from module import (ab, cd, ef, gh, ij, kl, mn, op, qr, st,\n"
            "                    uv, wx, yz)\n"
        ),
    ),
)
def test_isort_config(
    monkeypatch,
    tmpdir,
    find_project_root_cache_clear,
    line_length,
    settings_file,
    expect,
):
    """``apply_isort()`` parses ``pyproject.toml``correctly"""
    monkeypatch.chdir(tmpdir)
    (tmpdir / "pyproject.toml").write(
        dedent(
            f"""\
            [tool.isort]
            line_length = {line_length}
            """
        )
    )

    content = "from module import ab, cd, ef, gh, ij, kl, mn, op, qr, st, uv, wx, yz"
    config = str(tmpdir / settings_file) if settings_file else None

    actual = darker.import_sorting.apply_isort(
        TextDocument.from_str(content),
        Path("test1.py"),
        EditedLinenumsDiffer(Path("."), RevisionRange("master", "HEAD")),
        config,
    )
    assert actual.string == expect


@pytest.mark.kwparametrize(
    dict(src=Path("file.py"), expect={"settings_path": "{cwd}"}),
    dict(
        config="myconfig.toml",
        expect={"settings_file": "myconfig.toml"},
    ),
    dict(line_length=42, expect={"settings_path": "{cwd}", "line_length": 42}),
    src=Path("file.py"),
    config=None,
    line_length=None,
)
def test_build_isort_args(src, config, line_length, expect):
    """``_build_isort_args`` returns correct arguments for isort"""
    result = darker.import_sorting._build_isort_args(src, config, line_length)

    if "settings_path" in expect:
        expect["settings_path"] = str(expect["settings_path"].format(cwd=Path.cwd()))
    assert result == expect


def test_isort_file_skip_comment():
    """``apply_isort()`` handles ``FileSkipComment`` exception correctly"""
    # Avoid https://github.com/PyCQA/isort/pull/1833 by splitting the skip string
    content = "# iso" + "rt:skip_file"

    actual = darker.import_sorting.apply_isort(
        TextDocument.from_str(content),
        Path("test1.py"),
        EditedLinenumsDiffer(Path("."), RevisionRange("master", "HEAD")),
    )

    assert actual.string == content


@pytest.mark.kwparametrize(
    dict(edited_linenums=[], isort_chunks=[], expect=False),
    dict(edited_linenums=[1, 2, 3, 4, 5, 6, 7, 8, 9], isort_chunks=[], expect=False),
    dict(edited_linenums=[], isort_chunks=[(1, ("a", "b"), ("A", "B"))], expect=False),
    dict(edited_linenums=[1], isort_chunks=[(1, ("a", "b"), ("A", "B"))], expect=True),
    dict(edited_linenums=[2], isort_chunks=[(1, ("a", "b"), ("A", "B"))], expect=True),
    dict(edited_linenums=[3], isort_chunks=[(1, ("a", "b"), ("A", "B"))], expect=False),
    dict(edited_linenums=[], isort_chunks=[(1, ("A", "B"), ("A", "B"))], expect=False),
    dict(edited_linenums=[1], isort_chunks=[(1, ("A", "B"), ("A", "B"))], expect=False),
    dict(edited_linenums=[2], isort_chunks=[(1, ("A", "B"), ("A", "B"))], expect=False),
    dict(edited_linenums=[3], isort_chunks=[(1, ("A", "B"), ("A", "B"))], expect=False),
    dict(
        edited_linenums=[3, 9],
        isort_chunks=[
            (1, ("a", "b"), ("A", "B")),
            (3, ("c", "d", "e", "f", "g"), ("c", "d", "e", "f", "g")),
            (8, ("h", "i", "j"), ("h", "i", "j")),
        ],
        expect=False,
    ),
    dict(
        edited_linenums=[3, 9],
        isort_chunks=[
            (1, ("a", "b", "c"), ("A", "B", "C")),
            (4, ("d", "e", "f", "g"), ("d", "e", "f", "g")),
            (8, ("h", "i", "j"), ("h", "i", "j")),
        ],
        expect=True,
    ),
    dict(
        edited_linenums=[3, 9],
        isort_chunks=[
            (1, ("a", "b", "c"), ("a", "b", "c")),
            (4, ("d", "e", "f", "g"), ("d", "e", "f", "g")),
            (8, ("h", "i", "j"), ("H", "I", "J")),
        ],
        expect=True,
    ),
    dict(
        edited_linenums=[3, 9],
        isort_chunks=[
            (1, ("a", "b", "c", "d"), ("a", "b", "c", "d")),
            (5, ("e", "f", "g", "h", "i"), ("e", "f", "g", "h", "i")),
            (10, ("j"), ("J")),
        ],
        expect=False,
    ),
)
def test_diff_overlaps_with_edits(edited_linenums, isort_chunks, expect):
    """Overlapping edits and import sortings are detected correctly"""
    result = darker.import_sorting._diff_overlaps_with_edits(
        edited_linenums, isort_chunks
    )

    assert result == expect
