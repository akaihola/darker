"""Data structures configuring Darker and formatter plugin behavior."""

from enum import Enum


class TargetVersion(Enum):
    """Python version numbers."""

    PY33 = 3
    PY34 = 4
    PY35 = 5
    PY36 = 6
    PY37 = 7
    PY38 = 8
    PY39 = 9
    PY310 = 10
    PY311 = 11
    PY312 = 12
    PY313 = 13
