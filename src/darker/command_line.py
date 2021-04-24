from argparse import ArgumentParser, Namespace
from typing import List, Tuple

import darker.help
from darker.argparse_helpers import LogLevelAction, NewlinePreservingFormatter
from darker.config import (
    DarkerConfig,
    get_effective_config,
    get_modified_config,
    load_config,
)
from darker.version import __version__


def make_argument_parser(require_src: bool) -> ArgumentParser:
    """Create the argument parser object

    :param require_src: ``True`` to require at least one path as a positional argument
                        on the command line. ``False`` to not require on.

    """
    parser = ArgumentParser(
        description="\n".join(darker.help.DESCRIPTION),
        formatter_class=NewlinePreservingFormatter,
    )
    parser.register("action", "log_level", LogLevelAction)
    parser.add_argument(
        "src",
        nargs="+" if require_src else "*",
        help=darker.help.SRC,
        metavar="PATH",
    )
    parser.add_argument("-r", "--revision", default="HEAD", help=darker.help.REVISION)
    parser.add_argument("--diff", action="store_true", help=darker.help.DIFF)
    parser.add_argument("--check", action="store_true", help=darker.help.CHECK)
    parser.add_argument("-i", "--isort", action="store_true", help=darker.help.ISORT)
    parser.add_argument(
        "-L",
        "--lint",
        action="append",
        metavar="CMD",
        default=[],
        help=darker.help.LINT,
    )
    parser.add_argument("-c", "--config", metavar="PATH", help=darker.help.CONFIG)
    parser.add_argument(
        "-v",
        "--verbose",
        dest="log_level",
        action="log_level",
        const=-10,
        help=darker.help.VERBOSE,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="log_level",
        action="log_level",
        const=10,
        help=darker.help.QUIET,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help=darker.help.VERSION,
    )
    parser.add_argument(
        "-S",
        "--skip-string-normalization",
        action="store_const",
        const=True,
        dest="skip_string_normalization",
        help=darker.help.SKIP_STRING_NORMALIZATION,
    )
    parser.add_argument(
        "--no-skip-string-normalization",
        action="store_const",
        const=False,
        dest="skip_string_normalization",
        help=darker.help.NO_SKIP_STRING_NORMALIZATION,
    )
    parser.add_argument(
        "-l",
        "--line-length",
        type=int,
        dest="line_length",
        help=darker.help.LINE_LENGTH,
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
