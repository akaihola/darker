"""Exceptions which are used in multiple Darker modules"""


class DependencyError(Exception):
    """Parent class for exceptions about problems with dependencies of Darker"""


class IncompatiblePackageError(DependencyError):
    """Raised if an incompatible version of a required or optional package is found"""


class MissingPackageError(DependencyError):
    """Raised if a required or optional package is needed but is missing"""
