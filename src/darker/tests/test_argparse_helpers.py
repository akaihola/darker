"""Tests for the ``darker.argparse_helpers`` module"""

from argparse import ArgumentParser, Namespace
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING

import pytest

from darker import argparse_helpers
from darker.tests.helpers import raises_if_exception


@pytest.mark.kwparametrize(
    dict(line="", width=0, expect=ValueError),
    dict(line="", width=1, expect=[]),
    dict(
        line="lorem ipsum dolor sit amet",
        width=9,
        expect=["    lorem", "    ipsum", "    dolor", "    sit", "    amet"],
    ),
    dict(
        line="lorem ipsum dolor sit amet",
        width=15,
        expect=["    lorem ipsum", "    dolor sit", "    amet"],
    ),
)
def test_fill_line(line, width, expect):
    """``_fill_line()`` wraps lines correctly"""
    with raises_if_exception(expect):

        result = argparse_helpers._fill_line(  # pylint: disable=protected-access
            line, width, indent="    "
        )

        assert result.splitlines() == expect


@pytest.mark.kwparametrize(
    dict(
        text="lorem ipsum dolor sit amet",
        expect=["    lorem ipsum", "    dolor sit", "    amet"],
    ),
    dict(
        text="lorem\nipsum dolor sit amet",
        expect=["    lorem", "    ipsum dolor", "    sit amet"],
    ),
)
def test_newline_preserving_formatter(text, expect):
    """``NewlinePreservingFormatter`` wraps lines and keeps newlines correctly"""
    formatter = argparse_helpers.NewlinePreservingFormatter("dummy")

    result = formatter._fill_text(  # pylint: disable=protected-access
        text, width=15, indent="    "
    )

    assert result.splitlines() == expect


@pytest.mark.kwparametrize(
    dict(const=10, initial=NOTSET, expect=DEBUG),
    dict(const=10, initial=DEBUG, expect=INFO),
    dict(const=10, initial=INFO, expect=WARNING),
    dict(const=10, initial=WARNING, expect=ERROR),
    dict(const=10, initial=ERROR, expect=CRITICAL),
    dict(const=10, initial=CRITICAL, expect=CRITICAL),
    dict(const=-10, initial=DEBUG, expect=DEBUG),
    dict(const=-10, initial=INFO, expect=DEBUG),
    dict(const=-10, initial=WARNING, expect=INFO),
    dict(const=-10, initial=ERROR, expect=WARNING),
    dict(const=-10, initial=CRITICAL, expect=ERROR),
)
def test_log_level_action(const, initial, expect):
    """``LogLevelAction`` increments/decrements the log level value correctly"""
    action = argparse_helpers.LogLevelAction([], "log_level", const)
    parser = ArgumentParser()
    namespace = Namespace()
    namespace.log_level = initial

    action(parser, namespace, [])

    assert namespace.log_level == expect


@pytest.mark.kwparametrize(
    dict(const=10, count=NOTSET, expect=WARNING),
    dict(const=10, count=1, expect=ERROR),
    dict(const=10, count=2, expect=CRITICAL),
    dict(const=10, count=3, expect=CRITICAL),
    dict(const=-10, count=NOTSET, expect=WARNING),
    dict(const=-10, count=1, expect=INFO),
    dict(const=-10, count=2, expect=DEBUG),
    dict(const=-10, count=3, expect=DEBUG),
)
def test_argumentparser_log_level_action(const, count, expect):
    """The log level action works correctly with an ``ArgumentParser``"""
    parser = ArgumentParser()
    parser.register("action", "log_level", argparse_helpers.LogLevelAction)
    parser.add_argument("-l", dest="log_level", action="log_level", const=const)

    args = parser.parse_args(count * ["-l"])

    assert args.log_level == expect
