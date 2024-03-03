"""Helper functions for unit tests"""

import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Dict, Generator, List, Optional
from unittest.mock import patch

import pytest


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
            # pylint: disable=no-member
            fake_flynt_module.process = ModuleType("process")  # type: ignore
            fake_flynt_module.process.fstringify_code_by_line = None  # type: ignore
        yield
