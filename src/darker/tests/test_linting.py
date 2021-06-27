# pylint: disable=protected-access,too-many-arguments

"""Unit tests for :mod:`darker.linting`"""

from pathlib import Path
from textwrap import dedent
from unittest.mock import call, patch

import pytest

from darker import linting
from darker.git import RevisionRange


@pytest.mark.parametrize(
    "line, expect",
    [
        ("module.py:42: Description", (Path("module.py"), 42)),
        ("module.py:42:5: Description", (Path("module.py"), 42)),
        ("no-linenum.py: Description", (None, None)),
        ("mod.py:invalid-linenum:5: Description", (None, None)),
        ("invalid linter output", (None, None)),
    ],
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)

    result = linting._parse_linter_line(line, git_repo.root)

    assert result == expect


@pytest.mark.parametrize(
    "_descr, paths, location, expect",
    [
        ("No files to check, no output", [], "test.py:1:", []),
        (
            "Check one file, report on a modified line in test.py",
            ["one.py"],
            "test.py:1:",
            ["", "test.py:1: {git_repo.root / 'one.py'}"],
        ),
        (
            "Check one file, report on a column of a modified line in test.py",
            ["one.py"],
            "test.py:1:42:",
            ["", "test.py:1:42: {git_repo.root / 'one.py'}"],
        ),
        (
            "No output if report is on an unmodified line in test.py",
            ["one.py"],
            "test.py:2:42:",
            [],
        ),
        (
            "No output if report is on a column of an unmodified line in test.py",
            ["one.py"],
            "test.py:2:42:",
            [],
        ),
        (
            "Check two files, report on a modified line in test.py",
            ["one.py", "two.py"],
            "test.py:1:",
            ["", "test.py:1: {git_repo.root / 'one.py'} {git_repo.root / 'two.py'}"],
        ),
        (
            "Check two files, rpeort on a column of a modified line in test.py",
            ["one.py", "two.py"],
            "test.py:1:42:",
            ["", "test.py:1:42: {git_repo.root / 'one.py'} {git_repo.root / 'two.py'}"],
        ),
        (
            "No output if 2-file report is on an unmodified line in test.py",
            ["one.py", "two.py"],
            "test.py:2:",
            [],
        ),
        (
            "No output if 2-file report is on a column of an unmodified line",
            ["one.py", "two.py"],
            "test.py:2:42:",
            [],
        ),
    ],
)
def test_run_linter(git_repo, monkeypatch, capsys, _descr, paths, location, expect):
    """Linter gets correct paths on command line and outputs just changed lines

    We use ``echo`` as our "linter". It just adds the paths of each file to lint as an
    "error" on a line of ``test.py``. What this test does is the equivalent of e.g.::

    - creating a ``test.py`` such that the first line is modified after the last commit
    - creating and committing ``one.py`` and ``two.py``
    - running::

          $ darker -L 'echo test.py:1:' one.py two.py
          test.py:1: git-repo-root/one.py git-repo-root/two.py

    """
    src_paths = git_repo.add({"test.py": "1\n2\n"}, commit="Initial commit")
    src_paths["test.py"].write_bytes(b"one\n2\n")
    monkeypatch.chdir(git_repo.root)
    cmdline = f"echo {location}"

    linting.run_linter(
        cmdline, Path(git_repo.root), {Path(p) for p in paths}, RevisionRange("HEAD")
    )

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    result = capsys.readouterr().out.splitlines()
    # Use evil `eval()` so we get Windows compatible expected paths:
    assert result == [eval(f'f"{line}"', {"git_repo": git_repo}) for line in expect]


def test_run_linter_non_worktree():
    """``run_linter()`` doesn't support linting commits, only the worktree"""
    with pytest.raises(NotImplementedError):

        linting.run_linter(
            "dummy-linter",
            Path("/dummy"),
            {Path("dummy.py")},
            RevisionRange.parse("..HEAD"),
        )


@pytest.mark.parametrize(
    "location, expect",
    [
        ("", 0),
        ("test.py:1:", 1),
        ("test.py:2:", 0),
    ],
)
def test_run_linter_return_value(git_repo, location, expect):
    """``run_linter()`` returns the number of linter errors on modified lines"""
    src_paths = git_repo.add({"test.py": "1\n2\n"}, commit="Initial commit")
    src_paths["test.py"].write_bytes(b"one\n2\n")
    cmdline = f"echo {location}"

    result = linting.run_linter(
        cmdline, Path(git_repo.root), {Path("test.py")}, RevisionRange("HEAD")
    )

    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        linter_cmdlines=[],
        linters_return=[],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[None],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[0],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[1],
        expect_result=True,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[42],
        expect_result=True,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[None, None],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[None, 0],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[None, 42],
        expect_result=True,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[0, 0],
        expect_result=False,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[0, 42],
        expect_result=True,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2 command line"],
        linters_return=[42, 42],
        expect_result=True,
    ),
)
def test_run_linters(linter_cmdlines, linters_return, expect_result):
    """Unit test for ``run_linters()``"""
    with patch.object(linting, "run_linter") as run_linter:
        run_linter.side_effect = linters_return

        result = linting.run_linters(
            linter_cmdlines,
            Path("dummy git_root"),
            {Path("dummy paths")},
            RevisionRange("dummy revrange"),
        )

        expect_calls = [
            call(
                linter_cmdline,
                Path("dummy git_root"),
                {Path("dummy paths")},
                RevisionRange("dummy revrange"),
            )
            for linter_cmdline in linter_cmdlines
        ]
        assert run_linter.call_args_list == expect_calls
        assert result == expect_result


def test_run_linter_line_separation(git_repo, capsys):
    """``run_linter`` separates contiguous blocks of linter output with empty lines"""
    paths = git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n"}, commit="Initial commit")
    paths["a.py"].write_bytes(b"a\nb\nc\nd\ne\nf\n")
    linter_output = git_repo.root / "dummy-linter-output.txt"
    linter_output.write_text(
        dedent(
            """
            a.py:2: first block
            a.py:3: of linter output
            a.py:5: second block
            a.py:6: of linter output
            """
        )
    )

    linting.run_linter(
        f"cat {linter_output}",
        Path(git_repo.root),
        {Path(p) for p in paths},
        RevisionRange("HEAD"),
    )

    result = capsys.readouterr().out
    assert result == dedent(
        """
        a.py:2: first block
        a.py:3: of linter output

        a.py:5: second block
        a.py:6: of linter output
        """
    )
