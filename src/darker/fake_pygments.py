"""Dummy implementation of Pygments parts we use. Used to satisfy Mypy."""

# pylint: disable=too-few-public-methods,unused-argument

from typing import IO, Any, Callable, Dict, Generator, List, Match, Tuple, Union


class TerminalFormatter:
    """Dummy replacement to satisfy Mypy"""


class _TokenType:
    """Dummy replacement to satisfy Mypy"""


class Lexer:
    """Dummy replacement to satisfy Mypy"""


class RegexLexer(Lexer):
    """Dummy replacement to satisfy Mypy"""


TokenWithoutState = Tuple[str, _TokenType]
TokenWithState = Tuple[str, _TokenType, str]
Token = Union[TokenWithoutState, TokenWithState]


class Python3Lexer(RegexLexer):
    """Dummy replacement to satisfy Mypy"""

    tokens: Dict[str, List[Token]] = {"root": []}


class LexerContext:
    """Dummy replacement to satisfy Mypy"""


class combined(tuple):  # type: ignore  # pylint: disable=invalid-name
    """Dummy implementation to satisfy Mypy"""


# The `Any` below should really be a cyclic reference to `LexerCallback`,
# but Mypy doesn't yet support that.
LexerGenerator = Generator[
    Tuple[int, Union[None, _TokenType, Any], LexerContext], None, None
]
LexerCallback = Callable[[Lexer, Match[str], LexerContext], LexerGenerator]


def bygroups(*args: _TokenType) -> LexerCallback:
    """Dummy implementation to satisfy Mypy"""


def get_lexer_by_name(_alias: str, *options: Union[bool, int, str]) -> Lexer:
    """Dummy implementation to satisfy Mypy"""


def highlight(
    code: str, lexer: Lexer, formatter: TerminalFormatter, outfile: IO[str] = None
) -> str:
    """Dummy implementation to satisfy Mypy"""


Error = Number = String = Text = _TokenType()
