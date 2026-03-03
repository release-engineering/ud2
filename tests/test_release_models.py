"""
Unit tests for Release manifest models.
"""

import unittest

from pydantic import ValidationError

from ud2.models import (
    ProductRef,
    Release,
    ReleaseSyncMetadata,
    RepositoryEntry,
    VersionRef,
)
from ud2.models.repository import RepositoryCreate
from ud2.release import entry_to_repository_create

from . import DEFAULT_SHA256


class TestProductRef(unittest.TestCase):
    def test_valid_with_id(self) -> None:
        ref = ProductRef.model_validate({'id': 123})
        self.assertEqual(ref.id, 123)
        self.assertIsNone(ref.eng_id)
        self.assertIsNone(ref.name)

    def test_valid_with_eng_id_and_name(self) -> None:
        ref = ProductRef.model_validate(
            {'engId': 4001, 'name': 'Project Atlas'},
        )
        self.assertIsNone(ref.id)
        self.assertEqual(ref.eng_id, 4001)
        self.assertEqual(ref.name, 'Project Atlas')


class TestVersionRef(unittest.TestCase):
    def test_valid_minimal(self) -> None:
        ref = VersionRef.model_validate({'version': '1.0'})
        self.assertEqual(ref.version, '1.0')
        self.assertIsNone(ref.id)

    def test_valid_full(self) -> None:
        ref = VersionRef.model_validate({
            'id': 456,
            'version': '1.2.3',
            'architecture': 'x86_64',
            'platform': 'linux',
        })
        self.assertEqual(ref.id, 456)
        self.assertEqual(ref.version, '1.2.3')
        self.assertEqual(ref.architecture, 'x86_64')
        self.assertEqual(ref.platform, 'linux')


class TestRepositoryEntry(unittest.TestCase):
    def test_valid_minimal(self) -> None:
        entry = RepositoryEntry.model_validate({
            'description': 'Installer',
            'fileName': 'installer.iso',
            'fileSize': 1024,
            'sha256': DEFAULT_SHA256,
            'md5': 'a' * 32,
            'issues': [],
            'visibility': 'visible',
            'classifier': [],
        })
        self.assertEqual(entry.description, 'Installer')
        self.assertEqual(entry.file_name, 'installer.iso')
        self.assertIsNone(entry.id)
        self.assertIsNone(entry.path)

    def test_sha256_validation(self) -> None:
        with self.assertRaises(ValueError):
            RepositoryEntry.model_validate({
                'description': 'Bad',
                'fileName': 'x.iso',
                'fileSize': 1024,
                'sha256': 'short',
                'md5': 'a' * 32,
                'issues': [],
                'visibility': 'visible',
                'classifier': [],
            })


class TestRelease(unittest.TestCase):
    def test_valid_minimal(self) -> None:
        release = Release.model_validate({
            'product': {'engId': 4001, 'name': 'Atlas'},
            'version': {'version': '1.0'},
            'repositories': [],
        })
        self.assertEqual(release.product.eng_id, 4001)
        self.assertEqual(release.version.version, '1.0')
        self.assertEqual(len(release.repositories), 0)
        self.assertIsNone(release.sync)


class TestEntryToRepositoryCreate(unittest.TestCase):
    def test_excludes_id_and_path(self) -> None:
        entry = RepositoryEntry.model_validate({
            'id': 789,
            'path': '/tmp/file.iso',
            'description': 'Installer',
            'fileName': 'installer.iso',
            'fileSize': 1024,
            'sha256': DEFAULT_SHA256,
            'md5': 'a' * 32,
            'issues': [],
            'visibility': 'visible',
            'classifier': [],
        })
        created = entry_to_repository_create(entry)
        self.assertIsInstance(created, RepositoryCreate)
        self.assertEqual(created.description, 'Installer')
        self.assertEqual(created.file_name, 'installer.iso')
        self.assertFalse(hasattr(created, 'id'))
        self.assertFalse(hasattr(created, 'path'))


# The end.
