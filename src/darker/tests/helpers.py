"""Helper functions for unit tests"""

import re
import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Any, ContextManager, Dict, List, Optional, Union
from unittest.mock import patch

import pytest
from _pytest.python_api import RaisesContext

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:
    from contextlib import suppress as nullcontext


def filter_dict(dct: Dict[str, Any], filter_key: str) -> Dict[str, Any]:
    """Return only given keys with their values from a dictionary"""
    return {key: value for key, value in dct.items() if key == filter_key}


def raises_if_exception(expect: Any) -> Union[RaisesContext[Any], ContextManager[None]]:
    """Return a ``pytest.raises`` context manager only if expecting an exception

    If the expected value is not an exception, return a dummy context manager.
    On Python 3.8+ :class:`contextlib.nullcontext` is returned,
    while on older Pythons :class:`contextlib.suppress` is used instead.

    """
    if (isinstance(expect, type) and issubclass(expect, BaseException)) or (
        isinstance(expect, tuple)
        and all(
            isinstance(item, type) and issubclass(item, BaseException)
            for item in expect
        )
    ):
        return pytest.raises(expect)
    if isinstance(expect, BaseException):
        return pytest.raises(type(expect), match=re.escape(str(expect)))
    return nullcontext()


def matching_attrs(obj: BaseException, attrs: List[str]) -> Dict[str, int]:
    """Return object attributes whose name matches one in the given list"""
    return {attname: getattr(obj, attname) for attname in dir(obj) if attname in attrs}


@contextmanager
def raises_or_matches(expect, match_exc_attrs):
    """Helper for matching an expected value or an expected raised exception"""
    if isinstance(expect, BaseException):
        with pytest.raises(type(expect)) as exc_info:
            # The lambda callback should never get called
            yield lambda result: False
        exception_attributes = matching_attrs(exc_info.value, match_exc_attrs)
        expected_attributes = matching_attrs(expect, match_exc_attrs)
        assert exception_attributes == expected_attributes
    else:

        def check(result):
            assert result == expect

        yield check


@contextmanager
def isort_present(present):
    """Context manager to remove or add the `isort` package temporarily for a test"""
    if present:
        # Inject a dummy `isort` package temporarily
        fake_isort_module: Optional[ModuleType] = ModuleType("isort")
        # dummy function required by `import_sorting`:
        fake_isort_module.code = None  # type: ignore
    else:
        # Remove the `isort` package temporarily
        fake_isort_module = None
    with patch.dict(sys.modules, {"isort": fake_isort_module}):
        yield
