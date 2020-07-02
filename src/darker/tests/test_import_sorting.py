from pathlib import Path

import pytest

from darker.import_sorting import apply_isort, get_isort_settings

ORIGINAL_SOURCE = "import sys\nimport os\n"
ISORTED_SOURCE = "import os\nimport sys\n"


def test_apply_isort():
    result = apply_isort(ORIGINAL_SOURCE)

    assert result == ISORTED_SOURCE


@pytest.mark.parametrize("config", (None, "pyproject.toml"))
def test_get_isort_settings(config, tmpdir, isort_config):
    src = Path(tmpdir / "test1.py")
    config = str(tmpdir / config) if config else None

    isort_settings = get_isort_settings(src, config)
    assert isort_settings["line_length"] == 120
