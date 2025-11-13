""
"Factory helpers for UD model unit tests."
""


from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, Optional

from ud2.models.compat import BaseModel
from ud2.models.enums import Architecture, Platform, Visibility
from ud2.models.pagination import PaginatedProducts, PaginatedRepositories
from ud2.models.product import Product, ProductCreate
from ud2.models.repository import Repository, RepositoryCreate
from ud2.models.version import Version, VersionCreate

__all__ = (
    'DEFAULT_SHA256',
    'DEFAULT_TIMESTAMP',
    'dump_model',
    'make_product_create',
    'make_product',
    'make_version_create',
    'make_version',
    'make_repository_create',
    'make_repository',
    'make_paginated_products',
    'make_paginated_repositories',
)


DEFAULT_SHA256 = 'f' * 64
DEFAULT_TIMESTAMP = datetime(2024, 1, 1, tzinfo=timezone.utc)


def dump_model(model: BaseModel) -> Dict[str, Any]:
    """
    Serialize a model using API-friendly aliases.
    """

    return _normalize(model.model_dump(by_alias=True, exclude_none=True))


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, list):
        return [_normalize(item) for item in value]

    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}

    return value


def make_product_create(**overrides: Any) -> ProductCreate:
    """
    Construct a ProductCreate instance with sensible defaults for testing.
    """

    payload = {
        'eng_id': 101,
        'name': 'Test Product',
        'arch': Architecture.X86_64,
        'category': 'Operating System',
        'product_code': 'TESTPROD',
        'product_group': 'TEST',
        'product_group_name': 'Test Group',
    }
    payload.update(overrides)
    return ProductCreate.model_validate(payload)


def make_product(**overrides: Any) -> Product:
    """
    Construct a Product instance with sensible defaults for testing.
    """

    base = dump_model(make_product_create())
    base.setdefault('id', 1)
    base.update(overrides)
    return Product.model_validate(base)


def make_version_create(**overrides: Any) -> VersionCreate:
    """
    Construct a VersionCreate instance with sensible defaults for testing.
    """

    payload = {
        'version': '1.0',
        'architecture': Architecture.X86_64,
        'cpe': 'cpe:/o:test',
        'platform': Platform.LINUX,
        'visibility': Visibility.VISIBLE,
    }
    payload.update(overrides)
    return VersionCreate.model_validate(payload)


def make_version(**overrides: Any) -> Version:
    """
    Construct a Version instance with sensible defaults for testing.
    """

    base = dump_model(make_version_create())
    base.setdefault('id', 1)
    base.setdefault('productId', 1)
    base.update(overrides)
    return Version.model_validate(base)


def make_repository_create(**overrides: Any) -> RepositoryCreate:
    """
    Construct a RepositoryCreate instance with sensible defaults for testing.
    """

    payload = {
        'description': 'Installer media',
        'file_name': 'installer.iso',
        'file_size': 4096,
        'sha256': DEFAULT_SHA256,
        'content_types': ['binary'],
        'installation': 'Run installer',
        'long_description': 'Detailed installation steps.',
    }
    payload.update(overrides)
    return RepositoryCreate.model_validate(payload)


def make_repository(**overrides: Any) -> Repository:
    """
    Construct a Repository instance with sensible defaults for testing.
    """

    base = dump_model(make_repository_create())
    base.setdefault('id', 1)
    base.setdefault('productName', 'Test Product')
    base.setdefault('productVersion', '1.0')
    base.setdefault('publishDate', DEFAULT_TIMESTAMP.isoformat())
    base.setdefault('updateDate', DEFAULT_TIMESTAMP.isoformat())
    base.update(overrides)
    return Repository.model_validate(base)


def make_paginated_products(
        products: Optional[Iterable[Product]] = None,
        **overrides: Any) -> PaginatedProducts:
    """
    Construct a PaginatedProducts instance for testing.
    """

    product_list = list(products) if products is not None else []
    payload = {
        'data': [dump_model(product) for product in product_list],
        'limit': overrides.pop('limit', max(len(product_list), 1)),
        'page': overrides.pop('page', 1),
        'total': overrides.pop('total', len(product_list)),
        'total_pages': overrides.pop('total_pages', 1 if product_list else 0),
    }
    payload.update(overrides)
    return PaginatedProducts.model_validate(payload)


def make_paginated_repositories(
        repositories: Optional[Iterable[Repository]] = None,
        **overrides: Any) -> PaginatedRepositories:
    """
    Construct a PaginatedRepositories instance for testing.
    """

    repository_list = list(repositories) if repositories is not None else []
    payload = {
        'data': [dump_model(repository) for repository in repository_list],
        'limit': overrides.pop('limit', max(len(repository_list), 1)),
        'page': overrides.pop('page', 1),
        'total': overrides.pop('total', len(repository_list)),
        'total_pages': overrides.pop('total_pages', 1 if repository_list else 0),
    }
    payload.update(overrides)
    return PaginatedRepositories.model_validate(payload)


# The end.
