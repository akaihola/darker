"""Wrapper for applying `pyupgrade` on Python source code"""

from darker.utils import TextDocument

try:
    from pyupgrade import _main as pyupgrade_main
except ImportError:
    # `pyupgrade` is an optional dependency. Prevent the `ImportError` if it's missing.
    pyupgrade_main = None


__all__ = ["apply_pyupgrade", "pyupgrade_main"]


def apply_pyupgrade(content: TextDocument) -> TextDocument:
    """Upgrade syntax to newer version of Python using `pyupgrade`

    :param content: The Python source code to upgrade
    :return: The upgraded Python source code

    """
    # pylint: disable=protected-access
    min_version = (3, 6)
    result = pyupgrade_main._fix_plugins(
        content.string, pyupgrade_main.Settings(min_version=min_version)
    )
    result = pyupgrade_main._fix_tokens(result, min_version)
    result = pyupgrade_main._fix_py36_plus(result, min_version=min_version)
    return TextDocument.from_str(result)
