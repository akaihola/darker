import logging
from pathlib import Path
from typing import List, cast

try:
    from isort import SortImports
except ImportError:
    SortImports = None

logger = logging.getLogger(__name__)


def apply_isort(content: str) -> str:
    logger.debug(
        "SortImports(file_contents=..., check=True, multi_line_output=3, "
        "include_trailing_comma=True, force_grid_wrap=0, use_parentheses=True, "
        "line_length=88, quiet=True)"
    )
    result = SortImports(
        file_contents=content,
        check=True,
        multi_line_output=3,
        include_trailing_comma=True,
        force_grid_wrap=0,
        use_parentheses=True,
        line_length=88,
        quiet=True,
    )
    return cast(str, result.output)
