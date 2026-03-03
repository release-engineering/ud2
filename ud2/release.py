"""
Release push/sync logic: resolve, ensure, check, and apply.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

from .client import UDClient
from .models import (Product, ProductRef, Release, ReleaseSyncMetadata,
                     Repository, RepositoryCreate, RepositoryEntry,
                     Version, VersionCreate, VersionRef)


class MatchKind(str, Enum):
    """How a repository was matched."""

    ID = 'id'
    SHA256 = 'sha256'
    TITLE = 'title'


class RepoMatchError(str, Enum):
    """Repository matching error."""

    FILENAME_MISMATCH = 'filename_mismatch'


class ReleaseError(Exception):
    """Error during release check or push."""

    def __init__(
            self,
            message: str,
            kind: Optional[RepoMatchError] = None) -> None:
        super().__init__(message)
        self.kind = kind


def _validate_product_ref(product_ref: ProductRef) -> None:
    """Ensure product_ref has sufficient data for lookup."""
    has_id = product_ref.id is not None
    has_search = (
        product_ref.eng_id is not None
        and product_ref.name is not None
    )
    if not has_id and not has_search:
        raise ReleaseError(
            'product must specify either id or both eng_id and name',
        )


def resolve_product(
        client: UDClient,
        product_ref: ProductRef) -> Optional[Product]:
    """
    Resolve product by ID or by eng_id+name search.

    :param client: UD client.
    :param product_ref: Product reference from manifest.
    :returns: Product if found, None otherwise.
    """

    _validate_product_ref(product_ref)

    if product_ref.id is not None:
        try:
            return client.get_product(product_ref.id)
        except requests.HTTPError as exc:
            if (
                getattr(exc, 'response', None) is not None
                and exc.response.status_code == 404
            ):
                pass
            else:
                raise

    if product_ref.eng_id is not None and product_ref.name is not None:
        for product in client.iter_products():
            if (
                product.eng_id == product_ref.eng_id
                and product.name == product_ref.name
            ):
                return product

    return None


def resolve_version(
        client: UDClient,
        product: Product,
        version_ref: VersionRef) -> Optional[Version]:
    """
    Resolve version by ID or by (product, version) search.

    :param client: UD client.
    :param product: Resolved product.
    :param version_ref: Version reference from manifest.
    :returns: Version if found, None otherwise.
    """

    if version_ref.id is not None:
        try:
            version = client.get_product_version(version_ref.id)
            if version.product_id == product.id:
                return version
        except requests.HTTPError as exc:
            if (
                getattr(exc, 'response', None) is not None
                and exc.response.status_code == 404
            ):
                pass
            else:
                raise

    versions = client.list_product_versions(product.id)
    for version in versions:
        if version.version == version_ref.version:
            return version

    return None


def resolve_repository(
        client: UDClient,
        product_version_id: int,
        entry: RepositoryEntry,
        existing: List[Repository],
        version_ref: VersionRef,
        force_filename: bool = False,
) -> Tuple[Optional[Repository], Optional[MatchKind], Optional[RepoMatchError]]:
    """
    Resolve repository by ID, sha256, or title.

    :param client: UD client.
    :param product_version_id: Product version ID.
    :param entry: Repository entry from manifest.
    :param existing: Existing repositories for the version.
    :param version_ref: Version reference for ownership check.
    :param force_filename: If True, allow same filename when content differs.
    :returns: (repository or None, match kind or None, error or None).
    """

    # 1. Try ID
    if entry.id is not None:
        for repo in existing:
            if repo.id == entry.id:
                return (repo, MatchKind.ID, None)
        try:
            repo = client.get_repository(entry.id)
            if repo.product_version == version_ref.version:
                return (repo, MatchKind.ID, None)
        except requests.HTTPError as exc:
            if (
                getattr(exc, 'response', None) is not None
                and exc.response.status_code == 404
            ):
                pass
            else:
                raise

    # 2. Try sha256
    for repo in existing:
        if repo.sha256 == entry.sha256:
            return (repo, MatchKind.SHA256, None)

    # 3. Try title (description)
    for repo in existing:
        if repo.description == entry.description:
            if repo.sha256 == entry.sha256:
                return (repo, MatchKind.TITLE, None)
            if repo.file_name == entry.file_name and not force_filename:
                return (repo, None, RepoMatchError.FILENAME_MISMATCH)
            return (repo, MatchKind.TITLE, None)

    return (None, None, None)


def entry_to_repository_create(entry: RepositoryEntry) -> RepositoryCreate:
    """Build RepositoryCreate from RepositoryEntry, excluding id and path."""

    return RepositoryCreate(
        description=entry.description,
        file_name=entry.file_name,
        file_size=entry.file_size,
        sha256=entry.sha256,
        md5=entry.md5,
        issues=entry.issues,
        visibility=entry.visibility,
        classifier=entry.classifier,
        content_types=entry.content_types,
        installation=entry.installation,
        long_description=entry.long_description,
    )


def ensure_version(
        client: UDClient,
        product: Product,
        version_ref: VersionRef) -> Version:
    """
    Ensure version exists; create if not found.

    :param client: UD client.
    :param product: Resolved product.
    :param version_ref: Version reference from manifest.
    :returns: Version (existing or newly created).
    """

    version = resolve_version(client, product, version_ref)
    if version is not None:
        return version

    payload = VersionCreate(
        version=version_ref.version,
        architecture=version_ref.architecture,
        cpe=version_ref.cpe,
        platform=version_ref.platform,
        visibility=version_ref.visibility,
    )
    return client.create_product_version(product.id, payload)


def ensure_repository(
        client: UDClient,
        product_version_id: int,
        entry: RepositoryEntry,
        existing: List[Repository],
        version_ref: VersionRef,
        force_filename: bool = False) -> Tuple[Repository, bool]:
    """
    Ensure repository exists; create or update as needed.

    :param client: UD client.
    :param product_version_id: Product version ID.
    :param entry: Repository entry from manifest.
    :param existing: Existing repositories for the version.
    :param version_ref: Version reference for ownership check.
    :param force_filename: If True, allow same filename when content differs.
    :returns: Repository (existing, updated, or newly created).
    :raises ReleaseError: On filename mismatch without force_filename.
    """

    repo, match_kind, error = resolve_repository(
        client,
        product_version_id,
        entry,
        existing,
        version_ref,
        force_filename=force_filename,
    )

    if error == RepoMatchError.FILENAME_MISMATCH:
        raise ReleaseError(
            f"Filename mismatch for '{entry.description}': same title and "
            f"filename but different sha256. Change filename when content "
            f"changes, or use --force-filename.",
            kind=RepoMatchError.FILENAME_MISMATCH,
        )

    payload = entry_to_repository_create(entry)

    if repo is not None:
        return (client.update_repository(repo.id, payload), False)

    return (client.create_repository(product_version_id, payload), True)


# Check report structures (dataclass-like via TypedDict or simple dict)
def check_release(
        client: UDClient,
        release: Release,
        force_filename: bool = False) -> Dict[str, Any]:
    """
    Check release manifest against server state (no writes).

    :param client: UD client.
    :param release: Loaded release manifest.
    :param force_filename: If True, treat filename mismatch as update.
    :returns: Check report dict with product, version, repos, errors.
    """

    report = {
        'product': {'status': 'unknown', 'product': None},
        'version': {'status': 'unknown', 'version': None},
        'repos': [],
        'errors': [],
        'in_sync': True,
    }

    product = resolve_product(client, release.product)
    if product is None:
        report['product']['status'] = 'not_found'
        report['errors'].append('Product not found')
        report['in_sync'] = False
        return report

    report['product']['status'] = 'found'
    report['product']['product'] = product

    version = resolve_version(client, product, release.version)
    if version is None:
        report['version']['status'] = 'would_create'
        report['version']['version'] = None
        report['in_sync'] = False
    else:
        report['version']['status'] = 'found'
        report['version']['version'] = version

    if version is None:
        report['repos'] = [
            {'entry': e, 'action': 'would_create', 'reason': 'version missing'}
            for e in release.repositories
        ]
        return report

    existing = client.list_repositories(version.id)
    for entry in release.repositories:
        repo, match_kind, error = resolve_repository(
            client,
            version.id,
            entry,
            existing,
            release.version,
            force_filename=force_filename,
        )

        if error == RepoMatchError.FILENAME_MISMATCH:
            report['repos'].append({
                'entry': entry,
                'action': 'error',
                'error': 'filename_mismatch',
                'message': (
                    f"'{entry.description}': same title and filename but "
                    "different sha256"
                ),
            })
            report['errors'].append(
                f"Repository '{entry.description}': filename mismatch",
            )
            report['in_sync'] = False
        elif repo is not None:
            action = 'would_update' if match_kind else 'would_update'
            report['repos'].append({
                'entry': entry,
                'action': action,
                'match_kind': match_kind.value if match_kind else None,
                'repo': repo,
            })
            report['in_sync'] = False
        else:
            report['repos'].append({
                'entry': entry,
                'action': 'would_create',
            })
            report['in_sync'] = False

    return report


def apply_release(
        client: UDClient,
        release: Release,
        force_filename: bool = False,
        upload: bool = False,
        manifest_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Apply release to server (create/update resources).

    :param client: UD client.
    :param release: Loaded release manifest.
    :param force_filename: If True, allow same filename when content differs.
    :param upload: If True, invoke upload utility (not yet implemented).
    :param manifest_path: Path to manifest for write-back.
    :returns: Apply result dict.
    :raises ReleaseError: On product not found, filename mismatch, or upload.
    """

    if upload:
        raise ReleaseError(
            'Upload support not yet implemented. The --upload option will '
            'invoke file uploading utilities once they are available.',
        )

    product = resolve_product(client, release.product)
    if product is None:
        raise ReleaseError('Product not found')

    version = ensure_version(client, product, release.version)
    existing = client.list_repositories(version.id)

    created = []
    updated = []
    result_repos = []

    for entry in release.repositories:
        repo, was_create = ensure_repository(
            client,
            version.id,
            entry,
            existing,
            release.version,
            force_filename=force_filename,
        )

        result_repos.append(repo)
        if was_create:
            created.append(repo)
        else:
            updated.append(repo)

        existing = client.list_repositories(version.id)

    result = {
        'product': product,
        'version': version,
        'created': created,
        'updated': updated,
    }

    if manifest_path:
        sync_meta = ReleaseSyncMetadata(
            product_id=product.id,
            version_id=version.id,
            file_ids=[r.id for r in result_repos],
        )
        _write_sync_metadata(manifest_path, sync_meta)

    return result


def _write_sync_metadata(path: str, sync_meta: ReleaseSyncMetadata) -> None:
    """Merge sync metadata into manifest file."""

    import yaml
    from pathlib import Path

    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    data['_sync'] = sync_meta.model_dump(by_alias=True, exclude_none=True)

    with p.open('w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
