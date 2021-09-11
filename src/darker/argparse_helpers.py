"""Custom formatter and action for argparse"""

import logging
import re
import sys
from argparse import SUPPRESS, Action, ArgumentParser, HelpFormatter, Namespace
from textwrap import fill
from typing import Any, List, Optional, Sequence, Union

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


class OptionsForReadmeAction(Action):
    """Implementation of the ``--options-for-readme`` argument

    This argparse action prints optional command line arguments in a format suitable for
    inclusion in ``README.rst``.

    """

    # pylint: disable=too-few-public-methods

    def __init__(
        self, option_strings: List[str], dest: str = SUPPRESS, help: str = None
    ):  # pylint: disable=redefined-builtin
        super().__init__(option_strings, dest, 0)

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: Optional[Union[str, Sequence[Any]]],
        option_string: str = None,
    ) -> None:
        optional_arguments_group = next(
            group
            for group in parser._action_groups
            if group.title == "optional arguments"
        )
        actions = []
        for action in optional_arguments_group._group_actions:
            if action.dest in {"help", "version", "options_for_readme"}:
                continue
            if action.help is not None:
                action.help = action.help.replace("`", "``")
            actions.append(action)
        formatter = HelpFormatter(parser.prog, max_help_position=7, width=88)
        formatter.add_arguments(actions)
        sys.stderr.write(formatter.format_help())
        parser.exit()


class LogLevelAction(Action):  # pylint: disable=too-few-public-methods
    """Support for command line actions which increment/decrement the log level"""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        option_strings: List[str],
        dest: str,
        const: int,
        default: int = logging.WARNING,
        required: bool = False,
        help: str = None,  # pylint: disable=redefined-builtin
        metavar: str = None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            const=const,
            default=default,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: str = None,
    ) -> None:
        assert isinstance(values, list)
        assert all(isinstance(v, str) for v in values)
        current_level = getattr(namespace, self.dest, self.default)
        new_level = current_level + self.const
        new_level = max(new_level, logging.DEBUG)
        new_level = min(new_level, logging.CRITICAL)
        setattr(namespace, self.dest, new_level)
