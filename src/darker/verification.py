"""Verification for unchanged AST before and after reformatting"""

from typing import Dict, List

from black import assert_equivalent, parse_ast, stringify_ast

from darker.utils import DiffChunk, TextDocument, debug_dump


class NotEquivalentError(Exception):
    pass


class BinarySearch:
    """Effectively search the first index for which a condition is ``True``

    Example usage to find first number between 0 and 100 whose square is larger than
    1000:

    >>> s = BinarySearch(0, 100)
    >>> while not s.found:
    ...     s.respond(s.get_next() ** 2 > 1000)
    >>> assert s.result == 32

    """

    def __init__(self, low: int, high: int):
        self.low = self.mid = low
        self.high = high

    def get_next(self) -> int:
        """Get the next integer index to try"""
        return self.mid

    def respond(self, value: bool) -> None:
        """Provide a ``False`` or ``True`` answer for the current integer index"""
        if value:
            self.high = self.mid
        else:
            self.low = self.mid + 1
        self.mid = (self.low + self.high) // 2

    @property
    def found(self) -> bool:
        """Return ``True`` if the lowest ``True`` response index has been found"""
        return self.low >= self.high

    @property
    def result(self) -> int:
        """Return the lowest index with a ``True`` response"""
        if not self.found:
            raise RuntimeError(
                "Trying to get binary search result before search has been exhausted"
            )
        return self.high


def verify_ast_unchanged(
    edited_to_file: TextDocument,
    reformatted: TextDocument,
    black_chunks: List[DiffChunk],
    edited_linenums: List[int],
) -> None:
    """Verify that source code parses to the same AST before and after reformat"""
    try:
        assert_equivalent(edited_to_file.string, reformatted.string)
    except AssertionError as exc_info:
        debug_dump(black_chunks, edited_linenums)
        raise NotEquivalentError(str(exc_info))


class ASTVerifier:  # pylint: disable=too-few-public-methods
    """Verify if reformatted TextDocument is AST-equivalent to baseline

    Keeps in-memory data about previous comparisons to improve performance.

    """

    def __init__(self, baseline: TextDocument) -> None:
        self._baseline_ast_str = self._to_ast_str(baseline)
        self._comparisons: Dict[str, bool] = {baseline.string: True}

    @staticmethod
    def _to_ast_str(document: TextDocument) -> str:
        return "\n".join(stringify_ast(parse_ast(document.string)))

    def is_equivalent_to_baseline(self, document: TextDocument) -> bool:
        """Returns true if document is AST-equivalent to baseline"""
        if document.string in self._comparisons:
            return self._comparisons[document.string]

        try:
            document_ast_str = self._to_ast_str(document)
        except SyntaxError:
            comparison = False
        else:
            comparison = self._baseline_ast_str == document_ast_str

        self._comparisons[document.string] = comparison
        return self._comparisons[document.string]
