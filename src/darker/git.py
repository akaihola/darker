"""Helpers for listing modified files and getting unmodified content from Git"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, run  # nosec
from typing import Iterable, List, Set

from darker.diff import opcodes_to_edit_linenums
from darker.multiline_strings import get_multiline_string_ranges
from darkgraylib.diff import diff_and_get_opcodes
from darkgraylib.git import (
    WORKTREE,
    RevisionRange,
    git_check_output_lines,
    git_get_content_at_revision,
    make_git_env,
)
from darkgraylib.utils import TextDocument

logger = logging.getLogger(__name__)


# Split a revision range into the "from" and "to" revisions and the dots in between.
# Handles these cases:
# <rev>..   <rev>..<rev>   ..<rev>
# <rev>...  <rev>...<rev>  ...<rev>


# A colon is an invalid character in tag/branch names. Use that in the special value for
# - denoting the working tree as one of the "revisions" in revision ranges
# - referring to the `PRE_COMMIT_FROM_REF` and `PRE_COMMIT_TO_REF` environment variables
#   for determining the revision range


def git_is_repository(path: Path) -> bool:
    """Return ``True`` if ``path`` is inside a Git working tree"""
    try:
        lines = git_check_output_lines(
            ["rev-parse", "--is-inside-work-tree"], path, exit_on_error=False
        )
        return lines[:1] == ["true"]
    except CalledProcessError as exc_info:
        if exc_info.returncode != 128 or not exc_info.stderr.startswith(
            "fatal: not a git repository"
        ):
            raise
        return False


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
    """Return ``True`` if the given path is an existing ``*.py`` file

    :param path: The path to inspect
    :return: ``False`` if the path doesn't exist or is not a ``.py`` file

    """
    return path.exists() and get_path_in_repo(path).suffix == ".py"


def _git_exists_in_revision(path: Path, rev2: str, git_cwd: Path) -> bool:
    """Return ``True`` if the given path exists in the given Git revision

    :param path: The path of the file or directory to check, either relative to current
                 working directory or absolute
    :param rev2: The Git revision to look at
    :param git_cwd: The working directory to use when invoking Git. This has to be
                    either the root of the working tree, or another directory inside it.
    :return: ``True`` if the file or directory exists at the revision, or ``False`` if
             it doesn't.

    """
    while not git_cwd.exists():
        # The working directory for running Git doesn't exist. Walk up the directory
        # tree until we find an existing directory. This is necessary because `git
        # cat-file` doesn't work if the current working directory doesn't exist.
        git_cwd = git_cwd.parent
    relative_path = (Path.cwd() / path).relative_to(git_cwd.resolve())
    # Surprise: On Windows, `git cat-file` doesn't work with backslash directory
    # separators in paths. We need to use Posix paths and forward slashes instead.
    # Surprise #2: `git cat-file` assumes paths are relative to the repository root.
    # We need to prepend `./` to paths relative to the working directory.
    cmd = ["git", "cat-file", "-e", f"{rev2}:./{relative_path.as_posix()}"]
    logger.debug("[%s]$ %s", git_cwd, " ".join(cmd))
    result = run(  # nosec
        cmd,
        cwd=str(git_cwd),
        check=False,
        stderr=DEVNULL,
        env=make_git_env(),
    )
    return result.returncode == 0


def get_missing_at_revision(paths: Iterable[Path], rev2: str, cwd: Path) -> Set[Path]:
    """Return paths missing in the given revision

    In case of ``WORKTREE``, just check if the files exist on the filesystem instead of
    asking Git.

    :param paths: Paths to check, relative to the current working directory or absolute
    :param rev2: The Git revision to look at, or ``WORKTREE`` for the working tree
    :param cwd: The working directory to use when invoking Git. This has to be either
                the root of the working tree, or another directory inside it.
    :return: The set of file or directory paths which are missing in the revision

    """
    if rev2 == WORKTREE:
        return {path for path in paths if not path.exists()}
    return {path for path in paths if not _git_exists_in_revision(path, rev2, cwd)}


def _git_diff_name_only(
    rev1: str, rev2: str, relative_paths: Iterable[Path], repo_root: Path
) -> Set[Path]:
    """Collect names of changed files between commits from Git

    :param rev1: The old commit to compare to
    :param rev2: The new commit to compare, or the string ``":WORKTREE:"`` to compare
                 current working tree to ``rev1``
    :param relative_paths: Relative paths from repository root to the files to compare
    :param repo_root: The Git repository root
    :return: Relative paths of changed files

    """
    diff_cmd = [
        "diff",
        "--name-only",
        "--relative",
        "--diff-filter=MA",
        rev1,
        # rev2 is inserted here if not WORKTREE
        "--",
        *{path.as_posix() for path in relative_paths},
    ]
    if rev2 != WORKTREE:
        diff_cmd.insert(diff_cmd.index("--"), rev2)
    lines = git_check_output_lines(diff_cmd, repo_root)
    return {Path(line) for line in lines}


def _git_ls_files_others(relative_paths: Iterable[Path], cwd: Path) -> Set[Path]:
    """Collect names of untracked non-excluded files from Git

    This will return those files in ``relative_paths`` which are untracked and not
    excluded by ``.gitignore`` or other Git's exclusion mechanisms.

    :param relative_paths: Relative paths from repository root to the files to consider
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
    lines = git_check_output_lines(ls_files_cmd, cwd)
    return {Path(line) for line in lines}


def git_get_modified_python_files(
    paths: Iterable[Path], revrange: RevisionRange, repo_root: Path
) -> Set[Path]:
    """Ask Git for modified and untracked ``*.py`` files

    - ``git diff --name-only --relative <rev> -- <path(s)>``
    - ``git ls-files --others --exclude-standard -- <path(s)>``

    :param paths: Files to diff, either relative to the current working dir or absolute
    :param revrange: Git revision range to compare
    :param repo_root: The Git repository root
    :return: File names relative to the Git repository root

    """
    repo_paths = [path.resolve().relative_to(repo_root) for path in paths]
    changed_paths = _git_diff_name_only(
        revrange.rev1, revrange.rev2, repo_paths, repo_root
    )
    if revrange.rev2 == WORKTREE:
        changed_paths.update(_git_ls_files_others(repo_paths, repo_root))
    return {path for path in changed_paths if should_reformat_file(repo_root / path)}


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
    # 2. diff the given revisions for the file
    edited_opcodes = diff_and_get_opcodes(old, content)
    multiline_string_ranges = list(get_multiline_string_ranges(content))
    # 3. extract line numbers in each edited to-file for changed lines
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
