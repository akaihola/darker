import logging
from pathlib import Path

try:
    from isort import SortImports
except ImportError:
    SortImports = None

logger = logging.getLogger(__name__)


def apply_isort(src: Path) -> None:
    logger.debug(
        f"SortImports({str(src)!r}, multi_line_output=3, include_trailing_comma=True,"
        " force_grid_wrap=0, use_parentheses=True,"
        " line_length=88)"
    )
    _ = SortImports(
        src,
        multi_line_output=3,
        include_trailing_comma=True,
        force_grid_wrap=0,
        use_parentheses=True,
        line_length=88,
    )
