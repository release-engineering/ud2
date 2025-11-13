"""
Pydantic models representing repository resources.
"""

from typing import List, Optional

from .compat import StrictModel, Field


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


# The end.
