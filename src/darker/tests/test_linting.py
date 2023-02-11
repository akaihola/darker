# pylint: disable=protected-access,too-many-arguments,use-dict-literal

"""Unit tests for :mod:`darker.linting`"""

import os
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable, List, Tuple, Union

import pytest

from darker import linting
from darker.git import WORKTREE, RevisionRange
from darker.linting import (
    DiffLineMapping,
    LinterMessage,
    MessageLocation,
    make_linter_env,
)
from darker.tests.helpers import raises_if_exception
from darker.utils import WINDOWS

SKIP_ON_WINDOWS = [pytest.mark.skip] if WINDOWS else []
SKIP_ON_UNIX = [] if WINDOWS else [pytest.mark.skip]


@pytest.mark.kwparametrize(
    dict(column=0, expect=f"{Path('/path/to/file.py')}:42"),
    dict(column=5, expect=f"{Path('/path/to/file.py')}:42:5"),
)
def test_message_location_str(column, expect):
    """Null column number is hidden from string representation of message location"""
    location = MessageLocation(Path("/path/to/file.py"), 42, column)

    result = str(location)

    assert result == expect


@pytest.mark.kwparametrize(
    dict(
        new_location=("/path/to/new_file.py", 43, 8),
        old_location=("/path/to/old_file.py", 42, 13),
        get_location=("/path/to/new_file.py", 43, 21),
        expect_location=("/path/to/old_file.py", 42, 21),
    ),
    dict(
        new_location=("/path/to/new_file.py", 43, 8),
        old_location=("/path/to/old_file.py", 42, 13),
        get_location=("/path/to/a_different_file.py", 43, 21),
        expect_location=("", 0, 0),
    ),
    dict(
        new_location=("/path/to/file.py", 43, 8),
        old_location=("/path/to/file.py", 42, 13),
        get_location=("/path/to/file.py", 42, 21),
        expect_location=("", 0, 0),
    ),
)
def test_diff_line_mapping_ignores_column(
    new_location, old_location, get_location, expect_location
):
    """Diff location mapping ignores column and attaches column of queried location"""
    mapping = linting.DiffLineMapping()
    new_location_ = MessageLocation(Path(new_location[0]), *new_location[1:])
    old_location = MessageLocation(Path(old_location[0]), *old_location[1:])
    get_location = MessageLocation(Path(get_location[0]), *get_location[1:])
    expect = MessageLocation(Path(expect_location[0]), *expect_location[1:])

    mapping[new_location_] = old_location
    result = mapping.get(get_location)

    assert result == expect


def test_normalize_whitespace():
    """Whitespace runs and leading/trailing whitespace is normalized"""
    description = "module.py:42:  \t  indented message,    trailing spaces and tabs \t "
    message = LinterMessage("mylinter", description)

    result = linting.normalize_whitespace(message)

    assert result == LinterMessage(
        "mylinter", "module.py:42: indented message, trailing spaces and tabs"
    )


@pytest.mark.kwparametrize(
    dict(
        line="module.py:42: Just a line number\n",
        expect=(Path("module.py"), 42, 0, "Just a line number"),
    ),
    dict(
        line="module.py:42:5: With column  \n",
        expect=(Path("module.py"), 42, 5, "With column"),
    ),
    dict(
        line="{git_root_absolute}{sep}mod.py:42: Full path\n",
        expect=(Path("mod.py"), 42, 0, "Full path"),
    ),
    dict(
        line="{git_root_absolute}{sep}mod.py:42:5: Full path with column\n",
        expect=(Path("mod.py"), 42, 5, "Full path with column"),
    ),
    dict(
        line="mod.py:42: 123 digits start the description\n",
        expect=(Path("mod.py"), 42, 0, "123 digits start the description"),
    ),
    dict(
        line="mod.py:42:    indented description\n",
        expect=(Path("mod.py"), 42, 0, "   indented description"),
    ),
    dict(
        line="mod.py:42:5:    indented description\n",
        expect=(Path("mod.py"), 42, 5, "   indented description"),
    ),
    dict(
        line="nonpython.txt:5: Non-Python file\n",
        expect=(Path("nonpython.txt"), 5, 0, "Non-Python file"),
    ),
    dict(line="mod.py: No line number\n", expect=(Path(), 0, 0, "")),
    dict(line="mod.py:foo:5: Invalid line number\n", expect=(Path(), 0, 0, "")),
    dict(line="mod.py:42:bar: Invalid column\n", expect=(Path(), 0, 0, "")),
    dict(
        line="/outside/mod.py:5: Outside the repo\n",
        expect=(Path(), 0, 0, ""),
        marks=SKIP_ON_WINDOWS,
    ),
    dict(
        line="C:\\outside\\mod.py:5: Outside the repo\n",
        expect=(Path(), 0, 0, ""),
        marks=SKIP_ON_UNIX,
    ),
    dict(line="invalid linter output\n", expect=(Path(), 0, 0, "")),
    dict(line=" leading:42: whitespace\n", expect=(Path(), 0, 0, "")),
    dict(line=" leading:42:5 whitespace and column\n", expect=(Path(), 0, 0, "")),
    dict(line="trailing :42: filepath whitespace\n", expect=(Path(), 0, 0, "")),
    dict(line="leading: 42: linenum whitespace\n", expect=(Path(), 0, 0, "")),
    dict(line="trailing:42 : linenum whitespace\n", expect=(Path(), 0, 0, "")),
    dict(line="plus:+42: before linenum\n", expect=(Path(), 0, 0, "")),
    dict(line="minus:-42: before linenum\n", expect=(Path(), 0, 0, "")),
    dict(line="plus:42:+5 before column\n", expect=(Path(), 0, 0, "")),
    dict(line="minus:42:-5 before column\n", expect=(Path(), 0, 0, "")),
)
def test_parse_linter_line(git_repo, monkeypatch, line, expect):
    """Linter output is parsed correctly"""
    monkeypatch.chdir(git_repo.root)
    root_abs = git_repo.root.absolute()
    line_expanded = line.format(git_root_absolute=root_abs, sep=os.sep)

    result = linting._parse_linter_line("linter", line_expanded, git_repo.root)

    assert result == (MessageLocation(*expect[:3]), LinterMessage("linter", expect[3]))


