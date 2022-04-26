"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, check_output, run  # nosec
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union, overload

from darker.diff import diff_and_get_opcodes, opcodes_to_edit_linenums
from darker.multiline_strings import get_multiline_string_ranges
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


def git_is_repository(path: Path) -> bool:
    """Return ``True`` if ``path`` is inside a Git working tree"""
    try:
        lines = _git_check_output_lines(
            ["rev-parse", "--is-inside-work-tree"], path, exit_on_error=False
        )
        return lines[:1] == ["true"]
    except CalledProcessError as exc_info:
        if exc_info.returncode != 128 or not exc_info.stderr.startswith(
            "fatal: not a git repository"
        ):
            raise
        return False


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
    if path.is_absolute():
        raise ValueError(
            f"the 'path' parameter must receive a relative path, got {path!r} instead"
        )

    if revision == WORKTREE:
        abspath = cwd / path
        return TextDocument.from_file(abspath)
    cmd = ["show", f"{revision}:./{path.as_posix()}"]
    try:
        return TextDocument.from_bytes(
            _git_check_output(cmd, cwd, exit_on_error=False),
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


def get_path_in_repo(path: Path) -> Path:
    """Return the relative path to the file in the old revision

    This is usually the same as the relative path on the command line. But in the
    special case of VSCode temporary files (like ``file.py.12345.tmp``), we actually
    want to diff against the corresponding ``.py`` file instead.

    """
    if path.suffixes[-3::2] != [".py", ".tmp"]:
        # The file name is not like `*.py.<HASH>.tmp`. Return it as such.
        return path
    # This is a VSCode temporary file. Drop the hash and the `.tmp` suffix to get the
    # original file name for retrieving the previous revision to diff against.
    path_with_hash = path.with_suffix("")
    return path_with_hash.with_suffix("")


def should_reformat_file(path: Path) -> bool:
    return path.exists() and get_path_in_repo(path).suffix == ".py"


@lru_cache(maxsize=1)
def _make_git_env() -> Dict[str, str]:
    """Create custom minimal environment variables to use when invoking Git

    This makes sure that
    - Git always runs in English
    - ``$PATH`` is preserved (essential on NixOS)
    - the environment is otherwise cleared

    """
    return {"LC_ALL": "C", "PATH": os.environ["PATH"]}


def _git_check_output_lines(
    cmd: List[str], cwd: Path, exit_on_error: bool = True
) -> List[str]:
    """Log command line, run Git, split stdout to lines, exit with 123 on error"""
    return _git_check_output(
        cmd,
        cwd,
        exit_on_error=exit_on_error,
        encoding="utf-8",
    ).splitlines()


@overload
def _git_check_output(
    cmd: List[str], cwd: Path, *, exit_on_error: bool = ..., encoding: None = ...
) -> bytes:
    ...


@overload
def _git_check_output(
    cmd: List[str], cwd: Path, *, exit_on_error: bool = ..., encoding: str
) -> str:
    ...


def _git_check_output(
    cmd: List[str],
    cwd: Path,
    *,
    exit_on_error: bool = True,
    encoding: Optional[str] = None,
) -> Union[str, bytes]:
    """Log command line, run Git, return stdout, exit with 123 on error"""
    logger.debug("[%s]$ git %s", cwd, " ".join(cmd))
    try:
        return check_output(  # nosec
            ["git"] + cmd,
            cwd=str(cwd),
            encoding=encoding,
            stderr=PIPE,
            env=_make_git_env(),
        )
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


def _git_exists_in_revision(path: Path, rev2: str, cwd: Path) -> bool:
    """Return ``True`` if the given path exists in the given Git revision

    :param path: The path of the file or directory to check
    :param rev2: The Git revision to look at
    :param cwd: The Git repository root
    :return: ``True`` if the file or directory exists at the revision, or ``False`` if
             it doesn't.

    """
    if (cwd / path).resolve() == cwd.resolve():
        return True
    # Surprise: On Windows, `git cat-file` doesn't work with backslash directory
    # separators in paths. We need to use Posix paths and forward slashes instead.
    cmd = ["git", "cat-file", "-e", f"{rev2}:{path.as_posix()}"]
    logger.debug("[%s]$ %s", cwd, " ".join(cmd))
    result = run(  # nosec
        cmd,
        cwd=str(cwd),
        check=False,
        stderr=DEVNULL,
        env=_make_git_env(),
    )
    return result.returncode == 0


def get_missing_at_revision(paths: Iterable[Path], rev2: str, cwd: Path) -> Set[Path]:
    """Return paths missing in the given revision

    In case of ``WORKTREE``, just check if the files exist on the filesystem instead of
    asking Git.

    :param paths: Paths to check
    :param rev2: The Git revision to look at, or ``WORKTREE`` for the working tree
    :param cwd: The Git repository root
    :return: The set of file or directory paths which are missing in the revision

    """
    if rev2 == WORKTREE:
        return {path for path in paths if not path.exists()}
    return {path for path in paths if not _git_exists_in_revision(path, rev2, cwd)}


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


def _revision_vs_lines(
    root: Path, path_in_repo: Path, rev1: str, content: TextDocument, context_lines: int
) -> List[int]:
    """Return changed line numbers between the given revision and given text content

    The revision range was provided when this `EditedLinenumsDiffer` object was
    created. Content for the given `path_in_repo` at `rev1` of that revision is
    taken from the Git repository, and the provided text content is compared against
    that historical version.

    The actual implementation is here instead of in
    `EditedLinenumsDiffer._revision_vs_lines` so it is accessibe both as a method and as
    a module global for use in the `_compare_revisions` function.

    :param root: Root directory for the relative path `path_in_repo`
    :param path_in_repo: Path of the file to compare, relative to repository root
    :param rev1: The Git revision to compare the on-disk worktree version to
    :param content: The contents to compare to, e.g. from current working tree
    :param context_lines: The number of lines to include before and after a change
    :return: Line numbers of lines changed between the revision and given content

    """
    old = git_get_content_at_revision(path_in_repo, rev1, root)
    edited_opcodes = diff_and_get_opcodes(old, content)
    multiline_string_ranges = get_multiline_string_ranges(content)
    return list(
        opcodes_to_edit_linenums(edited_opcodes, context_lines, multiline_string_ranges)
    )


@lru_cache(maxsize=1)
def _compare_revisions(
    root: Path, path_in_repo: Path, rev1: str, context_lines: int
) -> List[int]:
    """Get line numbers of lines changed between a given revision and the worktree

    Also includes `context_lines` number of extra lines before and after each
    modified line.

    The actual implementation is here instead of in
    `EditedLinenumsDiffer.compare_revisions` because `lru_cache` leaks memory when used
    on methods. See https://stackoverflow.com/q/33672412/15770

    :param root: Root directory for the relative path `path_in_repo`
    :param path_in_repo: Path of the file to compare, relative to repository root
    :param rev1: The Git revision to compare the on-disk worktree version to
    :param context_lines: The number of lines to include before and after a change
    :return: Line numbers of lines changed between the revision and given content

    """
    content = TextDocument.from_file(root / path_in_repo)
    linenums = _revision_vs_lines(root, path_in_repo, rev1, content, context_lines)
    logger.debug(
        "Edited line numbers in %s: %s",
        path_in_repo,
        " ".join(str(n) for n in linenums),
    )
    return linenums


@dataclass(frozen=True)
class EditedLinenumsDiffer:
    """Find out changed lines for a file between given Git revisions"""

    root: Path
    revrange: RevisionRange

    def compare_revisions(self, path_in_repo: Path, context_lines: int) -> List[int]:
        """Get line numbers of lines changed between a given revision and the worktree

        Also includes `context_lines` number of extra lines before and after each
        modified line.

        The actual implementation is in the module global `_compare_revisions` function
        because `lru_cache` leaks memory when used on methods.
        See https://stackoverflow.com/q/33672412/15770

        :param path_in_repo: Path of the file to compare, relative to repository root
        :param context_lines: The number of lines to include before and after a change
        :return: Line numbers of lines changed between the revision and given content

        """
        return _compare_revisions(
            self.root, path_in_repo, self.revrange.rev1, context_lines
        )

    def revision_vs_lines(
        self, path_in_repo: Path, content: TextDocument, context_lines: int
    ) -> List[int]:
        """Return changed line numbers between the given revision and given text content

        The revision range was provided when this `EditedLinenumsDiffer` object was
        created. Content for the given `path_in_repo` at `rev1` of that revision is
        taken from the Git repository, and the provided text content is compared against
        that historical version.

        The actual implementation is in the module global `_revision_vs_lines` function
        so this can be called from both as a method and the module global
        `_compare_revisions` function.

        :param path_in_repo: Path of the file to compare, relative to repository root
        :param content: The contents to compare to, e.g. from current working tree
        :param context_lines: The number of lines to include before and after a change
        :return: Line numbers of lines changed between the revision and given content

        """
        return _revision_vs_lines(
            self.root, path_in_repo, self.revrange.rev1, content, context_lines
        )
