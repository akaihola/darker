"""Git diffing"""
import logging
from pathlib import Path
from subprocess import check_output
from typing import Generator

logger = logging.getLogger(__name__)


def git_diff_u0(path: Path) -> bytes:
    """Run ``git diff -U0 <path>`` on the given path, and return the output"""
    cmd = ["git", "diff", "-U0", "--", path.name]
    logger.info("[%s]$ %s", path.parent, " ".join(cmd))
    return check_output(cmd, cwd=str(path.parent))


def get_edit_linenums(patch: bytes) -> Generator[int, None, None]:
    """Yield changed line numbers in Git diff to-file

    The patch must be in ``git diff -U0`` format, and only contain differences for a
    single file.

    """
    if not patch:
        logger.info("No edits found in the source file")
        return
    git_diff_lines = patch.split(b"\n")
    assert git_diff_lines[0].startswith(b"diff --git ")
    assert git_diff_lines[1].startswith(b"index ")
    assert git_diff_lines[2].startswith(b"--- a/")
    assert git_diff_lines[3].startswith(b"+++ b/")
    for line in git_diff_lines[4:]:
        assert not line.startswith((b"diff --git ", b"index "))
        if not line or line.startswith((b"+", b"-")):
            continue
        assert line.startswith(b"@@ ")
        start_str, *length_str = line.split()[2].split(b",")
        start_linenum = int(start_str)
        length = int(length_str[0]) if length_str else 1
        logger.info(
            "Found edited %s",
            f"line {start_linenum}"
            if length == 1
            else f"lines {start_linenum}-{start_linenum + length - 1}",
        )
        yield from range(start_linenum, start_linenum + length)
