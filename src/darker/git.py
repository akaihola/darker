"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
from pathlib import Path
from subprocess import check_output
from typing import Iterable, List, Set

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


def git_diff_name_only(paths: Iterable[Path], cwd: Path) -> Set[Path]:
    """Run ``git diff --name-only`` and return file names from the output

    Return file names relative to the Git repository root.

    :paths: Paths to the files to diff
    :cwd: The Git repository root

    """
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--relative",
        "--",
        *[str(path) for path in relative_paths],
    ]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    lines = check_output(cmd, cwd=str(cwd)).decode("utf-8").splitlines()
    changed_paths = (Path(line) for line in lines)
    return {path for path in changed_paths if should_reformat_file(cwd / path)}
