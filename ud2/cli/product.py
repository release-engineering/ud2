"""
Product resource command registrations.
"""


from typing import Optional, Sequence

from click import Choice, argument, echo, option

from ..loader import pretty_yaml, load_yaml
from ..models import Product, ProductCreate
from . import main
from .util import CLIState, pass_state, catchall, tabulate


def render_products(products: Sequence[Product], yaml: bool) -> None:
    """
    Render products according to the configured output mode.
    """

    if yaml:
        pretty_yaml(products)
        return

    headers = ("ID", "Name", "Engineering ID", "Product Code")
    rows = [
        (
            product.id,
            product.name,
            product.eng_id,
            product.product_code,
        )
        for product in products
    ]
    tabulate(headers, rows)


def render_product(product: Product, yaml: bool) -> None:
    """
    Render a single product according to the configured output mode.
    """

    if yaml:
        pretty_yaml(product)
        return

    echo(f"{product.name} [ID: {product.id}]")
    echo(f"Engineering ID: {product.eng_id}")
    echo(f"Product Code: {product.product_code}")
    echo(f"Visibility: {product.visibility.value if product.visibility else ''}")
    echo(f"Architecture: {product.architecture.value if product.architecture else ''}")
    echo(f"Platform: {product.platform.value if product.platform else ''}")


@main.group(name="product", help="Product related operations.")
def product() -> None:
    """
    Product commands.
    """


@product.command(name="list")
@option("--page", type=int, help="Page number used for pagination.")
@option("--limit", type=int, help="Items per page for pagination.")
@option("--sort", type=Choice(("asc", "desc"), case_sensitive=False),
        help="Sort order applied to results.")
@pass_state
@catchall
def list_products(
        state: CLIState,
        page: Optional[int],
        limit: Optional[int],
        sort: Optional[str]) -> None:
    """
    List products from the Unified Downloads API.
    """

    paginated_explicitly = page is not None or limit is not None

    if paginated_explicitly:
        page_obj = state.client.page_products(
            page=page,
            limit=limit,
            sort=sort,
        )
        products = list(page_obj.data)
    else:
        products = list(state.client.iter_products(sort=sort))

    render_products(products, state.yaml_output)


@product.command(name="get")
@argument("product_id", type=int)
@pass_state
@catchall
def get_product(
        state: CLIState,
        product_id: int) -> None:
    """
    Retrieve a product by identifier.
    """

    product = state.client.get_product(product_id)
    render_product(product, state.yaml_output)


@product.command(name="create")
@option("--file", "payload_path", required=True,
        help="Path to a YAML file describing the product payload.")
@pass_state
@catchall
def create_product(
        state: CLIState,
        payload_path: str) -> None:
    """
    Create a product using a YAML payload.
    """

    data = load_yaml(payload_path)
    payload = ProductCreate.model_validate(data)
    product = state.client.create_product(payload)
    render_product(product, state.yaml_output)


@product.command(name="update")
@argument("product_id", type=int)
@option("--file", "payload_path", required=True, type=str,
        help="Path to a YAML file describing the product payload.")
@pass_state
@catchall
def update_product(
        state: CLIState,
        product_id: int,
        payload_path: str) -> None:
    """
    Update a product using a YAML payload.
    """

    payload = load_yaml(payload_path, model=ProductCreate)
    product = state.client.update_product(product_id, payload)
    render_product(product, state.yaml_output)


@product.command(name="delete")
@argument("product_id", type=int)
@pass_state
@catchall
def delete_product(
        state: CLIState,
        product_id: int) -> None:
    """
    Delete a product.
    """

    state.client.delete_product(product_id)
    echo("Success.")


# The end.
