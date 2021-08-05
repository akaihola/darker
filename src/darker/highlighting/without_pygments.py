"""Linter output highlighting helper to be used when Pygments is not installed"""


def colorize(output: str, lexer_name: str) -> str:  # pylint: disable=unused-argument
    """Return the output unaltered"""
    return output