@pytest.mark.kwparametrize(
    dict(rev2="master", expect=NotImplementedError),
    dict(rev2=WORKTREE, expect=None),
)
def test_require_rev2_worktree(rev2, expect):
    """``_require_rev2_worktree`` raises an exception if rev2 is not ``WORKTREE``"""
    with raises_if_exception(expect):

        linting._require_rev2_worktree(rev2)


@pytest.mark.kwparametrize(
    dict(cmdline="echo", expect=["first.py the  2nd.py\n"]),
    dict(cmdline="echo words before", expect=["words before first.py the  2nd.py\n"]),
    dict(
        cmdline='echo "two  spaces"',
        expect=["two  spaces first.py the  2nd.py\n"],
        marks=[
            pytest.mark.xfail(
                reason=(
                    "Quotes not removed on Windows."
                    " See https://github.com/akaihola/darker/issues/456"
                )
            )
        ]
        if WINDOWS
        else [],
    ),
    dict(cmdline="echo eat  spaces", expect=["eat spaces first.py the  2nd.py\n"]),
)
def test_check_linter_output(tmp_path, cmdline, expect):
    """``_check_linter_output()`` runs linter and returns the stdout stream"""
    with linting._check_linter_output(
        cmdline,
        tmp_path,
        {Path("first.py"), Path("the  2nd.py")},
        make_linter_env(tmp_path, "WORKTREE"),
    ) as stdout:
        lines = list(stdout)

    assert lines == expect


