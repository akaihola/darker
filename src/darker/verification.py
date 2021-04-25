"""Verification for unchanged AST before and after reformatting"""

from typing import List

from black import assert_equivalent

from darker.utils import DiffChunk, TextDocument, debug_dump


class NotEquivalentError(Exception):
    pass


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
