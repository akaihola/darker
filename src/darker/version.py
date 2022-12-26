__all__ = ('__version__',)

from pbr.version import VersionInfo

# Check the PBR version module docs for other options than release_string()
__version__ = VersionInfo('<my_package>').release_string()
