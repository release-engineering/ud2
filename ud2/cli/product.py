"""
Product resource command registrations.
"""


from io import StringIO
from pathlib import Path
from typing import Optional, Sequence

from click import Choice, ClickException, argument, echo, option, group

from ..loader import pretty_yaml, load_yaml
from ..models import Product, ProductCreate
from .util import CLIState, merge_payload, pass_state, catchall, tabulate


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

    echo(f"Product: {product.name} [ID: {product.id}]")
    echo(f"  Engineering ID: {product.eng_id}")
    echo(f"  Category: {product.category}")
    echo(f"  Arch: {product.arch.value if product.arch else ''}")
    echo(f"  Product Code: {product.product_code}")
    echo(f"  Product Group: {product.product_group}")
    echo(f"  Product Group Name: {product.product_group_name}")


@group(name="product", help="Product related operations.")
def product() -> None:
    """
    Product commands.
    """


@product.command(name="list")
@option("--page", type=int, help="Page number used for pagination.")
@option("--limit", type=int, help="Items per page for pagination.")
@option("--sort", type=Choice(("asc", "desc"), case_sensitive=False),
        help="Sort by resource ID: asc (default) or desc.")
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
        products = state.client.list_products(sort=sort)

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
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the product payload.")
@option("--name", type=str, help="Product name.")
@option("--eng-id", "eng_id", type=int, help="Engineering ID.")
@option("--arch", type=str, help="Architecture (e.g. x86_64).")
@option("--category", type=str, help="Category.")
@option("--product-code", "product_code", type=str, help="Product code.")
@option("--product-group", "product_group", type=str, help="Product group.")
@option("--product-group-name", "product_group_name", type=str,
        help="Product group name.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def create_product(
        state: CLIState,
        yaml_path: Optional[Path],
        name: Optional[str],
        eng_id: Optional[int],
        arch: Optional[str],
        category: Optional[str],
        product_code: Optional[str],
        product_group: Optional[str],
        product_group_name: Optional[str],
        dry_run: bool = False) -> None:
    """
    Create a product. Use --yaml-file or --name with --eng-id.
    """

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        data = merge_payload(
            data,
            name=name,
            eng_id=eng_id,
            arch=arch,
            category=category,
            product_code=product_code,
            product_group=product_group,
            product_group_name=product_group_name,
        )
    else:
        if name is None or eng_id is None:
            raise ClickException(
                "Provide --yaml-file or both --name and --eng-id.",
            )
        data = merge_payload(
            {},
            name=name,
            eng_id=eng_id,
            arch=arch,
            category=category,
            product_code=product_code,
            product_group=product_group,
            product_group_name=product_group_name,
        )

    payload = ProductCreate.model_validate(data)
    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    product = state.client.create_product(payload)
    render_product(product, state.yaml_output)


@product.command(name="update")
@argument("product_id", type=int)
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the product payload.")
@option("--name", type=str, help="Product name.")
@option("--eng-id", "eng_id", type=int, help="Engineering ID.")
@option("--arch", type=str, help="Architecture (e.g. x86_64).")
@option("--category", type=str, help="Category.")
@option("--product-code", "product_code", type=str, help="Product code.")
@option("--product-group", "product_group", type=str, help="Product group.")
@option("--product-group-name", "product_group_name", type=str,
        help="Product group name.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def update_product(
        state: CLIState,
        product_id: int,
        yaml_path: Optional[Path],
        name: Optional[str],
        eng_id: Optional[int],
        arch: Optional[str],
        category: Optional[str],
        product_code: Optional[str],
        product_group: Optional[str],
        product_group_name: Optional[str],
        dry_run: bool = False) -> None:
    """
    Update a product. Provide --yaml-file or at least one field to update.
    """

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        data = merge_payload(
            data,
            name=name,
            eng_id=eng_id,
            arch=arch,
            category=category,
            product_code=product_code,
            product_group=product_group,
            product_group_name=product_group_name,
        )
        payload = ProductCreate.model_validate(data)
    else:
        has_option = any(
            v is not None
            for v in (
                name,
                eng_id,
                arch,
                category,
                product_code,
                product_group,
                product_group_name,
            )
        )
        if not has_option:
            raise ClickException(
                "Provide --yaml-file or at least one field to update.",
            )
        existing = state.client.get_product(product_id)
        data = existing.model_dump(by_alias=False, exclude_none=True)
        data.pop('id', None)
        data = merge_payload(
            data,
            name=name,
            eng_id=eng_id,
            arch=arch,
            category=category,
            product_code=product_code,
            product_group=product_group,
            product_group_name=product_group_name,
        )
        payload = ProductCreate.model_validate(data)

    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    product = state.client.update_product(product_id, payload)
    render_product(product, state.yaml_output)


@product.command(name="search")
@option("--name", type=str, help="Product name (partial, case-insensitive).")
@option("--eng-id", "eng_id", type=int,
        help="Engineering ID (exact match, must be > 0).")
@option("--page", type=int, help="Page number.")
@option("--limit", type=int, help="Items per page.")
@pass_state
@catchall
def search_products(
        state: CLIState,
        name: Optional[str],
        eng_id: Optional[int],
        page: Optional[int],
        limit: Optional[int]) -> None:
    """
    Search products by name and/or engineering ID.
    """

    if name is None and eng_id is None:
        raise ClickException("At least one of --name or --eng-id is required.")

    page_obj = state.client.search_products(
        name=name,
        eng_id=eng_id,
        page=page,
        limit=limit,
    )
    render_products(list(page_obj.data), state.yaml_output)


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
