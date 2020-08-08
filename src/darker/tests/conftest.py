import sys
import types
from subprocess import check_call
from typing import Dict, Optional
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
        self, paths_and_contents: Dict[str, Optional[str]], commit: str = None
    ) -> Dict[str, LocalPath]:
        """Add/remove/modify files and optionally commit the changes

        :param paths_and_contents: Paths of the files relative to repository root, and
                                   new contents for the files as strings. ``None`` can
                                   be specified as the contents in order to remove a
                                   file.
        :param commit: The message for the commit, or ``None`` to skip making a commit.

        """
        absolute_paths = {
            relative_path: self.root / relative_path
            for relative_path in paths_and_contents
        }
        for relative_path, content in paths_and_contents.items():
            path = absolute_paths[relative_path]
            if content is None:
                check_call(["git", "rm", "--", relative_path], cwd=self.root)
            else:
                path.write(content, ensure=True)
                check_call(["git", "add", "--", relative_path], cwd=self.root)
        if commit:
            check_call(["git", "commit", "-m", commit], cwd=self.root)
        return absolute_paths


@pytest.fixture
def git_repo(tmpdir, monkeypatch):
    """Create a temporary Git repository and change current working directory into it"""
    check_call(["git", "init"], cwd=tmpdir)
    monkeypatch.chdir(tmpdir)
    return GitRepoFixture(tmpdir)
