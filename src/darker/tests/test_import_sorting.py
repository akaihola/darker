from pathlib import Path
from textwrap import dedent

import pytest
from black import find_project_root

from darker.import_sorting import apply_isort

ORIGINAL_SOURCE = "import sys\nimport os\n"
ISORTED_SOURCE = "import os\nimport sys\n"


def test_apply_isort():
    result = apply_isort(ORIGINAL_SOURCE, Path("test1.py"))

    assert result == ISORTED_SOURCE


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

    actual = apply_isort(content, Path("test1.py"), config)
    assert actual == expect
