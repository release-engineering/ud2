""
"Product resource command registrations."
""


from typing import Any, Dict, Optional

import click

from ..models import ProductCreate
from . import CLIState, emit, invoke_with_handling, load_model, pass_state, with_error_handling


def register(root: click.Group) -> None:
    """
    Attach product related commands to the provided root group.
    """

    @root.group(name="products", help="Product related operations.")
    def products() -> None:
        """
        Product commands.
        """

    @products.command(name="list")
    @click.option("--page", type=int, help="Page number used for pagination.")
    @click.option("--limit", type=int, help="Items per page for pagination.")
    @click.option(
        "--sort",
        type=click.Choice(("asc", "desc"), case_sensitive=False),
        help="Sort order applied to results.",
    )
    @with_error_handling
    @pass_state
    def list_products(
            state: CLIState,
            page: Optional[int],
            limit: Optional[int],
            sort: Optional[str]) -> None:
        """
        List products from the Unified Downloads API.
        """

        params: Dict[str, Any] = {}

        if page is not None:
            params["page"] = page

        if limit is not None:
            params["limit"] = limit

        if sort is not None:
            params["sort"] = sort.lower()

        result = invoke_with_handling(
            lambda: state.client.list_products(params=params or None),
        )

        emit(result, state)

    @products.command(name="get")
    @click.argument("product_id", type=int)
    @with_error_handling
    @pass_state
    def get_product(
            state: CLIState,
            product_id: int) -> None:
        """
        Retrieve a product by identifier.
        """

        result = invoke_with_handling(
            lambda: state.client.get_product(product_id),
        )

        emit(result, state)

    @products.command(name="create")
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the product payload.",
    )
    @with_error_handling
    @pass_state
    def create_product(
            state: CLIState,
            payload_path: str) -> None:
        """
        Create a product using a YAML payload.
        """

        payload = load_model(payload_path, ProductCreate)

        result = invoke_with_handling(
            lambda: state.client.create_product(payload),
        )

        emit(result, state)

    @products.command(name="update")
    @click.argument("product_id", type=int)
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the product payload.",
    )
    @with_error_handling
    @pass_state
    def update_product(
            state: CLIState,
            product_id: int,
            payload_path: str) -> None:
        """
        Update a product using a YAML payload.
        """

        payload = load_model(payload_path, ProductCreate)

        result = invoke_with_handling(
            lambda: state.client.update_product(product_id, payload),
        )

        emit(result, state)

    @products.command(name="delete")
    @click.argument("product_id", type=int)
    @with_error_handling
    @pass_state
    def delete_product(
            state: CLIState,
            product_id: int) -> None:
        """
        Delete a product.
        """

        result = invoke_with_handling(
            lambda: state.client.delete_product(product_id),
        )

        emit(result, state)


# The end.
