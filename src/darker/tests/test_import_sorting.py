from pathlib import Path
from textwrap import dedent

import pytest
from black import find_project_root

from darker.import_sorting import apply_isort
from darker.utils import TextDocument

ORIGINAL_SOURCE = ("import sys", "import os")
ISORTED_SOURCE = ("import os", "import sys")


@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-1"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_apply_isort(encoding, newline):
    """Import sorting is applied correctly, with encoding and newline intact"""
    result = apply_isort(
        TextDocument.from_lines(ORIGINAL_SOURCE, encoding=encoding, newline=newline),
        Path("test1.py"),
    )

    assert result.lines == ISORTED_SOURCE
    assert result.encoding == encoding
    assert result.newline == newline


@pytest.mark.parametrize(
    "line_length, settings_file, expect",
    [
        (
            50,
            None,
            "from module import (ab, cd, ef, gh, ij, kl, mn,\n"
            "                    op, qr, st, uv, wx, yz)\n",
        ),
        (
            50,
            "pyproject.toml",
            "from module import (ab, cd, ef, gh, ij, kl, mn,\n"
            "                    op, qr, st, uv, wx, yz)\n",
        ),
        (
            60,
            None,
            "from module import (ab, cd, ef, gh, ij, kl, mn, op, qr, st,\n"
            "                    uv, wx, yz)\n",
        ),
        (
            60,
            "pyproject.toml",
            "from module import (ab, cd, ef, gh, ij, kl, mn, op, qr, st,\n"
            "                    uv, wx, yz)\n",
        ),
    ],
)
def test_isort_config(monkeypatch, tmpdir, line_length, settings_file, expect):
    find_project_root.cache_clear()
    monkeypatch.chdir(tmpdir)
    (tmpdir / 'pyproject.toml').write(
        dedent(
            f"""\
            [tool.isort]
            line_length = {line_length}
            """
        )
    )

    content = "from module import ab, cd, ef, gh, ij, kl, mn, op, qr, st, uv, wx, yz"
    config = str(tmpdir / settings_file) if settings_file else None

    actual = apply_isort(TextDocument.from_str(content), Path("test1.py"), config)
    assert actual.string == expect
