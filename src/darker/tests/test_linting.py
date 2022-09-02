# pylint: disable=protected-access,too-many-arguments

"""Unit tests for :mod:`darker.linting`"""

import os
import sys
from pathlib import Path
from textwrap import dedent
from unittest.mock import call, patch

import pytest

from darker import linting
from darker.git import WORKTREE, RevisionRange
from darker.tests.helpers import raises_if_exception

SKIP_ON_WINDOWS = [pytest.mark.skip] if sys.platform.startswith("win") else []
SKIP_ON_UNIX = [] if sys.platform.startswith("win") else [pytest.mark.skip]


@pytest.mark.kwparametrize(
    dict(
        line="module.py:42: Just a line number\n",
        expect=(Path("module.py"), 42, "module.py:42:", "Just a line number"),
    ),
    dict(
        line="module.py:42:5: With column  \n",
        expect=(Path("module.py"), 42, "module.py:42:5:", "With column"),
    ),
    dict(
        line="{git_root_absolute}{sep}mod.py:42: Full path\n",
        expect=(
            Path("mod.py"),
            42,
            "{git_root_absolute}{sep}mod.py:42:",
            "Full path",
        ),
    ),
    dict(
        line="{git_root_absolute}{sep}mod.py:42:5: Full path with column\n",
        expect=(
            Path("mod.py"),
            42,
            "{git_root_absolute}{sep}mod.py:42:5:",
            "Full path with column",
        ),
    ),
    dict(
        line="mod.py:42: 123 digits start the description\n",
        expect=(Path("mod.py"), 42, "mod.py:42:", "123 digits start the description"),
    ),
    dict(
        line="mod.py:42:    indented description\n",
        expect=(Path("mod.py"), 42, "mod.py:42:", "   indented description"),
    ),
    dict(
        line="mod.py:42:5:    indented description\n",
        expect=(Path("mod.py"), 42, "mod.py:42:5:", "   indented description"),
    ),
    dict(
        line="nonpython.txt:5: Non-Python file\n",
        expect=(Path("nonpython.txt"), 5, "nonpython.txt:5:", "Non-Python file"),
    ),
    dict(line="mod.py: No line number\n", expect=(Path(), 0, "", "")),
    dict(line="mod.py:foo:5: Invalid line number\n", expect=(Path(), 0, "", "")),
    dict(line="mod.py:42:bar: Invalid column\n", expect=(Path(), 0, "", "")),
    dict(line="/outside/mod.py:5: Outside the repo\n", expect=(Path(), 0, "", "")),
    dict(line="invalid linter output\n", expect=(Path(), 0, "", "")),
    dict(line=" leading:42: whitespace\n", expect=(Path(), 0, "", "")),
    dict(line=" leading:42:5 whitespace and column\n", expect=(Path(), 0, "", "")),
    dict(line="trailing :42: filepath whitespace\n", expect=(Path(), 0, "", "")),
    dict(line="leading: 42: linenum whitespace\n", expect=(Path(), 0, "", "")),
    dict(line="trailing:42 : linenum whitespace\n", expect=(Path(), 0, "", "")),
    dict(line="plus:+42: before linenum\n", expect=(Path(), 0, "", "")),
    dict(line="minus:-42: before linenum\n", expect=(Path(), 0, "", "")),
    dict(line="plus:42:+5 before column\n", expect=(Path(), 0, "", "")),
    dict(line="minus:42:-5 before column\n", expect=(Path(), 0, "", "")),
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)
    root_abs = git_repo.root.absolute()
    line_expanded = line.format(git_root_absolute=root_abs, sep=os.sep)

    result = linting._parse_linter_line(line_expanded, git_repo.root)

    expect_expanded = (
        expect[0],
        expect[1],
        expect[2].format(git_root_absolute=root_abs, sep=os.sep),
        expect[3],
    )
    assert result == expect_expanded


