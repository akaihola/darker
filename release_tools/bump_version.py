#!/usr/bin/env python

"""Helper script for bumping the version number

None of the existing tools (like `bump2version`) worked for this project out of the box
without modifications. Hence this script.

Usage::

    python release_tools/bump_version.py {--major|--minor} [--dry-run]

Increments the patch version by default unless `--major` or `--minor` is specified.
With `--dry-run` will print out modified files on the terminal or crash with an
exception and a non-zero return value.

`.github/workflows/test-bump-version.yml` runs this with `--dry-run` to ensure all
regular expressions match content of the files to modify.

"""

import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Match, Optional, Tuple
from warnings import warn

import click
import requests
from packaging.version import Version

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


VERSION_PY_PATH = "src/darker/version.py"


# Below are the regular expression patterns for finding and replacing version and
# milestone numbers in files. Keys are file paths relative to the repository root.
# Values are sets of regular expression pattern strings which contain a magic
# `{OLD->NEW}` expression. For matching text, that expression will be turned into a
# regular expression string which matches the expected version or milestone string in
# the current content of a file. For replacing those matches with updated information,
# `NEW` specifies which kind of a version or milestone number should be used as the
# replacement.
#
# For example, if the current version ("old_version") was `1.0.1` and bumping the minor
# version was requested, the entry
#
#   `"README.rst": {r"next version: {old_version->new_version}"}`
#
# would find
#
#   `r"next version: (1\.0\.1)"`
#
# in `README.rst` and replace the text matched by the capture group with "1.1".

PATTERNS = {
    VERSION_PY_PATH: {r"^__version__ *= *\"{old_version->new_version}\""},
    "action.yml": {
        (
            r"^    description: \'Version of Darker to use, e\.g\."
            r' "~={old_version->new_version}"'
        ),
        (
            r"^    description: \'Version of Darker to use, e\.g\."
            r' "~=.*?", "{old_version->new_version}"'
        ),
        r'^    default: "~={old_version->new_version}"',
        (
            r"^      uses: akaihola/darker/.github/actions/commit-range"
            r"@{old_version->new_version}"
        ),
    },
    "README.rst": {
        r"^  pip install --upgrade darker~={old_version->new_version}",
        r"^  conda install -c conda-forge darker~={old_version->new_version} isort",
        r"^           rev: {old_version->new_version}",
        r"^       rev: {old_version->new_version}",
        r"^        rev: {old_version->new_version}",
        r"^         - uses: akaihola/darker@{old_version->new_version}",
        r'^             version: "~={old_version->new_version}"',
        r"label=release%20{any_version->next_version}",
        (
            r"^\.\. \|next-milestone\| image::"
            r" https://img\.shields\.io/github/milestones/progress/akaihola/darker/"
            r"{any_milestone->next_milestone}"
        ),
        (
            r"^\.\. _next-milestone:"
            r" https://github\.com/akaihola/darker/milestone/"
            r"{any_milestone->next_milestone}"
        ),
    },
    ".github/ISSUE_TEMPLATE/bug_report.md": {
        r"^ - Darker version \[e\.g\. {old_version->new_version}\]"
    },
}


@click.command()
@click.option("-n", "--dry-run", is_flag=True, default=False)
@click.option("-M", "--major", "increment_major", is_flag=True, default=False)
@click.option("-m", "--minor", "increment_minor", is_flag=True, default=False)
@click.option("--token")
def bump_version(  # pylint: disable=too-many-locals
    dry_run: bool, increment_major: bool, increment_minor: bool, token: Optional[str]
) -> None:
    """Bump the version number"""
    (patterns, replacements, new_version) = get_replacements(
        increment_major,
        increment_minor,
        token,
        dry_run,
    )
    for path_str, pattern_templates in PATTERNS.items():
        path = Path(path_str)
        content = path.read_text(encoding="utf-8")
        for pattern_template in pattern_templates:
            # example: pattern_template == r"darker/{any_milestone->next_milestone}"
            template_match = CAPTURE_RE.search(pattern_template)
            if not template_match:
                raise NoMatch("Can't find `{CAPTURE_RE}` in `{pattern_template}`")
            current_pattern, replacement = lookup_patterns(
                template_match, patterns, replacements
            )
            # example: current_pattern == "14", replacement == "15"
            pattern = replace_span(
                template_match.span(), f"({current_pattern})", pattern_template
            )
            # example: pattern = r"darker/(14)"
            content = replace_group_1(pattern, replacement, content, path=path_str)
        if dry_run:
            print(f"\n######## {path_str} ########\n")
            print(content)
        else:
            path.write_text(content, encoding="utf-8")
    patch_changelog(new_version, dry_run)


