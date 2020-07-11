from argparse import ArgumentParser, Namespace
from typing import List

from darker.argparse_helpers import NewlinePreservingFormatter

ISORT_INSTRUCTION = "Please run `pip install 'darker[isort]'`"


def parse_command_line(argv: List[str]) -> Namespace:
    description = [
        "Re-format Python source files by using",
        "- `isort` to sort Python import definitions alphabetically within logical"
        " sections",
        "- `black` to re-format code changed since the last Git commit",
    ]
    try:
        import isort
    except ImportError:
        isort = None
        description.extend(
            ["", f"{ISORT_INSTRUCTION} to enable sorting of import definitions"]
        )
    parser = ArgumentParser(
        description="\n".join(description), formatter_class=NewlinePreservingFormatter,
    )
    parser.add_argument("src", nargs="*")
    isort_help = ["Also sort imports using the `isort` package"]
    if not isort:
        isort_help.append(f". {ISORT_INSTRUCTION} to enable usage of this option.")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Don't write the files back, just output a diff for each file on stdout",
    )
    parser.add_argument(
        "-i", "--isort", action="store_true", help="".join(isort_help),
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        help="Ask `black` and `isort` to read configuration from PATH.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="log_level",
        action="append_const",
        const=10,
        help="Show steps taken and summarize modifications",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="log_level",
        action="append_const",
        const=-10,
        help="Reduce amount of output",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show the version of `darker`"
    )
    parser.add_argument(
        "-S",
        "--skip-string-normalization",
        action="store_true",
        dest="skip_string_normalization",
        help="Don't normalize string quotes or prefixes",
    )
    parser.add_argument(
        "-l",
        "--line-length",
        type=int,
        dest="line_length",
        help="How many characters per line to allow [default: 88]",
    )
    return parser.parse_args(argv)
