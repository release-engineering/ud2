"""
ud2 package providing the command line interface entry point and shared metadata.
"""


from .client import UDClient
from .config import UDConfig
from .models import (
    Product,
    ProductCreate,
    Repository,
    RepositoryCreate,
    Version,
    VersionCreate,
)


__version__ = "0.1.0"


__all__ = (
    "UDClient",
    "UDConfig",
    "Product",
    "ProductCreate",
    "Repository",
    "RepositoryCreate",
    "Version",
    "VersionCreate",
)


# The end.
