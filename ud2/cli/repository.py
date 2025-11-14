"""
Repository resource command registrations.
"""


from typing import Optional, Sequence

from click import Choice, argument, echo, option, group

from ..loader import pretty_yaml, load_yaml
from ..models import Repository, RepositoryCreate
from .util import CLIState, catchall, tabulate, pass_state


def render_repositories(repositories: Sequence[Repository], yaml: bool) -> None:
    """
    Render repositories according to the configured output mode.
    """

    if yaml:
        pretty_yaml(repositories)
        return

    headers = ("ID", "Description", "File Name", "File Size", "Product", "Version")
    rows = [
        (
            repository.id,
            repository.description,
            repository.file_name,
            repository.file_size,
            repository.product_name or "",
            repository.product_version or "",
        )
        for repository in repositories
    ]
    tabulate(headers, rows)


def render_repository(repository: Repository, yaml: bool) -> None:
    """
    Render a single repository according to the configured output mode.
    """

    if yaml:
        pretty_yaml(repository)
        return

    echo(f"Description: {repository.description}  [ID: {repository.id}]")
    echo(f"File Name: {repository.file_name}")
    echo(f"File Size: {repository.file_size}")
    echo(f"Visibility: {repository.visibility.value if repository.visibility else ''}")
    echo(f"Product: {repository.product_name or ''}")
    echo(f"Version: {repository.product_version or ''}")
    echo(f"Architecture: {repository.architecture.value if repository.architecture else ''}")
    echo(f"Platform: {repository.platform.value if repository.platform else ''}")
    echo(f"Created At: {repository.created_at.isoformat() if repository.created_at else ''}")
    echo(f"Updated At: {repository.updated_at.isoformat() if repository.updated_at else ''}")


@group(name="repository", help="Repository operations.")
def repository() -> None:
    """
    Repository commands.
    """


@repository.command(name="list")
@argument("product_version_id", type=int)
@option("--page", type=int, help="Page number used for pagination.")
@option("--limit", type=int, help="Items per page for pagination.")
@option("--sort", type=Choice(("asc", "desc"), case_sensitive=False),
        help="Sort order applied to results.")
@pass_state
@catchall
def list_repositories(
        state: CLIState,
        product_version_id: int,
        page: Optional[int],
        limit: Optional[int],
        sort: Optional[str]) -> None:
    """
    List repositories for a product version.
    """

    paginated_explicitly = page is not None or limit is not None

    if paginated_explicitly:
        page = state.client.page_repositories(
            product_version_id=product_version_id,
            page=page,
            limit=limit,
            sort=sort,
        )
        repos = list(page.data)

    else:
        repos = state.client.list_repositories(
            product_version_id=product_version_id,
            sort=sort,
        )

    render_repositories(repos, state.yaml_output)


@repository.command(name="get")
@argument("product_version_id", type=int)
@argument("repository_id", type=int)
@pass_state
@catchall
def get_repository(
        state: CLIState,
        product_version_id: int,
        repository_id: int) -> None:
    """
    Retrieve a repository by identifier.
    """

    repository = state.client.get_repository(product_version_id, repository_id)
    render_repository(repository, state.yaml_output)


@repository.command(name="create")
@argument("product_version_id", type=int)
@option("--file", "payload_path", required=True,
        help="Path to a YAML file describing the repository payload.")
@pass_state
@catchall
def create_repository(
        state: CLIState,
        product_version_id: int,
        payload_path: str) -> None:
    """
    Create a repository for a product version.
    """

    payload = load_yaml(payload_path, model=RepositoryCreate)
    repository = state.client.create_repository(product_version_id, payload)
    render_repository(repository, state.yaml_output)


@repository.command(name="update")
@argument("product_version_id", type=int)
@argument("repository_id", type=int)
@option("--file", "payload_path", required=True,
        help="Path to a YAML file describing the repository payload.")
@pass_state
@catchall
def update_repository(
        state: CLIState,
        product_version_id: int,
        repository_id: int,
        payload_path: str) -> None:
    """
    Update a repository for a product version.
    """

    payload = load_yaml(payload_path, model=RepositoryCreate)
    repository = state.client.update_repository(product_version_id, repository_id, payload)
    render_repository(repository, state.yaml_output)


@repository.command(name="delete")
@argument("product_version_id", type=int)
@argument("repository_id", type=int)
@pass_state
@catchall
def delete_repository(
        state: CLIState,
        product_version_id: int,
        repository_id: int) -> None:
    """
    Delete a repository for a product version.
    """

    state.client.delete_repository(product_version_id, repository_id)
    echo("Success.")


# The end.
