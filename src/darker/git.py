"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, check_output, run
from typing import Iterable, List, Set

from darker.diff import diff_and_get_opcodes, opcodes_to_edit_linenums
from darker.utils import GIT_DATEFORMAT, TextDocument

logger = logging.getLogger(__name__)


# Split a revision range into the "from" and "to" revisions and the dots in between.
# Handles these cases:
# <rev>..   <rev>..<rev>   ..<rev>
# <rev>...  <rev>...<rev>  ...<rev>
COMMIT_RANGE_RE = re.compile(r"(.*?)(\.{2,3})(.*)$")


# A colon is an invalid character in tag/branch names. Use that in the special value for
# - denoting the working tree as one of the "revisions" in revision ranges
# - referring to the `PRE_COMMIT_FROM_REF` and `PRE_COMMIT_TO_REF` environment variables
#   for determining the revision range
WORKTREE = ":WORKTREE:"
PRE_COMMIT_FROM_TO_REFS = ":PRE-COMMIT:"


def git_get_mtime_at_commit(path: Path, revision: str, cwd: Path) -> str:
    """Return the committer date of the given file at the given revision

    :param path: The relative path of the file in the Git repository
    :param revision: The Git revision for which to get the file modification time
    :param cwd: The root of the Git repository

    """
    cmd = ["log", "-1", "--format=%ct", revision, "--", path.as_posix()]
    lines = _git_check_output_lines(cmd, cwd)
    return datetime.utcfromtimestamp(int(lines[0])).strftime(GIT_DATEFORMAT)


def git_get_content_at_revision(path: Path, revision: str, cwd: Path) -> TextDocument:
    """Get unmodified text lines of a file at a Git revision

    :param path: The relative path of the file in the Git repository
    :param revision: The Git revision for which to get the file content, or ``WORKTREE``
                     to get what's on disk right now.
    :param cwd: The root of the Git repository

    """
    assert (
        not path.is_absolute()
    ), f"the 'path' parameter must receive a relative path, got {path!r} instead"

    if revision == WORKTREE:
        abspath = cwd / path
        return TextDocument.from_file(abspath)
    cmd = ["show", f"{revision}:./{path.as_posix()}"]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    try:
        return TextDocument.from_lines(
            _git_check_output_lines(cmd, cwd, exit_on_error=False),
            mtime=git_get_mtime_at_commit(path, revision, cwd),
        )
    except CalledProcessError as exc_info:
        if exc_info.returncode != 128:
            for error_line in exc_info.stderr.splitlines():
                logger.error(error_line)
            raise
        # The file didn't exist at the given revision. Act as if it was an empty
        # file, so all current lines appear as edited.
        return TextDocument()


@dataclass(frozen=True)
class RevisionRange:
    """Represent a range of commits in a Git repository for comparing differences

    ``rev1`` is the "old" revision, and ``rev2``, the "new" revision which should be
    compared against ``rev1``.

    If ``use_common_ancestor`` is true, the comparison should not be made against
    ``rev1`` but instead against the branch point, i.e. the latest commit which is
    common to both ``rev1`` and ``rev2``. This is useful e.g. when CI is doing a check
    on a feature branch, and there have been commits in the main branch after the branch
    point. Without the ability to compare to the branch point, Darker would suggest
    corrections to formatting on lines changes in the main branch even if those lines
    haven't been touched in the feature branch.

    """

    rev1: str
    rev2: str = WORKTREE
    use_common_ancestor: bool = False

    def __post_init__(self) -> None:
        if self.rev2 == "":
            super().__setattr__("rev2", WORKTREE)

    @classmethod
    def parse(cls, revision_range: str) -> "RevisionRange":
        """Convert a range expression to a ``RevisionRange`' object

        >>> RevisionRange.parse("a..b")
        RevisionRange(rev1='a', rev2='b', use_common_ancestor=False)
        >>> RevisionRange.parse("a...b")
        RevisionRange(rev1='a', rev2='b', use_common_ancestor=True)
        >>> RevisionRange.parse("a..")
        RevisionRange(rev1='a', rev2=':WORKTREE:', use_common_ancestor=False)
        >>> RevisionRange.parse("a...")
        RevisionRange(rev1='a', rev2=':WORKTREE:', use_common_ancestor=True)

        """
        if revision_range == PRE_COMMIT_FROM_TO_REFS:
            try:
                return cls(
                    os.environ["PRE_COMMIT_FROM_REF"],
                    os.environ["PRE_COMMIT_TO_REF"],
                    use_common_ancestor=True,
                )
            except KeyError:
                # Fallback to running against HEAD
                revision_range = "HEAD"
        match = COMMIT_RANGE_RE.match(revision_range)
        if match:
            rev1, range_dots, rev2 = match.groups()
            use_common_ancestor = range_dots == "..."
            return cls(rev1 or "HEAD", rev2, use_common_ancestor)
        return cls(
            revision_range or "HEAD",
            WORKTREE,
            use_common_ancestor=revision_range not in ["", "HEAD"],
        )


