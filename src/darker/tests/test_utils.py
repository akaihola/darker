from darker.utils import joinlines, debug_dump


def test_debug_dump(capsys):
    debug_dump([(1, ["black"], ["chunks"])], "old content", "new content", [2, 3])
    assert capsys.readouterr().out == (
        "[2, 3]\n"
        "[(1, ['black'], ['chunks'])]\n"
        "[(1, 'old content')]\n"
        "new content\n"
    )


def test_joinlines():
    result = joinlines(["a", "b", "c"])
    assert result == "a\nb\nc\n"
