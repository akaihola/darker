"""Helper functions for unit tests"""

import re
import sys
from contextlib import contextmanager, nullcontext
from types import ModuleType
from typing import Any, ContextManager, Dict, Generator, List, Optional, Union
from unittest.mock import patch

import pytest
from _pytest.python_api import RaisesContext


def filter_dict(dct: Dict[str, Any], filter_key: str) -> Dict[str, Any]:
    """Return only given keys with their values from a dictionary"""
    return {key: value for key, value in dct.items() if key == filter_key}


def raises_if_exception(expect: Any) -> Union[RaisesContext[Any], ContextManager[None]]:
    """Return a ``pytest.raises`` context manager only if expecting an exception

    If the expected value is not an exception, return a dummy context manager.

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
def _package_present(
    package_name: str, present: bool
) -> Generator[Optional[ModuleType], None, None]:
    """Context manager to remove or add a package temporarily for a test"""
    if present:
        # Inject a dummy package temporarily
        fake_module: Optional[ModuleType] = ModuleType(package_name)
    else:
        # Remove the `isort` package temporarily
        fake_module = None
    with patch.dict(sys.modules, {package_name: fake_module}):
        yield fake_module


@contextmanager
def isort_present(present: bool) -> Generator[None, None, None]:
    """Context manager to remove or add the `isort` package temporarily for a test"""
    with _package_present("isort", present) as fake_isort_module:
        if present:
            # dummy function required by `import_sorting`:
            fake_isort_module.code = None  # type: ignore
        yield


@contextmanager
def flynt_present(present: bool) -> Generator[None, None, None]:
    """Context manager to remove or add the `flynt` package temporarily for a test"""
    with _package_present("flynt", present) as fake_flynt_module:
        if present:
            # dummy module and function required by `fstring`:
            fake_flynt_module.__version__ = "1.0.0"  # type: ignore
            fake_flynt_module.code_editor = ModuleType("process")  # type: ignore
            fake_flynt_module.code_editor.fstringify_code_by_line = None  # type: ignore
        yield
