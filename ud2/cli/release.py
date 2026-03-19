"""
Release check and push command registrations.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from click import ClickException, Path as ClickPath, argument, echo, group, option

from ..checksums import file_metadata
from ..loader import load_yaml, pretty_yaml
from ..models import ProductRef, Release, RepositoryEntry, VersionRef
from ..release import (
    ReleaseError,
    apply_release,
    check_release,
    load_release_manifest,
    write_release_manifest,
)
from .util import CLIState, catchall, merge_payload, pass_state


def resolve_release_path(path: Path) -> Path:
    """
    Resolve release manifest path. If path is a directory, use dir/ud-release.yml.
    """

    if path.is_dir():
        candidate = path / 'ud-release.yml'
        if not candidate.is_file():
            raise ClickException(
                f"Directory {path} does not contain ud-release.yml",
            )
        return candidate
    return path


def _split_comma(s: Optional[str]) -> List[str]:
    """Split comma-separated string into list, stripping whitespace."""

    if s is None or not s.strip():
        return []
    return [part.strip() for part in s.split(',') if part.strip()]


def _report_to_serializable(report: Dict[str, Any]) -> Dict[str, Any]:
    """Convert report to JSON/YAML-serializable form."""
    result = {
        'product': {
            'status': report['product']['status'],
            'product': (
                report['product']['product'].model_dump(by_alias=False)
                if report['product']['product'] else None
            ),
        },
        'version': {
            'status': report['version']['status'],
            'version': (
                report['version']['version'].model_dump(by_alias=False)
                if report['version']['version'] else None
            ),
        },
        'repos': [],
        'errors': report['errors'],
        'in_sync': report['in_sync'],
    }

    for item in report['repos']:
        entry = item['entry']
        row = {
            'description': entry.description,
            'fileName': entry.file_name,
            'action': item['action'],
        }
        if 'match_kind' in item and item['match_kind']:
            row['match_kind'] = item['match_kind']
        if 'error' in item:
            row['error'] = item['error']
        if 'message' in item:
            row['message'] = item['message']
        if 'repo' in item and item['repo']:
            row['repo_id'] = item['repo'].id
        result['repos'].append(row)

    return result


def render_check_report(report: Dict[str, Any], yaml_mode: bool) -> None:
    """Render check report in friendly or YAML mode."""
    if yaml_mode:
        pretty_yaml(_report_to_serializable(report))
        return

    echo(f"Product: {report['product']['status']}")
    if report['product']['product']:
        p = report['product']['product']
        echo(f"  ID: {p.id}, Name: {p.name}")

    echo(f"Version: {report['version']['status']}")
    if report['version']['version']:
        v = report['version']['version']
        echo(f"  ID: {v.id}, Version: {v.version}")

    echo("Files:")
    for item in report['repos']:
        entry = item['entry']
        action = item['action']
        repo = item.get('repo')
        file_id_str = f" [ID: {repo.id}]" if repo else ""
        if action == 'error':
            echo(f"  [{entry.description}]{file_id_str} ERROR: {item.get('message', '')}")
        else:
            match = item.get('match_kind', '')
            match_str = f" (by {match})" if match else ""
            echo(f"  [{entry.description}]{file_id_str} {action}{match_str}")

    if report['errors']:
        echo("")
        echo("Errors:")
        for err in report['errors']:
            echo(f"  - {err}")


@group(name="release", help="Release check and push operations.")
def release() -> None:
    """Release commands."""


@release.command(name="init")
@argument("releasefile", type=click.Path(path_type=Path))
@option("--product-id", "product_id", type=int, help="Product ID.")
@option("--product-eng-id", "product_eng_id", type=int, help="Product eng ID.")
@option("--product-name", "product_name", type=str, help="Product name.")
@option("--version", "version_str", required=True, type=str,
        help="Version string.")
@option("--architecture", type=str, help="Architecture.")
@option("--platform", type=str, help="Platform.")
@option("--visibility", type=str, help="Visibility.")
@option("--cpe", type=str, help="CPE.")
@option("--force", is_flag=True, help="Overwrite existing file.")
@pass_state
@catchall
def init(
        state: CLIState,
        releasefile: Path,
        product_id: Optional[int],
        product_eng_id: Optional[int],
        product_name: Optional[str],
        version_str: str,
        architecture: Optional[str],
        platform: Optional[str],
        visibility: Optional[str],
        cpe: Optional[str],
        force: bool) -> None:
    """Create a new release manifest."""
    has_id = product_id is not None
    has_search = product_eng_id is not None and product_name is not None
    if not has_id and not has_search:
        raise ClickException(
            "Specify --product-id or both --product-eng-id and --product-name.",
        )

    path = Path(releasefile)
    if path.exists() and not force:
        raise ClickException(
            f"File exists: {path}. Use --force to overwrite.",
        )

    if has_id:
        product_ref = ProductRef(id=product_id)
    else:
        product_ref = ProductRef(
            eng_id=product_eng_id,
            name=product_name,
        )

    version_ref = VersionRef(
        version=version_str,
        architecture=architecture,
        platform=platform,
        visibility=visibility,
        cpe=cpe,
    )

    release_obj = Release(
        product=product_ref,
        version=version_ref,
        repositories=[],
    )

    write_release_manifest(path, release_obj)
    echo(f"Created {path}")


@release.command(name="add")
@argument("releasefile", type=click.Path(
    exists=True, path_type=Path, file_okay=True, dir_okay=True))
@option("--file", "artifact_path", type=ClickPath(exists=True, path_type=Path),
        help="Path to artifact (sets file_name, file_size, sha256, md5).")
@option("--desc", "description", type=str, help="Short description (title).")
@option("--file-name", "file_name", type=str, help="File name (explicit mode).")
@option("--file-size", "file_size", type=int, help="File size (explicit mode).")
@option("--sha256", type=str, help="SHA256 checksum (explicit mode).")
@option("--md5", type=str, help="MD5 checksum (explicit mode).")
@option("--visibility", type=str, default='visible', help="Visibility.")
@option("--content-type", "content_type", type=str, multiple=True,
        help="Content type (repeatable).")
@option("--issues", type=str, help="Comma-separated issue IDs.")
@option("--classifier", type=str, help="Comma-separated classifier values.")
@option("--installation", type=str, help="Installation instructions.")
@option("--long-desc", "long_description", type=str,
        help="Long description.")
@option("--long-desc-file", "long_desc_file",
        type=ClickPath(exists=True, path_type=Path),
        help="Path to file for long description.")
@option("--no-path", "no_path", is_flag=True,
        help="Do not set path in entry when using --file.")
@pass_state
@catchall
def add(
        state: CLIState,
        releasefile: Path,
        artifact_path: Optional[Path],
        description: Optional[str],
        file_name: Optional[str],
        file_size: Optional[int],
        sha256: Optional[str],
        md5: Optional[str],
        visibility: Optional[str],
        content_type: tuple,
        issues: Optional[str],
        classifier: Optional[str],
        installation: Optional[str],
        long_description: Optional[str],
        long_desc_file: Optional[Path],
        no_path: bool) -> None:
    """Add a repository entry to the release manifest."""

    manifest_path = resolve_release_path(Path(releasefile))
    if long_desc_file is not None:
        long_description = long_desc_file.read_text(encoding='utf-8')

    if artifact_path is not None:
        if description is None:
            raise ClickException(
                "Provide --desc when using --file.",
            )
        meta = file_metadata(artifact_path)
        data = {
            'description': description,
            'fileName': meta['fileName'],
            'fileSize': meta['fileSize'],
            'sha256': meta['sha256'],
            'md5': meta['md5'],
            'issues': _split_comma(issues) if issues else [],
            'visibility': visibility or 'visible',
            'classifier': _split_comma(classifier) if classifier else [],
            'contentTypes': list(content_type) if content_type else [],
            'installation': installation,
            'longDescription': long_description,
        }
        if not no_path:
            data['path'] = str(artifact_path.resolve())
    else:
        required = (description, file_name, file_size, sha256, md5)
        if not all(r is not None for r in required):
            raise ClickException(
                "Provide --file with --desc, or all of --desc, --file-name, "
                "--file-size, --sha256, --md5.",
            )
        data = {
            'description': description,
            'fileName': file_name,
            'fileSize': file_size,
            'sha256': sha256,
            'md5': md5,
            'issues': _split_comma(issues) if issues else [],
            'visibility': visibility or 'visible',
            'classifier': _split_comma(classifier) if classifier else [],
            'contentTypes': list(content_type) if content_type else [],
            'installation': installation,
            'longDescription': long_description,
        }

    entry = RepositoryEntry.model_validate(data)
    release_obj = load_release_manifest(manifest_path)
    release_obj.repositories.append(entry)
    write_release_manifest(manifest_path, release_obj)
    echo(f"Added {entry.description}")


def _find_entry(
        release: Release,
        file_name: Optional[str],
        by_index: Optional[int]) -> int:
    """Return index of matching repository entry. Raise ClickException if not found."""

    if (file_name is None) == (by_index is None):
        raise ClickException(
            "Specify exactly one of --file-name or --by-index.",
        )

    if by_index is not None:
        if by_index < 0 or by_index >= len(release.repositories):
            raise ClickException(
                f"Index {by_index} out of range (0..{len(release.repositories) - 1}).",
            )
        return by_index

    for i, entry in enumerate(release.repositories):
        if entry.file_name == file_name:
            return i
    raise ClickException(f"No entry with file name '{file_name}'.")


@release.command(name="edit")
@argument("releasefile", type=click.Path(
    exists=True, path_type=Path, file_okay=True, dir_okay=True))
@option("--file-name", "file_name", type=str, help="Find entry by file name.")
@option("--by-index", "by_index", type=int, help="Find entry by index.")
@option("--file", "artifact_path", type=ClickPath(exists=True, path_type=Path),
        help="Recompute from artifact on disk.")
@option("--desc", "description", type=str, help="Short description.")
@option("--new-file-name", "file_name_new", type=str, help="New file name.")
@option("--file-size", "file_size", type=int, help="File size.")
@option("--sha256", type=str, help="SHA256 checksum.")
@option("--md5", type=str, help="MD5 checksum.")
@option("--visibility", type=str, help="Visibility.")
@option("--content-type", "content_type", type=str, multiple=True,
        help="Content type (repeatable).")
@option("--issues", type=str, help="Comma-separated issue IDs.")
@option("--classifier", type=str, help="Comma-separated classifier values.")
@option("--installation", type=str, help="Installation instructions.")
@option("--long-desc", "long_description", type=str,
        help="Long description.")
@option("--long-desc-file", "long_desc_file",
        type=ClickPath(exists=True, path_type=Path),
        help="Path to file for long description.")
@option("--path", "path_val", type=str, help="Set path for upload.")
@option("--clear-path", is_flag=True, help="Clear path.")
@option("--dry-run", is_flag=True, help="Show changes, do not write.")
@pass_state
@catchall
def edit(
        state: CLIState,
        releasefile: Path,
        file_name: Optional[str],
        by_index: Optional[int],
        artifact_path: Optional[Path],
        description: Optional[str],
        file_name_new: Optional[str],
        file_size: Optional[int],
        sha256: Optional[str],
        md5: Optional[str],
        visibility: Optional[str],
        content_type: tuple,
        issues: Optional[str],
        classifier: Optional[str],
        installation: Optional[str],
        long_description: Optional[str],
        long_desc_file: Optional[Path],
        path_val: Optional[str],
        clear_path: bool,
        dry_run: bool) -> None:
    """Edit an existing repository entry in the release manifest."""

    manifest_path = resolve_release_path(Path(releasefile))
    if long_desc_file is not None:
        long_description = long_desc_file.read_text(encoding='utf-8')

    if clear_path and path_val is not None:
        raise ClickException("Specify --path or --clear-path, not both.")

    release_obj = load_release_manifest(manifest_path)
    idx = _find_entry(release_obj, file_name, by_index)
    entry = release_obj.repositories[idx]

    existing = entry.model_dump(by_alias=False, exclude_none=True)

    if artifact_path is not None:
        meta = file_metadata(artifact_path)
        existing = merge_payload(
            existing,
            file_name=meta['fileName'],
            file_size=meta['fileSize'],
            sha256=meta['sha256'],
            md5=meta['md5'],
        )

    existing = merge_payload(
        existing,
        description=description,
        file_name=file_name_new,
        file_size=file_size,
        sha256=sha256,
        md5=md5,
        visibility=visibility,
        contentTypes=list(content_type) if content_type else None,
        issues=_split_comma(issues) if issues else None,
        classifier=_split_comma(classifier) if classifier else None,
        installation=installation,
        longDescription=long_description,
    )

    if path_val is not None:
        existing['path'] = path_val
    elif clear_path:
        existing['path'] = None

    updated = RepositoryEntry.model_validate(existing)
    if dry_run:
        pretty_yaml(updated.model_dump(by_alias=True, exclude_none=True))
        return

    release_obj.repositories[idx] = updated
    write_release_manifest(manifest_path, release_obj)
    echo(f"Updated {updated.description}")


@release.command(name="remove")
@argument("releasefile", type=click.Path(
    exists=True, path_type=Path, file_okay=True, dir_okay=True))
@option("--file-name", "file_name", type=str, help="Find entry by file name.")
@option("--by-index", "by_index", type=int, help="Find entry by index.")
@option("--dry-run", is_flag=True, help="Show what would be removed.")
@pass_state
@catchall
def remove(
        state: CLIState,
        releasefile: Path,
        file_name: Optional[str],
        by_index: Optional[int],
        dry_run: bool) -> None:
    """Remove a repository entry from the release manifest."""

    manifest_path = resolve_release_path(Path(releasefile))
    release_obj = load_release_manifest(manifest_path)
    idx = _find_entry(release_obj, file_name, by_index)
    entry = release_obj.repositories[idx]

    if dry_run:
        echo(f"Would remove: {entry.description} ({entry.file_name})")
        return

    release_obj.repositories.pop(idx)
    write_release_manifest(manifest_path, release_obj)
    echo(f"Removed {entry.description}")


@release.command(name="check")
@argument("releasefile", type=click.Path(
    exists=True, path_type=Path, file_okay=True, dir_okay=True))
@pass_state
@catchall
def check(state: CLIState, releasefile: Path) -> None:
    """Check release manifest against server state (no writes)."""
    manifest_path = resolve_release_path(Path(releasefile))
    release_obj = load_yaml(str(manifest_path), model=Release)
    report = check_release(state.client, release_obj)
    render_check_report(report, state.yaml_output)
    if report['errors']:
        sys.exit(1)
    if not report['in_sync']:
        sys.exit(2)
    sys.exit(0)


@release.command(name="push")
@argument("releasefile", type=click.Path(
    exists=True, path_type=Path, file_okay=True, dir_okay=True))
@option("--force-filename", is_flag=True,
        help="Allow same filename when content (sha256) differs.")
@option("--upload", is_flag=True,
        help="Upload file binaries before pushing metadata (not yet implemented).")
@pass_state
@catchall
def push(
        state: CLIState,
        releasefile: Path,
        force_filename: bool,
        upload: bool) -> None:
    """Push release to the server."""
    manifest_path = resolve_release_path(Path(releasefile))
    try:
        release_obj = load_yaml(str(manifest_path), model=Release)
        result = apply_release(
            state.client, release_obj,
            force_filename=force_filename, upload=upload,
            manifest_path=str(manifest_path),
        )
    except ReleaseError as exc:
        raise ClickException(str(exc)) from exc

    if state.yaml_output:
        out = {
            'product': result['product'].model_dump(by_alias=False),
            'version': result['version'].model_dump(by_alias=False),
            'created': [r.model_dump(by_alias=False) for r in result['created']],
            'updated': [r.model_dump(by_alias=False) for r in result['updated']],
        }
        pretty_yaml(out)
        return

    echo(f"Product: {result['product'].name} [ID: {result['product'].id}]")
    echo(f"Version: {result['version'].version} [ID: {result['version'].id}]")
    echo(f"Created: {len(result['created'])} repository(ies)")
    echo(f"Updated: {len(result['updated'])} repository(ies)")


# The end.
