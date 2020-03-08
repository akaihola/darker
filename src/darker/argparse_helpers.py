import re
from argparse import HelpFormatter
from textwrap import fill

WORD_RE = re.compile(r"\w")


def _fill_line(line: str, width: int, indent: str) -> str:
    first_word_match = WORD_RE.search(line)
    first_word_offset = first_word_match.start() if first_word_match else 0
    return fill(
        line,
        width,
        initial_indent=indent,
        subsequent_indent=indent + first_word_offset * " ",
    )


class NewlinePreservingFormatter(HelpFormatter):
    def _fill_text(self, text: str, width: int, indent: str) -> str:
        if "\n" in text:
            return "\n".join(
                _fill_line(line, width, indent) for line in text.split("\n")
            )
        return super()._fill_text(text, width, indent)
