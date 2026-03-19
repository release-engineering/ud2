"""
Release check and push command registrations.
"""

import sys
from pathlib import Path
from typing import Any, Dict

import click
from click import ClickException, argument, echo, group, option

from ..loader import load_yaml, pretty_yaml
from ..models import Release
from ..release import ReleaseError, apply_release, check_release
from .util import CLIState, catchall, pass_state


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

    for item in report['repos']:
        entry = item['entry']
        action = item['action']
        if action == 'error':
            echo(f"  [{entry.description}] ERROR: {item.get('message', '')}")
        else:
            match = item.get('match_kind', '')
            match_str = f" (by {match})" if match else ""
            echo(f"  [{entry.description}] {action}{match_str}")

    if report['errors']:
        echo("")
        echo("Errors:")
        for err in report['errors']:
            echo(f"  - {err}")


@group(name="release", help="Release check and push operations.")
def release() -> None:
    """Release commands."""


@release.command(name="check")
@argument("releasefile", type=click.Path(exists=True, path_type=Path))
@pass_state
@catchall
def check(state: CLIState, releasefile: Path) -> None:
    """Check release manifest against server state (no writes)."""
    release_obj = load_yaml(str(releasefile), model=Release)
    report = check_release(state.client, release_obj)
    render_check_report(report, state.yaml_output)
    if report['errors']:
        sys.exit(1)
    if not report['in_sync']:
        sys.exit(2)
    sys.exit(0)


@release.command(name="push")
@argument("releasefile", type=click.Path(exists=True, path_type=Path))
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
    try:
        release_obj = load_yaml(str(releasefile), model=Release)
        result = apply_release(
            state.client, release_obj,
            force_filename=force_filename, upload=upload,
            manifest_path=str(releasefile),
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
