"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, run
from typing import Iterable, List, Set, Tuple

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


class NotGitRespository(Exception):
    "Raised when git commands are run in a folder that is not a git repository"


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

    When parsing a revision range expression with triple dots (e.g. ``master...HEAD``),
    the branch point, or common ancestor of the revisions, is used instead of the
    provided ``rev1``. This is useful e.g. when CI is doing a check
    on a feature branch, and there have been commits in the main branch after the branch
    point. Without the ability to compare to the branch point, Darker would suggest
    corrections to formatting on lines changes in the main branch even if those lines
    haven't been touched in the feature branch.

    """

    rev1: str
    rev2: str

    @classmethod
    def parse_with_common_ancestor(
        cls, revision_range: str, cwd: Path
    ) -> "RevisionRange":
        """Convert a range expression to a ``RevisionRange`` object

        If the expression contains triple dots (e.g. ``master...HEAD``), finds the
        common ancestor of the two revisions and uses that as the first revision.

        """
        rev1, rev2, use_common_ancestor = cls._parse(revision_range)
        if use_common_ancestor:
            return cls._with_common_ancestor(rev1, rev2, cwd)
        return cls(rev1, rev2)

    @staticmethod
    def _parse(revision_range: str) -> Tuple[str, str, bool]:
        """Convert a range expression to revisions, using common ancestor if appropriate

        >>> RevisionRange._parse("a..b")
        ('a', 'b', False)
        >>> RevisionRange._parse("a...b")
        ('a', 'b', True)
        >>> RevisionRange._parse("a..")
        ('a', ':WORKTREE:', False)
        >>> RevisionRange._parse("a...")
        ('a', ':WORKTREE:', True)

        """
        if revision_range == PRE_COMMIT_FROM_TO_REFS:
            try:
                return (
                    os.environ["PRE_COMMIT_FROM_REF"],
                    os.environ["PRE_COMMIT_TO_REF"],
                    True,
                )
            except KeyError:
                # Fallback to running against HEAD
                revision_range = "HEAD"
        match = COMMIT_RANGE_RE.match(revision_range)
        if match:
            rev1, range_dots, rev2 = match.groups()
            use_common_ancestor = range_dots == "..."
            return (rev1 or "HEAD", rev2 or WORKTREE, use_common_ancestor)
        return (revision_range or "HEAD", WORKTREE, revision_range not in ["", "HEAD"])

    @classmethod
    def _with_common_ancestor(cls, rev1: str, rev2: str, cwd: Path) -> "RevisionRange":
        """Find common ancestor for revisions and return a ``RevisionRange`` object"""
        rev2_for_merge_base = "HEAD" if rev2 == WORKTREE else rev2
        merge_base_cmd = ["merge-base", rev1, rev2_for_merge_base]
        common_ancestor = _git_check_output_lines(merge_base_cmd, cwd)[0]
        rev1_hash = _git_check_output_lines(["show", "-s", "--pretty=%H", rev1], cwd)[0]
        return cls(rev1 if common_ancestor == rev1_hash else common_ancestor, rev2)


def should_reformat_file(path: Path) -> bool:
    return path.exists() and path.suffix == ".py"


def _git_check_output_lines(
    cmd: List[str], cwd: Path, exit_on_error: bool = True
) -> List[str]:
    """Log command line, run Git, split stdout to lines, exit with 123 on error"""
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    try:
        result = run(
            ["git"] + cmd,
            cwd=str(cwd),
            check=True,
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
            env={"LC_ALL": "C"},
        )
        return result.stdout.splitlines()
    except CalledProcessError as exc_info:
        retval = exc_info.returncode
        msg = exc_info.stderr
        if (retval == 129 and msg.startswith("Not a git repository")) or (
            retval == 1 and msg.startswith("error: could not access ")
        ):
            raise NotGitRespository(f"{cwd} is not a git repository") from exc_info
        if not exit_on_error:
            raise
        if retval != 128:
            sys.stderr.write(msg)
            raise

        # Bad revision or another Git failure. Follow Black's example and return the
        # error status 123.
        for error_line in msg.splitlines():
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


def _git_diff_name_only(
    rev1: str, rev2: str, relative_paths: Set[Path], cwd: Path
) -> Set[Path]:
    """Collect names of changed files between commits from Git

    :param rev1: The old commit to compare to
    :param rev2: The new commit to compare, or the string ``":WORKTREE:"`` to compare
                 current working tree to ``rev1``
    :param relative_paths: Relative paths to the files to compare
    :param cwd: The Git repository root
    :return: Relative paths of changed files

    """
    diff_cmd = [
        "diff",
        "--name-only",
        "--relative",
        rev1,
        # rev2 is inserted here if not WORKTREE
        "--",
        *{path.as_posix() for path in relative_paths},
    ]
    if rev2 != WORKTREE:
        diff_cmd.insert(diff_cmd.index("--"), rev2)
    lines = _git_check_output_lines(diff_cmd, cwd)
    return {Path(line) for line in lines}


def _git_ls_files_others(relative_paths: Set[Path], cwd: Path) -> Set[Path]:
    """Collect names of untracked non-excluded files from Git

    This will return those files in ``relative_paths`` which are untracked and not
    excluded by ``.gitignore`` or other Git's exclusion mechanisms.

    :param relative_paths: Relative paths to the files to consider
    :param cwd: The Git repository root
    :return: Relative paths of untracked files

    """
    ls_files_cmd = [
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        *{path.as_posix() for path in relative_paths},
    ]
    lines = _git_check_output_lines(ls_files_cmd, cwd)
    return {Path(line) for line in lines}


def git_get_modified_python_files(
    paths: Iterable[Path], revrange: RevisionRange, cwd: Path
) -> Set[Path]:
    """Ask Git for modified and untracked ``*.py`` files

    - ``git diff --name-only --relative <rev> -- <path(s)>``
    - ``git ls-files --others --exclude-standard -- <path(s)>``

    :param paths: Paths to the files to diff
    :param revrange: Git revision range to compare
    :param cwd: The Git repository root
    :return: File names relative to the Git repository root

    """
    relative_paths = {p.resolve().relative_to(cwd) for p in paths}
    changed_paths = _git_diff_name_only(
        revrange.rev1, revrange.rev2, relative_paths, cwd
    )
    if revrange.rev2 == WORKTREE:
        changed_paths.update(_git_ls_files_others(relative_paths, cwd))
    return {path for path in changed_paths if should_reformat_file(cwd / path)}


@dataclass(frozen=True)
class EditedLinenumsDiffer:
    """Find out changed lines for a file between given Git revisions"""

    root: Path
    revrange: RevisionRange

    @lru_cache(maxsize=1)
    def compare_revisions(self, path_in_repo: Path, context_lines: int) -> List[int]:
        """Return numbers of lines changed between a given revision and the worktree"""
        content = TextDocument.from_file(self.root / path_in_repo)
        linenums = self.revision_vs_lines(path_in_repo, content, context_lines)
        logger.debug(
            "Edited line numbers in %s: %s",
            path_in_repo,
            " ".join(str(n) for n in linenums),
        )
        return linenums

    def revision_vs_lines(
        self, path_in_repo: Path, content: TextDocument, context_lines: int
    ) -> List[int]:
        """For file `path_in_repo`, return changed line numbers from given revision

        :param path_in_repo: Path of the file to compare, relative to repository root
        :param content: The contents to compare to, e.g. from current working tree
        :param context_lines: The number of lines to include before and after a change
        :return: Line numbers of lines changed between the revision and given content

        """
        old = git_get_content_at_revision(path_in_repo, self.revrange.rev1, self.root)
        edited_opcodes = diff_and_get_opcodes(old, content)
        return list(opcodes_to_edit_linenums(edited_opcodes, context_lines))
