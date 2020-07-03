import pytest

from darker.verification import NotEquivalentError, verify_ast_unchanged


@pytest.mark.parametrize(
    "src_content, dst_content, expect",
    [
        ("if True: pass\n", "if False: pass\n", AssertionError),
        ("if True: pass\n", "if True:\n    pass\n", None),
    ],
)
def test_verify_ast_unchanged(src_content, dst_content, expect):
    black_chunks = [(1, ["black"], ["chunks"])]
    edited_linenums = [1, 2]
    try:
        verify_ast_unchanged(src_content, dst_content, black_chunks, edited_linenums)
    except NotEquivalentError:
        assert expect is AssertionError
    else:
        assert expect is None