@pytest.mark.kwparametrize(
    dict(rev2="master", expect=NotImplementedError),
    dict(rev2=WORKTREE, expect=None),
)
def test_require_rev2_worktree(rev2, expect):
    """``_require_rev2_worktree`` raises an exception if rev2 is not ``WORKTREE``"""
    with raises_if_exception(expect):

        linting._require_rev2_worktree(rev2)


def test_check_linter_output():
    """``_check_linter_output()`` runs linter and returns the stdout stream"""
    with linting._check_linter_output(
        "echo", Path("root/of/repo"), {Path("first.py"), Path("second.py")}
    ) as stdout:
        lines = list(stdout)

    assert lines == [
        f"{Path('root/of/repo/first.py')} {Path('root/of/repo/second.py')}\n"
    ]


@pytest.mark.kwparametrize(
    dict(
        _descr="No files to check, no output",
        paths=[],
        location="test.py:1:",
        expect_output=[],
        expect_log=[],
    ),
    dict(
        _descr="Check one file, report on a modified line in test.py",
        paths=["one.py"],
        location="test.py:1:",
        expect_output=["", "test.py:1: {root/one.py}"],
        expect_log=[],
    ),
    dict(
        _descr="Check one file, report on a column of a modified line in test.py",
        paths=["one.py"],
        location="test.py:1:42:",
        expect_output=["", "test.py:1:42: {root/one.py}"],
        expect_log=[],
    ),
    dict(
        _descr="No output if report is on an unmodified line in test.py",
        paths=["one.py"],
        location="test.py:2:42:",
        expect_output=[],
        expect_log=[],
    ),
    dict(
        _descr="No output if report is on a column of an unmodified line in test.py",
        paths=["one.py"],
        location="test.py:2:42:",
        expect_output=[],
        expect_log=[],
    ),
    dict(
        _descr="Check two files, report on a modified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:1:",
        expect_output=["", "test.py:1: {root/one.py} {root/two.py}"],
        expect_log=[],
    ),
    dict(
        _descr="Check two files, rpeort on a column of a modified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:1:42:",
        expect_output=["", "test.py:1:42: {root/one.py} {root/two.py}"],
        expect_log=[],
    ),
    dict(
        _descr="No output if 2-file report is on an unmodified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:2:",
        expect_output=[],
        expect_log=[],
    ),
    dict(
        _descr="No output if 2-file report is on a column of an unmodified line",
        paths=["one.py", "two.py"],
        location="test.py:2:42:",
        expect_output=[],
        expect_log=[],
    ),
    dict(
        _descr="Warning for a file missing from the working tree",
        paths=["missing.py"],
        location="missing.py:1:",
        expect_output=[],
        expect_log=["WARNING Missing file missing.py from echo missing.py:1:"],
    ),
    dict(
        _descr="Linter message for a non-Python file is ignored with a warning",
        paths=["one.py"],
        location="nonpython.txt:1:",
        expect_output=[],
        expect_log=[
            "WARNING Linter message for a non-Python file: "
            "nonpython.txt:1: {root/one.py}"
        ],
    ),
    dict(
        _descr="Message for file outside common root is ignored with a warning (Unix)",
        paths=["one.py"],
        location="/elsewhere/mod.py:1:",
        expect_output=[],
        expect_log=[
            "WARNING Linter message for a file /elsewhere/mod.py "
            "outside requested directory {root/}"
        ],
        marks=SKIP_ON_WINDOWS,
    ),
    dict(
        _descr="Message for file outside common root is ignored with a warning (Win)",
        paths=["one.py"],
        location="C:\\elsewhere\\mod.py:1:",
        expect_output=[],
        expect_log=[
            "WARNING Linter message for a file C:\\elsewhere\\mod.py "
            "outside requested directory {root/}"
        ],
        marks=SKIP_ON_UNIX,
    ),
)
def test_run_linter(
    git_repo, capsys, caplog, _descr, paths, location, expect_output, expect_log
):
    """Linter gets correct paths on command line and outputs just changed lines

    We use ``echo`` as our "linter". It just adds the paths of each file to lint as an
    "error" on a line of ``test.py``. What this test does is the equivalent of e.g.::

    - creating a ``test.py`` such that the first line is modified after the last commit
    - creating and committing ``one.py`` and ``two.py``
    - running::

          $ darker -L 'echo test.py:1:' one.py two.py
          test.py:1: git-repo-root/one.py git-repo-root/two.py

    """
    src_paths = git_repo.add(
        {"test.py": "1\n2\n", "nonpython.txt": "hello\n"}, commit="Initial commit"
    )
    src_paths["test.py"].write_bytes(b"one\n2\n")
    cmdline = f"echo {location}"
    revrange = RevisionRange("HEAD", ":WORKTREE:")

    linting.run_linter(
        cmdline, git_repo.root, {Path(p) for p in paths}, revrange, use_color=False
    )

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    result = capsys.readouterr().out.splitlines()
    assert result == git_repo.expand_root(expect_output)
    logs = [f"{record.levelname} {record.message}" for record in caplog.records]
    assert logs == git_repo.expand_root(expect_log)


