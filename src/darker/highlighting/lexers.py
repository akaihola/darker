"""Custom Pygments lexers for highlighting linter output"""

from typing import Generator, Tuple

from pygments.lexer import Lexer, RegexLexer, bygroups, combined
from pygments.lexers.python import PythonLexer
from pygments.token import Error, Number, String, Text, _TokenType


class LocationLexer(Lexer):
    """Lexer for linter output ``path:line:col:`` prefix"""

    aliases = ["lint_location"]

    def get_tokens_unprocessed(
        self, text: str
    ) -> Generator[Tuple[int, _TokenType, str], None, None]:
        """Tokenize and generate (index, tokentype, value) tuples for highlighted tokens

        "index" is the starting position of the token within the input text.

        """
        path, *positions = text.split(":")
        yield 0, String, path
        pos = len(path)
        for position in positions:
            yield pos, Text, ":"
            yield pos + 1, Number, position
            pos += 1 + len(position)


class DescriptionLexer(RegexLexer):
    """Lexer for linter output descriptions

    Highlights embedded Python code and expressions using the Python 3 lexer.

    """

    aliases = "lint_description"

    # Make normal text in linter messages look like strings in source code.
    # This is a decent choice since it lets source code stand out fairly well.
    message = String

    # Customize the Python lexer
    tokens = PythonLexer.tokens.copy()

    # Move the main Python lexer into a separate state
    tokens["python"] = tokens["root"]
    tokens["python"].insert(0, ('"', message, "#pop"))
    tokens["python"].insert(0, ("'", message, "#pop"))

    # The root state manages a possible prefix for the description.
    # It highlights error codes, and also catches coverage output and assumes that
    # Python code follows and uses the Python lexer to highlight that.
    tokens["root"] = [
        (r"\s*no coverage: ", message, "python"),
        (r"[CEFNW]\d{3,4}\b|error\b", Error, "description"),
        (r"", Text, "description"),
    ]

    # Highlight a single space-separated word using the Python lexer
    tokens["one-python-identifier"] = [
        (" ", message, "#pop"),
    ]

    # The description state handles everything after the description prefix
    tokens["description"] = [
        # Highlight quoted expressions using the Python lexer.
        ('"', message, combined("python", "dqs")),
        ("'", message, combined("python", "sqs")),
        # Also catch a few common patterns which are followed by Python expressions,
        # but exclude a couple of special cases.
        (r"\bUnused (argument|variable) ", message),
        (
            r"\b(Returning|Unused|Base type|imported from) ",
            message,
            combined("one-python-identifier", "python"),
        ),
        # Highlight parenthesized message identifiers at the end of messages
        (
            r"(\()([a-z][a-z-]+[a-z])(\))(\s*)$",
            bygroups(message, Error, message, message),
        ),
        # Everything else is considered just plain non-highlighted text
        (r"\s+", message),
        (r"\S+", message),
    ]
