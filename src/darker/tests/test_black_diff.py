from textwrap import dedent

from black import FileMode, format_str

from darker.black_diff import diff_and_get_opcodes, opcodes_to_chunks

FUNCTIONS2_PY = dedent(
    '''\
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
'''
)


def test_diff_opcodes():
    src_lines = FUNCTIONS2_PY.splitlines()
    dst_lines = format_str(FUNCTIONS2_PY, mode=FileMode()).splitlines()
    opcodes = diff_and_get_opcodes(src_lines, dst_lines)
    assert opcodes == [
        ('replace', 0, 4, 0, 1),
        ('equal', 4, 6, 1, 3),
        ('replace', 6, 8, 3, 5),
        ('equal', 8, 15, 5, 12),
        ('insert', 15, 15, 12, 14),
        ('equal', 15, 17, 14, 16),
        ('insert', 17, 17, 16, 17),
        ('equal', 17, 19, 17, 19),
        ('insert', 19, 19, 19, 20),
        ('equal', 19, 20, 20, 21),
        ('insert', 20, 20, 21, 23),
        ('equal', 20, 23, 23, 26),
        ('insert', 23, 23, 26, 27),
        ('equal', 23, 24, 27, 28),
    ]


def test_mixed():
    src_lines = FUNCTIONS2_PY.splitlines()
    dst_lines = format_str(FUNCTIONS2_PY, mode=FileMode()).splitlines()
    opcodes = [
        ('replace', 0, 4, 0, 1),
        ('equal', 4, 6, 1, 3),
        ('replace', 6, 8, 3, 5),
        ('equal', 8, 15, 5, 12),
        ('insert', 15, 15, 12, 14),
        ('equal', 15, 17, 14, 16),
        ('insert', 17, 17, 16, 17),
        ('equal', 17, 19, 17, 19),
        ('insert', 19, 19, 19, 20),
        ('equal', 19, 20, 20, 21),
        ('insert', 20, 20, 21, 23),
        ('equal', 20, 23, 23, 26),
        ('insert', 23, 23, 26, 27),
        ('equal', 23, 24, 27, 28),
    ]
    chunks = list(opcodes_to_chunks(opcodes, src_lines, dst_lines))
    assert chunks == [
        (
            0,
            ['def f(', '  a,', '  **kwargs,', ') -> A:'],
            ['def f(a, **kwargs,) -> A:'],
        ),
        (
            4,
            ['    with cache_dir():', '        if something:'],
            ['    with cache_dir():', '        if something:'],
        ),
        (
            6,
            [
                '            result = (',
                '                CliRunner().invoke(black.main, [str(src1), str(src2), '
                '"--diff", "--check"])',
            ],
            [
                '            result = CliRunner().invoke(',
                '                black.main, [str(src1), str(src2), "--diff", "--check"]',
            ],
        ),
        (
            8,
            [
                '            )',
                '    limited.append(-limited.pop())  # negate top',
                '    return A(',
                '        very_long_argument_name1=very_long_value_for_the_argument,',
                '        very_long_argument_name2=-very.long.value.for_the_argument,',
                '        **kwargs,',
                '    )',
            ],
            [
                '            )',
                '    limited.append(-limited.pop())  # negate top',
                '    return A(',
                '        very_long_argument_name1=very_long_value_for_the_argument,',
                '        very_long_argument_name2=-very.long.value.for_the_argument,',
                '        **kwargs,',
                '    )',
            ],
        ),
        (15, [], ['', '']),
        (15, ['def g():', '    "Docstring."'], ['def g():', '    "Docstring."']),
        (17, [], ['']),
        (
            17,
            ['    def inner():', '        pass'],
            ['    def inner():', '        pass'],
        ),
        (19, [], ['']),
        (
            19,
            ['    print("Inner defs should breathe a little.")'],
            ['    print("Inner defs should breathe a little.")'],
        ),
        (20, [], ['', '']),
        (
            20,
            ['def h():', '    def inner():', '        pass'],
            ['def h():', '    def inner():', '        pass'],
        ),
        (23, [], ['']),
        (
            23,
            ['    print("Inner defs should breathe a little.")'],
            ['    print("Inner defs should breathe a little.")'],
        ),
    ]
