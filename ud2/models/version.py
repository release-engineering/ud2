"""
Pydantic models representing version resources.
"""

from typing import Optional

from .compat import StrictModel, Field


class VersionBase(StrictModel):
    """
    Base model for version resources.
    """

    version: str
    architecture: Optional[str] = None
    cpe: Optional[str] = None
    platform: Optional[str] = None
    visibility: Optional[str] = None


class VersionCreate(VersionBase):
    """
    Capture the payload for creating a product version.

    :param version: Version string (for example, '8.5').
    :param architecture: Optional architecture string.
    :param cpe: Optional Common Platform Enumeration value.
    :param platform: Optional platform descriptor.
    :param visibility: Optional visibility marker.
    """

    pass


class Version(VersionBase):
    """
    Represent the product version data returned by the API.

    :param id: Database identifier.
    :param product_id: Owning product identifier.
    :param version: Version string (for example, '8.5').
    :param architecture: Optional architecture string.
    :param cpe: Optional Common Platform Enumeration value.
    :param platform: Optional platform descriptor.
    :param visibility: Optional visibility marker.
    """

    id: int
    product_id: int = Field(
        alias='productId',
        serialization_alias='productId',
    )


# The end.
