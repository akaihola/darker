"""Helper functions for unit tests"""

import sys
from typing import Any, ContextManager, Dict, Union

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
    if isinstance(expect, type) and issubclass(expect, BaseException):
        return pytest.raises(expect)
    else:
        return nullcontext()