class PatternDict(TypedDict):
    r"""Patterns for old and new version and the milestone number for the new version

    Example:

    >>> patterns: PatternDict = {
    ...     "any_version": r"\d+(?:\.\d+)*",
    ...     "old_version": r"1\.0",
    ...     "new_version": r"1\.1",
    ...     "any_milestone": r"\d+",
    ... }

    """

    any_version: str
    old_version: str
    new_version: str
    any_milestone: str


class ReplacementDict(TypedDict):
    """Replacement strings of new and next version and milestone num for next version

    Example:

    >>> replacement: ReplacementDict = {
    ...     "new_version": "1.1",
    ...     "next_version": "2.0",
    ...     "next_milestone": "23",
    ... }

    """

    new_version: str
    next_version: str
    next_milestone: str


if sys.version_info >= (3, 9):
    PATTERN_NAMES = PatternDict.__required_keys__  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa
    REPLACEMENT_NAMES = ReplacementDict.__required_keys__  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa
else:
    PATTERN_NAMES = PatternDict.__annotations__  # pylint: disable=no-member
    REPLACEMENT_NAMES = ReplacementDict.__annotations__  # pylint: disable=no-member


def get_replacements(
    increment_major: bool,
    increment_minor: bool,
    token: Optional[str],
    dry_run: bool,
) -> Tuple[PatternDict, ReplacementDict, Version]:
    """Return search patterns and replacements for version numbers and milestones

    Gets the current version from `version.py` and the milestone numbers from the GitHub
    API. Based on these, builds the search patterns for the old and new version numbers
    and the milestone number of the new version, as well as replacement strings for the
    new and next version numbers and the milestone number of the next version.

    :param increment_major: `True` to increment the major version number
    :param increment_minor: `True` to increment the minor version number
    :param token: The GitHub access token to use, or `None` to use none
    :param dry_run: `True` if running in dry-run mode
    :return: Patterns, replacements and the new version number

    """
    old_version = get_current_version()
    new_version = get_next_version(old_version, increment_major, increment_minor)
    milestone_numbers = get_milestone_numbers(token)
    next_version = get_next_milestone_version(new_version, milestone_numbers, dry_run)
    if dry_run:
        milestone_numbers.setdefault(next_version, "MISSING_MILESTONE")
    patterns: PatternDict = {
        "any_version": r"\d+(?:\.\d+)*",
        "old_version": re.escape(str(old_version)),
        "new_version": re.escape(str(new_version)),
        "any_milestone": r"\d+",
    }
    replacements: ReplacementDict = {
        "new_version": str(new_version),
        "next_version": str(next_version),
        "next_milestone": milestone_numbers[next_version],
    }
    return patterns, replacements, new_version


def get_current_version() -> Version:
    """Find the current version number from `version.py`

    :return: The current version number
    :raises NoMatch: Raised if `version.py` doesn't match the expected format

    """
    version_py = Path(VERSION_PY_PATH).read_text(encoding="utf-8")
    match = CURRENT_VERSION_RE.search(version_py)
    if not match:
        raise NoMatch("Can't find `{SEARCH_CURRENT_VERSION}` in `{VERSION_PY_PATH}`")
    current_version = match.group(1)
    return Version(current_version)


CURRENT_VERSION_RE = re.compile(
    next(iter(PATTERNS[VERSION_PY_PATH])).format(
        **{"old_version->new_version": r"([\d\.a-z]+)"}
    ),
    flags=re.MULTILINE,
)


class NoMatch(Exception):
    """Raised if pattern couldn't be found in the content"""


def get_next_version(
    current_version: Version, increment_major: bool, increment_minor: bool
) -> Version:
    """Return the next version number by incrementing elements as specified

    :param current_version: The version number to increment
    :param increment_major: `True` to increment the major version number
    :param increment_minor: `True` to increment the minor version number
    :return: The new version number

    """
    major, minor, micro = current_version.release
    if increment_major:
        return Version(f"{major + 1}.0.0")
    if increment_minor:
        return Version(f"{major}.{minor + 1}.0")
    if current_version.is_devrelease or current_version.is_prerelease:
        return current_version
    return Version(f"{major}.{minor}.{micro + 1}")


def get_milestone_numbers(token: Optional[str]) -> Dict[Version, str]:
    """Fetch milestone names and numbers from the GitHub API

    :param token: The GitHub access token to use, or `None` to use none
    :return: Milestone names as version numbers, and corresponding milestone numbers
    :raises TypeError: Raised on unexpected JSON response

    """
    milestones = requests.get(
        "https://api.github.com/repos/akaihola/darker/milestones",
        headers={"Authorization": f"Bearer {token}"} if token else {},
        timeout=10,
    ).json()
    if not isinstance(milestones, list):
        raise TypeError(f"Expected a JSON list from GitHub API, got {milestones}")
    return {Version(m["title"]): str(m["number"]) for m in milestones}


CAPTURE_RE = re.compile(r"\{(\w+)->(\w+)\}")


