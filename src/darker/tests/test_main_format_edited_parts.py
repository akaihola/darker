"""Tests for the `darker.__main__.format_edited_parts` function."""

# pylint: disable=no-member,redefined-outer-name
# pylint: disable=too-many-arguments,too-many-positional-arguments
# pylint: disable=use-dict-literal,use-implicit-booleaness-not-comparison

import logging
import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import darker.__main__
import darker.verification
from darker.config import Exclusions
from darker.formatters.black_formatter import BlackFormatter
from darker.formatters.ruff_formatter import RuffFormatter
from darker.tests.examples import A_PY, A_PY_BLACK, A_PY_BLACK_FLYNT, A_PY_BLACK_ISORT
from darker.tests.helpers import unix_and_windows_newline_repos
from darker.verification import NotEquivalentError
from darkgraylib.git import WORKTREE, RevisionRange
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture
from darkgraylib.utils import TextDocument, joinlines

A_PY_ISORT = ["import os", "import sys", "", "print( '{}'.format('42'))", ""]
A_PY_BLACK_UNNORMALIZE = ("import sys", "import os", "", "print('{}'.format('42'))", "")
A_PY_BLACK_ISORT_FLYNT = ["import os", "import sys", "", 'print("42")', ""]


@pytest.fixture(scope="module")
def format_edited_parts_repo(request, tmp_path_factory):
    """Create Git repositories for testing `format_edited_parts`."""
    fixture = {}
    with unix_and_windows_newline_repos(request, tmp_path_factory) as repos:
        for newline, repo in repos.items():
            fixture[newline] = SimpleNamespace(
                root=repo.root,
                paths=repo.add(
                    {"a.py": newline, "b.py": newline}, commit="Initial commit"
                ),
            )
            fixture[newline].paths["a.py"].write_bytes(
                newline.join(A_PY).encode("ascii")
            )
            fixture[newline].paths["b.py"].write_bytes(
                f"print(42 ){newline}".encode("ascii")
            )
        yield fixture


@pytest.mark.kwparametrize(
    dict(
        black_exclude=set(),
        expect=[A_PY_BLACK],
    ),
    dict(
        black_exclude=set(),
        isort_exclude=set(),
        expect=[A_PY_BLACK_ISORT],
    ),
    dict(
        black_exclude=set(),
        flynt_exclude=set(),
        expect=[A_PY_BLACK_FLYNT],
    ),
    dict(
        black_exclude=set(),
        isort_exclude=set(),
        flynt_exclude=set(),
        expect=[A_PY_BLACK_ISORT_FLYNT],
    ),
    dict(
        formatter_config={"skip_string_normalization": True},
        black_exclude=set(),
        expect=[A_PY_BLACK_UNNORMALIZE],
    ),
    dict(
        black_exclude={Path("a.py")},
        expect=[],
    ),
    dict(
        black_exclude={Path("a.py")},
        isort_exclude=set(),
        expect=[A_PY_ISORT],
    ),
    formatter_config={},
    black_exclude={"**/*"},
    isort_exclude={"**/*"},
    flynt_exclude={"**/*"},
)
@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_format_edited_parts(
    format_edited_parts_repo,
    formatter_config,
    black_exclude,
    isort_exclude,
    flynt_exclude,
    formatter_class,
    newline,
    expect,
):
    """Correct reformatting and import sorting changes are produced.

    Black reformatting is done even if a file is excluded in Black configuration.
    File exclusion is done in Darker before calling
    :func:`~darker.__main__.format_edited_parts`.

    """
    formatter = formatter_class()
    formatter.config = formatter_config

    result = darker.__main__.format_edited_parts(
        Path(format_edited_parts_repo[newline].root),
        {Path("a.py")},
        Exclusions(formatter=black_exclude, isort=isort_exclude, flynt=flynt_exclude),
        RevisionRange("HEAD", ":WORKTREE:"),
        formatter,
        report_unmodified=False,
    )

    changes = [
        (path, worktree_content.string, chosen.string, chosen.lines)
        for path, worktree_content, chosen in result
    ]
    expect_changes = [
        (
            format_edited_parts_repo[newline].paths["a.py"],
            newline.join(A_PY),
            newline.join(expect_lines),
            tuple(expect_lines[:-1]),
        )
        for expect_lines in expect
    ]
    assert changes == expect_changes


