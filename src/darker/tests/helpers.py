"""Helper functions for unit tests"""

import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Generator, Optional
from unittest.mock import patch


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
            fake_flynt_module.__version__ = "1.0.0"  # type: ignore
            fake_flynt_module.code_editor = ModuleType("process")  # type: ignore
            fake_flynt_module.code_editor.fstringify_code_by_line = None  # type: ignore
        yield
