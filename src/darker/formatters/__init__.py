"""Built-in code re-formatter plugins."""

from __future__ import annotations

import sys
from importlib.metadata import EntryPoint, entry_points
from typing import cast

from darker.formatters.base_formatter import BaseFormatter

ENTRY_POINT_GROUP = "darker.formatter"


def get_formatter_entry_points(name: str | None = None) -> tuple[EntryPoint, ...]:
    """Get the entry points of all built-in code re-formatter plugins."""
    if sys.version_info < (3, 10):
        return tuple(
            ep
            for ep in entry_points()[ENTRY_POINT_GROUP]
            if not name or ep.name == name
        )
    if name:
        result = entry_points(group=ENTRY_POINT_GROUP, name=name)
    else:
        result = entry_points(group=ENTRY_POINT_GROUP)
    return cast(tuple[EntryPoint, ...], result)


def get_formatter_names() -> list[str]:
    """Get the names of all built-in code re-formatter plugins."""
    return [ep.name for ep in get_formatter_entry_points()]


def create_formatter(name: str) -> BaseFormatter:
    """Create a code re-formatter plugin instance by name."""
    matching_entry_points = get_formatter_entry_points(name)
    formatter_class = next(iter(matching_entry_points)).load()
    return cast(BaseFormatter, formatter_class())
