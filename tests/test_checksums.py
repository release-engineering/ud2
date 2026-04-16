"""
Unit tests for checksum utilities.
"""

import tempfile
import unittest
from pathlib import Path

from ud2.checksums import file_metadata


class TestFileMetadata(unittest.TestCase):

    def test_returns_file_name_size_sha256_md5(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            f.write(b'hello world')
            path = Path(f.name)

        try:
            result = file_metadata(path)

            self.assertEqual(result['fileName'], str(path))
            self.assertEqual(result['fileSize'], 11)
            self.assertEqual(
                result['sha256'],
                'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9',
            )
            self.assertEqual(result['md5'], '5eb63bbbe01eeed093cb22bb8f5acdc3')
        finally:
            path.unlink(missing_ok=True)

    def test_raises_on_missing_file(self) -> None:
        path = Path('/nonexistent/path/to/file')

        with self.assertRaises(OSError) as ctx:
            file_metadata(path)

        self.assertIn('not found', str(ctx.exception).lower())


# The end.
