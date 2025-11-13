import pathlib
import unittest
from typing import Any, Dict, List, Optional

import requests

from ud2.client import UDClient
from ud2.config import UDConfig
from ud2.models import Product, ProductCreate, Repository, RepositoryCreate, Version


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
        self.cert: Optional[str] = None
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
            certificate=pathlib.Path('/tmp/cert.pem'),
            timeout=5.0,
            verify=True,
        )

    def test_list_products_uses_products_endpoint(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={'data': [], 'page': 1, 'limit': 10},
            ),
        ])
        client = UDClient(config=self.config, session=session)

        payload = client.list_products(params={'page': 2})

        self.assertEqual(len(session.requests), 1)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products',
        )
        self.assertEqual(captured['params'], {'page': 2})
        self.assertEqual(payload['data'], [])

    def test_create_product_returns_model(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={
                    'id': 10,
                    'eng_id': 23,
                    'name': 'RHEL',
                },
            ),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.create_product(ProductCreate(eng_id=23, name='RHEL'))

        self.assertIsInstance(result, Product)
        self.assertEqual(result.id, 10)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'POST')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products',
        )
        self.assertEqual(captured['json'], {'eng_id': 23, 'name': 'RHEL'})

    def test_list_product_versions_coerces_models(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data=[
                    {
                        'id': 4,
                        'productId': 10,
                        'version': '9.0',
                    },
                ],
            ),
        ])
        client = UDClient(config=self.config, session=session)

        versions = client.list_product_versions(product_id=10)

        self.assertEqual(len(versions), 1)
        self.assertIsInstance(versions[0], Version)
        self.assertEqual(versions[0].product_id, 10)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'GET')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/products/10/product_versions',
        )

    def test_create_repository_serializes_aliases(self) -> None:
        session = StubSession([
            StubResponse(
                headers={'Content-Type': 'application/json'},
                json_data={
                    'id': 7,
                    'description': 'Installer',
                    'fileName': 'setup.iso',
                    'fileSize': 1024,
                    'sha256': 'abc123',
                },
            ),
        ])
        client = UDClient(config=self.config, session=session)
        payload = RepositoryCreate(
            description='Installer',
            file_name='setup.iso',
            file_size=1024,
            sha256='abc123',
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
            'https://downloads.example.test/api/product_versions/3/repositories',
        )
        self.assertEqual(
            captured['json'],
            {
                'description': 'Installer',
                'fileName': 'setup.iso',
                'fileSize': 1024,
                'sha256': 'abc123',
            },
        )

    def test_delete_repository_uses_nested_endpoint(self) -> None:
        session = StubSession([
            StubResponse(status_code=204, headers={}),
        ])
        client = UDClient(config=self.config, session=session)

        result = client.delete_repository(
            product_version_id=11,
            repository_id=5,
        )

        self.assertIsNone(result)
        captured = session.requests[0]
        self.assertEqual(captured['method'], 'DELETE')
        self.assertEqual(
            captured['url'],
            'https://downloads.example.test/api/product_versions/11/repositories/5',
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
            client.GET('products')


if __name__ == '__main__':
    unittest.main()


# The end.
