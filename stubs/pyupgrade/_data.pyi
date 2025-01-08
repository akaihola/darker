"""Type stubs for bits used from `pyupgrade._data`.

Can be removed if https://github.com/asottile/pyupgrade/issues/977 is resolved.

"""

from typing import NamedTuple

Version = tuple[int, ...]

class Settings(NamedTuple):
    min_version: Version = ...
    keep_percent_format: bool = ...
    keep_mock: bool = ...
    keep_runtime_typing: bool = ...
