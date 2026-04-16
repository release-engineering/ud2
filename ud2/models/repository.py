"""
Pydantic models representing repository resources.
"""

from datetime import datetime
from typing import List, Optional, Union

from .compat import Field, StrictModel, field_validator
from .enums import ContentType, coerce_enum


SHA256_LENGTH = 64

ContentTypeValue = Union[ContentType, str]


class FileIssue(StrictModel):
    """
    Issue reference (e.g. Jira) for a file.

    :param id: Issue identifier (e.g. TUSC-1234).
    :param type: Issue type (e.g. jira). Defaults to "jira".
    """

    id: str
    type: str = "jira"


def _coerce_issue(item: Union[FileIssue, str, dict]) -> dict:
    """Coerce str or dict to FileIssue-compatible dict."""

    if isinstance(item, str):
        return {"id": item, "type": "jira"}
    if isinstance(item, dict):
        return item
    if isinstance(item, FileIssue):
        return item.model_dump()
    raise ValueError(
        f"issues item must be str, dict, or FileIssue, got {type(item)}",
    )


class RepositoryBase(StrictModel):
    """
    Base model for repository resources.

    :param description: Short description (title) of the repository.
    :param file_name: Repository archive file name.
    :param file_size: Repository archive size expressed in bytes.
    :param sha256: SHA-256 checksum of the repository archive.
    :param content_types: Optional list of content types delivered by the archive.
    :param installation: Optional installation instructions.
    :param long_description: Optional detailed description.
    """

    description: str

    file_name: str = Field(alias='fileName')
    file_size: int = Field(alias='fileSize')
    sha256: str
    md5: str
    issues: List[FileIssue]
    visibility: str
    classifier: List[str]

    content_types: List[ContentTypeValue] = Field(
        alias='contentTypes',
        default_factory=list,
    )
    installation: Optional[str] = Field(alias='installation', default=None)
    long_description: Optional[str] = Field(alias='longDescription', default=None)


    @field_validator('file_size')
    def _validate_file_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError('file_size must be greater than zero')
        return value


    @field_validator('issues', mode='before')
    def _coerce_issues(cls, value: Optional[List]) -> List:
        if not isinstance(value, list):
            raise ValueError("issues must be a list")

        return [_coerce_issue(item) for item in value]


    @field_validator('content_types', mode='before')
    def _coerce_content_types(cls, value: Optional[List]) -> List:
        if not isinstance(value, list):
            raise ValueError("content_types must be a list")

        return [coerce_enum(ContentType, item) for item in value]


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
    :param download_link: Computed URL for file download (returned via get only).
    """

    id: int
    product_id: Optional[int] = Field(alias='productId', default=None)
    product_version_id: Optional[int] = Field(alias='productVersionId', default=None)
    product_name: Optional[str] = Field(alias='productName', default=None)
    product_version: Optional[str] = Field(alias='productVersion', default=None)
    publish_date: Optional[datetime] = Field(alias='publishDate', default=None)
    update_date: Optional[datetime] = Field(alias='updateDate', default=None)
    download_link: Optional[str] = Field(alias='downloadLink', default=None)

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


class RepositoryResult(StrictModel):
    """
    Reduced repository representation returned by the file search API.

    The search endpoint returns only id, product_id, product_version_id,
    description, file_name, and download_link.
    """

    id: int
    product_id: Optional[int] = Field(alias='productId', default=None)
    product_version_id: Optional[int] = Field(alias='productVersionId', default=None)
    description: str
    file_name: str = Field(alias='fileName')
    download_link: Optional[str] = Field(alias='downloadLink', default=None)


# The end.
