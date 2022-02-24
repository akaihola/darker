from itertools import chain
from textwrap import dedent

import pytest

from darker.diff import (
    diff_and_get_opcodes,
    opcodes_to_chunks,
    opcodes_to_edit_linenums,
)
from darker.utils import TextDocument

FUNCTIONS2_PY = dedent(
    """\
    def f(
      a,
      **kwargs,
    ) -> A:
        with cache_dir():
            if something:
                result = (
                    CliRunner().invoke(black.main, [str(src1), str(src2), "--diff", "--check"])
                )
        limited.append(-limited.pop())  # negate top
        return A(
            very_long_argument_name1=very_long_value_for_the_argument,
            very_long_argument_name2=-very.long.value.for_the_argument,
            **kwargs,
        )
    def g():
        "Docstring."
        def inner():
            pass
        print("Inner defs should breathe a little.")
    def h():
        def inner():
            pass
        print("Inner defs should breathe a little.")
"""  # noqa: E501
)


FUNCTIONS2_PY_REFORMATTED = dedent(
    """\
    def f(
        a,
        **kwargs,
    ) -> A:
        with cache_dir():
            if something:
                result = CliRunner().invoke(
                    black.main, [str(src1), str(src2), "--diff", "--check"]
                )
        limited.append(-limited.pop())  # negate top
        return A(
            very_long_argument_name1=very_long_value_for_the_argument,
            very_long_argument_name2=-very.long.value.for_the_argument,
            **kwargs,
        )


    def g():
        "Docstring."

        def inner():
            pass

        print("Inner defs should breathe a little.")


    def h():
        def inner():
            pass

        print("Inner defs should breathe a little.")
    """
)


EXPECT_OPCODES = [
    ("equal", 0, 1, 0, 1),
    ("replace", 1, 3, 1, 3),
    ("equal", 3, 6, 3, 6),
    ("replace", 6, 8, 6, 8),
    ("equal", 8, 15, 8, 15),
    ("insert", 15, 15, 15, 17),
    ("equal", 15, 17, 17, 19),
    ("insert", 17, 17, 19, 20),
    ("equal", 17, 19, 20, 22),
    ("insert", 19, 19, 22, 23),
    ("equal", 19, 20, 23, 24),
    ("insert", 20, 20, 24, 26),
    ("equal", 20, 23, 26, 29),
    ("insert", 23, 23, 29, 30),
    ("equal", 23, 24, 30, 31),
]


def test_diff_and_get_opcodes():
    src = TextDocument.from_str(FUNCTIONS2_PY)
    dst = TextDocument.from_str(FUNCTIONS2_PY_REFORMATTED)
    opcodes = diff_and_get_opcodes(src, dst)
    assert opcodes == EXPECT_OPCODES


def test_opcodes_to_chunks():
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
                '                black.main, [str(src1), str(src2), "--diff", "--check"]',  # noqa: E501
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


EXAMPLE_OPCODES = [
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
]


@pytest.mark.kwparametrize(
    dict(context_lines=0, expect=[1, 4, 5, 13, 14, 17, 20, 22, 23, 27]),
    dict(context_lines=1, expect=[[1, 6], [12, 24], [26, 28]]),
    dict(context_lines=2, expect=[[1, 7], [11, 28]]),
)
def test_opcodes_to_edit_linenums(context_lines, expect):
    edit_linenums = list(opcodes_to_edit_linenums(EXAMPLE_OPCODES, context_lines, []))
    expect_ranges = [[n, n] if isinstance(n, int) else n for n in expect]
    expect_linenums = list(chain(*(range(n[0], n[1] + 1) for n in expect_ranges)))

    assert edit_linenums == expect_linenums


def test_opcodes_to_edit_linenums_empty_opcodes():
    result = list(
        opcodes_to_edit_linenums([], context_lines=0, multiline_string_ranges=[])
    )

    assert result == []
