#!/usr/bin/env python

"""Helper script for bumping the version number

None of the existing tools (like `bump2version`) worked for this project out of the box
without modifications. Hence this script.

Usage::

    python release_tools/bump_version.py {major|minor|patch}

"""

import re
import sys
from datetime import date
from pathlib import Path
from typing import Tuple

import click
from packaging.version import Version, parse

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


VERSION_PY_PATH = "src/darker/version.py"

PATTERNS = {
    VERSION_PY_PATH: {r"^__version__ *= *\"{version}\""},
    "action.yml": {
        r'^    description: \'Python Version specifier \(PEP440\) - e\.g\. "{version}"',
        r'^    default: "{version}"',
        r"^      uses: akaihola/darker/.github/actions/commit-range@{version}",
    },
    "README.rst": {
        r"^           rev: {version}",
        r"^       rev: {version}",
        r"^         - uses: akaihola/darker@{version}",
        r'^             version: "{version}"',
    },
    ".github/ISSUE_TEMPLATE/bug_report.md": {
        r"^ - Darker version \[e\.g\. {version}\]"
    },
}

SEARCH_CURRENT_VERSION = re.compile(
    next(iter(PATTERNS[VERSION_PY_PATH])).format(version=r"([\d\.a-z]+)"),
    flags=re.MULTILINE,
).search


@click.command()
@click.option("-n", "--dry-run", is_flag=True, default=False)
@click.option("-M", "--major", "increment_major", is_flag=True, default=False)
@click.option("-m", "--minor", "increment_minor", is_flag=True, default=False)
def bump_version(dry_run: bool, increment_major: bool, increment_minor: bool) -> None:
    """Bump the version number"""
    current_version = get_current_version()
    current_version_pattern = re.escape(str(current_version))
    next_version = get_next_version(current_version, increment_major, increment_minor)
    for path_str, pattern_templates in PATTERNS.items():
        path = Path(path_str)
        content = path.read_text(encoding="utf-8")
        for pattern_template in pattern_templates:
            (version_number_start, version_number_end) = get_version_number_span(
                pattern_template, current_version_pattern, content
            )
            before = content[:version_number_start]
            after = content[version_number_end:]
            content = f"{before}{next_version}{after}"
        if dry_run:
            print(f"\n######## {path_str} ########\n")
            print(content)
    patch_changelog(next_version, dry_run)


def get_current_version() -> Version:
    version_py = Path("src/darker/version.py").read_text(encoding="utf-8")
    current_version = SEARCH_CURRENT_VERSION(version_py).group(1)
    return parse(current_version)


def get_next_version(
    current_version: Version, increment_major: bool, increment_minor: bool
) -> Version:
    major, minor, micro = current_version.release
    if increment_major:
        return f"{major + 1}.0.0"
    if increment_minor:
        return f"{major}.{minor + 1}.0"
    if current_version.is_devrelease or current_version.is_prerelease:
        return str(current_version)
    return f"{major}.{minor}.{micro + 1}"


def get_version_number_span(
    pattern_template: str, current_version_pattern: str, content: str
) -> Tuple[int, int]:
    pattern = pattern_template.format(version=f"({current_version_pattern})")
    match = re.search(pattern, content, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Can't find r'{pattern}' in `{path_str}`")
    _, version_number_span = match.regs
    return version_number_span


def patch_changelog(next_version: str, dry_run: bool) -> None:
    content = Path("CHANGES.rst").read_text(encoding="utf-8")
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


if __name__ == "__main__":
    bump_version()
