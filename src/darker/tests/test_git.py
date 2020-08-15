from pathlib import Path

import pytest

from darker.git import (
    EditedLinenumsDiffer,
    git_get_modified_files,
    git_get_unmodified_content,
    should_reformat_file,
)


@pytest.mark.parametrize(
    "revision, expect",
    [("HEAD", ["modified content"]), ("HEAD^", ["original content"]), ("HEAD~2", []),],
)
def test_get_unmodified_content(git_repo, revision, expect):
    git_repo.add({"my.txt": "original content"}, commit="Initial commit")
    paths = git_repo.add({"my.txt": "modified content"}, commit="Initial commit")
    paths['my.txt'].write('new content')

    original_content = git_get_unmodified_content(
        Path("my.txt"), revision, cwd=git_repo.root
    )

    assert original_content == expect


@pytest.mark.parametrize(
    'path, create, expect',
    [
        ('.', False, False),
        ('main', True, False),
        ('main.c', True, False),
        ('main.py', True, True),
        ('main.py', False, False),
        ('main.pyx', True, False),
        ('main.pyi', True, False),
        ('main.pyc', True, False),
        ('main.pyo', True, False),
        ('main.js', True, False),
    ],
)
def test_should_reformat_file(tmpdir, path, create, expect):
    if create:
        (tmpdir / path).ensure()

    result = should_reformat_file(Path(tmpdir / path))

    assert result == expect


@pytest.mark.parametrize(
    'modify_paths, paths, expect',
    [
        ({}, ['a.py'], []),
        ({}, [], []),
        ({'a.py': 'new'}, [], ['a.py']),
        ({'a.py': 'new'}, ['b.py'], []),
        ({'a.py': 'new'}, ['a.py', 'b.py'], ['a.py']),
        ({'c/d.py': 'new'}, ['c/d.py', 'd/f/g.py'], ['c/d.py']),
        ({'c/e.js': 'new'}, ['c/e.js'], []),
        ({'a.py': 'original'}, ['a.py'], []),
        ({'a.py': None}, ['a.py'], []),
        ({"h.py": "untracked"}, ["h.py"], ["h.py"]),
        ({}, ["h.py"], []),
    ],
)
def test_git_get_modified_files(git_repo, modify_paths, paths, expect):
    """Tests for `darker.git.git_get_modified_files()`"""
    root = Path(git_repo.root)
    git_repo.add(
        {
            'a.py': 'original',
            'b.py': 'original',
            'c/d.py': 'original',
            'c/e.js': 'original',
            'd/f/g.py': 'original',
        },
        commit="Initial commit",
    )
    for path, content in modify_paths.items():
        absolute_path = git_repo.root / path
        if content is None:
            absolute_path.remove()
        else:
            absolute_path.write(content, ensure=True)
    result = git_get_modified_files({root / p for p in paths}, "HEAD", cwd=root)
    assert {str(p) for p in result} == set(expect)


edited_linenums_differ_cases = pytest.mark.parametrize(
    "context_lines, expect",
    [
        (0, [3, 7]),
        (1, [2, 3, 4, 6, 7, 8]),
        (2, [1, 2, 3, 4, 5, 6, 7, 8]),
        (3, [1, 2, 3, 4, 5, 6, 7, 8]),
    ],
)


@edited_linenums_differ_cases
def test_edited_linenums_differ_revision_vs_worktree(git_repo, context_lines, expect):
    """Tests for EditedLinenumsDiffer.revision_vs_worktree()"""
    paths = git_repo.add({"a.py": "1\n2\n3\n4\n5\n6\n7\n8\n"}, commit="Initial commit")
    paths["a.py"].write("1\n2\nthree\n4\n5\n6\nseven\n8\n")
    differ = EditedLinenumsDiffer(git_repo.root, "HEAD")

    result = differ.revision_vs_worktree(Path("a.py"), context_lines)

    assert result == expect


@edited_linenums_differ_cases
def test_edited_linenums_differ_revision_vs_lines(git_repo, context_lines, expect):
    """Tests for EditedLinenumsDiffer.revision_vs_lines()"""
    git_repo.add({'a.py': '1\n2\n3\n4\n5\n6\n7\n8\n'}, commit='Initial commit')
    lines = ['1', '2', 'three', '4', '5', '6', 'seven', '8']
    differ = EditedLinenumsDiffer(git_repo.root, "HEAD")

    result = differ.revision_vs_lines(Path("a.py"), lines, context_lines)

    assert result == expect
