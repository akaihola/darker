from pathlib import Path
from textwrap import dedent

import pytest

from darker.import_sorting import apply_isort

ORIGINAL_SOURCE = "import sys\nimport os\n"
ISORTED_SOURCE = "import os\nimport sys\n"


def test_apply_isort():
    result = apply_isort(ORIGINAL_SOURCE)

    assert result == ISORTED_SOURCE


@pytest.mark.parametrize("settings_file", [None, "pyproject.toml"])
@pytest.mark.parametrize("line_length", [20, 60])
def test_isort_config(monkeypatch, tmpdir, line_length, settings_file):
    from black import find_project_root

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
    src = Path(tmpdir / "test1.py") if not settings_file else None
    config = str(tmpdir / settings_file) if settings_file else None

    actual = apply_isort(content, src, config)
    expected = apply_isort(content, line_length=line_length)
    assert actual == expected
