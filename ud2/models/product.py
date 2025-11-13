"""
Pydantic models representing product resources.
"""

from typing import Optional, Union

from .compat import StrictModel, field_validator
from .enums import Architecture, coerce_enum

ArchitectureValue = Union[Architecture, str]


class ProductBase(StrictModel):
    """
    Base model for product resources.

    :param eng_id: Engineering identifier assigned to the product.
    :param name: Human-readable product name.
    :param arch: Optional architecture string.
    :param category: Optional category descriptor.
    :param product_code: Optional product code.
    :param product_group: Optional group identifier.
    :param product_group_name: Optional group name.
    """

    eng_id: int
    name: str
    arch: Optional[ArchitectureValue] = None
    category: Optional[str] = None
    product_code: Optional[str] = None
    product_group: Optional[str] = None
    product_group_name: Optional[str] = None

    @field_validator('arch', mode='before')
    def _coerce_architecture(cls, value: Optional[str]) -> Optional[ArchitectureValue]:
        return coerce_enum(Architecture, value)

    @field_validator('product_code', mode='before')
    def _normalize_product_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        return normalized.upper()


class ProductCreate(ProductBase):
    """
    Capture the payload for creating a product.

    :param eng_id: Engineering identifier assigned to the product.
    :param name: Human-readable product name.
    :param arch: Optional architecture string.
    :param category: Optional category descriptor.
    :param product_code: Optional product code.
    :param product_group: Optional group identifier.
    :param product_group_name: Optional group name.
    """

    pass


class Product(ProductBase):
    """
    Represent the product data returned by the API.

    :param id: Database identifier.
    :param eng_id: Engineering identifier assigned to the product.
    :param name: Human-readable product name.
    :param arch: Optional architecture string.
    :param category: Optional category descriptor.
    :param product_code: Optional product code.
    :param product_group: Optional group identifier.
    :param product_group_name: Optional group name.
    """

    id: int


# The end.
