from textwrap import dedent

ORIGINAL = dedent(
    '''\
    original first line
    original second line
    original third line
'''
)

CHANGE_SECOND_LINE = dedent(
    '''\
    diff --git test1.py test1.py
    index 9ed6856..5a6b0d2 100644
    --- test1.py
    +++ test1.py
    @@ -2,1 +2,1 @@
    -original second line
    +changed second line
'''
)

CHANGED = dedent(
    '''\
    original first line
    changed second line
    original third line
'''
)


TWO_FILES_CHANGED = dedent(
    """\
    diff --git src/darker/git_diff.py src/darker/git_diff.py
    index cd3479b..237d999 100644
    --- src/darker/git_diff.py
    +++ src/darker/git_diff.py
    @@ -103,0 +104,4 @@ def get_edit_linenums(patch: bytes) -> Generator[int, None, None]:
    +
    +
    +# TODO: add multiple file git diffing
    +
    diff --git src/darker/tests/git_diff_example_output.py src/darker/tests/git_diff_example_output.py
    index 3cc7ca1..c5404dd 100644
    --- src/darker/tests/git_diff_example_output.py
    +++ src/darker/tests/git_diff_example_output.py
    @@ -29,0 +30,4 @@ CHANGED = dedent(
    +
    +
    +TWO_FILES_CHANGED = 'TODO: test case for two changed files'
    +
   """
)
