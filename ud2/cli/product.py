""
"Product resource command registrations."
""


from typing import Any, Dict, List, Optional

import click

from ..models import PaginatedProducts, ProductCreate
from . import CLIState, emit, invoke_with_handling, load_model, pass_state, with_error_handling


FRIENDLY_PRODUCT_COLUMNS = (
    "id",
    "name",
    "eng_id",
    "product_code",
)


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

        params = _build_product_params(page=page, limit=limit, sort=sort)

        payload = invoke_with_handling(
            lambda: _collect_products(state, params),
        )

        if not state.yaml_output:
            payload = _prepare_friendly_product_list(payload)

        emit(payload, state)

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


def _build_product_params(
        page: Optional[int],
        limit: Optional[int],
        sort: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Construct request parameters for product listing calls.
    """

    params: Dict[str, Any] = {}

    if page is not None:
        params["page"] = page

    if limit is not None:
        params["limit"] = limit

    if sort is not None:
        params["sort"] = sort.lower()

    return params or None


def _collect_products(
        state: CLIState,
        params: Optional[Dict[str, Any]]) -> PaginatedProducts:
    """
    Retrieve product listings, defaulting to all pages when pagination is unset.
    """

    base_params: Dict[str, Any] = dict(params or {})
    paginated_explicitly = any(key in base_params for key in ("page", "limit"))

    initial = state.client.list_products(params=base_params or None)
    initial_page = _ensure_paginated_products(initial)

    if paginated_explicitly or initial_page.total_pages <= 1:
        return initial_page

    all_rows: List[Dict[str, Any]] = [
        product.model_dump()
        for product in initial_page.data
    ]

    for next_page in range(initial_page.page + 1, initial_page.total_pages + 1):
        page_params = dict(base_params)
        page_params["page"] = next_page
        page_params["limit"] = initial_page.limit

        page_result = state.client.list_products(params=page_params)
        page_obj = _ensure_paginated_products(page_result)

        all_rows.extend(
            product.model_dump()
            for product in page_obj.data
        )

    combined = initial_page.model_dump()
    combined.update({
        "page": 1,
        "limit": len(all_rows),
        "total": len(all_rows),
        "total_pages": 1,
        "data": all_rows,
    })

    return PaginatedProducts.model_validate(combined)


def _ensure_paginated_products(payload: Any) -> PaginatedProducts:
    """
    Coerce arbitrary payloads into a PaginatedProducts instance.
    """

    if isinstance(payload, PaginatedProducts):
        return payload

    return PaginatedProducts.model_validate(payload)


def _prepare_friendly_product_list(payload: PaginatedProducts) -> Dict[str, Any]:
    """
    Format a product listing payload for friendly CLI presentation.
    """

    page_obj = _ensure_paginated_products(payload)

    prepared = page_obj.model_dump()
    rows = prepared.get("data", [])

    trimmed: List[Dict[str, Any]] = []

    for entry in rows:
        trimmed_row: Dict[str, Any] = {}

        for field in FRIENDLY_PRODUCT_COLUMNS:
            trimmed_row[field] = entry.get(field, "")

        trimmed.append(trimmed_row)

    prepared["data"] = trimmed

    return prepared


# The end.