@pytest.mark.kwparametrize(
    dict(
        _descr="New message for test.py",
        messages_after=["test.py:1: new message"],
        expect_output=["", "test.py:1: new message [cat]"],
    ),
    dict(
        _descr="New message for test.py, including column number",
        messages_after=["test.py:1:42: new message with column number"],
        expect_output=["", "test.py:1:42: new message with column number [cat]"],
    ),
    dict(
        _descr="Identical message on an unmodified unmoved line in test.py",
        messages_before=["test.py:1:42: same message on same line"],
        messages_after=["test.py:1:42: same message on same line"],
    ),
    dict(
        _descr="Identical message on an unmodified moved line in test.py",
        messages_before=["test.py:3:42: same message on a moved line"],
        messages_after=["test.py:4:42: same message on a moved line"],
    ),
    dict(
        _descr="Additional message on an unmodified moved line in test.py",
        messages_before=["test.py:3:42: same message"],
        messages_after=[
            "test.py:4:42: same message",
            "test.py:4:42: additional message",
        ],
        expect_output=["", "test.py:4:42: additional message [cat]"],
    ),
    dict(
        _descr="Changed message on an unmodified moved line in test.py",
        messages_before=["test.py:4:42: old message"],
        messages_after=["test.py:4:42: new message"],
        expect_output=["", "test.py:4:42: new message [cat]"],
    ),
    dict(
        _descr="Identical message but on an inserted line in test.py",
        messages_before=["test.py:1:42: same message also on an inserted line"],
        messages_after=[
            "test.py:1:42: same message also on an inserted line",
            "test.py:2:42: same message also on an inserted line",
        ],
        expect_output=["", "test.py:2:42: same message also on an inserted line [cat]"],
    ),
    dict(
        _descr="Warning for a file missing from the working tree",
        messages_after=["missing.py:1: a missing Python file"],
        expect_log=["WARNING Missing file missing.py from cat messages"],
    ),
    dict(
        _descr="Linter message for a non-Python file is ignored with a warning",
        messages_after=["nonpython.txt:1: non-py"],
        expect_log=[
            "WARNING Linter message for a non-Python file: nonpython.txt:1: non-py"
        ],
    ),
    dict(
        _descr="Message for file outside common root is ignored with a warning (Unix)",
        messages_after=["/elsewhere/mod.py:1: elsewhere"],
        expect_log=[
            "WARNING Linter message for a file /elsewhere/mod.py outside root"
            " directory {root}"
        ],
        marks=SKIP_ON_WINDOWS,
    ),
    dict(
        _descr="Message for file outside common root is ignored with a warning (Win)",
        messages_after=["C:\\elsewhere\\mod.py:1: elsewhere"],
        expect_log=[
            "WARNING Linter message for a file C:\\elsewhere\\mod.py outside root"
            " directory {root}"
        ],
        marks=SKIP_ON_UNIX,
    ),
    messages_before=[],
    expect_output=[],
    expect_log=[],
)
def test_run_linters(
    git_repo,
    capsys,
    caplog,
    _descr,
    messages_before,
    messages_after,
    expect_output,
    expect_log,
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
        {
            "test.py": "1 unmoved\n2 modify\n3 to 4 moved\n",
            "nonpython.txt": "hello\n",
            "messages": "\n".join(messages_before),
        },
        commit="Initial commit",
    )
    src_paths["test.py"].write_bytes(
        b"1 unmoved\n2 modified\n3 inserted\n3 to 4 moved\n"
    )
    src_paths["messages"].write_text("\n".join(messages_after))
    cmdlines: List[Union[str, List[str]]] = ["cat messages"]
    revrange = RevisionRange("HEAD", ":WORKTREE:")

    linting.run_linters(
        cmdlines, git_repo.root, {Path("dummy path")}, revrange, use_color=False
    )

    # We can now verify that the linter received the correct paths on its command line
    # by checking standard output from the our `echo` "linter".
    # The test cases also verify that only linter reports on modified lines are output.
    result = capsys.readouterr().out.splitlines()
    assert result == git_repo.expand_root(expect_output)
    logs = [
        f"{record.levelname} {record.message}"
        for record in caplog.records
        if record.levelname != "DEBUG"
    ]
    assert logs == git_repo.expand_root(expect_log)


def test_run_linters_non_worktree():
    """``run_linters()`` doesn't support linting commits, only the worktree"""
    with pytest.raises(NotImplementedError):

        linting.run_linters(
            ["dummy-linter"],
            Path("/dummy"),
            {Path("dummy.py")},
            RevisionRange.parse_with_common_ancestor(
                "..HEAD", Path("dummy cwd"), stdin_mode=False
            ),
            use_color=False,
        )


@pytest.mark.parametrize(
    "message, expect",
    [
        ("", 0),
        ("test.py:1: message on modified line", 1),
        ("test.py:2: message on unmodified line", 0),
    ],
)
def test_run_linters_return_value(git_repo, message, expect):
    """``run_linters()`` returns the number of linter errors on modified lines"""
    src_paths = git_repo.add({"test.py": "1\n2\n"}, commit="Initial commit")
    src_paths["test.py"].write_bytes(b"one\n2\n")
    cmdline = f"echo {message}"

    result = linting.run_linters(
        [cmdline],
        git_repo.root,
        {Path("test.py")},
        RevisionRange("HEAD", ":WORKTREE:"),
        use_color=False,
    )

    assert result == expect


def test_run_linters_on_new_file(git_repo, capsys):
    """``run_linters()`` considers file missing from history as empty

    Passes through all linter errors as if the original file was empty.

    """
    git_repo.add({"file1.py": "1\n"}, commit="Initial commit")
    git_repo.create_tag("initial")
    (git_repo.root / "file2.py").write_bytes(b"1\n2\n")

    linting.run_linters(
        ["echo file2.py:1: message on a file not seen in Git history"],
        Path(git_repo.root),
        {Path("file2.py")},
        RevisionRange("initial", ":WORKTREE:"),
        use_color=False,
    )

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "",
        "file2.py:1: message on a file not seen in Git history file2.py [echo]",
    ]


def test_run_linters_line_separation(git_repo, capsys):
    """``run_linters`` separates contiguous blocks of linter output with empty lines"""
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
    cat_command = "cmd /c type" if WINDOWS else "cat"

    linting.run_linters(
        [f"{cat_command} {linter_output}"],
        git_repo.root,
        {Path(p) for p in paths},
        RevisionRange("HEAD", ":WORKTREE:"),
        use_color=False,
    )

    result = capsys.readouterr().out
    cat_cmd = "cmd" if WINDOWS else "cat"
    assert result == dedent(
        f"""
        a.py:2: first block [{cat_cmd}]
        a.py:3: of linter output [{cat_cmd}]

        a.py:5: second block [{cat_cmd}]
        a.py:6: of linter output [{cat_cmd}]
        """
    )


