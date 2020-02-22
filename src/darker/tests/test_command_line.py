import re

import pytest

from darker.command_line import parse_command_line


@pytest.fixture
def darker_help_output(capsys):
    with pytest.raises(SystemExit):
        parse_command_line(["--help"])
    return re.sub(r'\s+', ' ', capsys.readouterr().out)


def test_help_description_without_isort_package(without_isort, darker_help_output):
    assert (
        "Please run `pip install 'darker[isort]'` to enable sorting of import "
        "definitions" in darker_help_output
    )


def test_help_isort_option_without_isort_package(without_isort, darker_help_output):
    assert (
        "Please run `pip install 'darker[isort]'` to enable usage of this option."
        in darker_help_output
    )


def test_help_with_isort_package(with_isort, darker_help_output):
    assert "Please run" not in darker_help_output
