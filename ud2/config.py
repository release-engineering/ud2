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

from configparser import ConfigParser
from pathlib import Path
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
    client_cert: Path
    client_key: Path
    ca_cert: Optional[Path] = None
    timeout: Optional[float] = None
    verify: bool = True


    @classmethod
    def from_file(cls, path: Path, environment: str = None) -> 'UDConfig':
        """
        Read user configuration and produce a UDConfig instance.

        :param path: Location of the configuration file to load.
        :param environment: Name of the environment profile to select (e.g. 'dev', 'prod').

        :returns: Loaded configuration for the requested environment.
        """

        parser = ConfigParser()

        logger.debug(f"Reading configuration file: {path}")
        if not parser.read(path):
            raise ConfigurationError(f"Configuration file not found or unreadable: {path}")

        return cls.from_config(parser, environment)


    @classmethod
    def from_config(cls, parser: ConfigParser, environment: str = None) -> 'UDConfig':
        """
        Load user configuration and produce a UDConfig instance.

        :param parser: ConfigParser instance to read from.
        :param environment: Name of the environment profile to select (e.g. 'dev', 'prod').

        :returns: Loaded configuration for the requested environment.
        """

        logger.debug(f"Requested environment: {environment!r}")
        if environment is None:
            defaults = parser.default_section
            environment = defaults.get('default_environment')
            logger.debug(f"Configuration specifies 'default': {environment!r}")

        if not environment:
            raise ConfigurationError("No environment specified and no default environment found in configuration file")

        if environment not in parser:
            raise ConfigurationError(f"Environment '{environment}' not found in configuration file")

        section = parser[environment]

        base_url: Optional[str] = section.get('base_url')
        client_cert: Optional[str] = section.get('client_cert')
        client_key: Optional[str] = section.get('client_key')

        if not base_url or not client_cert or not client_key:
            raise ConfigurationError("Fields 'base_url', 'client_cert', and 'client_key' must be defined.")

        timeout = section.getfloat('timeout', None)
        verify = section.getboolean('verify', True)
        ca_cert_value = section.get('ca_cert')
        ca_cert = Path(ca_cert_value).expanduser().resolve() if ca_cert_value else None

        return cls(
            name=environment,
            base_url=base_url,
            client_cert=Path(client_cert).expanduser().resolve(),
            client_key=Path(client_key).expanduser().resolve(),
            timeout=timeout,
            verify=verify,
            ca_cert=ca_cert,
        )


# The end.
