"""
Version resource command registrations.
"""


from typing import Sequence

from click import argument, echo, group, option

from ..loader import load_yaml, pretty_yaml
from ..models import Version, VersionCreate
from .util import CLIState, catchall, pass_state, tabulate


def render_versions(versions: Sequence[Version], yaml: bool) -> None:
    """
    Render versions according to the configured output mode.
    """

    if yaml:
        pretty_yaml([
            version.model_dump(by_alias=True, exclude_none=True)
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

    echo(f"Version: {version.version} [ID: {version.id}]")
    echo(f"  Product ID: {version.product_id}")
    echo(f"  CPE: {version.cpe}")
    echo(f"  Architecture: {version.architecture}")
    echo(f"  Platform: {version.platform}")
    echo(f"  Visibility: {version.visibility}")


@group(name="version", help="Product version operations.")
def version() -> None:
    """
    Product version commands.
    """


@version.command(name="list")
@argument("product_id", type=int)
@pass_state
@catchall
def list_versions(
        state: CLIState,
        product_id: int) -> None:
    """
    List product versions for a product.
    """

    versions = state.client.list_product_versions(product_id)
    render_versions(versions, state.yaml_output)


@version.command(name="get")
@argument("version_id", type=int)
@pass_state
@catchall
def get_version(
        state: CLIState,
        version_id: int) -> None:
    """
    Retrieve a product version by identifier.
    """

    version = state.client.get_product_version(version_id)
    render_version(version, state.yaml_output)


@version.command(name="create")
@argument("product_id", type=int)
@option(
    "--file",
    "payload_path",
    required=True,
    type=str,
    help="Path to a YAML file describing the product version payload.",
)
@pass_state
@catchall
def create_version(
        state: CLIState,
        product_id: int,
        payload_path: str) -> None:
    """
    Create a product version.
    """

    payload = load_yaml(payload_path, model=VersionCreate)
    version = state.client.create_product_version(product_id, payload)
    render_version(version, state.yaml_output)


@version.command(name="update")
@argument("version_id", type=int)
@option(
    "--file",
    "payload_path",
    required=True,
    type=str,
    help="Path to a YAML file describing the product version payload.",
)
@pass_state
@catchall
def update_version(
        state: CLIState,
        version_id: int,
        payload_path: str) -> None:
    """
    Update a product version.
    """

    payload = load_yaml(payload_path, model=VersionCreate)
    version = state.client.update_product_version(version_id, payload)
    render_version(version, state.yaml_output)


@version.command(name="delete")
@argument("version_id", type=int)
@pass_state
@catchall
def delete_version(
        state: CLIState,
        version_id: int) -> None:
    """
    Delete a product version.
    """

    state.client.delete_product_version(version_id)
    echo("Success.")


# The end.
