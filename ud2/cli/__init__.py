"""
UDv2 Command Line Interface package.

:author: Christopher O'Brien <cobrien@redhat.com>
:license: GPLv3
"""

import os
import logging
import pathlib

from click import Context, Group, Path, option, group, pass_context
from .util import build_cli_state


DEFAULT_CONFIG_PATH = pathlib.Path("~/.config/ud2/config.ini")


class MagicGroup(Group):
    def _load_commands(self):
        # delaying to avoid circular imports
        from . import product     # noqa: F401
        from . import repository  # noqa: F401
        from . import version     # noqa: F401

    def get_command(self, ctx, cmd_name):
        self._load_commands()
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        self._load_commands()
        return super().list_commands(ctx)


@group(cls=MagicGroup)
@option("--config", "config_path", type=Path(dir_okay=False),
        help="Path to the ud2 configuration file.")
@option("--env", "environment", default="default",
        help="Environment profile to load from the configuration file.")
@option("--yaml", "yaml_output", is_flag=True, default=False,
        help="Render results as YAML instead of friendly text.")
@option("--debug", is_flag=True, default=False,
        help="Enable verbose logging.")
@pass_context
def main(
        ctx: Context,
        config_path: str,
        environment: str,
        yaml_output: bool,
        debug: bool) -> None:
    """
    ud2 command line interface entry point.
    """

    log_level = os.environ.get('LOGLEVEL', '').strip().upper()
    if log_level:
        logging.basicConfig(level=log_level)

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    ctx.obj = build_cli_state(config_path, environment, yaml_output, debug)


# The end.
