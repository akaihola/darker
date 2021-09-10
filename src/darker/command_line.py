"""Command line parsing for the ``darker`` binary"""

from argparse import SUPPRESS, ArgumentParser, Namespace
from typing import Any, List, Optional, Text, Tuple

from darker import help as hlp
from darker.argparse_helpers import (
    LogLevelAction,
    NewlinePreservingFormatter,
    OptionsForReadmeAction,
)
from darker.config import (
    DarkerConfig,
    OutputMode,
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
        description=hlp.DESCRIPTION, formatter_class=NewlinePreservingFormatter
    )
    parser.register("action", "log_level", LogLevelAction)

    def add_arg(help_text: Optional[Text], *name_or_flags: Text, **kwargs: Any) -> None:
        kwargs["help"] = help_text
        parser.add_argument(*name_or_flags, **kwargs)

    add_arg(hlp.SRC, "src", nargs="+" if require_src else "*", metavar="PATH")
    add_arg(hlp.REVISION, "-r", "--revision", default="HEAD", metavar="REV")
    add_arg(hlp.DIFF, "--diff", action="store_true")
    add_arg(hlp.STDOUT, "-d", "--stdout", action="store_true")
    add_arg(hlp.CHECK, "--check", action="store_true")
    add_arg(hlp.ISORT, "-i", "--isort", action="store_true")
    add_arg(hlp.LINT, "-L", "--lint", action="append", metavar="CMD", default=[])
    add_arg(hlp.CONFIG, "-c", "--config", metavar="PATH")
    add_arg(
        hlp.VERBOSE,
        "-v",
        "--verbose",
        action="log_level",
        dest="log_level",
        const=-10,
    )
    add_arg(hlp.QUIET, "-q", "--quiet", action="log_level", dest="log_level", const=10)
    add_arg(hlp.VERSION, "--version", action="version", version=__version__)
    add_arg(
        hlp.SKIP_STRING_NORMALIZATION,
        "-S",
        "--skip-string-normalization",
        action="store_const",
        const=True,
    )
    add_arg(
        hlp.NO_SKIP_STRING_NORMALIZATION,
        "--no-skip-string-normalization",
        action="store_const",
        dest="skip_string_normalization",
        const=False,
    )
    add_arg(
        hlp.SKIP_MAGIC_TRAILING_COMMA,
        "--skip-magic-trailing-comma",
        action="store_const",
        dest="skip_magic_trailing_comma",
        const=True,
    )
    add_arg(
        hlp.LINE_LENGTH,
        "-l",
        "--line-length",
        type=int,
        dest="line_length",
        metavar="LENGTH",
    )
    # A hidden option for printing command lines option in a format suitable for
    # `README.rst`:
    add_arg(SUPPRESS, "--options-for-readme", action=OptionsForReadmeAction)
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

    # 4. Make sure there aren't invalid option combinations after merging configuration
    #    and command line options.
    OutputMode.validate_diff_stdout(args.diff, args.stdout)
    OutputMode.validate_stdout_src(args.stdout, args.src)

    # 5. Also create a parser which uses the original default configuration values.
    #    This is used to find out differences between the effective configuration and
    #    default configuration values, and print them out in verbose mode.
    parser_with_original_defaults = make_argument_parser(require_src=True)
    return (
        args,
        get_effective_config(args),
        get_modified_config(parser_with_original_defaults, args),
    )
