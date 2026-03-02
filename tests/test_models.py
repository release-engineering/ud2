""
"Unit tests covering model enumerations, validators, and pagination types."
""


import unittest
from datetime import datetime, timezone

from ud2.models import (Architecture, PaginatedProducts, PaginatedRepositories,
                        Product, ProductCreate, Repository, RepositoryCreate,
                        VersionCreate, Visibility)

from . import (DEFAULT_SHA256, dump_model, make_product, make_product_create,
               make_repository)


class TestProductModels(unittest.TestCase):
    def test_architecture_coerces_to_enum(self) -> None:
        model = ProductCreate.model_validate(
            {
                'eng_id': 1,
                'name': 'Test',
                'arch': 'x86_64',
            },
        )
        self.assertEqual(model.arch, Architecture.X86_64)

    def test_architecture_preserves_unknown_values(self) -> None:
        model = ProductCreate.model_validate(
            {
                'eng_id': 1,
                'name': 'Test',
                'arch': 'armv9-custom',
            },
        )
        self.assertEqual(model.arch, 'armv9-custom')

    def test_product_code_normalization(self) -> None:
        model = make_product_create(product_code='  demo ')
        self.assertEqual(model.product_code, 'DEMO')


class TestVersionModels(unittest.TestCase):
    def test_visibility_coerces_to_enum(self) -> None:
        model = VersionCreate.model_validate(
            {
                'version': '1.0',
                'visibility': 'visible',
            },
        )
        self.assertEqual(model.visibility, Visibility.VISIBLE)

    def test_platform_preserves_unknown_values(self) -> None:
        model = VersionCreate.model_validate(
            {
                'version': '1.0',
                'platform': 'solaris',
            },
        )
        self.assertEqual(model.platform, 'solaris')


class TestRepositoryModels(unittest.TestCase):
    def test_sha256_validation_enforces_length(self) -> None:
        with self.assertRaises(ValueError):
            RepositoryCreate.model_validate(
                {
                    'description': 'Invalid',
                    'file_name': 'artifact.iso',
                    'file_size': 2048,
                    'sha256': 'abc123',
                },
            )

    def test_repository_dates_parse_iso_strings(self) -> None:
        repository = Repository.model_validate(
            {
                'id': 1,
                'description': 'Installer',
                'fileName': 'installer.iso',
                'fileSize': 4096,
                'sha256': DEFAULT_SHA256,
                'md5': 'a' * 32,
                'issues': [],
                'visibility': 'visible',
                'classifier': [],
                'publishDate': '2024-01-02T03:04:05Z',
                'updateDate': '2024-01-03T06:07:08+02:00',
            },
        )
        self.assertIsInstance(repository.publish_date, datetime)
        self.assertEqual(
            repository.publish_date,
            datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        self.assertIsInstance(repository.update_date, datetime)


class TestPaginationModels(unittest.TestCase):
    def test_paginated_products_deserializes_data(self) -> None:
        page = PaginatedProducts.model_validate(
            {
                'data': [dump_model(make_product())],
                'limit': 10,
                'page': 1,
                'total': 1,
                'total_pages': 1,
            },
        )
        self.assertIsInstance(page, PaginatedProducts)
        self.assertIsInstance(page.data[0], Product)

    def test_paginated_repositories_deserializes_data(self) -> None:
        repository = make_repository()
        page = PaginatedRepositories.model_validate(
            {
                'data': [dump_model(repository)],
                'limit': 5,
                'page': 1,
                'total': 1,
                'total_pages': 1,
            },
        )
        self.assertIsInstance(page, PaginatedRepositories)
        self.assertIsInstance(page.data[0], Repository)


# The end.
