"""
Pydantic models representing product resources.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
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

    model_config = ConfigDict(extra='forbid')

    eng_id: int
    name: str
    arch: Optional[str] = None
    category: Optional[str] = None
    product_code: Optional[str] = None
    product_group: Optional[str] = None
    product_group_name: Optional[str] = None


class Product(BaseModel):
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

    model_config = ConfigDict(extra='forbid')

    id: int
    eng_id: int
    name: str
    arch: Optional[str] = None
    category: Optional[str] = None
    product_code: Optional[str] = None
    product_group: Optional[str] = None
    product_group_name: Optional[str] = None


# The end.
