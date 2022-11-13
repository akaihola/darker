"""Some tests for `difflib` to ensure and illustrate its logic"""

from difflib import SequenceMatcher

from darker.tests.git_diff_example_output import (
    BLANK_SEP_CHANGED,
    BLANK_SEP_ORIGINAL,
    BLANK_SEP_SANDWICH_CHANGED,
    BLANK_SEP_SANDWICH_ORIGINAL,
    CHANGED,
    ORIGINAL,
)


def test_sequencematcher():
    """``SequenceMatcher`` detects a single changed line in between correctly"""
    matcher = SequenceMatcher(
        None, ORIGINAL.splitlines(), CHANGED.splitlines(), autojunk=False
    )
    assert matcher.get_opcodes() == [
        ("equal", 0, 1, 0, 1),
        ("replace", 1, 2, 1, 2),
        ("equal", 2, 3, 2, 3),
    ]


def test_sequencematcher_blank_separated_changes_unchanged_sandwiched():
    """``SequenceMatcher`` detects blank line delimited unchanged region correctly"""
    matcher = SequenceMatcher(
        None,
        BLANK_SEP_SANDWICH_ORIGINAL.splitlines(),
        BLANK_SEP_SANDWICH_CHANGED.splitlines(),
        autojunk=False,
    )
    assert matcher.get_opcodes() == [
        ("replace", 0, 1, 0, 1),
        ("equal", 1, 4, 1, 4),
        ("replace", 4, 5, 4, 5),
    ]


def test_sequencematcher_blank_separated_changes():
    """``SequenceMatcher`` detects blank line delimited changes correctly"""
    matcher = SequenceMatcher(
        None,
        BLANK_SEP_ORIGINAL.splitlines(),
        BLANK_SEP_CHANGED.splitlines(),
        autojunk=False,
    )
    assert matcher.get_opcodes() == [
        ("replace", 0, 1, 0, 1),
        ("equal", 1, 2, 1, 2),
        ("replace", 2, 3, 2, 3),
        ("equal", 3, 4, 3, 4),
        ("replace", 4, 5, 4, 5),
    ]
