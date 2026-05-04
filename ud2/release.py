"""
Release push/sync logic: resolve, ensure, check, and apply.
"""

import sys
import yaml
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from .client import UDClient
from .loader import load_yaml, PrettyYAML
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


def _default_soft_key_warn(message: str) -> None:
    """Emit soft-key ambiguity warning (same text as release init)."""

    print(message, file=sys.stderr)


def _soft_key_match_products(
        products: List[Product],
        *,
        product_eng_id: Optional[int] = None,
        product_name: Optional[str] = None,
        product_code: Optional[str] = None) -> Tuple[List[Product], str, str]:
    """
    Filter products by exactly one of eng_id, name, or product_code.

    :param products: Full product list from the API.
    :param product_eng_id: Match ``Product.eng_id`` (exact).
    :param product_name: Match ``Product.name`` (case-insensitive).
    :param product_code: Match ``Product.product_code`` (case-insensitive).

    :returns: (matches, kind_label, search_display) for errors and warnings.
    :raises ValueError: If not exactly one lookup key is provided.
    """

    active: List[Tuple[str, Any]] = []
    if product_eng_id is not None:
        active.append(('engineering ID', product_eng_id))
    if product_name is not None:
        active.append(('name', product_name))
    if product_code is not None:
        active.append(('product code', product_code))

    if len(active) != 1:
        raise ValueError('expected exactly one lookup key for API product resolution')

    kind_label, search_value = active[0]

    if product_eng_id is not None:
        matches = [p for p in products if p.eng_id == product_eng_id]
        search_display = str(product_eng_id)
    elif product_name is not None:
        key = product_name.casefold()
        matches = [p for p in products if p.name.casefold() == key]
        search_display = product_name
    else:
        assert product_code is not None
        key = product_code.casefold()
        matches = [
            p for p in products
            if p.product_code is not None
            and p.product_code.casefold() == key
        ]
        search_display = product_code

    return (matches, kind_label, search_display)


def _choose_product_from_soft_key_matches(
        matches: List[Product],
        kind_label: str,
        search_display: str,
        warn: Optional[Callable[[str], None]] = None) -> Optional[Product]:
    """
    Pick one product from soft-key matches (largest id; warn if ambiguous).

    :param matches: Products matching the soft key.
    :param kind_label: Human-readable key kind (for warning text).
    :param search_display: Search value as shown to the user.
    :param warn: Optional callback for ambiguity warning; defaults to stderr.
    :returns: Chosen product, or None if matches is empty.
    """

    if not matches:
        return None

    if warn is None:
        warn = _default_soft_key_warn

    chosen = max(matches, key=lambda p: p.id)
    if len(matches) > 1:
        warn(
            "Warning: Multiple products match {0} {1!r}; using product id {2}.".format(
                kind_label, search_display, chosen.id,
            ),
        )

    return chosen


def _validate_product_ref(product_ref: ProductRef) -> None:
    """Ensure product_ref has sufficient data for lookup."""

    if product_ref.id is not None:
        return

    has_eng = product_ref.eng_id is not None
    has_name = product_ref.name is not None
    has_code = product_ref.product_code is not None
    legacy_pair = has_eng and has_name and not has_code
    single_key = (
        sum((has_eng, has_name, has_code)) == 1
    )

    if legacy_pair or single_key:
        return

    raise ReleaseError(
        'product must specify id, or engId and name (legacy), or exactly one '
        'of engId, name, or productCode',
    )


def resolve_product(
        client: UDClient,
        product_ref: ProductRef) -> Optional[Product]:
    """
    Resolve product by id, legacy eng_id+name pair, or a single soft key.

    When ``id`` is set, only ``get_product(id)`` is used (no fallback).

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
                return None
            raise

    if product_ref.eng_id is not None and product_ref.name is not None:
        for product in client.iter_products():
            if (
                product.eng_id == product_ref.eng_id
                and product.name == product_ref.name
            ):
                return product

        return None

    products = client.list_products()
    matches, kind_label, search_display = _soft_key_match_products(
        products,
        product_eng_id=product_ref.eng_id,
        product_name=product_ref.name,
        product_code=product_ref.product_code,
    )

    return _choose_product_from_soft_key_matches(
        matches,
        kind_label,
        search_display,
        warn=_default_soft_key_warn,
    )


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

    # in order to preserve the order of the repositories in the manifest, we
    # need to process them in reverse order
    for entry in reversed(release.repositories):
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

    # if manifest_path:
    #     sync_meta = ReleaseSyncMetadata(
    #         product_id=product.id,
    #         version_id=version.id,
    #         file_ids=[r.id for r in result_repos],
    #     )
    #     _write_sync_metadata(manifest_path, sync_meta)

    return result


def load_release_manifest(path: Path) -> Release:
    """
    Load and validate release manifest from path.

    :param path: Path to release manifest YAML.
    :returns: Validated Release model.
    """

    return load_yaml(str(path), model=Release)


def write_release_manifest(path: Path, release: Release) -> None:
    """
    Write release manifest to path.

    :param path: Path to write manifest.
    :param release: Release model to serialize.
    """

    data = release.model_dump(by_alias=True, exclude_none=True)
    with Path(path).open('w', encoding='utf-8') as f:
        yaml.dump(
            data,
            f,
            Dumper=PrettyYAML,
            default_flow_style=False,
            sort_keys=False,
        )


def _write_sync_metadata(path: str, sync_meta: ReleaseSyncMetadata) -> None:
    """Merge sync metadata into manifest file."""

    import yaml
    from pathlib import Path

    p = Path(path)
    with p.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    data['_sync'] = sync_meta.model_dump(by_alias=False, exclude_none=True)

    with p.open('w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
