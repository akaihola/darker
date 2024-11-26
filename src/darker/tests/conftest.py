"""Configuration and fixtures for the Pytest based test suite."""

import pytest

try:
    from black.files import _load_toml
except ImportError:
    # Black 24.1.1 and earlier don't have `_load_toml`.
    _load_toml = None  # type: ignore[assignment]


@pytest.fixture
def load_toml_cache_clear() -> None:
    """Clear LRU caching in `black.files._load_toml` before each test.

    To use this on all test cases in a test module, add this to the top::

        pytestmark = pytest.mark.usefixtures("load_toml_cache_clear")

    """
    if _load_toml:
        # Black 24.1.1 and earlier don't have `_load_toml`, so no LRU cache to clear.
        _load_toml.cache_clear()
