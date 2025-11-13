"""
ud2 package providing the command line interface entry point and shared metadata.
"""

from importlib import metadata as _metadata


def _detect_version() -> str:
    """
    Resolve the distribution version as recorded by setuptools.

    :returns: The version string, or the fallback declared in the source package metadata.
    """
    try:
        return _metadata.version("ud2")
    except _metadata.PackageNotFoundError:
        return "0.1.0"


__version__ = _detect_version()


# The end.
