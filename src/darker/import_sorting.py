import logging
import sys
from pathlib import Path
from typing import Any, Optional

from black import find_project_root

from darker.exceptions import IncompatiblePackageError, MissingPackageError
from darker.utils import TextDocument

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


try:
    import isort

    # Work around Mypy problem
    # https://github.com/python/mypy/issues/7030#issuecomment-504128883
    try:
        isort_code = getattr(isort, "code")
    except AttributeError:
        # Postpone error message about incompatbile `isort` version until `--isort` is
        # actually used.
        def isort_code(*args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
            """Fake `isort.code()` function to use when `isort < 5` is installed"""
            raise IncompatiblePackageError(
                "An incompatible 'isort' package was found. Please install version"
                " 5.0.0 or later."
            )
except ImportError:
    # `isort` is an optional dependency. Prevent the `ImportError` if it's missing.
    isort = None  # type: ignore

    def isort_code(*args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
        """Fake `isort.code()` function to use when `isort` isn't installed"""
        raise MissingPackageError(
            "No module named 'isort'. Please install the 'isort' package before using"
            " the --isort / -i option."
        )


__all__ = ["apply_isort", "isort"]

logger = logging.getLogger(__name__)


class IsortArgs(TypedDict, total=False):
    line_length: int
    settings_file: str
    settings_path: str


def apply_isort(
    content: TextDocument,
    src: Path,
    config: Optional[str] = None,
    line_length: Optional[int] = None,
) -> TextDocument:
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
    return TextDocument.from_str(
        isort_code(code=content.string, **isort_args),
        encoding=content.encoding,
        mtime=content.mtime,
    )