def test_run_linter_non_worktree():
    """``run_linter()`` doesn't support linting commits, only the worktree"""
    with pytest.raises(NotImplementedError):

        linting.run_linter(
            "dummy-linter",
            Path("/dummy"),
            {Path("dummy.py")},
            RevisionRange.parse_with_common_ancestor("..HEAD", Path("dummy cwd")),
            use_color=False,
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
        cmdline,
        git_repo.root,
        {Path("test.py")},
        RevisionRange("HEAD", ":WORKTREE:"),
        use_color=False,
    )

    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        linter_cmdlines=[],
        linters_return=[],
        expect_result=0,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[0],
        expect_result=0,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[1],
        expect_result=1,
    ),
    dict(
        linter_cmdlines=["linter"],
        linters_return=[42],
        expect_result=42,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[0, 0],
        expect_result=0,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2"],
        linters_return=[0, 42],
        expect_result=42,
    ),
    dict(
        linter_cmdlines=["linter1", "linter2 command line"],
        linters_return=[42, 42],
        expect_result=84,
    ),
)
def test_run_linters(linter_cmdlines, linters_return, expect_result):
    """Unit test for ``run_linters()``"""
    with patch.object(linting, "run_linter") as run_linter:
        run_linter.side_effect = linters_return

        result = linting.run_linters(
            linter_cmdlines,
            Path("dummy root"),
            {Path("dummy paths")},
            RevisionRange("dummy rev1", "dummy rev2"),
            use_color=False,
        )

        expect_calls = [
            call(
                linter_cmdline,
                Path("dummy root"),
                {Path("dummy paths")},
                RevisionRange("dummy rev1", "dummy rev2"),
                False,
            )
            for linter_cmdline in linter_cmdlines
        ]
        assert run_linter.call_args_list == expect_calls
        assert result == expect_result


def test_run_linter_on_new_file(git_repo, capsys):
    """``run_linter()`` considers file missing from history as empty

    Passes through all linter errors as if the original file was empty.

    """
    git_repo.add({"file1.py": "1\n"}, commit="Initial commit")
    git_repo.create_tag("initial")
    (git_repo.root / "file2.py").write_bytes(b"1\n2\n")

    linting.run_linter(
        "echo file2.py:1:",
        Path(git_repo.root),
        {Path("file2.py")},
        RevisionRange("initial", ":WORKTREE:"),
        use_color=False,
    )

    output = capsys.readouterr().out.splitlines()
    assert output == ["", f"file2.py:1: {git_repo.root / 'file2.py'}"]


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
        RevisionRange("HEAD", ":WORKTREE:"),
        use_color=False,
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
