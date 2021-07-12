"""Tests for :mod:`darker.import_sorting`"""

from importlib import reload
from pathlib import Path
from textwrap import dedent

import pytest
from black import find_project_root

import darker.import_sorting
from darker.tests.helpers import isort_present
from darker.utils import TextDocument

ORIGINAL_SOURCE = ("import sys", "import os")
ISORTED_SOURCE = ("import os", "import sys")


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
def test_apply_isort(encoding, newline):
    """Import sorting is applied correctly, with encoding and newline intact"""
    result = darker.import_sorting.apply_isort(
        TextDocument.from_lines(ORIGINAL_SOURCE, encoding=encoding, newline=newline),
        Path("test1.py"),
    )

    assert result.lines == ISORTED_SOURCE
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
def test_isort_config(monkeypatch, tmpdir, line_length, settings_file, expect):
    """``apply_isort()`` parses ``pyproject.toml``correctly"""
    find_project_root.cache_clear()
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
        TextDocument.from_str(content), Path("test1.py"), config
    )
    assert actual.string == expect
