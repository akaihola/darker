"""Configuration and fixtures for the Pytest based test suite"""

import pytest
from black import find_project_root as black_find_project_root


@pytest.fixture
def find_project_root_cache_clear():
    """Clear LRU caching in :func:`black.find_project_root` before each test

    NOTE: We use `darker.black_compat.find_project_root` to wrap Black's original
    function since its signature has changed along the way. However, clearing the cache
    needs to be done on the original of course.

    """
    black_find_project_root.cache_clear()