def test_run_linters_stdin():
    """`linting.run_linters` raises a `NotImplementeError` on ``--stdin-filename``"""
    with pytest.raises(
        NotImplementedError,
        match=r"^The -l/--lint option isn't yet available with --stdin-filename$",
    ):
        # end of test setup

        _ = linting.run_linters(
            ["dummy-linter-command"],
            Path("/dummy-dir"),
            {Path("dummy.py")},
            RevisionRange("HEAD", ":STDIN:"),
            use_color=False,
        )


def _build_messages(
    lines_and_messages: Iterable[Union[Tuple[int, str], Tuple[int, str, str]]],
) -> Dict[MessageLocation, List[LinterMessage]]:
    return {
        MessageLocation(Path("a.py"), line, 0): [
            LinterMessage(*msg.split(":")) for msg in msgs
        ]
        for line, *msgs in lines_and_messages
    }


def test_print_new_linter_messages(capsys):
    """`linting._print_new_linter_messages()` hides old intact linter messages"""
    baseline = _build_messages(
        [
            (2, "mypy:single message on an unmodified line"),
            (4, "mypy:single message on a disappearing line"),
            (6, "mypy:single message on a moved line"),
            (8, "mypy:single message on a modified line"),
            (10, "mypy:multiple messages", "pylint:on the same moved line"),
            (
                12,
                "mypy:old message which will be replaced",
                "pylint:on an unmodified line",
            ),
            (14, "mypy:old message on a modified line"),
        ]
    )
    new_messages = _build_messages(
        [
            (2, "mypy:single message on an unmodified line"),
            (5, "mypy:single message on a moved line"),
            (8, "mypy:single message on a modified line"),
            (11, "mypy:multiple messages", "pylint:on the same moved line"),
            (
                12,
                "mypy:new message replacing the old one",
                "pylint:on an unmodified line",
            ),
            (14, "mypy:new message on a modified line"),
            (16, "mypy:multiple messages", "pylint:on the same new line"),
        ]
    )
    diff_line_mapping = DiffLineMapping()
    for new_line, old_line in {2: 2, 5: 6, 11: 10, 12: 12}.items():
        diff_line_mapping[MessageLocation(Path("a.py"), new_line)] = MessageLocation(
            Path("a.py"), old_line
        )

    linting._print_new_linter_messages(
        baseline, new_messages, diff_line_mapping, use_color=False
    )

    result = capsys.readouterr().out.splitlines()
    assert result == [
        "",
        "a.py:8: single message on a modified line [mypy]",
        "",
        "a.py:12: new message replacing the old one [mypy]",
        "",
        "a.py:14: new message on a modified line [mypy]",
        "",
        "a.py:16: multiple messages [mypy]",
        "a.py:16: on the same new line [pylint]",
    ]


LINT_EMPTY_LINES_CMD = [
    "python",
    "-c",
    dedent(
        """
        from pathlib import Path
        for path in Path(".").glob("**/*.py"):
            for linenum, line in enumerate(path.open(), start=1):
                if not line.strip():
                    print(f"{path}:{linenum}: EMPTY")
        """
    ),
]

LINT_NONEMPTY_LINES_CMD = [
    "python",
    "-c",
    dedent(
        """
        from pathlib import Path
        for path in Path(".").glob("**/*.py"):
            for linenum, line in enumerate(path.open(), start=1):
                if line.strip():
                    print(f"{path}:{linenum}: {line.strip()}")
        """
    ),
]


def test_get_messages_from_linters_for_baseline(git_repo):
    """Test for `linting._get_messages_from_linters_for_baseline`"""
    git_repo.add({"a.py": "First line\n\nThird line\n"}, commit="Initial commit")
    initial = git_repo.get_hash()
    git_repo.add({"a.py": "Just one line\n"}, commit="Second commit")
    git_repo.create_branch("baseline", initial)

    result = linting._get_messages_from_linters_for_baseline(
        linter_cmdlines=[LINT_EMPTY_LINES_CMD, LINT_NONEMPTY_LINES_CMD],
        root=git_repo.root,
        paths=[Path("a.py"), Path("subdir/b.py")],
        revision="baseline",
    )

    a_py = Path("a.py")
    expect = {
        MessageLocation(a_py, 1): [LinterMessage("python", "First line")],
        MessageLocation(a_py, 2): [LinterMessage("python", "EMPTY")],
        MessageLocation(a_py, 3): [LinterMessage("python", "Third line")],
    }
    assert result == expect
