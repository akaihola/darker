"""Command line parsing for the ``darker`` binary"""

import warnings
from argparse import ArgumentParser, Namespace
from functools import partial
from typing import List, Optional, Tuple

import darkgraylib.command_line
from darker import help as hlp
from darker.config import (
    DEPRECATED_CONFIG_OPTIONS,
    REMOVED_CONFIG_OPTIONS,
    DarkerConfig,
    OutputMode,
)
from darker.configuration.target_version import TargetVersion
from darker.formatters import get_formatter_names
from darker.version import __version__
from darkgraylib.command_line import add_parser_argument
from darkgraylib.config import ConfigurationError


def make_argument_parser(require_src: bool) -> ArgumentParser:
    """Create the argument parser object

    :param require_src: ``True`` to require at least one path as a positional argument
                        on the command line. ``False`` to not require on.

    """
    parser = darkgraylib.command_line.make_argument_parser(
        require_src,
        "Darker",
        hlp.DESCRIPTION,
        "Make `darker`, `black` and `isort` read configuration from `PATH`. Note that"
        " other tools like `flynt` won't use this configuration file.",
        __version__,
    )

    add_arg = partial(add_parser_argument, parser)

    add_arg(hlp.DIFF, "--diff", action="store_true")
    add_arg(hlp.STDOUT, "-d", "--stdout", action="store_true")
    add_arg(hlp.CHECK, "--check", action="store_true")
    add_arg(hlp.FLYNT, "-f", "--flynt", action="store_true")
    add_arg(hlp.ISORT, "-i", "--isort", action="store_true")
    add_arg(hlp.PREVIEW, "--preview", action="store_true")
    add_arg(hlp.LINT, "-L", "--lint", action="append", metavar="CMD", default=[])
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
    add_arg(
        hlp.TARGET_VERSION,
        "-t",
        "--target-version",
        type=str,
        dest="target_version",
        metavar="VERSION",
        choices=[v.name.lower() for v in TargetVersion],
    )
    add_arg(
        hlp.FORMATTER,
        "--formatter",
        default="black",
        choices=get_formatter_names(),
        metavar="FORMATTER",
    )
    return parser


def show_config_deprecations(config: DarkerConfig) -> None:
    """Show deprecation warnings for configuration keys from the config file."""
    removal_messages = {
        REMOVED_CONFIG_OPTIONS[option]
        for option in config
        if option in REMOVED_CONFIG_OPTIONS
    }
    if removal_messages:
        raise ConfigurationError(" ".join(sorted(removal_messages)))
    for option in DEPRECATED_CONFIG_OPTIONS & set(config):
        warnings.warn(
            f"The configuration option `{option}` in [tool.darker] is deprecated"
            " and will be removed in Darker 4.0.",
            DeprecationWarning,
            stacklevel=2,
        )
    if "lint" in config:
        warnings.warn(
            "Baseline linting has been moved to the Graylint package. Please"
            " remove the `lint =` option from your configuration file.",
            DeprecationWarning,
            stacklevel=2,
        )


def parse_command_line(
    argv: Optional[List[str]],
) -> Tuple[Namespace, DarkerConfig, DarkerConfig]:
    """Return the parsed command line, using defaults from a configuration file

    Also return the effective configuration which combines defaults, the configuration
    read from ``pyproject.toml`` (or the path given in ``--config``), environment
    variables, and command line arguments.

    Finally, also return the set of configuration options which differ from defaults.

    :param argv: Command line arguments to parse (excluding the path of the script). If
                 ``None``, use ``sys.argv``.
    :return: A tuple of the parsed command line, the effective configuration, and the
             set of modified configuration options from the defaults.

    """
    args, effective_cfg, modified_cfg = darkgraylib.command_line.parse_command_line(
        make_argument_parser,
        argv,
        "darker",
        DarkerConfig,
        show_config_deprecations,
    )
    OutputMode.validate_diff_stdout(args.diff, args.stdout)
    OutputMode.validate_stdout_src(args.src, args.stdin_filename, stdout=args.stdout)
    return args, effective_cfg, modified_cfg
