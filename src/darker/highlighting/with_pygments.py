"""Linter output highlighting helper to be used when Pygments is installed"""

import sys
from typing import cast

from pygments import highlight
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers import get_lexer_by_name


def colorize(output: str, lexer_name: str) -> str:
    """Return the output highlighted for terminal if Pygments is available"""
    if not highlight or not sys.stdout.isatty():
        return output
    lexer = get_lexer_by_name(lexer_name)
    highlighted = highlight(output, lexer, TerminalFormatter())
    if "\n" not in output:
        # see https://github.com/pygments/pygments/issues/1107
        highlighted = highlighted.rstrip("\n")
    return cast(str, highlighted)
