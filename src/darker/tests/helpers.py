"""Helper functions for unit tests"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Generator, Optional
from unittest.mock import patch

from darkgraylib.testtools.git_repo_plugin import GitRepoFixture

if TYPE_CHECKING:
    import pytest
    from _pytest.fixtures import SubRequest


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
def black_present(*, present: bool) -> Generator[None, None, None]:
    """Context manager to remove or add the ``black`` package temporarily for a test."""
    with _package_present("black", present):
        del sys.modules["darker.formatters.black_wrapper"]
        yield


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


@contextmanager
def unix_and_windows_newline_repos(
    request: SubRequest, tmp_path_factory: pytest.TempPathFactory
) -> Generator[dict[str, GitRepoFixture], None, None]:
    """Create temporary repositories for Unix and windows newlines separately."""
    with GitRepoFixture.context(
        request, tmp_path_factory
    ) as repo_unix, GitRepoFixture.context(request, tmp_path_factory) as repo_windows:
        yield {"\n": repo_unix, "\r\n": repo_windows}
