import re
from typing import Pattern

from setuptools import setup

SIDEBAR_RE = re.compile(r"\+---.*:alt: Support", re.DOTALL)
CONTRIBUTORS_RE = re.compile(r"""\nThanks goes .*\nThis project follows """, re.DOTALL)


def replace(name: str, regex: Pattern[str], replacement: str, content: str) -> str:
    """Replace/remove a section from the package description, based on a regex

    Raise an exception if the regular expression doesn't match anything.

    """
    modified_content = regex.sub(replacement, content)
    if modified_content != content:
        return modified_content
    raise RuntimeError(
        f"The {name} wasn't found in README.rst using the pattern '{regex.pattern}'"
    )


def make_pypi_compliant_readme() -> str:
    """Remove raw HTML from ``README.rst`` before packaging

    The sidebar and the contributors table should only be shown on GitHub. They must be
    removed before being displayed on PyPI. The simplest way to do this is to simply
    match and strip it when creating a distribution archive.

    This function reads the contents of ``README.rst``, removes the sidebar, replaces
    the contributors raw HTML section with a plain-text link to the README on GitHub and
    returns the resulting string.

    :return: The contents of a PyPI compliant ``README.rst``

    """
    with open("README.rst", encoding="utf-8") as fp:
        original_readme = fp.read()
    no_sidebar_readme = replace("sidebar", SIDEBAR_RE, "", original_readme)
    return replace(
        "contributors table",
        CONTRIBUTORS_RE,
        "\nSee README.rst_ for the list of contributors.\n\nThis project follows ",
        no_sidebar_readme,
    )


setup(long_description=make_pypi_compliant_readme())