@pytest.fixture(scope="module")
def format_edited_parts_stdin_repo(request, tmp_path_factory):
    """Git repository fixture for `test_format_edited_parts_stdin`."""
    with unix_and_windows_newline_repos(request, tmp_path_factory) as repos:
        fixture = {}
        for newline, repo in repos.items():
            n = newline
            paths = repo.add(
                {
                    "a.py": f"print('a.py HEAD' ){n}#{n}print( 'a.py HEAD'){n}",
                    "b.py": f"print('b.py HEAD' ){n}#{n}print( 'b.py HEAD'){n}",
                },
                commit="Initial commit",
            )
            paths["a.py"].write_bytes(
                f"print('a.py :WORKTREE:' ){n}#{n}print( 'a.py HEAD'){n}".encode(
                    "ascii"
                ),
            )
            paths["b.py"].write_bytes(
                f"print('b.py HEAD' ){n}#{n}print( 'b.py WORKTREE'){n}".encode("ascii"),
            )
            fixture[newline] = SimpleNamespace(root=repo.root, paths=paths)
        yield fixture


@pytest.mark.kwparametrize(
    dict(
        rev1="HEAD",
        rev2=":STDIN:",
        expect=[
            (
                "a.py",
                ("print('a.py HEAD' )", "#", "print( 'a.py STDIN')"),
                ("print('a.py HEAD' )", "#", 'print("a.py STDIN")'),
            ),
        ],
    ),
    dict(
        rev1=":WORKTREE:",
        rev2=":STDIN:",
        expect=[
            (
                "a.py",
                ("print('a.py :WORKTREE:' )", "#", "print( 'a.py STDIN')"),
                ("print('a.py :WORKTREE:' )", "#", 'print("a.py STDIN")'),
            ),
        ],
    ),
    dict(
        rev1="HEAD",
        rev2=":WORKTREE:",
        expect=[
            (
                "a.py",
                ("print('a.py :WORKTREE:' )", "#", "print( 'a.py HEAD')"),
                ('print("a.py :WORKTREE:")', "#", "print( 'a.py HEAD')"),
            ),
        ],
    ),
)
@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["unix", "windows"])
def test_format_edited_parts_stdin(
    format_edited_parts_stdin_repo, rev1, rev2, expect, formatter_class, newline
):
    """`format_edited_parts` with ``--stdin-filename``."""
    repo = format_edited_parts_stdin_repo[newline]
    n = newline  # pylint: disable=invalid-name
    stdin = f"print('a.py {rev1}' ){n}#{n}print( 'a.py STDIN'){n}".encode("ascii")
    with patch.object(
        darker.__main__.sys,  # type: ignore[attr-defined]
        "stdin",
        Mock(buffer=BytesIO(stdin)),
    ):
        # end of test setup

        result = list(
            darker.__main__.format_edited_parts(
                Path(repo.root),
                {Path("a.py")},
                Exclusions(formatter=set(), isort=set()),
                RevisionRange(rev1, rev2),
                formatter_class(),
                report_unmodified=False,
            ),
        )

    expect = [
        (
            repo.paths[path],
            TextDocument.from_lines(before),
            TextDocument.from_lines(after),
        )
        for path, before, after in expect
    ]
    assert result == expect


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_format_edited_parts_all_unchanged(git_repo, monkeypatch, formatter_class):
    """``format_edited_parts()`` yields nothing if no reformatting was needed."""
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add({"a.py": "pass\n", "b.py": "pass\n"}, commit="Initial commit")
    # Note: `ruff format` likes to add a blank line between strings, Black not
    #       - but since black won't remove it either, this works for our test:
    paths["a.py"].write_bytes(b'"properly"\n\n"formatted"\n')
    paths["b.py"].write_bytes(b'"not"\n\n"checked"\n')

    result = list(
        darker.__main__.format_edited_parts(
            Path(git_repo.root),
            {Path("a.py"), Path("b.py")},
            Exclusions(),
            RevisionRange("HEAD", ":WORKTREE:"),
            formatter_class(),
            report_unmodified=False,
        ),
    )

    assert result == []


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_format_edited_parts_ast_changed(git_repo, caplog, formatter_class):
    """``darker.__main__.format_edited_parts()`` when reformatting changes the AST."""
    caplog.set_level(logging.DEBUG, logger="darker.__main__")
    paths = git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
    paths["a.py"].write_bytes(b"8\n7\n6\n5\n4\n3\n2\n1\n")
    mock_ctx = patch.object(
        darker.verification.ASTVerifier,
        "is_equivalent_to_baseline",
        return_value=False,
    )
    with mock_ctx, pytest.raises(NotEquivalentError):
        _ = list(
            darker.__main__.format_edited_parts(
                git_repo.root,
                {Path("a.py")},
                Exclusions(isort={"**/*"}),
                RevisionRange("HEAD", ":WORKTREE:"),
                formatter_class(),
                report_unmodified=False,
            ),
        )
    a_py = str(paths["a.py"])
    main = "darker.__main__:__main__.py"
    log = [
        line
        for line in re.sub(r":\d+", "", caplog.text).splitlines()
        if " lines of context " in line
    ]
    assert log == [
        f"DEBUG    {main} AST verification of {a_py} with 0 lines of context failed",
        f"DEBUG    {main} Trying with 5 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 5 lines of context failed",
        f"DEBUG    {main} Trying with 7 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 7 lines of context failed",
        f"DEBUG    {main} Trying with 8 lines of context for `git diff -U {a_py}`",
        f"DEBUG    {main} AST verification of {a_py} with 8 lines of context failed",
    ]


