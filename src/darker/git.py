"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
import sys
from pathlib import Path
from subprocess import CalledProcessError, check_output
from typing import Iterable, List, Set

from darker.diff import diff_and_get_opcodes, opcodes_to_edit_linenums

logger = logging.getLogger(__name__)


def git_get_unmodified_content(path: Path, cwd: Path) -> List[str]:
    """Get unmodified text lines of a file at Git HEAD

    :param path: The relative path of the file in the Git repository
    :param cwd: The root of the Git repository

    """
    cmd = ["git", "show", f":./{path}"]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    return check_output(cmd, cwd=str(cwd), encoding='utf-8').splitlines()


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


def git_get_modified_files(paths: Iterable[Path], cwd: Path) -> Set[Path]:
    """Ask Git for modified and untracked files

    - ``git diff --name-only --relative HEAD -- <path(s)>``
    - ``git ls-files --others --exclude-standard -- <path(s)>``

    Return file names relative to the Git repository root.

    :paths: Paths to the files to diff
    :cwd: The Git repository root

    """
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    str_paths = [str(path) for path in relative_paths]
    diff_cmd = [
        "git",
        "diff",
        "--name-only",
        "--relative",
        "--",
        *str_paths,
    ]
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


class EditedLinenumsDiffer:
    """Find out changed lines for a file compared to Git HEAD"""

    def __init__(self, git_root: Path):
        self._git_root = git_root

    def head_vs_lines(
        self, path_in_repo: Path, lines: List[str], context_lines: int
    ) -> List[int]:
        head_lines = git_get_unmodified_content(path_in_repo, self._git_root)
        edited_opcodes = diff_and_get_opcodes(head_lines, lines)
        return list(opcodes_to_edit_linenums(edited_opcodes, context_lines))
