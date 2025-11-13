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
Configuration helpers for ud2.
"""

import configparser
import pathlib
from dataclasses import dataclass
from typing import Optional


import logging
logger = logging.getLogger('UDConfig')


class ConfigurationError(Exception):
    """
    Raised when configuration parsing fails.
    """


@dataclass(frozen=True)
class UDConfig:
    """
    Application configuration.
    """

    name: str
    base_url: str
    client_cert: pathlib.Path
    client_key: pathlib.Path
    ca_cert: Optional[pathlib.Path] = None
    timeout: Optional[float] = None
    verify: bool = True


def load_config(path: pathlib.Path, environment: str) -> UDConfig:
    """
    Read user configuration and produce a UDConfig instance.

    :param path: Location of the configuration file to load.
    :param environment: Name of the environment profile to select (e.g. 'dev', 'prod').

    :returns: Loaded configuration for the requested environment.
    """
    parser = configparser.ConfigParser()

    if not parser.read(path):
        raise ConfigurationError(f"Configuration file not found or unreadable: {path}")

    if environment not in parser:
        raise ConfigurationError(f"Environment '{environment}' not found in {path}")

    section = parser[environment]

    base_url: Optional[str] = section.get('base_url')
    client_cert: Optional[str] = section.get('client_cert')
    client_key: Optional[str] = section.get('client_key')

    if not base_url or not client_cert or not client_key:
        raise ConfigurationError("Fields 'base_url', 'client_cert', and 'client_key' must be defined.")

    timeout = section.get('timeout', None)
    if isinstance(timeout, str):
        try:
            timeout = float(timeout)
        except ValueError:
            logger.warning(f"Invalid timeout value: {timeout}")
            timeout = None

    verify = section.get('verify', True)
    if isinstance(verify, str):
        lowered = verify.lower()
        verify = lowered in ('true', '1', 'yes')

    ca_cert_value = section.get('ca_cert')
    ca_cert: Optional[pathlib.Path]
    if ca_cert_value:
        ca_cert = pathlib.Path(ca_cert_value).expanduser().resolve()
    else:
        ca_cert = None

    return UDConfig(
        name=environment,
        base_url=base_url,
        client_cert=pathlib.Path(client_cert).expanduser().resolve(),
        client_key=pathlib.Path(client_key).expanduser().resolve(),
        timeout=timeout,
        verify=verify,
        ca_cert=ca_cert,
    )


# The end.
