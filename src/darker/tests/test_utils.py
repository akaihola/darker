from pathlib import Path
from textwrap import dedent

from darker.utils import debug_dump, get_common_git_root, joinlines


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


def test_get_common_git_root(tmpdir):
    tmpdir = Path(tmpdir)
    (tmpdir / "a" / ".git").mkdir(parents=True)
    path1 = tmpdir / "a/b/c/d"
    path2 = tmpdir / "a/e/../b/f/g"
    path3 = tmpdir / "a/h/../b/i"
    result = get_common_git_root([path1, path2, path3])
    assert result == tmpdir / "a"
