import logging
import sys
from pathlib import Path
from typing import Optional

from black import find_project_root

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


try:
    import isort
except ImportError:
    isort = None

logger = logging.getLogger(__name__)


class IsortArgs(TypedDict, total=False):
    line_length: int
    settings_file: str
    settings_path: str


def apply_isort(
    content: str,
    src: Path,
    config: Optional[str] = None,
    line_length: Optional[int] = None,
) -> str:
    isort_args = IsortArgs()
    if config:
        isort_args["settings_file"] = config
    else:
        isort_args["settings_path"] = str(find_project_root((str(src),)))
    if line_length:
        isort_args["line_length"] = line_length

    logger.debug(
        "isort.code(code=..., {})".format(
            ", ".join(f"{k}={v!r}" for k, v in isort_args.items())
        )
    )
    result: str = isort.code(code=content, **isort_args)
    return result
