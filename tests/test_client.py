import pathlib
import unittest
from typing import Any, Dict, List, Optional
from unittest import mock

import requests

from ud2.client import UDClient
from ud2.config import UDConfig
from ud2.models import (PaginatedProducts, PaginatedRepositories,
                        PaginatedVersions, Product, Repository, Version)

from . import (DEFAULT_SHA256, dump_model, make_paginated_products,
               make_paginated_repositories, make_paginated_versions,
               make_product, make_product_create, make_repository,
               make_repository_create, make_version, make_version_create)


class StubResponse:
    def __init__(
            self,
            status_code: int = 200,
            headers: Optional[Dict[str, str]] = None,
            json_data: Any = None,
            content: bytes = b'') -> None:

        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("No JSON payload configured.")
        return self._json_data


class StubSession:
    def __init__(self, responses: List[StubResponse]) -> None:
        self._responses = list(responses)
        self.requests: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}
        self.cert: Optional[Any] = None
        self.verify = True

    def request(
            self,
            method: str,
            url: str,
            params: Optional[Dict[str, Any]] = None,
            json: Optional[Dict[str, Any]] = None,
            timeout: Optional[float] = None) -> StubResponse:

        self.requests.append(
            {
                'method': method,
                'url': url,
                'params': params,
                'json': json,
                'timeout': timeout,
            },
        )
        if not self._responses:
            raise AssertionError("No response configured for request.")
        return self._responses.pop(0)