@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_format_edited_parts_isort_on_already_formatted(git_repo, formatter_class):
    """An already correctly formatted file after ``isort`` is simply skipped."""
    before = [
        "import a",
        "import b",
        "",
        "a.foo()",
        "b.bar()",
    ]
    after = [
        "import b",
        "",
        "b.bar()",
    ]
    paths = git_repo.add({"a.py": joinlines(before)}, commit="Initial commit")
    paths["a.py"].write_text(joinlines(after))

    result = darker.__main__.format_edited_parts(
        git_repo.root,
        {Path("a.py")},
        Exclusions(),
        RevisionRange("HEAD", ":WORKTREE:"),
        formatter_class(),
        report_unmodified=False,
    )

    assert list(result) == []


@pytest.fixture(scope="module")
def format_edited_parts_historical_repo(request, tmp_path_factory):
    """Git repository fixture for `test_format_edited_parts_historical`."""
    with GitRepoFixture.context(request, tmp_path_factory) as repo:
        a_py = {
            "HEAD^": TextDocument.from_lines(
                [
                    "import a",
                    "from b import bar, foo",
                    "",
                    "a.foo()",
                    "bar()",
                ],
            ),
            "HEAD": TextDocument.from_lines(
                [
                    "from b import bar, foo",
                    "",
                    "bar()",
                ],
            ),
            ":WORKTREE:": TextDocument.from_lines(
                [
                    "from b import foo, bar",
                    "",
                    "bar( )",
                ],
            ),
            "reformatted": TextDocument.from_lines(
                [
                    "from b import bar, foo",
                    "",
                    "bar()",
                ],
            ),
        }
        paths = repo.add({"a.py": a_py["HEAD^"].string}, commit="Initial commit")
        repo.add({"a.py": a_py["HEAD"].string}, commit="Modified a.py")
        paths["a.py"].write_text(a_py[":WORKTREE:"].string)
        yield SimpleNamespace(root=repo.root, paths=paths, source_a_py=a_py)


@pytest.mark.kwparametrize(
    dict(rev1="HEAD^", rev2="HEAD", expect=[]),
    dict(rev1="HEAD^", rev2=WORKTREE, expect=[(":WORKTREE:", "reformatted")]),
    dict(rev1="HEAD", rev2=WORKTREE, expect=[(":WORKTREE:", "reformatted")]),
)
@pytest.mark.parametrize("formatter_class", [BlackFormatter, RuffFormatter])
def test_format_edited_parts_historical(
    format_edited_parts_historical_repo, rev1, rev2, expect, formatter_class
):
    """``format_edited_parts()`` is correct for different commit pairs."""
    repo = format_edited_parts_historical_repo

    result = darker.__main__.format_edited_parts(
        repo.root,
        {Path("a.py")},
        Exclusions(),
        RevisionRange(rev1, rev2),
        formatter_class(),
        report_unmodified=False,
    )

    assert list(result) == [
        (repo.paths["a.py"], repo.source_a_py[x[0]], repo.source_a_py[x[1]])
        for x in expect
    ]
