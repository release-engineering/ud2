"""
Pydantic models representing repository resources.
"""

from datetime import datetime
from typing import List, Optional

from .compat import Field, StrictModel, field_validator


SHA256_LENGTH = 64


class RepositoryBase(StrictModel):
    """
    Base model for repository resources.

    :param description: Short description of the repository.
    :param file_name: Repository archive file name.
    :param file_size: Repository archive size expressed in bytes.
    :param sha256: SHA-256 checksum of the repository archive.
    :param content_types: Optional list of content types delivered by the archive.
    :param installation: Optional installation instructions.
    :param long_description: Optional detailed description.
    """

    description: str
    file_name: str = Field(
        alias='fileName',
        serialization_alias='fileName',
    )
    file_size: int = Field(
        alias='fileSize',
        serialization_alias='fileSize',
    )
    sha256: str
    content_types: Optional[List[str]] = Field(
        default=None,
        alias='contentTypes',
        serialization_alias='contentTypes',
    )
    installation: Optional[str] = Field(
        default=None,
        alias='Installation',
        serialization_alias='Installation',
    )
    long_description: Optional[str] = Field(
        default=None,
        alias='longDescription',
        serialization_alias='longDescription',
    )

    @field_validator('file_size')
    def _validate_file_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('file_size must be greater than zero')
        return value

    @field_validator('sha256', mode='before')
    def _normalize_sha256(cls, value: Optional[str]) -> str:
        if not isinstance(value, str):
            raise ValueError('sha256 must be supplied as a hexadecimal string')

        normalized = value.strip().lower()
        if len(normalized) != SHA256_LENGTH:
            raise ValueError('sha256 must be a 64 character hexadecimal string')

        if not all(char in '0123456789abcdef' for char in normalized):
            raise ValueError('sha256 must contain only hexadecimal characters')

        return normalized


class RepositoryCreate(RepositoryBase):
    """
    Capture the payload for creating a repository.

    :param description: Short description of the repository.
    :param file_name: Repository archive file name.
    :param file_size: Repository archive size expressed in bytes.
    :param sha256: SHA-256 checksum of the repository archive.
    :param content_types: Optional list of content types delivered by the archive.
    :param installation: Optional installation instructions.
    :param long_description: Optional detailed description.
    """

    pass


class Repository(RepositoryBase):
    """
    Represent the repository data returned by the API.

    :param id: Database identifier.
    :param description: Short description of the repository.
    :param file_name: Repository archive file name.
    :param file_size: Repository archive size expressed in bytes.
    :param sha256: SHA-256 checksum of the repository archive.
    :param content_types: Optional list of content types delivered by the archive.
    :param installation: Optional installation instructions.
    :param long_description: Optional detailed description.
    :param product_name: Optional product name.
    :param product_version: Optional product version string.
    :param publish_date: Optional publication date.
    :param update_date: Optional update date.
    """

    id: int
    product_name: Optional[str] = Field(
        default=None,
        alias='productName',
        serialization_alias='productName',
    )
    product_version: Optional[str] = Field(
        default=None,
        alias='productVersion',
        serialization_alias='productVersion',
    )
    publish_date: Optional[datetime] = Field(
        default=None,
        alias='publishDate',
        serialization_alias='publishDate',
    )
    update_date: Optional[datetime] = Field(
        default=None,
        alias='updateDate',
        serialization_alias='updateDate',
    )

    @field_validator('publish_date', 'update_date', mode='before')
    def _parse_datetime(cls, value: Optional[str]) -> Optional[datetime]:
        if value is None or isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            raise ValueError('Expected ISO 8601 string for date fields')

        candidate = value.strip()
        if not candidate:
            return None

        if candidate.endswith('Z'):
            candidate = candidate[:-1] + '+00:00'

        try:
            return datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO 8601 datetime: {value}") from exc


# The end.
