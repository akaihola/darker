"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import Iterable, List, Set

from darker.diff import diff_and_get_opcodes, opcodes_to_edit_linenums

logger = logging.getLogger(__name__)


def git_get_unmodified_content(path: Path, revision: str, cwd: Path) -> List[str]:
    """Get unmodified text lines of a file at a Git revision

    :param path: The relative path of the file in the Git repository
    :param revision: The Git revision for which to get the file content
    :param cwd: The root of the Git repository

    """
    cmd = ["git", "show", f"{revision}:./{path}"]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    try:
        return check_output(cmd, cwd=str(cwd), encoding="utf-8").splitlines()
    except CalledProcessError as exc_info:
        if exc_info.returncode == 128:
            # The file didn't exist at the given revision. Act as if it was an empty
            # file, so all current lines appear as edited.
            return []
        else:
            raise


def should_reformat_file(path: Path) -> bool:
    return path.exists() and path.suffix == ".py"


def _git_check_output_lines(cmd: List[str], cwd: Path) -> List[str]:
    """Log command line, run Git, split stdout to lines, exit with 123 on error"""
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    try:
        return check_output(cmd, cwd=str(cwd)).decode("utf-8").splitlines()
    except CalledProcessError as exc_info:
        if exc_info.returncode == 128:
            # Bad revision or another Git failure
            sys.exit(123)
        else:
            raise


def git_get_modified_files(
    paths: Iterable[Path], revision: str, cwd: Path
) -> Set[Path]:
    """Ask Git for modified and untracked files

    - ``git diff --name-only --relative <rev> -- <path(s)>``
    - ``git ls-files --others --exclude-standard -- <path(s)>``

    Return file names relative to the Git repository root.

    :paths: Paths to the files to diff
    :param revision: Git revision to compare current working tree against
    :cwd: The Git repository root

    """
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    str_paths = [str(path) for path in relative_paths]
    diff_cmd = [
        "git",
        "diff",
        "--name-only",
        "--relative",
        # `revision` is inserted here if non-empty
        "--",
        *str_paths,
    ]
    if revision:
        diff_cmd.insert(diff_cmd.index("--"), revision)
    lines = _git_check_output_lines(diff_cmd, cwd)
    ls_files_cmd = [
        "git",
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        *str_paths,
    ]
    lines.extend(_git_check_output_lines(ls_files_cmd, cwd))
    changed_paths = (Path(line) for line in lines)
    return {path for path in changed_paths if should_reformat_file(cwd / path)}


@dataclass(frozen=True)
class EditedLinenumsDiffer:
    """Find out changed lines for a file compared to a given Git revision"""

    git_root: Path
    revision: str

    @lru_cache(maxsize=1)
    def revision_vs_worktree(self, path_in_repo: Path, context_lines: int) -> List[int]:
        """Return numbers of lines changed between a given revision and the worktree"""
        lines = (self.git_root / path_in_repo).read_text("utf-8").splitlines()
        return self.revision_vs_lines(path_in_repo, lines, context_lines)

    def revision_vs_lines(
        self, path_in_repo: Path, lines: List[str], context_lines: int
    ) -> List[int]:
        """For file `path_in_repo`, return changed line numbers from given revision

        :param path_in_repo: Path of the file to compare, relative to repository root
        :param lines: The contents to compare to, e.g. from current working tree
        :return: Line numbers of lines changed between the revision and given content

        """
        revision_lines = git_get_unmodified_content(
            path_in_repo, self.revision, self.git_root
        )
        edited_opcodes = diff_and_get_opcodes(revision_lines, lines)
        return list(opcodes_to_edit_linenums(edited_opcodes, context_lines))
