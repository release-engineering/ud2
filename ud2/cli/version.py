""
"Version resource command registrations."
""


import click

from ..models import VersionCreate
from . import CLIState, emit, invoke_with_handling, load_model, pass_state, with_error_handling


def register(root: click.Group) -> None:
    """
    Attach version related commands to the provided root group.
    """

    @root.group(name="versions", help="Product version operations.")
    def versions() -> None:
        """
        Product version commands.
        """

    @versions.command(name="list")
    @click.argument("product_id", type=int)
    @with_error_handling
    @pass_state
    def list_versions(
            state: CLIState,
            product_id: int) -> None:
        """
        List product versions for a product.
        """

        result = invoke_with_handling(
            lambda: state.client.list_product_versions(product_id),
        )

        emit(result, state)

    @versions.command(name="get")
    @click.argument("product_id", type=int)
    @click.argument("version_id", type=int)
    @with_error_handling
    @pass_state
    def get_version(
            state: CLIState,
            product_id: int,
            version_id: int) -> None:
        """
        Retrieve a product version by identifier.
        """

        result = invoke_with_handling(
            lambda: state.client.get_product_version(product_id, version_id),
        )

        emit(result, state)

    @versions.command(name="create")
    @click.argument("product_id", type=int)
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the product version payload.",
    )
    @with_error_handling
    @pass_state
    def create_version(
            state: CLIState,
            product_id: int,
            payload_path: str) -> None:
        """
        Create a product version.
        """

        payload = load_model(payload_path, VersionCreate)

        result = invoke_with_handling(
            lambda: state.client.create_product_version(product_id, payload),
        )

        emit(result, state)

    @versions.command(name="update")
    @click.argument("product_id", type=int)
    @click.argument("version_id", type=int)
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the product version payload.",
    )
    @with_error_handling
    @pass_state
    def update_version(
            state: CLIState,
            product_id: int,
            version_id: int,
            payload_path: str) -> None:
        """
        Update a product version.
        """

        payload = load_model(payload_path, VersionCreate)

        result = invoke_with_handling(
            lambda: state.client.update_product_version(product_id, version_id, payload),
        )

        emit(result, state)

    @versions.command(name="delete")
    @click.argument("product_id", type=int)
    @click.argument("version_id", type=int)
    @with_error_handling
    @pass_state
    def delete_version(
            state: CLIState,
            product_id: int,
            version_id: int) -> None:
        """
        Delete a product version.
        """

        result = invoke_with_handling(
            lambda: state.client.delete_product_version(product_id, version_id),
        )

        emit(result, state)


# The end.
