"""Highlighting of terminal output"""

try:
    import pygments  # noqa: F401
except ImportError:
    from darker.highlighting import without_pygments

    colorize = without_pygments.colorize
else:
    from darker.highlighting import with_pygments

    colorize = with_pygments.colorize
