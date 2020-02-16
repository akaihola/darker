from difflib import SequenceMatcher

from darker.tests.example_3_lines import CHANGED, ORIGINAL


def test_sequencematcher():
    s = SequenceMatcher(None, ORIGINAL.splitlines(), CHANGED.splitlines())
    assert s.get_opcodes() == [
        ("equal", 0, 1, 0, 1),
        ("replace", 1, 2, 1, 2),
        ("equal", 2, 3, 2, 3),
    ]
