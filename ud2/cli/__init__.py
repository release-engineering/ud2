# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, see <http://www.gnu.org/licenses/>.

"""
UDv2 Command Line Interface package.

::author: Christopher O'Brien <cobrien@redhat.com>
::license: GPLv3
"""

import functools
from typing import Any, Callable, Dict, Tuple

import click

from .. import __version__

ResourceAction = Callable[[Dict[str, Any]], int]
ActionKey = Tuple[str, str]


def _emit_not_implemented_message(resource: str, verb: str, params: Dict[str, Any]) -> int:
    """
    Provide a functional stub for actions that have not been implemented yet.

    :param resource: Name of the resource being handled.
    :param verb: CRUD/REST verb representing the action to perform.
    :param params: Dictionary of keyword arguments provided to the CLI command.

    :returns: An exit status code representing success (0) for the stub.
    """
    click.echo(f"[stub] {resource}:{verb} called with {params}")
    return 0


def _resource_action(resource: str, verb: str) -> Callable[..., None]:
    @click.pass_context
    def command(ctx: click.Context, **kwargs: Any) -> None:
        action: ResourceAction = ctx.obj['actions'][(resource, verb)]
        status = action(kwargs)
        ctx.exit(status)

    command.__name__ = f"{resource}_{verb}"
    command.__doc__ = f"Perform the {verb} action for {resource} resources."
    return command


def _build_default_action_map() -> Dict[ActionKey, ResourceAction]:
    verbs = ('create', 'update', 'delete', 'search', 'list')
    resources = ('product', 'version', 'repository')
    return {
        (resource, verb): functools.partial(
            _emit_not_implemented_message,
            resource=resource,
            verb=verb,
        )
        for resource in resources
        for verb in verbs
    }


def register_resource_group(root: click.Group, resource: str) -> None:
    """
    Attach CRUD-style commands for the provided resource name.

    Parameters
    ----------
    root:
        The root CLI group to which the resource commands should be attached.
    resource:
        The resource name driving the command hierarchy.
    """
    group = click.Group(name=resource, help=f"{resource.title()} related operations.")

    for verb in ('create', 'update', 'delete', 'search', 'list'):
        group.command(name=verb)(_resource_action(resource, verb))

    root.add_command(group)


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    ud2 command line interface entry point.
    """

    ctx.ensure_object(dict)
    ctx.obj.setdefault('actions', _build_default_action_map())


def _register_resource_commands() -> None:
    from .product import register as register_product
    from .repository import register as register_repository
    from .version import register as register_version

    for register in (register_product, register_repository, register_version):
        register(cli)


_register_resource_commands()


def main() -> None:
    """
    Entrypoint for console_scripts.
    """

    cli(obj={})


# The end.
