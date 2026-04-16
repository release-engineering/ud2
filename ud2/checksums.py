"""
File metadata and checksum utilities.
"""

import hashlib
from pathlib import Path
from typing import Any, Dict


CHUNK_SIZE = 65536


def file_metadata(path: Path) -> Dict[str, Any]:
    """
    Read file and return file_name, file_size, sha256, md5.

    :param path: Path to file on disk.
    :returns: Dict with fileName, fileSize, sha256, md5.
    :raises OSError: If file does not exist or is not readable.
    """

    p = Path(path)
    if not p.exists():
        raise OSError(f"File not found: {p}")
    if not p.is_file():
        raise OSError(f"Not a regular file: {p}")

    file_size = p.stat().st_size
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()

    with p.open('rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sha256_hash.update(chunk)
            md5_hash.update(chunk)

    return {
        'fileName': str(path),
        'fileSize': file_size,
        'sha256': sha256_hash.hexdigest().lower(),
        'md5': md5_hash.hexdigest().lower(),
    }


# The end.
