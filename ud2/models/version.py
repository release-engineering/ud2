"""
Pydantic models representing version resources.
"""

from typing import Optional, Union

from .compat import StrictModel, Field, field_validator
from .enums import Architecture, Visibility, coerce_enum

VisibilityValue = Union[Visibility, str]
ArchitectureValue = Union[Architecture, str]


class VersionBase(StrictModel):
    """
    Base model for version resources.
    """

    version: str
    sort_version: Optional[str] = None
    architecture: Optional[ArchitectureValue] = None
    cpe: Optional[str] = None
    platform: Optional[str] = None
    visibility: Optional[VisibilityValue] = None

    @field_validator('architecture', mode='before')
    def _coerce_architecture(cls, value: Optional[str]) -> Optional[ArchitectureValue]:
        return coerce_enum(Architecture, value)

    @field_validator('visibility', mode='before')
    def _coerce_visibility(cls, value: Optional[str]) -> Optional[VisibilityValue]:
        return coerce_enum(Visibility, value)


class VersionCreate(VersionBase):
    """
    Capture the payload for creating a product version.

    :param version: Version string (for example, '8.5').
    :param sort_version: Optional string for API ordering (for example, '8.5.0').
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
    :param sort_version: Optional string the API uses for ordering.
    :param architecture: Optional architecture string.
    :param cpe: Optional Common Platform Enumeration value.
    :param platform: Optional platform descriptor.
    :param visibility: Optional visibility marker.
    """

    id: int
    product_id: int = Field(alias='productId')


# The end.
