"""
Pydantic models for the Release manifest.
"""

from typing import List, Optional

from .compat import Field, StrictModel, field_validator
from .repository import SHA256_LENGTH


class ProductRef(StrictModel):
    """Product reference for lookup or identification."""

    id: Optional[int] = None
    eng_id: Optional[int] = Field(None, alias='engId')
    name: Optional[str] = None


class VersionRef(StrictModel):
    """
    Version reference within a product.
    """

    id: Optional[int] = None
    version: str
    sort_version: Optional[str] = None
    architecture: Optional[str] = None
    cpe: Optional[str] = None
    platform: Optional[str] = None
    visibility: Optional[str] = None


class RepositoryEntry(StrictModel):
    """
    A single repository (file) entry in the release manifest.

    Mapped to ``RepositoryCreate`` for API calls. Optional ``id`` from prior
    push enables fast-path lookup. When ``path`` is present and ``--upload``
    is used, the upload utility is invoked to obtain/confirm file metadata
    before metadata is pushed.
    """

    id: Optional[int] = None
    description: str
    file_name: str = Field(..., alias='fileName')
    file_size: int = Field(..., alias='fileSize')
    sha256: str
    md5: str
    issues: List[str] = Field(default_factory=list)
    visibility: str
    classifier: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(
        default_factory=list,
        alias='contentTypes',
    )
    installation: Optional[str] = None
    long_description: Optional[str] = Field(None, alias='longDescription')
    path: Optional[str] = None


    @field_validator('file_size')
    def _validate_file_size(cls, value: int) -> int:
        if value < 0:
            raise ValueError('file_size must be greater than or equal to zero')
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


class ReleaseSyncMetadata(StrictModel):
    """
    Write-back metadata from a successful push.

    Populated by the push operation; used to accelerate subsequent syncs.
    """

    product_id: int = Field(..., alias='productId')
    version_id: int = Field(..., alias='versionId')
    file_ids: List[int] = Field(default_factory=list, alias='fileIds')


class Release(StrictModel):
    """
    Release manifest: product, version, and collection of repository files.
    """

    product: ProductRef
    version: VersionRef
    repositories: List[RepositoryEntry] = Field(default_factory=list)

    dirname: Optional[str] = Field(
        None,
        description=(
            'Prefix path for downloads relative to the download URL root. '
            'When set, ``release add`` builds fileName as dirname/basename '
            'unless ``--file-name`` is given.'
        ),
    )

    sync: Optional[ReleaseSyncMetadata] = Field(None, alias='_sync')


# The end.
