"""Example content for `darker.tests.test_difflib`"""

from textwrap import dedent

ORIGINAL = dedent(
    '''\
    original first line
    original second line
    original third line
'''
)

CHANGED = dedent(
    '''\
    original first line
    changed second line
    original third line
'''
)

BLANK_SEP_ORIGINAL = dedent(
    """\
    original first line

    original third line

    original fifth line
    """
)

BLANK_SEP_CHANGED = dedent(
    """\
    changed first line

    original third line

    changed fifth line
    """
)

BLANK_SEP_SANDWICH_ORIGINAL = dedent(
    """\
    original first line

    original third line

    original fifth line
    """
)

BLANK_SEP_SANDWICH_CHANGED = dedent(
    """\
    changed first line

    original third line

    changed fifth line
    """
)


BLANK_SEP_ORIGINAL = dedent(
    """\
    original first line

    original third line

    original fifth line
    """
)

BLANK_SEP_CHANGED = dedent(
    """\
    changed first line

    changed third line

    changed fifth line
    """
)
