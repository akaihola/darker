from argparse import ArgumentParser, Namespace
from typing import List

from darker.argparse_helpers import NewlinePreservingFormatter
from darker.version import __version__

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
    parser.add_argument(
        "src",
        nargs="+",
        help="Path(s) to the Python source file(s) to reformat",
        metavar="PATH",
    )
    parser.add_argument(
        "-r",
        "--revision",
        default="HEAD",
        help=(
            "Git revision against which to compare the working tree. Tags, branch"
            " names, commit hashes, and other expressions like HEAD~5 work here."
        ),
    )
    isort_help = ["Also sort imports using the `isort` package"]
    if not isort:
        isort_help.append(f". {ISORT_INSTRUCTION} to enable usage of this option.")
    parser.add_argument(
        "--diff",
        action="store_true",
        help=(
            "Don't write the files back, just output a diff for each file on stdout."
            " Highlight syntax on screen if the `pygments` package is available."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Don't write the files back, just return the status.  Return code 0 means"
            " nothing would change.  Return code 1 means some files would be"
            " reformatted."
        ),
    )
    parser.add_argument(
        "-i", "--isort", action="store_true", help="".join(isort_help),
    )
    parser.add_argument(
        "-L",
        "--lint",
        action="append",
        metavar="CMD",
        type=lambda s: s.split(),
        default=[],
        help=(
            "Also run a linter on changed files. CMD can be a name of path of the "
            "linter binary, or a full quoted command line"
        ),
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
        "--version",
        action="version",
        version=__version__,
        help="Show the version of `darker`",
    )
    parser.add_argument(
        "-S",
        "--skip-string-normalization",
        action="store_const",
        const=True,
        dest="skip_string_normalization",
        help="Don't normalize string quotes or prefixes",
    )
    parser.add_argument(
        "--no-skip-string-normalization",
        action="store_const",
        const=False,
        dest="skip_string_normalization",
        help=(
            "Normalize string quotes or prefixes. This can be used to override"
            " `skip_string_normalization = true` from a configuration file."
        ),
    )
    parser.add_argument(
        "-l",
        "--line-length",
        type=int,
        dest="line_length",
        help="How many characters per line to allow [default: 88]",
    )
    return parser.parse_args(argv)
