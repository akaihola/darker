"""Unit tests for :mod:`darker.verification`"""

# pylint: disable=use-dict-literal

import pytest

from darker.verification import ASTVerifier, BinarySearch
from darkgraylib.utils import TextDocument


def test_ast_verifier_is_equivalent():
    """``darker.verification.ASTVerifier.is_equivalent_to_baseline``"""
    verifier = ASTVerifier(baseline=TextDocument.from_lines(["if True: pass"]))
    assert verifier.is_equivalent_to_baseline(
        TextDocument.from_lines(["if True:", "    pass"])
    )
    assert not verifier.is_equivalent_to_baseline(
        TextDocument.from_lines(["if False: pass"])
    )
    assert not verifier.is_equivalent_to_baseline(
        TextDocument.from_lines(["if False:"])
    )


def test_binary_search_premature_result():
    """``darker.verification.BinarySearch``"""
    with pytest.raises(RuntimeError):

        _ = BinarySearch(0, 5).result


def test_binary_search():
    """``darker.verification.BinarySearch``"""
    search = BinarySearch(0, 5)
    tries = []
    while not search.found:
        tries.append(search.get_next())

        search.respond(tries[-1] > 2)
    assert search.result == 3
    assert tries == [0, 3, 2]


@pytest.mark.parametrize("i", range(50))
def test_binary_search_in_50(i):
    """Simple 'fuzzy test' for BinarySearch"""
    search = BinarySearch(0, 50)
    while not search.found:
        search.respond(search.get_next() >= i)
    assert search.result == i
