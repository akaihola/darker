"""Unit tests for `darker.diff`"""

# pylint: disable=use-dict-literal

from itertools import chain
from typing import List, Literal, Tuple

import pytest

from darker.diff import opcodes_to_chunks, opcodes_to_edit_linenums
from darkgraylib.testtools.diff_helpers import (
    EXPECT_OPCODES,
    FUNCTIONS2_PY,
    FUNCTIONS2_PY_REFORMATTED,
)
from darkgraylib.utils import TextDocument


def test_opcodes_to_chunks():
    """``opcode_to_chunks()`` chucks opcodes correctly"""
    src = TextDocument.from_str(FUNCTIONS2_PY)
    dst = TextDocument.from_str(FUNCTIONS2_PY_REFORMATTED)

    chunks = list(opcodes_to_chunks(EXPECT_OPCODES, src, dst))

    assert chunks == [
        (1, ("def f(",), ("def f(",)),
        (2, ("  a,", "  **kwargs,"), ("    a,", "    **kwargs,")),
        (
            4,
            (") -> A:", "    with cache_dir():", "        if something:"),
            (") -> A:", "    with cache_dir():", "        if something:"),
        ),
        (
            7,
            (
                "            result = (",
                "                CliRunner().invoke(black.main, [str(src1), str(src2), "
                '"--diff", "--check"])',
            ),
            (
                "            result = CliRunner().invoke(",
                (
                    '                black.main, [str(src1), str(src2), "--diff",'
                    ' "--check"]'
                ),
            ),
        ),
        (
            9,
            (
                "            )",
                "    limited.append(-limited.pop())  # negate top",
                "    return A(",
                "        very_long_argument_name1=very_long_value_for_the_argument,",
                "        very_long_argument_name2=-very.long.value.for_the_argument,",
                "        **kwargs,",
                "    )",
            ),
            (
                "            )",
                "    limited.append(-limited.pop())  # negate top",
                "    return A(",
                "        very_long_argument_name1=very_long_value_for_the_argument,",
                "        very_long_argument_name2=-very.long.value.for_the_argument,",
                "        **kwargs,",
                "    )",
            ),
        ),
        (16, (), ("", "")),
        (16, ("def g():", '    "Docstring."'), ("def g():", '    "Docstring."')),
        (18, (), ("",)),
        (
            18,
            ("    def inner():", "        pass"),
            ("    def inner():", "        pass"),
        ),
        (20, (), ("",)),
        (
            20,
            ('    print("Inner defs should breathe a little.")',),
            ('    print("Inner defs should breathe a little.")',),
        ),
        (21, (), ("", "")),
        (
            21,
            ("def h():", "    def inner():", "        pass"),
            ("def h():", "    def inner():", "        pass"),
        ),
        (24, (), ("",)),
        (
            24,
            ('    print("Inner defs should breathe a little.")',),
            ('    print("Inner defs should breathe a little.")',),
        ),
    ]


EXAMPLE_OPCODES: List[
    Tuple[Literal["replace", "delete", "insert", "equal"], int, int, int, int]
] = [
    # 0-based, end-exclusive
    ("replace", 0, 4, 0, 1),
    ("equal", 4, 6, 1, 3),
    ("replace", 6, 8, 3, 5),
    ("equal", 8, 15, 5, 12),
    ("insert", 15, 15, 12, 14),
    ("equal", 15, 17, 14, 16),
    ("insert", 17, 17, 16, 17),
    ("equal", 17, 19, 17, 19),
    ("insert", 19, 19, 19, 20),
    ("equal", 19, 20, 20, 21),
    ("insert", 20, 20, 21, 23),
    ("equal", 20, 23, 23, 26),
    ("insert", 23, 23, 26, 27),
    ("equal", 23, 24, 27, 28),
    ("replace", 24, 34, 28, 38),
    ("equal", 34, 35, 38, 39),
]


@pytest.mark.kwparametrize(
    dict(
        context_lines=0,
        multiline_string_ranges=[],
        expect=[0, 3, 4, 12, 13, 16, 19, 21, 22, 26, [28, 37]],  # 0-based
    ),
    dict(
        context_lines=1,
        multiline_string_ranges=[],
        expect=[[0, 5], [11, 23], [25, 38]],  # 0-based, end-inclusive
    ),
    dict(
        context_lines=2,
        multiline_string_ranges=[],
        expect=[[0, 6], [10, 38]],  # 0-based, end-inclusive
    ),
    dict(
        context_lines=0,
        multiline_string_ranges=[  # 0-based, end exclusive
            (2, 4),  # partial left overlap with (3, 5)
            (13, 15),  # partial right overlap with (12, 14)
            (16, 17),  # exact overlap with (16, 17)
            (18, 21),  # overextending overlap with (19, 20)
            (22, 27),  # inner overlap with (21, 23) and full overlap with (26, 27)
            (28, 30),  # full overlap with (28, 38)...
            (36, 46),  # ...partial left overlap with (28, 38)
        ],
        expect=[0, [2, 4], [12, 14], 16, [18, 26], [28, 45]],  # 0-based, end-inclusive
    ),
)
def test_opcodes_to_edit_linenums(context_lines, multiline_string_ranges, expect):
    """`opcodes_to_edit_linenums()` gives correct results"""
    edit_linenums = list(
        opcodes_to_edit_linenums(
            EXAMPLE_OPCODES,
            context_lines,
            # Convert ranges from 0 to 1 based. The test case is defined using 0-based
            # ranges so it's easier to reason about the relation between multi-line
            # string ranges and opcode ranges.
            [(start + 1, end + 1) for start, end in multiline_string_ranges],
        )
    )
    # Normalize expected lines/ranges to 0-based, end-exclusive.
    expect_ranges = [[n, n] if isinstance(n, int) else n for n in expect]
    expect_linenums = list(chain(*(range(n[0], n[1] + 1) for n in expect_ranges)))

    # Normalize result to 0-based, end-exclusive before comparison
    assert [linenum - 1 for linenum in edit_linenums] == expect_linenums


def test_opcodes_to_edit_linenums_empty_opcodes():
    """``opcodes_to_edit_linenums()`` returns nothing for an empty list of opcodes"""
    result = list(
        opcodes_to_edit_linenums([], context_lines=0, multiline_string_ranges=[])
    )

    assert result == []  # pylint: disable=use-implicit-booleaness-not-comparison
