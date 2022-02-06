"""Functions for maintaining compatibility with multiple Black versions"""

from pathlib import Path
from typing import Any, Sequence, Tuple, cast

from black import find_project_root as black_find_project_root


def find_project_root(srcs: Sequence[str]) -> Path:
    """Hide changed return value type in Black behind this wrapper

    :param srcs: Files and directories to find the common root for
    :return: Project root path

    """
    root = cast(Any, black_find_project_root(tuple(srcs or ["."])))
    if isinstance(root, tuple):
        # Black >= 22.1
        return cast(Tuple[Path], root)[0]
    # Black < 22
    return cast(Path, root)
