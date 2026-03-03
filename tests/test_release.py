"""
Unit tests for release resolve, ensure, check, and apply logic.
"""

import pathlib
import unittest
from unittest import mock

from ud2.client import UDClient
from ud2.config import UDConfig
from ud2.models import (
    ProductRef,
    Release,
    RepositoryEntry,
    VersionRef,
)
from ud2.release import (
    RepoMatchError,
    ReleaseError,
    apply_release,
    check_release,
    ensure_repository,
    ensure_version,
    entry_to_repository_create,
    resolve_product,
    resolve_repository,
    resolve_version,
)

from . import (
    DEFAULT_SHA256,
    dump_model,
    make_product,
    make_repository,
    make_version,
    make_version_create,
)


def make_repository_entry(**overrides) -> RepositoryEntry:
    """Construct a RepositoryEntry for testing."""
    payload = {
        'description': 'Installer',
        'fileName': 'installer.iso',
        'fileSize': 1024,
        'sha256': DEFAULT_SHA256,
        'md5': 'a' * 32,
        'issues': [],
        'visibility': 'visible',
        'classifier': [],
    }
    payload.update(overrides)
    return RepositoryEntry.model_validate(payload)


class StubResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")
        if self.status_code == 404:
            import requests
            err = requests.HTTPError("HTTP 404")
            err.response = self
            raise err

    def json(self):
        return self._json_data


class StubSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def request(self, method, url, params=None, json=None, timeout=None):
        self.requests.append({'method': method, 'url': url, 'json': json})
        if not self._responses:
            raise AssertionError("No response configured")
        resp = self._responses.pop(0)
        if hasattr(resp, 'raise_for_status'):
            resp.raise_for_status()
        return resp


class TestResolveProduct(unittest.TestCase):
    def setUp(self):
        self.config = UDConfig(
            name='test',
            base_url='https://example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )

    def test_resolve_by_id(self):
        product = make_product(id=10, eng_id=4001, name='Atlas')
        session = StubSession([
            type('R', (), {
                'status_code': 200,
                'raise_for_status': lambda s: None,
                'json': lambda s: dump_model(product),
                'headers': {'Content-Type': 'application/json'},
            })(),
        ])
        # Use a real mock - StubSession doesn't handle raise_for_status properly
        with mock.patch.object(UDClient, 'get_product') as get_product:
            get_product.return_value = product
            client = UDClient(config=self.config)
            result = resolve_product(client, ProductRef(id=10))
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 10)

    def test_resolve_by_id_404_falls_through_to_search(self):
        import requests
        with mock.patch.object(UDClient, 'get_product') as get_product:
            err = requests.HTTPError("404")
            err.response = type('R', (), {'status_code': 404})()
            get_product.side_effect = err
            with mock.patch.object(UDClient, 'iter_products') as iter_products:
                iter_products.return_value = iter([])
                client = UDClient(config=self.config)
                result = resolve_product(
                    client,
                    ProductRef(id=10, eng_id=4001, name='Missing'),
                )
        self.assertIsNone(result)

    def test_resolve_requires_id_or_eng_id_name(self):
        client = UDClient(config=self.config)
        with self.assertRaises(ReleaseError) as ctx:
            resolve_product(client, ProductRef())
        self.assertIn('id or both eng_id and name', str(ctx.exception))


class TestResolveVersion(unittest.TestCase):
    def setUp(self):
        self.config = UDConfig(
            name='test',
            base_url='https://example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )
        self.product = make_product(id=1)
        self.version = make_version(id=5, productId=1, version='1.0')

    def test_resolve_by_version_string(self):
        with mock.patch.object(UDClient, 'list_product_versions') as list_ver:
            list_ver.return_value = [self.version]
            client = UDClient(config=self.config)
            result = resolve_version(
                client,
                self.product,
                VersionRef(version='1.0'),
            )
        self.assertIsNotNone(result)
        self.assertEqual(result.version, '1.0')


class TestResolveRepository(unittest.TestCase):
    def setUp(self):
        self.config = UDConfig(
            name='test',
            base_url='https://example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )
        self.version_ref = VersionRef(version='1.0')
        self.existing = [
            make_repository(
                id=1,
                description='Installer',
                fileName='installer.iso',
                sha256=DEFAULT_SHA256,
            ),
        ]

    def test_match_by_sha256(self):
        entry = make_repository_entry(sha256=DEFAULT_SHA256)
        client = UDClient(config=self.config)
        repo, kind, err = resolve_repository(
            client, 1, entry, self.existing, self.version_ref,
        )
        self.assertIsNotNone(repo)
        self.assertEqual(kind.value, 'sha256')
        self.assertIsNone(err)

    def test_match_by_title_different_sha256_same_filename_errors(self):
        existing = [
            make_repository(
                id=1,
                description='Installer',
                fileName='installer.iso',
                sha256='a' * 64,
            ),
        ]
        entry = make_repository_entry(
            description='Installer',
            fileName='installer.iso',
            sha256='b' * 64,
        )
        client = UDClient(config=self.config)
        repo, kind, err = resolve_repository(
            client, 1, entry, existing, self.version_ref,
            force_filename=False,
        )
        self.assertIsNotNone(repo)
        self.assertIsNone(kind)
        self.assertEqual(err, RepoMatchError.FILENAME_MISMATCH)


class TestEnsureRepository(unittest.TestCase):
    def setUp(self):
        self.config = UDConfig(
            name='test',
            base_url='https://example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )

    def test_filename_mismatch_raises_without_force(self):
        existing = [
            make_repository(
                id=1,
                description='Installer',
                fileName='installer.iso',
                sha256='a' * 64,
            ),
        ]
        entry = make_repository_entry(
            description='Installer',
            fileName='installer.iso',
            sha256='b' * 64,
        )
        client = UDClient(config=self.config)
        version_ref = VersionRef(version='1.0')
        with self.assertRaises(ReleaseError) as ctx:
            ensure_repository(
                client, 1, entry, existing, version_ref,
                force_filename=False,
            )
        self.assertEqual(ctx.exception.kind, RepoMatchError.FILENAME_MISMATCH)


class TestApplyRelease(unittest.TestCase):
    def test_upload_raises_not_implemented(self):
        config = UDConfig(
            name='test',
            base_url='https://example.test/api',
            client_cert=pathlib.Path('/tmp/cert.pem'),
            client_key=pathlib.Path('/tmp/key.pem'),
            timeout=5.0,
            verify=True,
        )
        client = UDClient(config=config)
        release = Release.model_validate({
            'product': {'id': 1},
            'version': {'version': '1.0'},
            'repositories': [],
        })
        with self.assertRaises(ReleaseError) as ctx:
            apply_release(client, release, upload=True)
        self.assertIn('not yet implemented', str(ctx.exception))


# The end.
