import logging
from pathlib import Path
from typing import List

try:
    from isort import SortImports
except ImportError:
    SortImports = None

logger = logging.getLogger(__name__)


def apply_isort(srcs: List[Path]) -> None:
    for src in srcs:
        logger.debug(
            f"SortImports({str(src)!r}, multi_line_output=3, "
            f"include_trailing_comma=True, force_grid_wrap=0, use_parentheses=True,"
            f" line_length=88, quiet=True)"
        )
        _ = SortImports(
            str(src),
            multi_line_output=3,
            include_trailing_comma=True,
            force_grid_wrap=0,
            use_parentheses=True,
            line_length=88,
            quiet=True,
        )
