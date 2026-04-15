"""
Version resource command registrations.
"""


from io import StringIO
from pathlib import Path
from typing import Optional, Sequence

from click import ClickException, argument, echo, group, option
from requests import HTTPError

from ..loader import load_yaml, pretty_yaml
from ..models import Version, VersionCreate
from .release import _init_resolve_product_id
from .util import (
    CLIState,
    catchall,
    confirm_deletion,
    merge_payload,
    pass_state,
    tabulate,
)


def _resolve_product_id_for_version_list(
        state: CLIState,
        product_spec: str) -> int:
    """
    Parse ``product_spec`` as a numeric product id, or resolve by product code.

    Non-numeric values are matched against ``Product.product_code`` (case-insensitive),
    using the same rules as ``release init --product-code``.
    """

    stripped = product_spec.strip()
    if not stripped:
        raise ClickException('Product identifier cannot be empty.')

    if stripped.isdigit():
        return int(stripped)

    return _init_resolve_product_id(state.client, product_code=stripped)


def _resolve_version_id_for_version_get(
        state: CLIState,
        product_or_version: str,
        version_spec: Optional[str]) -> int:
    """
    Resolve version get positional args to a product version ID.

    With one positional arg, value must be numeric and is treated as version ID.
    With two positional args, first is product id/code and second is version string.
    """

    first = product_or_version.strip()
    if not first:
        raise ClickException('Version identifier cannot be empty.')

    if version_spec is None:
        if first.isdigit():
            return int(first)
        raise ClickException(
            'When using a single argument, provide a numeric version ID.',
        )

    second = version_spec.strip()
    if not second:
        raise ClickException('Version string cannot be empty.')

    product_id = _resolve_product_id_for_version_list(state, first)
    versions = state.client.list_product_versions(product_id)
    matches = [
        version for version in versions
        if version.version.strip().casefold() == second.casefold()
    ]
    if not matches:
        raise ClickException(
            "No version {0!r} found for product {1!r}.".format(second, first),
        )

    chosen = max(matches, key=lambda item: item.id)
    if len(matches) > 1:
        echo(
            "Warning: Multiple versions match {0!r}; using version id {1}.".format(
                second, chosen.id,
            ),
            err=True,
        )
    return chosen.id


def render_versions(versions: Sequence[Version], yaml: bool) -> None:
    """
    Render versions according to the configured output mode.
    """

    if yaml:
        pretty_yaml([
            version.model_dump(by_alias=False, exclude_none=True)
            for version in versions
        ])
        return

    headers = ("ID", "Version", "Architecture", "Platform", "Visibility")
    rows = [
        (
            version.id,
            version.version,
            version.architecture,
            version.platform,
            version.visibility,
        )
        for version in versions
    ]
    tabulate(headers, rows)


def render_version(version: Version, yaml: bool) -> None:
    """
    Render a single version according to the configured output mode.
    """

    if yaml:
        pretty_yaml(version)
        return

    echo(f"Version: '{version.version}' [ID: {version.id}]")
    echo(f"  Product ID: {version.product_id}")
    echo(f"  CPE: {version.cpe}")
    echo(f"  Architecture: {version.architecture}")
    echo(f"  Platform: {version.platform}")
    echo(f"  Visibility: {version.visibility}")
    if version.sort_version:
        echo(f"  Sort As: '{version.sort_version}'")


def echo_version_delete_preview(version: Version) -> None:
    """
    Print a short plain-text summary before a delete confirmation.
    """

    echo(f"Version: '{version.version}' [ID: {version.id}]")
    echo(f"  Product ID: {version.product_id}")


@group(name="version", help="Product version operations.")
def version() -> None:
    """
    Product version commands.
    """


@version.command(name="list")
@argument(
    "product_spec",
    type=str,
    metavar="PRODUCT",
)
@pass_state
@catchall
def list_versions(
        state: CLIState,
        product_spec: str) -> None:
    """
    List product versions for a product.

    PRODUCT may be a numeric id or a product code (case-insensitive).
    """

    product_id = _resolve_product_id_for_version_list(state, product_spec)

    try:
        versions = state.client.list_product_versions(product_id)
    except HTTPError as exc:
        response = getattr(exc, 'response', None)
        if response is not None and response.status_code == 404:
            raise ClickException(
                'No product was found for that identifier.',
            ) from exc
        raise

    render_versions(versions, state.yaml_output)


@version.command(name="get")
@argument('product_or_version', type=str, metavar='VERSION_ID|PRODUCT')
@argument('version_spec', type=str, required=False, metavar='VERSION')
@pass_state
@catchall
def get_version(
        state: CLIState,
        product_or_version: str,
        version_spec: Optional[str]) -> None:
    """
    Retrieve a product version by identifier.
    """

    version_id = _resolve_version_id_for_version_get(
        state,
        product_or_version,
        version_spec,
    )
    version = state.client.get_product_version(version_id)
    render_version(version, state.yaml_output)


