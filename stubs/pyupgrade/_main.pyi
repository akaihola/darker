"""Type stubs for bits used from `pyupgrade._main`.

Can be removed if https://github.com/asottile/pyupgrade/issues/977 is resolved.

"""

from typing import Sequence

from pyupgrade._data import Settings

def _fix_plugins(contents_text: str, settings: Settings) -> str: ...
def _fix_tokens(contents_text: str) -> str: ...
def main(argv: Sequence[str] | None = None) -> int: ...
