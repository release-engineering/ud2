"""
Shared pagination response models.
"""


from typing import List

from .compat import StrictModel
from .product import Product
from .repository import Repository
from .version import Version


__all__ = (
    'Pagination',
    'PaginatedProducts',
    'PaginatedRepositories',

    'ResponseVersions',
)


class Pagination(StrictModel):
    """
    Common pagination metadata returned by UD API responses.
    """

    limit: int
    page: int
    total: int
    total_pages: int


class PaginatedProducts(Pagination):
    """
    Paginated response containing product records.
    """

    data: List[Product]


class ResponseVersions(StrictModel):
    """
    Response containing version records. Not actually paginated, but
    vestigially is bundled in a dict with a 'data' key.
    """

    data: List[Version]


class PaginatedRepositories(Pagination):
    """
    Paginated response containing repository records.
    """

    data: List[Repository]


# The end.
