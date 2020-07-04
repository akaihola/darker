import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from black import find_project_root

try:
    from isort.api import sort_code_string as SortImports
    import isort.settings as isort_settings
except ImportError:
    SortImports = None
    isort_settings = None

logger = logging.getLogger(__name__)

IsortSettings = Dict[str, Union[bool, int, List[str], str, Tuple[str], None]]


def get_isort_settings(src: Optional[Path], config: Optional[str]) -> IsortSettings:
    if src and config is None:
        project_root = find_project_root((str(src),))
        settings: IsortSettings
        _, settings = isort_settings._find_config(str(project_root))
        return settings

    computed_settings: IsortSettings = {}
    if config:
        computed_settings.update(
            isort_settings._get_config_data(config, ('tool.isort',))
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
    output: str = SortImports(content, **isort_settings)
    return output
