""
"Repository resource command registrations."
""


from typing import Any, Dict, Optional

import click

from ..models import RepositoryCreate
from . import (
    CLIState,
    emit,
    invoke_with_handling,
    load_model,
    pass_state,
    with_error_handling,
)


def register(root: click.Group) -> None:
    """
    Attach repository related commands to the provided root group.
    """

    @root.group(name="repositories", help="Repository operations.")
    def repositories() -> None:
        """
        Repository commands.
        """

    @repositories.command(name="list")
    @click.argument("product_version_id", type=int)
    @click.option("--page", type=int, help="Page number used for pagination.")
    @click.option("--limit", type=int, help="Items per page for pagination.")
    @click.option(
        "--sort",
        type=click.Choice(("asc", "desc"), case_sensitive=False),
        help="Sort order applied to results.",
    )
    @with_error_handling
    @pass_state
    def list_repositories(
            state: CLIState,
            product_version_id: int,
            page: Optional[int],
            limit: Optional[int],
            sort: Optional[str]) -> None:
        """
        List repositories for a product version.
        """

        params: Dict[str, Any] = {}

        if page is not None:
            params["page"] = page

        if limit is not None:
            params["limit"] = limit

        if sort is not None:
            params["sort"] = sort.lower()

        result = invoke_with_handling(
            lambda: state.client.list_repositories(
                product_version_id,
                params=params or None,
            ),
        )

        emit(result, state)

    @repositories.command(name="get")
    @click.argument("product_version_id", type=int)
    @click.argument("repository_id", type=int)
    @with_error_handling
    @pass_state
    def get_repository(
            state: CLIState,
            product_version_id: int,
            repository_id: int) -> None:
        """
        Retrieve a repository by identifier.
        """

        result = invoke_with_handling(
            lambda: state.client.get_repository(product_version_id, repository_id),
        )

        emit(result, state)

    @repositories.command(name="create")
    @click.argument("product_version_id", type=int)
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the repository payload.",
    )
    @with_error_handling
    @pass_state
    def create_repository(
            state: CLIState,
            product_version_id: int,
            payload_path: str) -> None:
        """
        Create a repository for a product version.
        """

        payload = load_model(payload_path, RepositoryCreate)

        result = invoke_with_handling(
            lambda: state.client.create_repository(product_version_id, payload),
        )

        emit(result, state)

    @repositories.command(name="update")
    @click.argument("product_version_id", type=int)
    @click.argument("repository_id", type=int)
    @click.option(
        "--file",
        "payload_path",
        required=True,
        type=str,
        help="Path to a YAML file describing the repository payload.",
    )
    @with_error_handling
    @pass_state
    def update_repository(
            state: CLIState,
            product_version_id: int,
            repository_id: int,
            payload_path: str) -> None:
        """
        Update a repository for a product version.
        """

        payload = load_model(payload_path, RepositoryCreate)

        result = invoke_with_handling(
            lambda: state.client.update_repository(product_version_id, repository_id, payload),
        )

        emit(result, state)

    @repositories.command(name="delete")
    @click.argument("product_version_id", type=int)
    @click.argument("repository_id", type=int)
    @with_error_handling
    @pass_state
    def delete_repository(
            state: CLIState,
            product_version_id: int,
            repository_id: int) -> None:
        """
        Delete a repository for a product version.
        """

        result = invoke_with_handling(
            lambda: state.client.delete_repository(product_version_id, repository_id),
        )

        emit(result, state)


# The end.
