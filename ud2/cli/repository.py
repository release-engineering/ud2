"""
Repository resource command registrations.
"""


from io import StringIO
from pathlib import Path
from typing import List, Optional, Sequence

from click import Choice, ClickException, Path as ClickPath, argument, echo
from click import option, group

from ..checksums import file_metadata
from ..loader import pretty_yaml, load_yaml
from ..models import Repository, RepositoryCreate
from .util import CLIState, merge_payload, catchall, tabulate, pass_state


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

    echo(f"Repository: {repository.description} [ID: {repository.id}]")
    echo(f"  Product: {repository.product_name or ''}")
    echo(f"  Version: {repository.product_version or ''}")
    echo(f"  File Name: {repository.file_name}")
    echo(f"  File Size: {repository.file_size}")
    echo(f"  SHA256: {repository.sha256}")
    echo(f"  Content Types: {', '.join(repository.content_types)}")
    echo(f"  Published: {repository.publish_date.isoformat() if repository.publish_date else ''}")
    echo(f"  Updated: {repository.update_date.isoformat() if repository.update_date else ''}")


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
@argument("file_id", type=int)
@pass_state
@catchall
def get_repository(
        state: CLIState,
        file_id: int) -> None:
    """
    Retrieve a repository (file) by identifier.
    """

    repository = state.client.get_repository(file_id)
    render_repository(repository, state.yaml_output)


def _split_comma(s: Optional[str]) -> List[str]:
    """Split comma-separated string into list, stripping whitespace."""

    if s is None or not s.strip():
        return []
    return [part.strip() for part in s.split(',') if part.strip()]


@repository.command(name="create")
@argument("product_version_id", type=int)
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the repository payload.")
@option("--file", "artifact_path", type=ClickPath(exists=True, path_type=Path),
        help="Path to artifact on disk (sets file_name, file_size, sha256, md5).")
@option("--desc", "description", type=str, help="Short description (title).")
@option("--visibility", type=str, default='visible', help="Visibility.")
@option("--content-type", "content_type", type=str, multiple=True,
        help="Content type (repeatable).")
@option("--issues", type=str, help="Comma-separated issue IDs (e.g. TUSC-1234,TUSC-5678).")
@option("--classifier", type=str, help="Comma-separated classifier values.")
@option("--installation", type=str, help="Installation instructions.")
@option("--long-desc", "long_description", type=str,
        help="Long description.")
@option("--long-desc-file", "long_desc_file", type=ClickPath(exists=True, path_type=Path),
        help="Path to a file whose contents are used as the long description.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def create_repository(
        state: CLIState,
        product_version_id: int,
        yaml_path: Optional[Path],
        artifact_path: Optional[Path],
        description: Optional[str],
        visibility: Optional[str],
        content_type: tuple,
        issues: Optional[str],
        classifier: Optional[str],
        installation: Optional[str],
        long_description: Optional[str],
        long_desc_file: Optional[Path],
        dry_run: bool = False) -> None:
    """
    Create a repository. Use --yaml-file or --file with --description.
    """

    if long_desc_file is not None:
        long_description = long_desc_file.read_text(encoding='utf-8')

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        if artifact_path is not None:
            meta = file_metadata(artifact_path)
            data = merge_payload(
                data,
                fileName=meta['fileName'],
                fileSize=meta['fileSize'],
                sha256=meta['sha256'],
                md5=meta['md5'],
            )
        data = merge_payload(
            data,
            description=description,
            visibility=visibility,
            contentTypes=list(content_type) if content_type else None,
            issues=_split_comma(issues) if issues else None,
            classifier=_split_comma(classifier) if classifier else None,
            installation=installation,
            longDescription=long_description,
        )
    else:
        if artifact_path is None or description is None:
            raise ClickException(
                "Provide --yaml-file or both --file (artifact) and --description.",
            )
        meta = file_metadata(artifact_path)
        content_types = list(content_type) if content_type else []
        issues_list = _split_comma(issues) if issues else []
        classifier_list = _split_comma(classifier) if classifier else []

        data = {
            'description': description,
            'fileName': meta['fileName'],
            'fileSize': meta['fileSize'],
            'sha256': meta['sha256'],
            'md5': meta['md5'],
            'issues': issues_list,
            'visibility': visibility or 'visible',
            'classifier': classifier_list,
            'contentTypes': content_types,
            'installation': installation,
            'longDescription': long_description,
        }

    payload = RepositoryCreate.model_validate(data)
    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    repository = state.client.create_repository(product_version_id, payload)
    render_repository(repository, state.yaml_output)


@repository.command(name="update")
@argument("file_id", type=int)
@option("--yaml-file", "yaml_path", type=Path,
        help="Path to a YAML file describing the repository payload.")
@option("--file", "artifact_path", type=ClickPath(exists=True, path_type=Path),
        help="Path to artifact on disk (sets file_name, file_size, sha256, md5).")
@option("--desc", "description", type=str, help="Short description (title).")
@option("--visibility", type=str, help="Visibility.")
@option("--content-type", "content_type", type=str, multiple=True,
        help="Content type (repeatable).")
