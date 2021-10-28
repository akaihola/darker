# pylint: disable=protected-access,too-many-arguments

"""Unit tests for :mod:`darker.linting`"""

from pathlib import Path
from unittest.mock import call, patch

import pytest

from darker import linting
from darker.git import WORKTREE, RevisionRange
from darker.tests.helpers import raises_if_exception


@pytest.mark.kwparametrize(
    dict(line="module.py:42: Description", expect=(Path("module.py"), 42)),
    dict(line="module.py:42:5: Description", expect=(Path("module.py"), 42)),
    dict(line="no-linenum.py: Description", expect=(None, None)),
    dict(line="mod.py:invalid-linenum:5: Description", expect=(None, None)),
    dict(line="invalid linter output", expect=(None, None)),
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)

    result = linting._parse_linter_line(line, git_repo.root)

    assert result == expect


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
        expect_output=["", "test.py:1: {git_repo.root / 'one.py'}"],
        expect_log=[],
    ),
    dict(
        _descr="Check one file, report on a column of a modified line in test.py",
        paths=["one.py"],
        location="test.py:1:42:",
        expect_output=["", "test.py:1:42: {git_repo.root / 'one.py'}"],
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
        expect_output=[
            "",
            "test.py:1: {git_repo.root / 'one.py'} {git_repo.root / 'two.py'}"
        ],
        expect_log=[],
    ),
    dict(
        _descr="Check two files, rpeort on a column of a modified line in test.py",
        paths=["one.py", "two.py"],
        location="test.py:1:42:",
        expect_output=[
            "",
            "test.py:1:42: {git_repo.root / 'one.py'} {git_repo.root / 'two.py'}"
        ],
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
    src_paths = git_repo.add({"test.py": "1\n2\n"}, commit="Initial commit")
    src_paths["test.py"].write_bytes(b"one\n2\n")
    cmdline = f"echo {location}"
    revrange = RevisionRange("HEAD", ":WORKTREE:")

    linting.run_linter(cmdline, git_repo.root, {Path(p) for p in paths}, revrange)

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    result = capsys.readouterr().out.splitlines()
    # Use evil `eval()` so we get Windows compatible expected paths:
    # pylint: disable=eval-used
    assert result == [
        eval(f'f"{line}"', {"git_repo": git_repo}) for line in expect_output
    ]
    logs = [f"{record.levelname} {record.message}" for record in caplog.records]
    assert logs == expect_log


def test_run_linter_non_worktree():
    """``run_linter()`` doesn't support linting commits, only the worktree"""
    with pytest.raises(NotImplementedError):

        linting.run_linter(
            "dummy-linter",
            Path("/dummy"),
            {Path("dummy.py")},
            RevisionRange.parse_with_common_ancestor("..HEAD", Path("dummy cwd")),
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
        cmdline, git_repo.root, {Path("test.py")}, RevisionRange("HEAD", ":WORKTREE:")
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
            Path("dummy root"),
            {Path("dummy paths")},
            RevisionRange("dummy rev1", "dummy rev2"),
        )

        expect_calls = [
            call(
                linter_cmdline,
                Path("dummy root"),
                {Path("dummy paths")},
                RevisionRange("dummy rev1", "dummy rev2"),
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
    )

    output = capsys.readouterr().out.splitlines()
    assert output == ["", f"file2.py:1: {git_repo.root / 'file2.py'}"]
