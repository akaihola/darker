"""Configuration and fixtures for the Pytest based test suite"""

import os
import re
from pathlib import Path
from subprocess import check_call  # nosec
from typing import Dict, Iterable, List, Union

import pytest
from black import find_project_root as black_find_project_root

from darker.git import _git_check_output_lines


class GitRepoFixture:
    def __init__(self, root: Path, env: Dict[str, str]):
        self.root = root
        self.env = env

    @classmethod
    def create_repository(cls, root: Path) -> "GitRepoFixture":
        """Fixture method for creating a Git repository in the given directory"""
        # For testing, ignore ~/.gitconfig settings like templateDir and defaultBranch.
        # Also, this makes sure GIT_DIR or other GIT_* variables are not set, and that
        # Git's messages are in English.
        env = {"HOME": str(root), "LC_ALL": "C", "PATH": os.environ["PATH"]}
        instance = cls(root, env)
        # pylint: disable=protected-access
        instance._run("init", "--initial-branch=master")
        instance._run("config", "user.email", "ci@example.com")
        instance._run("config", "user.name", "CI system")
        return instance

    def _run(self, *args: str) -> None:
        """Helper method to run a Git command line in the repository root"""
        check_call(["git"] + list(args), cwd=self.root, env=self.env)  # nosec

    def _run_and_get_first_line(self, *args: str) -> str:
        """Helper method to run Git in repo root and return first line of output"""
        return _git_check_output_lines(list(args), Path(self.root))[0]

    def add(
        self, paths_and_contents: Dict[str, Union[str, bytes, None]], commit: str = None
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
                continue
            if isinstance(content, str):
                content = content.encode("utf-8")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
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

    def create_tag(self, tag_name: str) -> None:
        """Create a tag at current HEAD"""
        self._run("tag", tag_name)

    def create_branch(self, new_branch: str, start_point: str) -> None:
        """Fixture method to create and check out new branch at given starting point"""
        self._run("checkout", "-b", new_branch, start_point)

    def expand_root(self, lines: Iterable[str]) -> List[str]:
        """Replace "{root/<path>}" in strings with the path in the temporary Git repo

        This is used to generate expected strings corresponding to locations of files in
        the temporary Git repository.

        :param lines: The lines of text to process
        :return: Given lines with paths processed

        """
        return [
            re.sub(r"\{root/(.*?)\}", lambda m: str(self.root / str(m.group(1))), line)
            for line in lines
        ]


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Create a temporary Git repository and change current working directory into it"""
    repository = GitRepoFixture.create_repository(tmp_path)
    monkeypatch.chdir(tmp_path)
    # While `GitRepoFixture.create_repository()` already deletes `GIT_*` environment
    # variables for any Git commands run by the fixture, let's explicitly remove
    # `GIT_DIR` in case a test should call Git directly:
    monkeypatch.delenv("GIT_DIR", raising=False)
    return repository


@pytest.fixture
def find_project_root_cache_clear():
    """Clear LRU caching in :func:`black.find_project_root` before each test

    NOTE: We use `darker.black_compat.find_project_root` to wrap Black's original
    function since its signature has changed along the way. However, clearing the cache
    needs to be done on the original of course.

    """
    black_find_project_root.cache_clear()
