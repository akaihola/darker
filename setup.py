import re

from setuptools import setup

CONTRIBUTORS_RE = re.compile(r"""\nThanks goes .*\nThis project follows """, re.DOTALL)


def make_pypi_compliant_readme() -> str:
    """Remove raw HTML from ``README.rst`` before packaging

    The contributors table should only be shown on GitHub. It must be removed before
    being displayed on PyPI. The simplest way to do this is to simply match and strip it
    when creating a distribution archive.

    This function reads the contents of ``README.rst``, replaces the row HTML section
    with a plain-text link to the README on GitHub and returns the resulting string.

    :return: The contents of a PyPI compliant ``README.rst``

    """
    with open("README.rst", encoding="utf-8") as fp:
        original_readme = fp.read()
    modified_readme = CONTRIBUTORS_RE.sub(
        "\nSee README.rst_ for the list of contributors.\n\nThis project follows ",
        original_readme,
    )
    if modified_readme == original_readme:
        raise RuntimeError(
            f"The contributors table couldn't be found in README.rst using the pattern "
            f"'{CONTRIBUTORS_RE.pattern}'"
        )
    return modified_readme


setup(long_description=make_pypi_compliant_readme())
