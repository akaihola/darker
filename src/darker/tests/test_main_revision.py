import sys

if sys.version_info >= (3, 7):
    from contextlib import nullcontext
else:
    from contextlib import suppress as nullcontext

import pytest

from darker.__main__ import main


@pytest.mark.parametrize(
    'revision, expect',
    [
        (
            "",
            [
                "appear",
                "appear_and_modify",
                "delete",
                "modify",
                "modify_and_delete",
                "never_change",
            ],
        ),
        (
            "HEAD",
            [
                "appear",
                "appear_and_modify",
                "delete",
                "modify",
                "modify_and_delete",
                "never_change",
            ],
        ),
        (
            "HEAD^",
            [
                "appear",
                "appear_and_modify",
                "delete",
                "modify",
                "modify_and_delete",
                "never_change",
            ],
        ),
        (
            "HEAD~2",
            [
                "appear",
                "appear_and_modify",
                "delete",
                "modify",
                "modify_and_delete",
                "never_change",
            ],
        ),
        ("HEAD~3", SystemExit),
    ],
)
def test_revision(git_repo, monkeypatch, capsys, revision, expect):
    monkeypatch.chdir(git_repo.root)
    paths = git_repo.add(
        {
            'never_change.py': 'ORIGINAL = 1\n',
            'modify.py': 'ORIGINAL = 1\n',
            'delete.py': 'ORIGINAL = 1\n',
            'modify_and_delete.py': 'ORIGINAL = 1\n',
        },
        commit='First commit',
    )
    paths.update(
        git_repo.add(
            {
                'modify.py': 'MODIFIED = 1\n',
                'appear.py': 'ADDED = 1\n',
                'appear_and_modify.py': 'ORIGINAL = 1\n',
                'delete.py': None,
                'modify_and_delete.py': 'MODIFIED = 1\n',
            },
            commit='Second commit',
        )
    )
    git_repo.add(
        {'appear_and_modify.py': 'MODIFIED = 1\n', 'modify_and_delete.py': None},
        commit='Third commit',
    )
    for path in paths.values():
        path.write('USER_MODIFICATION=1\n')
    arguments = ["--diff", "--revision", revision, '.']
    should_raise = expect is SystemExit

    with pytest.raises(SystemExit) if should_raise else nullcontext():
        main(arguments)

    if not should_raise:
        expect_diff_output = [
            line
            for name in expect
            for line in [
                f'--- {name}.py',
                f'+++ {name}.py',
                '@@ -1 +1 @@',
                '',
                '-USER_MODIFICATION=1',
                '+USER_MODIFICATION = 1',
            ]
        ]
        assert capsys.readouterr().out.splitlines() == expect_diff_output
