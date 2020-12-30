from argparse import ArgumentParser, Namespace
from typing import List, Tuple

from darker.argparse_helpers import LogLevelAction, NewlinePreservingFormatter
from darker.config import (
    DarkerConfig,
    get_effective_config,
    get_modified_config,
    load_config,
)
from darker.version import __version__

ISORT_INSTRUCTION = "Please run `pip install 'darker[isort]'`"


def make_argument_parser(require_src: bool) -> ArgumentParser:
    """Create the argument parser object

    :param require_src: ``True`` to require at least one path as a positional argument
                        on the command line. ``False`` to not require on.

    """
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
    parser.register("action", "log_level", LogLevelAction)
    parser.add_argument(
        "src",
        nargs="+" if require_src else "*",
        help="Path(s) to the Python source file(s) to reformat",
        metavar="PATH",
    )
    parser.add_argument(
        "-r",
        "--revision",
        default="HEAD",
        help=(
            "Git revision against which to compare the working tree. Tags, branch"
            " names, commit hashes, and other expressions like HEAD~5 work here. Also"
            " a range like master...HEAD or master... can be used to compare the best"
            " common ancestor. With the magic value :PRE-COMMIT:, Darker expects the"
            " revision range from the PRE_COMMIT_FROM_REF and PRE_COMMIT_TO_REF"
            " environment variables."
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
        action="log_level",
        const=-10,
        help="Show steps taken and summarize modifications",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="log_level",
        action="log_level",
        const=10,
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
    return parser


def parse_command_line(argv: List[str]) -> Tuple[Namespace, DarkerConfig, DarkerConfig]:
    """Return the parsed command line, using defaults from a configuration file

    Also return the effective configuration which combines defaults, the configuration
    read from ``pyproject.toml`` (or the path given in ``--config``), and command line
    arguments.

    Finally, also return the set of configuration options which differ from defaults.

    """
    # 1. Parse the paths of files/directories to process into `args.src`.
    parser_for_srcs = make_argument_parser(require_src=False)
    args = parser_for_srcs.parse_args(argv)

    # 2. Locate `pyproject.toml` based on those paths, or in the current directory if no
    #    paths were given. Load Darker configuration from it.
    config = load_config(args.src)

    # 3. Use configuration as defaults for re-parsing command line arguments, and don't
    #    require file/directory paths if they are specified in configuration.
    parser = make_argument_parser(require_src=not config.get("src"))
    parser.set_defaults(**config)
    args = parser.parse_args(argv)

    # 4. Also create a parser which uses the original default configuration values.
    #    This is used to find out differences between the effective configuration and
    #    default configuration values, and print them out in verbose mode.
    parser_with_original_defaults = make_argument_parser(require_src=True)
    return (
        args,
        get_effective_config(args),
        get_modified_config(parser_with_original_defaults, args),
    )
