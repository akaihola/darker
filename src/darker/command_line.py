"""Command line parsing for the ``darker`` binary"""

from argparse import ArgumentParser
from functools import partial

from black import TargetVersion

import darkgraylib.command_line
from darker import help as hlp
from darkgraylib.command_line import add_parser_argument
from graylint.command_line import add_lint_arg


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
        " other tools like `flynt`, `mypy`, `pylint` or `flake8` won't use this"
        " configuration file.",
    )

    add_arg = partial(add_parser_argument, parser)

    add_arg(hlp.DIFF, "--diff", action="store_true")
    add_arg(hlp.STDOUT, "-d", "--stdout", action="store_true")
    add_arg(hlp.CHECK, "--check", action="store_true")
    add_arg(hlp.FLYNT, "-f", "--flynt", action="store_true")
    add_arg(hlp.ISORT, "-i", "--isort", action="store_true")
    add_lint_arg(parser)
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
    return parser
