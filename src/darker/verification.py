"""Verification for unchanged AST before and after reformatting"""

from typing import List, Tuple

from black import assert_equivalent

from darker.utils import _debug_dump, joinlines


def verify_ast_unchanged(
    edited_to_file_lines: List[str],
    reformatted_str: str,
    black_chunks: List[Tuple[int, List[str], List[str]]],
    edited_linenums: List[int],
):
    """Verify that source code parses to the same AST before and after reformat"""
    edited_to_file_str = joinlines(edited_to_file_lines)
    try:
        assert_equivalent(edited_to_file_str, reformatted_str)
    except AssertionError:
        _debug_dump(black_chunks, edited_to_file_str, reformatted_str, edited_linenums)
        raise