def should_reformat_file(path: Path) -> bool:
    return path.exists() and path.suffix == ".py"


def _git_check_output_lines(
    cmd: List[str], cwd: Path, exit_on_error: bool = True
) -> List[str]:
    """Log command line, run Git, split stdout to lines, exit with 123 on error"""
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    try:
        return check_output(
            ["git"] + cmd,
            cwd=str(cwd),
            encoding="utf-8",
            stderr=PIPE,
            env={"LC_ALL": "C"},
        ).splitlines()
    except CalledProcessError as exc_info:
        if not exit_on_error:
            raise
        if exc_info.returncode != 128:
            sys.stderr.write(exc_info.stderr)
            raise

        # Bad revision or another Git failure. Follow Black's example and return the
        # error status 123.
        for error_line in exc_info.stderr.splitlines():
            logger.error(error_line)
        sys.exit(123)


def _git_exists_in_revision(path: Path, rev2: str) -> bool:
    """Return ``True`` if the given path exists in the given Git revision

    :param path: The path of the file or directory to check
    :param rev2: The Git revision to look at
    :return: ``True`` if the file or directory exists at the revision, or ``False`` if
             it doesn't.

    """
    # Surprise: On Windows, `git cat-file` doesn't work with backslash directory
    # separators in paths. We need to use Posix paths and forward slashes instead.
    cmd = ["git", "cat-file", "-e", f"{rev2}:{path.as_posix()}"]
    result = run(cmd, check=False, stderr=DEVNULL, env={"LC_ALL": "C"})
    return result.returncode == 0


def get_missing_at_revision(paths: Iterable[Path], rev2: str) -> Set[Path]:
    """Return paths missing in the given revision

    In case of ``WORKTREE``, just check if the files exist on the filesystem instead of
    asking Git.

    :param paths: Paths to check
    :param rev2: The Git revision to look at, or ``WORKTREE`` for the working tree
    :return: The set of file or directory paths which are missing in the revision

    """
    if rev2 == WORKTREE:
        return {path for path in paths if not path.exists()}
    return {path for path in paths if not _git_exists_in_revision(path, rev2)}


def git_get_modified_files(
    paths: Iterable[Path], revrange: RevisionRange, cwd: Path
) -> Set[Path]:
    """Ask Git for modified and untracked files

    - ``git diff --name-only --relative <rev> -- <path(s)>``
    - ``git ls-files --others --exclude-standard -- <path(s)>``

    Return file names relative to the Git repository root.

    :param paths: Paths to the files to diff
    :param revrange: Git revision range to compare
    :param cwd: The Git repository root

    """
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    str_paths = [path.as_posix() for path in relative_paths]
    if revrange.use_common_ancestor:
        rev2 = "HEAD" if revrange.rev2 == WORKTREE else revrange.rev2
        merge_base_cmd = ["merge-base", revrange.rev1, rev2]
        rev1 = _git_check_output_lines(merge_base_cmd, cwd)[0]
    else:
        rev1 = revrange.rev1
    diff_cmd = [
        "diff",
        "--name-only",
        "--relative",
        rev1,
        # revrange.rev2 is inserted here if not WORKTREE
        "--",
        *str_paths,
    ]
    if revrange.rev2 != WORKTREE:
        diff_cmd.insert(diff_cmd.index("--"), revrange.rev2)
    lines = _git_check_output_lines(diff_cmd, cwd)
    if revrange.rev2 == WORKTREE:
        ls_files_cmd = [
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
    """Find out changed lines for a file between given Git revisions"""

    git_root: Path
    revrange: RevisionRange

    @lru_cache(maxsize=1)
    def compare_revisions(self, path_in_repo: Path, context_lines: int) -> List[int]:
        """Return numbers of lines changed between a given revision and the worktree"""
        content = TextDocument.from_file(self.git_root / path_in_repo)
        return self.revision_vs_lines(path_in_repo, content, context_lines)

    def revision_vs_lines(
        self, path_in_repo: Path, content: TextDocument, context_lines: int
    ) -> List[int]:
        """For file `path_in_repo`, return changed line numbers from given revision

        :param path_in_repo: Path of the file to compare, relative to repository root
        :param content: The contents to compare to, e.g. from current working tree
        :param context_lines: The number of lines to include before and after a change
        :return: Line numbers of lines changed between the revision and given content

        """
        old = git_get_content_at_revision(
            path_in_repo, self.revrange.rev1, self.git_root
        )
        edited_opcodes = diff_and_get_opcodes(old, content)
        return list(opcodes_to_edit_linenums(edited_opcodes, context_lines))
