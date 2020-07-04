import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, cast

from black import find_project_root

try:
    from isort.api import sort_stream as SortImports
    import isort.settings as isort_settings
except ImportError:
    SortImports = None
    isort_settings = None

logger = logging.getLogger(__name__)

IsortSettings = Dict[str, Union[bool, int, List[str], str, Tuple[str], None]]


def get_isort_settings(src: Optional[Path], config: Optional[str]) -> IsortSettings:
    if src and config is None:
        project_root = find_project_root((str(src),))
        settings: IsortSettings = isort_settings.from_path(str(project_root))
        return settings

    computed_settings: IsortSettings = isort_settings.default.copy()
    if config:
        isort_settings._update_with_config_file(
            config, ('tool.isort',), computed_settings
        )
    return computed_settings


def apply_isort(
    content: str,
    src: Optional[Path] = None,
    config: Optional[str] = None,
    line_length: Optional[int] = None,
) -> str:
    isort_settings = get_isort_settings(src, config)
    if line_length:
        isort_settings["line_length"] = line_length

    logger.debug(
        "SortImports(file_contents=..., check=True, {})".format(
            ", ".join(f"{k}={v}" for k, v in isort_settings.items())
        )
    )
    result = io.StringIO()
    SortImports(io.StringIO(content), result, check=True, **isort_settings)
    return result.getvalue()
