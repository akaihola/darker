import sys
import types
from unittest.mock import patch

import pytest


@pytest.fixture
def without_isort():
    with patch.dict(sys.modules, {"isort": None}):
        yield


@pytest.fixture
def with_isort():
    with patch.dict(sys.modules, {"isort": types.ModuleType("isort")}):
        yield