def lookup_patterns(
    template_match: Match[str], patterns: PatternDict, replacements: ReplacementDict
) -> Tuple[str, str]:
    r"""Look up the search pattern and replacement for the given search->replace names

    `patterns` must contain regular expressions for finding the old version, the new
    version, and the milestone number corresponding to the new version.

    `replacements` must contain strings for the new version number, the next version
    number after that, and the milestone number corresponding to the next version
    number.

    This function accepts a regular expression match object for a `{OLD->NEW}` string,
    finds the pattern corresponding to the `OLD` string from `patterns`, finds the
    replacement corresponding to the `NEW` string form `replacements`, and returns them
    both.

    Example:

    >>> patterns = {"new_version": r"1\.1"}
    >>> replacements = {"next_version": "2.0"}
    >>> template_match = re.match(r"(.*)->(.*)", "new_version->next_version")
    >>> lookup_patterns(template_match, patterns, replacements)
    ('1\\.1', '2.0')

    :param template_match: The match object with pattern name and replacement name as
                           capture groups
    :param patterns: The regular expression patterns corresponding to pattern names
    :param replacements: The replacement strings corresponding to replacement names
    :raises RuntimeError: Raised if pattern or replacement names are unknown
    :return: The matching regular expression pattern and replacement string

    """
    current_pattern_name, replacement_name = template_match.groups()
    # example: template_match.groups() == ("any_milestone", "next_milestone")
    if current_pattern_name not in PATTERN_NAMES:
        raise RuntimeError(
            f"Pattern name {current_pattern_name!r} for a current value is"
            f" unknown. Valid pattern names: {PATTERN_NAMES}"
        )
    current_pattern = patterns[current_pattern_name]  # type: ignore[literal-required]
    # example: current_pattern == "14"
    if replacement_name not in REPLACEMENT_NAMES:
        raise RuntimeError(
            f"Replacement name {replacement_name!r} is unknown. Valid"
            f" replacement names: {REPLACEMENT_NAMES}"
        )
    replacement = replacements[replacement_name]  # type: ignore[literal-required]
    # example: replacement == "15"
    return current_pattern, replacement


def get_next_milestone_version(
    version: Version, milestone_numbers: Dict[Version, str], dry_run: bool
) -> Version:
    """Get the next larger version number found among milestone names

    :param version: The version number to search a larger one for
    :param milestone_numbers: Milestone names and numbers from the GitHub API
    :param dry_run: `True` if running in dry-run mode
    :return: The next larger version number found
    :raises RuntimeError: Raised if no larger version number could be found

    """
    for milestone_version in sorted(milestone_numbers):
        if milestone_version > version:
            return milestone_version
    message = f"No milestone exists for a version later than {version}"
    if not dry_run:
        raise RuntimeError(message)
    warn(message)
    return Version(f"{version.major}.{version.minor}.{version.micro + 1}")


def replace_span(span: Tuple[int, int], replacement: str, content: str) -> str:
    """Replace given span in a string with the desired replacement string

    :param span: The span to replace
    :param replacement: The string to use as the replacement
    :param content: The content to replace the span in
    :return: The result after the replacement

    """
    start, end = span
    before = content[:start]
    after = content[end:]
    return f"{before}{replacement}{after}"


def replace_group_1(pattern: str, replacement: str, content: str, path: str) -> str:
    """Replace the first capture group of a regex pattern with the given string

    Raises an exception if the regular expression doesn't match.

    :param pattern: The regular expression pattern with at least one capture group
    :param replacement: The string to replace the capture group with
    :param content: The content to search and do the replacement in
    :param path: The originating file path for the content. Only used in the exception
                 message if the regular expression doesn't find any matches.
    :raises NoMatch: Raised if the regular expression doesn't find any matches
    :return: The resulting content after the replacement

    """
    match = re.search(pattern, content, flags=re.MULTILINE)
    if not match:
        raise NoMatch(f"Can't find `{pattern}` in `{path}`")
    return replace_span(match.span(1), replacement, content)


def patch_changelog(next_version: Version, dry_run: bool) -> None:
    """Insert the new version and create a new unreleased section in the change log

    :param next_version: The next version after the new version
    :param dry_run: `True` to just print the result

    """
    path = Path("CHANGES.rst")
    content = path.read_text(encoding="utf-8")
    before_unreleased = "These features will be included in the next release:\n\n"
    insert_point = content.index(before_unreleased) + len(before_unreleased)
    before = content[:insert_point]
    after = content[insert_point:]
    title = f"{next_version}_ - {date.today()}"
    new_content = (
        f"{before}"
        "Added\n"
        "-----\n\n"
        "Fixed\n"
        "-----\n\n\n"
        f"{title}\n"
        f"{len(title) * '='}\n\n"
        f"{after}"
    )
    if dry_run:
        print("######## CHANGES.rst ########")
        print(new_content[:200])
    else:
        path.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    bump_version()  # pylint: disable=no-value-for-parameter