@version.command(name="create")
@argument("product_id", type=int)
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the product version payload.")
@option("--version", "version_str", type=str, help="Version string (e.g. 8.5).")
@option("--sort-version", "sort_version_str", type=str, default=None, help="Sort version string (e.g. 8.5.0).")
@option("--architecture", type=str, help="Architecture (e.g. x86_64).")
@option("--cpe", type=str, help="CPE string.")
@option("--platform", type=str, help="Platform.")
@option("--visibility", type=str, help="Visibility.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def create_version(
        state: CLIState,
        product_id: int,
        yaml_path: Optional[Path],
        version_str: Optional[str],
        sort_version_str: Optional[str],
        architecture: Optional[str],
        cpe: Optional[str],
        platform: Optional[str],
        visibility: Optional[str],
        dry_run: bool = False) -> None:
    """
    Create a product version. Use --yaml-file or --version.
    """

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        data = merge_payload(
            data,
            version=version_str,
            sort_version=sort_version_str,
            architecture=architecture,
            cpe=cpe,
            platform=platform,
            visibility=visibility,
        )
    else:
        if version_str is None:
            raise ClickException("Provide --yaml-file or --version.")
        data = merge_payload(
            {},
            version=version_str,
            sort_version=sort_version_str,
            architecture=architecture,
            cpe=cpe,
            platform=platform,
            visibility=visibility,
        )

    payload = VersionCreate.model_validate(data)
    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    version = state.client.create_product_version(product_id, payload)
    render_version(version, state.yaml_output)


@version.command(name="update")
@argument("version_id", type=int)
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the product version payload.")
@option("--version", "version_str", type=str, help="Version string (e.g. 8.5).")
@option("--sort-version", "sort_version_str", type=str, default=None, help="Sort version string (e.g. 8.5.0).")
@option("--architecture", type=str, help="Architecture (e.g. x86_64).")
@option("--cpe", type=str, help="CPE string.")
@option("--platform", type=str, help="Platform.")
@option("--visibility", type=str, help="Visibility.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def update_version(
        state: CLIState,
        version_id: int,
        yaml_path: Optional[Path],
        version_str: Optional[str],
        sort_version_str: Optional[str],
        architecture: Optional[str],
        cpe: Optional[str],
        platform: Optional[str],
        visibility: Optional[str],
        dry_run: bool = False) -> None:
    """
    Update a product version. Provide --yaml-file or at least one field.
    """

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        data = merge_payload(
            data,
            version=version_str,
            sort_version=sort_version_str,
            architecture=architecture,
            cpe=cpe,
            platform=platform,
            visibility=visibility,
        )
        payload = VersionCreate.model_validate(data)
    else:
        has_option = any(
            v is not None
            for v in (version_str, sort_version_str, architecture, cpe, platform, visibility)
        )
        if not has_option:
            raise ClickException(
                "Provide --yaml-file or at least one field to update.",
            )
        existing = state.client.get_product_version(version_id)
        data = existing.model_dump(by_alias=False, exclude_none=True)
        data.pop('id', None)
        data.pop('product_id', None)
        data = merge_payload(
            data,
            version=version_str,
            sort_version=sort_version_str,
            architecture=architecture,
            cpe=cpe,
            platform=platform,
            visibility=visibility,
        )
        payload = VersionCreate.model_validate(data)

    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    version = state.client.update_product_version(version_id, payload)
    render_version(version, state.yaml_output)


@version.command(name="search")
@option("--version", "version_str", type=str,
        help="Version (glob pattern, case-insensitive).")
@option("--product-id", "product_id", type=int,
        help="Product ID (exact match, must be > 0).")
@option("--cpe", type=str, help="CPE string (glob pattern).")
@option("--page", type=int, help="Page number.")
@option("--limit", type=int, help="Items per page.")
@pass_state
@catchall
def search_versions(
        state: CLIState,
        version_str: Optional[str],
        product_id: Optional[int],
        cpe: Optional[str],
        page: Optional[int],
        limit: Optional[int]) -> None:
    """
    Search product versions by version, CPE, and/or product ID.
    """

    if version_str is None and product_id is None and cpe is None:
        raise ClickException(
            "At least one of --version, --product-id, or --cpe is required.",
        )

    page_obj = state.client.search_product_versions(
        version=version_str,
        product_id=product_id,
        cpe=cpe,
        page=page,
        limit=limit,
    )
    render_versions(list(page_obj.data), state.yaml_output)


@version.command(name="delete")
@argument("version_id", type=int)
@option("--force", is_flag=True,
        help="Delete without confirmation.")
@pass_state
@catchall
def delete_version(
        state: CLIState,
        version_id: int,
        force: bool) -> None:
    """
    Delete a product version.
    """

    version = state.client.get_product_version(version_id)
    repositories = state.client.list_repositories(version_id)

    if repositories:
        raise ClickException(
            f"Cannot delete version {version_id}: {len(repositories)} "
            f"repository file(s) still associated. Remove them first.",
        )

    echo_version_delete_preview(version)
    confirm_deletion(force, "Delete this entry?")

    state.client.delete_product_version(version_id)
    echo("Success.")


# The end.
