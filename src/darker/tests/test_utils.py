"""Unit tests for :mod:`darker.utils`"""

# pylint: disable=comparison-with-callable,redefined-outer-name,use-dict-literal

import logging
from textwrap import dedent

from darker.utils import debug_dump


def test_debug_dump(caplog, capsys):
    """darker.utils.debug_dump()"""
    caplog.set_level(logging.DEBUG)
    debug_dump([(1, ("black",), ("chunks",))], [2, 3])
    assert capsys.readouterr().out == (
        dedent(
            """\
            --------------------------------------------------------------------------------
             -   1 black
             +     chunks
            --------------------------------------------------------------------------------
            """
        )
    )
