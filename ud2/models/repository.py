"""
Pydantic models representing repository resources.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
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

    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True,
    )

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


class Repository(BaseModel):
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

    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True,
    )

    id: int
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
    installation: Optional[str] = None
    long_description: Optional[str] = Field(
        default=None,
        alias='longDescription',
        serialization_alias='longDescription',
    )
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
    publish_date: Optional[str] = Field(
        default=None,
        alias='publishDate',
        serialization_alias='publishDate',
    )
    update_date: Optional[str] = Field(
        default=None,
        alias='updateDate',
        serialization_alias='updateDate',
    )


# The end.
