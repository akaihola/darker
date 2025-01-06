"""Verification for unchanged AST before and after reformatting"""

from __future__ import annotations

import ast
import sys
import warnings
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from darkgraylib.utils import TextDocument


class NotEquivalentError(Exception):
    """Exception to raise if two ASTs being compared are not equivalent"""


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


def parse_ast(src: str) -> ast.AST:
    """Parse source code with fallback for type comments.

    This function has been adapted from Black 24.10.0.

    """
    filename = "<unknown>"
    versions = [(3, minor) for minor in range(5, sys.version_info[1] + 1)]

    first_error = ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        warnings.simplefilter("ignore", DeprecationWarning)
        # Try with type comments first
        for version in reversed(versions):
            try:
                return ast.parse(
                    src, filename, feature_version=version, type_comments=True
                )
            except SyntaxError as e:  # noqa: PERF203
                if not first_error:
                    first_error = str(e)

        # Fallback without type comments
        for version in reversed(versions):
            try:
                return ast.parse(
                    src, filename, feature_version=version, type_comments=False
                )
            except SyntaxError:  # noqa: PERF203
                continue

    raise SyntaxError(first_error)


def _normalize(lineend: str, value: str) -> str:
    """Strip any leading and trailing space from each line.

    This function has been adapted from Black 24.10.0.

    """
    stripped: list[str] = [i.strip() for i in value.splitlines()]
    normalized = lineend.join(stripped)
    # ...and remove any blank lines at the beginning and end of
    # the whole string
    return normalized.strip()


def stringify_ast(node: ast.AST) -> Iterator[str]:
    """Generate strings to compare ASTs by content using a simple visitor.

    This function has been adapted from Black 24.10.0.

    """
    return _stringify_ast(node, [])


def _stringify_ast_with_new_parent(
    node: ast.AST, parent_stack: list[ast.AST], new_parent: ast.AST
) -> Iterator[str]:
    """Generate strings to compare, recurse with a new parent.

    This function has been adapted from Black 24.10.0.

    """
    parent_stack.append(new_parent)
    yield from _stringify_ast(node, parent_stack)
    parent_stack.pop()


def _stringify_ast(node: ast.AST, parent_stack: list[ast.AST]) -> Iterator[str]:
    """Generate strings to compare ASTs by content.

    This function has been adapted from Black 24.10.0.

    """
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.kind == "u"
    ):
        # It's a quirk of history that we strip the u prefix over here. We used to
        # rewrite the AST nodes for Python version compatibility and we never copied
        # over the kind
        node.kind = None

    yield f"{'    ' * len(parent_stack)}{node.__class__.__name__}("

    for field in sorted(node._fields):
        # TypeIgnore has only one field 'lineno' which breaks this comparison
        if isinstance(node, ast.TypeIgnore):
            break

        try:
            value: object = getattr(node, field)
        except AttributeError:
            continue

        yield f"{'    ' * (len(parent_stack) + 1)}{field}="

        if isinstance(value, list):
            for item in value:
                yield from _stringify_list_item(field, item, node, parent_stack)

        elif isinstance(value, ast.AST):
            yield from _stringify_ast_with_new_parent(value, parent_stack, node)

        else:
            normalized: object
            if (
                isinstance(node, ast.Constant)
                and field == "value"
                and isinstance(value, str)
                and len(parent_stack) >= 2
                # Any standalone string, ideally this would
                # exactly match black.nodes.is_docstring
                and isinstance(parent_stack[-1], ast.Expr)
            ):
                # Constant strings may be indented across newlines, if they are
                # docstrings; fold spaces after newlines when comparing. Similarly,
                # trailing and leading space may be removed.
                normalized = _normalize("\n", value)
            elif field == "type_comment" and isinstance(value, str):
                # Trailing whitespace in type comments is removed.
                normalized = value.rstrip()
            else:
                normalized = value
            yield (
                f"{'    ' * (len(parent_stack) + 1)}{normalized!r},  #"
                f" {value.__class__.__name__}"
            )

    yield f"{'    ' * len(parent_stack)})  # /{node.__class__.__name__}"


def _stringify_list_item(
    field: str, item: ast.AST, node: ast.AST, parent_stack: list[ast.AST]
) -> Iterator[str]:
    """Generate string for an AST list item.

    This function has been adapted from Black 24.10.0.

    """
    # Ignore nested tuples within del statements, because we may insert
    # parentheses and they change the AST.
    if (
        field == "targets"
        and isinstance(node, ast.Delete)
        and isinstance(item, ast.Tuple)
    ):
        for elt in item.elts:
            yield from _stringify_ast_with_new_parent(elt, parent_stack, node)

    elif isinstance(item, ast.AST):
        yield from _stringify_ast_with_new_parent(item, parent_stack, node)


class ASTVerifier:  # pylint: disable=too-few-public-methods
    """Verify if reformatted TextDocument is AST-equivalent to baseline

    Keeps in-memory data about previous comparisons to improve performance.

    """

    def __init__(self, baseline: TextDocument) -> None:
        self._baseline_ast_str = self._to_ast_str(baseline)
        self._comparisons: dict[str, bool] = {baseline.string: True}

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
