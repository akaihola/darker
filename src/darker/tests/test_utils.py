from textwrap import dedent

from darker.utils import debug_dump, joinlines


def test_debug_dump(capsys):
    debug_dump([(1, ["black"], ["chunks"])], "old content", "new content", [2, 3])
    assert capsys.readouterr().out == (
        dedent(
            """\
            --------------------------------------------------------------------------------
             -   1 black
             +     chunks
            --------------------------------------------------------------------------------
            """
        )
    )


def test_joinlines():
    result = joinlines(["a", "b", "c"])
    assert result == "a\nb\nc\n"
