"""Verification for unchanged AST before and after reformatting"""

from typing import List, Tuple

from black import assert_equivalent

from darker.utils import debug_dump, joinlines


class NotEquivalentError(Exception):
    pass


def verify_ast_unchanged(
    edited_to_file_str: str,
    reformatted_str: str,
    black_chunks: List[Tuple[int, List[str], List[str]]],
    edited_linenums: List[int],
) -> None:
    """Verify that source code parses to the same AST before and after reformat"""
    try:
        assert_equivalent(edited_to_file_str, reformatted_str)
    except AssertionError as exc_info:
        debug_dump(black_chunks, edited_to_file_str, reformatted_str, edited_linenums)
        raise NotEquivalentError(str(exc_info))
