"""Configuration and fixtures for the Pytest based test suite"""

import os
from pathlib import Path
from subprocess import check_call
from typing import Dict, Optional

import pytest
from black import find_project_root

from darker.git import _git_check_output_lines


class GitRepoFixture:
    def __init__(self, root: Path, env: Dict[str, str]):
        self.root = root
        self.env = env

    @classmethod
    def create_repository(cls, root: Path) -> "GitRepoFixture":
        """Fixture method for creating a Git repository in the given directory"""
        env = os.environ.copy()
        # for testing, ignore ~/.gitconfig settings like templateDir and defaultBranch
        env["HOME"] = str(root)
        instance = cls(root, env)
        # pylint: disable=protected-access
        instance._run("init")
        instance._run("config", "user.email", "ci@example.com")
        instance._run("config", "user.name", "CI system")
        return instance

    def _run(self, *args: str) -> None:
        """Helper method to run a Git command line in the repository root"""
        check_call(["git"] + list(args), cwd=self.root, env=self.env)

    def _run_and_get_first_line(self, *args: str) -> str:
        """Helper method to run Git in repo root and return first line of output"""
        return _git_check_output_lines(list(args), Path(self.root))[0]

    def add(
        self, paths_and_contents: Dict[str, Optional[str]], commit: str = None
    ) -> Dict[str, Path]:
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
                self._run("rm", "--", relative_path)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode("utf-8"))
                self._run("add", "--", relative_path)
        if commit:
            self._run("commit", "-m", commit)
        return absolute_paths

    def get_hash(self, revision: str = "HEAD") -> str:
        """Return the commit hash at the given revision in the Git repository"""
        return self._run_and_get_first_line("rev-parse", revision)

    def get_branch(self) -> str:
        """Return the active branch name in the Git repository"""
        return self._run_and_get_first_line("symbolic-ref", "--short", "HEAD")

    def create_branch(self, new_branch: str, start_point: str) -> None:
        """Fixture method to create and check out new branch at given starting point"""
        self._run("checkout", "-b", new_branch, start_point)


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Create a temporary Git repository and change current working directory into it"""
    repository = GitRepoFixture.create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    return repository


@pytest.fixture
def find_project_root_cache_clear():
    """Clear LRU caching in :func:`black.find_project_root` before each test"""
    find_project_root.cache_clear()