class TestUDClient(unittest.TestCase):

    def setUp(self) -> None:
        self.config = UDConfig(
            name='test',
            base_url='https://downloads.example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )

    def test_page_products_uses_products_endpoint(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_products(
                        products=[],
                        limit=10,
                        page=1,
                        total=0,
                        total_pages=0,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        payload = client.page_products(page=2)

        self.assertEqual(len(session.requests), 1)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products',
        )
        self.assertEqual(captured['params'], {'page': 2})
        self.assertIsInstance(payload, PaginatedProducts)
        self.assertEqual(payload.data, [])
        self.assertEqual(payload.limit, 10)

    def test_list_products_collects_all_pages(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_products(
                        products=[
                            make_product(id=1, name='One'),
                        ],
                        limit=1,
                        page=1,
                        total=2,
                        total_pages=2,
                    ),
                ),
            ),
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_products(
                        products=[
                            make_product(id=2, name='Two'),
                        ],
                        limit=1,
                        page=2,
                        total=2,
                        total_pages=2,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        products = client.list_products(page_size=None)

        self.assertEqual(len(products), 2)
        self.assertTrue(all(isinstance(item, Product) for item in products))
        self.assertEqual({item.id for item in products}, {1, 2})
        self.assertEqual(len(session.requests), 2)
        first_request = session.requests[0]
        second_request = session.requests[1]
        self.assertEqual(first_request['params'], {'page': 1})
        self.assertEqual(second_request['params'], {'page': 2, 'limit': 1})

    def test_create_product_returns_model(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_product(
                        id=10,
                        eng_id=23,
                        name='RHEL',
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        payload = make_product_create(eng_id=23, name='RHEL')
        result = client.create_product(payload)

        self.assertIsInstance(result, Product)
        self.assertEqual(result.id, 10)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'POST')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products',
        )
        self.assertEqual(
            captured['json'],
            payload.model_dump(by_alias=False, exclude_none=True),
        )

    def test_get_product_with_wrapped_response_returns_model(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={
                    'data': dump_model(
                        make_product(
                            id=4852,
                            eng_id=101,
                            name='RHEL',
                        ),
                    ),
                },
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.get_product(product_id=4852)

        self.assertIsInstance(result, Product)
        self.assertEqual(result.id, 4852)
        self.assertEqual(result.eng_id, 101)
        self.assertEqual(result.name, 'RHEL')
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products/4852',
        )

    def test_get_product_with_unwrapped_response_still_validates(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_product(id=1, eng_id=2, name='Unwrapped'),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.get_product(product_id=1)

        self.assertIsInstance(result, Product)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, 'Unwrapped')

    def test_list_product_versions_returns_versions(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={'data': [  # XXX: hack, mismatch from swagger doc
                    {
                        'id': 4,
                        'productId': 10,
                        'version': '9.0',
                    },
                ],}
            ),
        ])
        client = UDClient(config=self.config, session=session)

        response = client.list_product_versions(product_id=10)

        self.assertEqual(len(response), 1)
        self.assertIsInstance(response[0], Version)
        self.assertEqual(response[0].product_id, 10)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products/10/product_versions',
        )

    def test_create_product_version_with_wrapped_response_returns_model(
            self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={
                    'data': dump_model(
                        make_version(id=3, productId=10, version='9.0'),
                    ),
                },
            ),
        ])
        client = UDClient(config=self.config, session=session)
        payload = make_version_create(version='9.0')

        result = client.create_product_version(product_id=10, payload=payload)

        self.assertIsInstance(result, Version)
        self.assertEqual(result.id, 3)
        self.assertEqual(result.version, '9.0')

    def test_get_product_version_uses_product_versions_path(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(make_version(id=3, productId=10, version='9.0')),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.get_product_version(version_id=3)

        self.assertIsInstance(result, Version)
        self.assertEqual(result.id, 3)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/3',
        )

    def test_update_product_version_uses_product_versions_path(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(make_version(id=3, productId=10, version='9.1')),
            ),
        ])
        client = UDClient(config=self.config, session=session)
        payload = make_version_create(version='9.1')

        result = client.update_product_version(version_id=3, payload=payload)

        self.assertIsInstance(result, Version)
        self.assertEqual(result.version, '9.1')
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'PUT')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/3',
        )

    def test_delete_product_version_uses_product_versions_path(self) -> None:
        session = StubSession([
            StubResponse(status_code=204, headers={}),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.delete_product_version(version_id=3)

        self.assertIsNone(result)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'DELETE')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/3',
        )

    def test_create_repository_serializes_payload(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_repository(
                        id=7,
                        description='Installer',
                        file_name='setup.iso',
                        file_size=1024,
                        sha256=DEFAULT_SHA256,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)
        payload = make_repository_create(
            description='Installer',
            file_name='setup.iso',
            file_size=1024,
            sha256=DEFAULT_SHA256,
        )

        repository = client.create_repository(
            product_version_id=3,
            payload=payload,
        )

        self.assertIsInstance(repository, Repository)
        self.assertEqual(repository.id, 7)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'POST')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/3/files',
        )
        self.assertEqual(
            captured['json'],
            payload.model_dump(by_alias=False, exclude_none=True),
        )

    def test_page_repositories_returns_paginated_model(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_repositories(
                        repositories=[],
                        limit=5,
                        page=1,
                        total=0,
                        total_pages=0,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.page_repositories(
            product_version_id=11,
            limit=5,
        )

        self.assertIsInstance(result, PaginatedRepositories)
        self.assertEqual(result.data, [])
        self.assertEqual(result.limit, 5)
        captured = session.requests[0]
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/11/files',
        )
        self.assertEqual(captured['params'], {'limit': 5})

    def test_list_repositories_collects_all_pages(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_repositories(
                        repositories=[
                            make_repository(id=1),
                        ],
                        limit=1,
                        page=1,
                        total=2,
                        total_pages=2,
                    ),
                ),
            ),
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_repositories(
                        repositories=[
                            make_repository(id=2),
                        ],
                        limit=1,
                        page=2,
                        total=2,
                        total_pages=2,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        repositories = client.list_repositories(product_version_id=11, page_size=None)

        self.assertEqual(len(repositories), 2)
        self.assertTrue(all(isinstance(item, Repository) for item in repositories))
        self.assertEqual({item.id for item in repositories}, {1, 2})
        self.assertEqual(len(session.requests), 2)
        first_request = session.requests[0]
        second_request = session.requests[1]
        self.assertEqual(first_request['params'], {'page': 1})
        self.assertEqual(second_request['params'], {'page': 2, 'limit': 1})

    def test_search_products_calls_search_endpoint_with_params(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_products(
                        products=[make_product(id=1, name='RHEL')],
                        limit=10,
                        page=1,
                        total=1,
                        total_pages=1,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.search_products(name='RHEL', eng_id=101)

        self.assertIsInstance(result, PaginatedProducts)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].name, 'RHEL')
        self.assertEqual(len(session.requests), 1)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertIn(
            '/products/search',
            captured['url'],
        )
        self.assertEqual(captured['params']['name'], 'RHEL')
        self.assertEqual(captured['params']['eng_id'], 101)

    def test_search_product_versions_calls_search_endpoint_with_params(
            self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_versions(
                        versions=[make_version(id=1, productId=5, version='8.5')],
                        limit=10,
                        page=1,
                        total=1,
                        total_pages=1,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.search_product_versions(
            version='8.5',
            product_id=5,
        )

        self.assertIsInstance(result, PaginatedVersions)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].version, '8.5')
        self.assertEqual(len(session.requests), 1)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertIn(
            '/product_versions/search',
            captured['url'],
        )
        self.assertEqual(captured['params']['version'], '8.5')
        self.assertEqual(captured['params']['product_id'], 5)

    def test_search_files_calls_search_endpoint_with_params(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=dump_model(
                    make_paginated_repositories(
                        repositories=[
                            make_repository(
                                id=1,
                                description='Installer',
                            ),
                        ],
                        limit=10,
                        page=1,
                        total=1,
                        total_pages=1,
                    ),
                ),
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.search_files(
            product_id=1,
            version_id=2,
        )

        self.assertIsInstance(result, PaginatedRepositories)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].description, 'Installer')
        self.assertEqual(len(session.requests), 1)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertIn(
            '/files/search',
            captured['url'],
        )
        self.assertEqual(captured['params']['product_id'], 1)
        self.assertEqual(captured['params']['version_id'], 2)

    def test_delete_repository_uses_files_endpoint(self) -> None:
        session = StubSession([
            StubResponse(status_code=204, headers={}),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.delete_repository(file_id=5)

        self.assertIsNone(result)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'DELETE')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/files/5',
        )

    def test_request_requires_absolute_path(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={'ok': True},
            ),
        ])
        client = UDClient(config=self.config, session=session)

        with self.assertRaises(ValueError):
            client._GET('products')


