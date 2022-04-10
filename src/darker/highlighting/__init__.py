"""Highlighting of terminal output"""

# pylint: disable=import-outside-toplevel,unused-import

import sys
from typing import Optional, cast


def should_use_color(config_color: Optional[bool]) -> bool:
    """Return ``True`` if configuration and package support allow output highlighting

    In ``config_color``, the combination of ``color =`` in ``pyproject.toml``, the
    ``PY_COLORS`` environment variable, and the ``--color``/``--no-color`` command line
    options determine whether the user wants to force enable or disable highlighting.

    If highlighting isn't forced either way, it is automatically enabled for terminal
    output.

    Finally, if ``pygments`` isn't installed, highlighting is disabled.

    :param config_color: The configuration as parsed from ``pyproject.toml`` and
                         overridden using environment variables and/or command line
                         options
    :return: ``True`` if highlighting should be used

    """
    if config_color is not None:
        use_color = config_color
    else:
        use_color = sys.stdout.isatty()

    if use_color:
        try:
            import pygments  # noqa

            return True
        except ImportError:
            pass
    return False


def colorize(output: str, lexer_name: str, use_color: bool) -> str:
    """Return the output highlighted for terminal if Pygments is available"""
    if not use_color:
        return output
    from pygments import highlight
    from pygments.formatters.terminal import TerminalFormatter
    from pygments.lexers import get_lexer_by_name

    lexer = get_lexer_by_name(lexer_name)
    highlighted = highlight(output, lexer, TerminalFormatter())
    if "\n" not in output:
        # see https://github.com/pygments/pygments/issues/1107
        highlighted = highlighted.rstrip("\n")
    return cast(str, highlighted)
