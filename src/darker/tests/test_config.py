from textwrap import dedent

import pytest

from darker.config import TomlArrayLinesEncoder, load_config, replace_log_level_name


@pytest.mark.parametrize(
    "list_value, expect",
    [
        ([], "[\n]"),
        (["one value"], '[\n    "one value",\n]'),
        (["two", "values"], '[\n    "two",\n    "values",\n]'),
        (
            [
                "a",
                "dozen",
                "short",
                "string",
                "values",
                "in",
                "the",
                "list",
                "of",
                "strings",
                "to",
                "format",
            ],
            '[\n    "a",\n    "dozen",\n    "short",\n    "string",\n    "values"'
            ',\n    "in",\n    "the",\n    "list",\n    "of",\n    "strings"'
            ',\n    "to",\n    "format",\n]',
        ),
    ],
)
def test_toml_array_lines_encoder(list_value, expect):
    result = TomlArrayLinesEncoder().dump_list(list_value)

    assert result == expect


@pytest.mark.parametrize(
    "log_level, expect",
    [
        (0, "NOTSET"),
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARNING"),
        (40, "ERROR"),
        (50, "CRITICAL"),
        ("DEBUG", 10),
        ("INFO", 20),
        ("WARNING", 30),
        ("WARN", 30),
        ("ERROR", 40),
        ("CRITICAL", 50),
        ("FOOBAR", "Level FOOBAR"),
    ],
)
def test_replace_log_level_name(log_level, expect):
    if log_level is None:
        config = {}
    else:
        config = {"log_level": log_level}

    replace_log_level_name(config)

    assert config["log_level"] == expect


@pytest.mark.parametrize(
    "srcs, cwd, expect",
    [
        ([], ".", {"CONFIG_PATH": "."}),
        ([], "level1", {"CONFIG_PATH": "."}),
        ([], "level1/level2", {"CONFIG_PATH": "."}),
        ([], "has_git", {}),
        ([], "has_git/level1", {}),
        ([], "has_pyproject", {"CONFIG_PATH": "has_pyproject"}),
        ([], "has_pyproject/level1", {"CONFIG_PATH": "has_pyproject"}),
        (["root.py"], ".", {"CONFIG_PATH": "."}),
        (["../root.py"], "level1", {"CONFIG_PATH": "."}),
        (["../root.py"], "has_git", {"CONFIG_PATH": "."}),
        (["../root.py"], "has_pyproject", {"CONFIG_PATH": "."}),
        (["root.py", "level1/level1.py"], ".", {"CONFIG_PATH": "."}),
        (["../root.py", "level1.py"], "level1", {"CONFIG_PATH": "."}),
        (["../root.py", "../level1/level1.py"], "has_git", {"CONFIG_PATH": "."}),
        (["../root.py", "../level1/level1.py"], "has_pyproject", {"CONFIG_PATH": "."}),
        (["has_pyproject/pyp.py", "level1/level1.py"], ".", {"CONFIG_PATH": "."}),
        (["../has_pyproject/pyp.py", "level1.py"], "level1", {"CONFIG_PATH": "."}),
        (
            ["../has_pyproject/pyp.py", "../level1/level1.py"],
            "has_git",
            {"CONFIG_PATH": "."},
        ),
        (["pyp.py", "../level1/level1.py"], "has_pyproject", {"CONFIG_PATH": "."}),
        (
            ["has_pyproject/level1/l1.py", "has_pyproject/level1b/l1b.py"],
            ".",
            {"CONFIG_PATH": "has_pyproject"},
        ),
        (
            ["../has_pyproject/level1/l1.py", "../has_pyproject/level1b/l1b.py"],
            "level1",
            {"CONFIG_PATH": "has_pyproject"},
        ),
        (
            ["../has_pyproject/level1/l1.py", "../has_pyproject/level1b/l1b.py"],
            "has_git",
            {"CONFIG_PATH": "has_pyproject"},
        ),
        (
            ["level1/l1.py", "level1b/l1b.py"],
            "has_pyproject",
            {"CONFIG_PATH": "has_pyproject"},
        ),
        (
            ["full_example/full.py"],
            ".",
            {
                "check": True,
                "diff": True,
                "isort": True,
                "lint": ["flake8", "mypy", "pylint"],
                "log_level": 10,
                "revision": "main",
                "src": ["src", "tests"],
            },
        ),
    ],
)
def test_load_config(
    find_project_root_cache_clear, tmp_path, monkeypatch, srcs, cwd, expect
):
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[tool.darker]\nCONFIG_PATH = "."\n')
    (tmp_path / "level1/level2").mkdir(parents=True)
    (tmp_path / "has_git/.git").mkdir(parents=True)
    (tmp_path / "has_git/level1").mkdir()
    (tmp_path / "has_pyproject/level1").mkdir(parents=True)
    (tmp_path / "has_pyproject/pyproject.toml").write_text(
        '[tool.darker]\nCONFIG_PATH = "has_pyproject"\n'
    )
    (tmp_path / "full_example").mkdir()
    (tmp_path / "full_example/pyproject.toml").write_text(
        dedent(
            """
            [tool.darker]
            src = [
                "src",
                "tests",
            ]
            revision = "main"
            diff = true
            check = true
            isort = true
            lint = [
                "flake8",
                "mypy",
                "pylint",
            ]
            log_level = "DEBUG"
            """
        )
    )
    monkeypatch.chdir(tmp_path / cwd)

    result = load_config(srcs)

    assert result == expect