class TestUDClientSession(unittest.TestCase):

    def setUp(self) -> None:
        self.session_patcher = mock.patch('ud2.client.requests.Session')
        self.mock_session_cls = self.session_patcher.start()
        self.mock_session = mock.Mock()
        self.mock_session.headers = {}
        self.mock_session.verify = True
        self.mock_session_cls.return_value = self.mock_session

    def tearDown(self) -> None:
        self.session_patcher.stop()

    def test_session_configuration_uses_ca_cert(self) -> None:
        config = UDConfig(
            name='test',
            base_url='https://downloads.example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
            ca_cert=pathlib.Path('/tmp/ca.pem'),
        )

        UDClient(config=config)

        self.mock_session_cls.assert_called_once()
        self.assertEqual(
            self.mock_session.cert,
            (
                str(config.client_cert),
                str(config.client_key),
            ),
        )
        self.assertEqual(
            self.mock_session.headers.get('Accept'),
            'application/json',
        )
        self.assertEqual(
            self.mock_session.headers.get('Content-Type'),
            'application/json',
        )
        self.assertEqual(self.mock_session.verify, str(config.ca_cert))

    def test_session_configuration_uses_verify_flag(self) -> None:
        config = UDConfig(
            name='test',
            base_url='https://downloads.example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=False,
            ca_cert=None,
        )

        UDClient(config=config)

        self.mock_session_cls.assert_called_once()
        self.assertEqual(self.mock_session.verify, False)

    def test_provided_session_is_not_reconfigured(self) -> None:
        config = UDConfig(
            name='test',
            base_url='https://downloads.example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
            ca_cert=None,
        )
        provided_session = mock.Mock()
        provided_session.headers = {'Existing': 'value'}
        provided_session.cert = ('existing-cert', 'existing-key')
        provided_session.verify = 'unchanged'

        UDClient(config=config, session=provided_session)

        self.mock_session_cls.assert_not_called()
        self.assertEqual(
            provided_session.headers,
            {'Existing': 'value'},
        )
        self.assertEqual(
            provided_session.cert,
            ('existing-cert', 'existing-key'),
        )
        self.assertEqual(provided_session.verify, 'unchanged')


# The end.
