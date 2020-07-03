from darker.import_sorting import apply_isort

ORIGINAL_SOURCE = "import sys\nimport os\n"
ISORTED_SOURCE = "import os\nimport sys\n"


def test_apply_isort():
    result = apply_isort(ORIGINAL_SOURCE)

    assert result == ISORTED_SOURCE
