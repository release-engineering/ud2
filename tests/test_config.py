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
Unit tests for configuration helpers.
"""

import pathlib
import tempfile
import unittest

from ud2.config import ConfigurationError, UDConfig


class TestLoadConfig(unittest.TestCase):
    """
    Validate configuration parsing behaviour.
    """

    def test_load_config_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir, "ud2.ini")
            cert_path = pathlib.Path(tmpdir, "certs", "prod.pem")
            key_path = pathlib.Path(tmpdir, "certs", "prod-key.pem")
            cert_path.parent.mkdir(parents=True, exist_ok=True)
            cert_path.touch()
            key_path.touch()
            config_path.write_text(
                "\n".join(
                    [
                        "[prod]",
                        "base_url = https://downloads.example.com/api",
                        f"client_cert = {cert_path}",
                        f"client_key = {key_path}",
                        "timeout = 3.5",
                        "verify = true",
                    ],
                ),
                encoding="utf-8",
            )

            loaded = UDConfig.from_file(config_path, "prod")

            self.assertIsInstance(loaded, UDConfig)
            self.assertEqual(loaded.name, "prod")
            self.assertEqual(loaded.base_url, "https://downloads.example.com/api")
            expected_cert = cert_path.resolve()
            expected_key = key_path.resolve()
            self.assertEqual(loaded.client_cert, expected_cert)
            self.assertEqual(loaded.client_key, expected_key)
            self.assertEqual(loaded.timeout, 3.5)
            self.assertTrue(loaded.verify)
            self.assertIsNone(loaded.ca_cert)

    def test_missing_file_raises_configuration_error(self) -> None:
        missing_path = pathlib.Path("/tmp/nonexistent-config.ini")

        with self.assertRaises(ConfigurationError) as caught:
            UDConfig.from_file(missing_path, "prod")

        message = str(caught.exception)
        self.assertIn("Configuration file not found", message)

    def test_missing_environment_raises_configuration_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            config_path = pathlib.Path(handle.name)
            cert_path = config_path.with_name("cert.pem")
            key_path = config_path.with_name("key.pem")
            handle.write(
                "[default]\n"
                "base_url = https://example.test\n"
                f"client_cert = {cert_path}\n"
                f"client_key = {key_path}\n",
            )
            handle.flush()

            with self.assertRaises(ConfigurationError) as caught:
                UDConfig.from_file(config_path, "prod")

        self.assertIn("Environment 'prod' not found", str(caught.exception))

    def test_missing_required_keys_raises_configuration_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            config_path = pathlib.Path(handle.name)
            handle.write(
                "[prod]\n"
                "base_url = https://example.test\n"
            )
            handle.flush()

            with self.assertRaises(ConfigurationError) as caught:
                UDConfig.from_file(config_path, "prod")

        self.assertIn("must be defined", str(caught.exception))

    def test_invalid_timeout_raises_value_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            config_path = pathlib.Path(handle.name)
            cert_path = config_path.with_name("cert.pem")
            key_path = config_path.with_name("key.pem")
            handle.write(
                "[prod]\n"
                "base_url = https://example.test\n"
                f"client_cert = {cert_path}\n"
                f"client_key = {key_path}\n"
                "timeout = not-a-number\n",
            )
            handle.flush()

            with self.assertRaises(ValueError):
                UDConfig.from_file(config_path, "prod")

    def test_verify_string_false_interpreted_as_false(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            config_path = pathlib.Path(handle.name)
            cert_path = config_path.with_name("cert.pem")
            key_path = config_path.with_name("key.pem")
            handle.write(
                "[prod]\n"
                "base_url = https://example.test\n"
                f"client_cert = {cert_path}\n"
                f"client_key = {key_path}\n"
                "verify = false\n",
            )
            handle.flush()

            loaded = UDConfig.from_file(config_path, "prod")

        self.assertFalse(loaded.verify)

    def test_ca_cert_path_resolves_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir, "ud2.ini")
            cert_path = pathlib.Path(tmpdir, "cert.pem")
            key_path = pathlib.Path(tmpdir, "key.pem")
            ca_path = pathlib.Path(tmpdir, "ca.pem")
            cert_path.touch()
            key_path.touch()
            ca_path.touch()
            config_path.write_text(
                "\n".join(
                    [
                        "[prod]",
                        "base_url = https://downloads.example.com/api",
                        f"client_cert = {cert_path}",
                        f"client_key = {key_path}",
                        f"ca_cert = {ca_path}",
                    ],
                ),
                encoding="utf-8",
            )

            loaded = UDConfig.from_file(config_path, "prod")

            self.assertEqual(loaded.ca_cert, ca_path.resolve())


# The end.