@option("--issues", type=str, help="Comma-separated issue IDs.")
@option("--classifier", type=str, help="Comma-separated classifier values.")
@option("--installation", type=str, help="Installation instructions.")
@option("--long-desc", "long_description", type=str,
        help="Long description.")
@option("--long-desc-file", "long_desc_file", type=ClickPath(exists=True, path_type=Path),
        help="Path to a file whose contents are used as the long description.")
@option("--dry-run", is_flag=True,
        help="Show payload YAML without sending.")
@pass_state
@catchall
def update_repository(
        state: CLIState,
        file_id: int,
        yaml_path: Optional[Path],
        artifact_path: Optional[Path],
        description: Optional[str],
        visibility: Optional[str],
        content_type: tuple,
        issues: Optional[str],
        classifier: Optional[str],
        installation: Optional[str],
        long_description: Optional[str],
        long_desc_file: Optional[Path],
        dry_run: bool = False) -> None:
    """
    Update a repository. Provide --yaml-file, --file, or at least one field.
    """

    if long_desc_file is not None:
        long_description = long_desc_file.read_text(encoding='utf-8')

    has_inline = any(
        v is not None
        for v in (
            description,
            visibility,
            content_type,
            issues,
            classifier,
            installation,
            long_description,
            long_desc_file,
        )
    )
    if yaml_path is None and artifact_path is None and not has_inline:
        raise ClickException(
            "Provide --yaml-file, --file (artifact), or at least one field.",
        )

    if yaml_path is not None:
        data = load_yaml(str(yaml_path))
        if artifact_path is not None:
            meta = file_metadata(artifact_path)
            data = merge_payload(
                data,
                fileName=meta['fileName'],
                fileSize=meta['fileSize'],
                sha256=meta['sha256'],
                md5=meta['md5'],
            )
        data = merge_payload(
            data,
            description=description,
            visibility=visibility,
            contentTypes=list(content_type) if content_type else None,
            issues=_split_comma(issues) if issues else None,
            classifier=_split_comma(classifier) if classifier else None,
            installation=installation,
            longDescription=long_description,
        )
    else:
        existing = state.client.get_repository(file_id)
        data = existing.model_dump(by_alias=False, exclude_none=True)
        data.pop('id', None)
        data.pop('product_name', None)
        data.pop('product_version', None)
        data.pop('publish_date', None)
        data.pop('update_date', None)

        if artifact_path is not None:
            meta = file_metadata(artifact_path)
            data = merge_payload(
                data,
                fileName=meta['fileName'],
                fileSize=meta['fileSize'],
                sha256=meta['sha256'],
                md5=meta['md5'],
            )
        data = merge_payload(
            data,
            description=description,
            visibility=visibility,
            contentTypes=list(content_type) if content_type else None,
            issues=_split_comma(issues) if issues else None,
            classifier=_split_comma(classifier) if classifier else None,
            installation=installation,
            longDescription=long_description,
        )

    payload = RepositoryCreate.model_validate(data)
    if dry_run:
        buf = StringIO()
        pretty_yaml(payload.model_dump(by_alias=False, exclude_none=True), out=buf)
        echo(buf.getvalue())
        return
    repository = state.client.update_repository(file_id, payload)
    render_repository(repository, state.yaml_output)


@repository.command(name="search")
@option("--product-id", "product_id", type=int,
        help="Product ID (exact match).")
@option("--version-id", "version_id", type=int,
        help="Product version ID (exact match).")
@option("--desc", "description", type=str,
        help="Description (glob pattern, case-insensitive).")
@option("--file-name", "file_name", type=str,
        help="File name (glob pattern).")
@option("--jira", type=str, help="Jira issue ID (e.g. TUSC-1234).")
@option("--content-type", "content_type", type=str, help="Content type.")
@option("--jboss-id", "jboss_id", type=int, help="JBoss ID (exact match).")
@option("--page", type=int, help="Page number.")
@option("--limit", type=int, help="Items per page.")
@pass_state
@catchall
def search_repositories(
        state: CLIState,
        product_id: Optional[int],
        version_id: Optional[int],
        description: Optional[str],
        file_name: Optional[str],
        jira: Optional[str],
        content_type: Optional[str],
        jboss_id: Optional[int],
        page: Optional[int],
        limit: Optional[int]) -> None:
    """
    Search files by various metadata.
    """

    has_search = any(
        v is not None
        for v in (
            product_id,
            version_id,
            description,
            file_name,
            jira,
            content_type,
            jboss_id,
        )
    )
    if not has_search:
        raise ClickException(
            "At least one search parameter is required "
            "(--product-id, --version-id, --description, --file-name, "
            "--jira, --content-type, or --jboss-id).",
        )

    page_obj = state.client.search_files(
        product_id=product_id,
        version_id=version_id,
        description=description,
        file_name=file_name,
        jira=jira,
        content_type=content_type,
        jboss_id=jboss_id,
        page=page,
        limit=limit,
    )
    render_repositories(list(page_obj.data), state.yaml_output)


@repository.command(name="delete")
@argument("file_id", type=int)
@pass_state
@catchall
def delete_repository(
        state: CLIState,
        file_id: int) -> None:
    """
    Delete a repository (file).
    """

    state.client.delete_repository(file_id)
    echo("Success.")


# The end.
