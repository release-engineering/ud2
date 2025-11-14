"""
UDv2 Command Line Interface package.

:author: Christopher O'Brien <cobrien@redhat.com>
:license: GPLv3
"""

import os
import logging
import pathlib
from typing import Optional

from click import Context, Path, option, group, pass_context
from .util import build_cli_state

from .product import product
from .repository import repository
from .version import version


__all__ = (
    "DEFAULT_CONFIG_PATH",
    "main",
)


DEFAULT_CONFIG_PATH = pathlib.Path("~/.config/ud2/config.ini").expanduser()


@group()
@option("--config", "config_path", type=Path(dir_okay=False),
        help="Path to the ud2 configuration file.")
@option("--env", "environment", default="default",
        help="Environment profile to load from the configuration file.")
@option("--yaml", "yaml_output", is_flag=True, default=False,
        help="Render results as YAML")
@option("--debug", is_flag=True, default=False,
        help="Enable verbose logging.")
@pass_context
def main(
        ctx: Context,
        config_path: Optional[str] = None,
        environment: Optional[str] = None,
        yaml_output: bool = False,
        debug: bool = False) -> None:
    """
    ud2 command line interface entry point.
    """

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        log_level = os.environ.get('LOGLEVEL', '').strip().upper()
        if log_level:
            logging.basicConfig(level=log_level)

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    ctx.obj = build_cli_state(config_path, environment, yaml_output, debug)


main.add_command(product)
main.add_command(repository)
main.add_command(version)


# The end.
