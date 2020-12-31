"""Unit tests for :mod:`darker.verification`"""


from typing import List

import pytest

from darker.utils import DiffChunk, TextDocument
from darker.verification import NotEquivalentError, verify_ast_unchanged


@pytest.mark.parametrize(
    "src_content, dst_content, expect",
    [
        ("if True: pass", ["if False: pass"], AssertionError),
        ("if True: pass", ["if True:", "    pass"], None),
    ],
)
def test_verify_ast_unchanged(src_content, dst_content, expect):
    black_chunks: List[DiffChunk] = [(1, ("black",), ("chunks",))]
    edited_linenums = [1, 2]
    try:
        verify_ast_unchanged(
            TextDocument.from_lines([src_content]),
            TextDocument.from_lines(dst_content),
            black_chunks,
            edited_linenums,
        )
    except NotEquivalentError:
        assert expect is AssertionError
    else:
        assert expect is None
