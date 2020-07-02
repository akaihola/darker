import sys
import types
from subprocess import check_call
from textwrap import dedent
from typing import Dict
from unittest.mock import patch

import pytest
from py.path import local as LocalPath


@pytest.fixture
def without_isort():
    with patch.dict(sys.modules, {"isort": None}):
        yield


@pytest.fixture
def with_isort():
    with patch.dict(sys.modules, {"isort": types.ModuleType("isort")}):
        yield


class GitRepoFixture:
    def __init__(self, root: LocalPath):
        self.root = root

    def add(
        self, paths_and_contents: Dict[str, str], commit: str = None
    ) -> Dict[str, LocalPath]:
        absolute_paths = {
            relative_path: self.root / relative_path
            for relative_path in paths_and_contents
        }
        for relative_path, content in paths_and_contents.items():
            absolute_paths[relative_path].write(content, ensure=True)
            check_call(["git", "add", relative_path], cwd=self.root)
        if commit:
            check_call(["git", "commit", "-m", commit], cwd=self.root)
        return absolute_paths


@pytest.fixture
def git_repo(tmpdir):
    check_call(["git", "init"], cwd=tmpdir)
    return GitRepoFixture(tmpdir)


@pytest.fixture
def isort_config(tmpdir):
    from darker.import_sorting import find_project_root

    find_project_root.cache_clear()

    config = tmpdir / 'pyproject.toml'
    config.write(
        dedent(
            """\
            [tool.isort]
            line_length = 120
            """
        )
    )
    return config
