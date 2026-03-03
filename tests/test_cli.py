
import unittest

from ud2.cli import main as cli_main


class TestCliRegistration(unittest.TestCase):
    def test_product_group_registered(self) -> None:
        commands = cli_main.list_commands(None)
        self.assertIn("product", commands)
        product_cmd = cli_main.get_command(None, "product")
        subcommands = product_cmd.list_commands(None)
        for expected in ("list", "get", "create", "update", "delete"):
            self.assertIn(expected, subcommands)

    def test_repository_group_registered(self) -> None:
        commands = cli_main.list_commands(None)
        self.assertIn("repository", commands)
        repository_cmd = cli_main.get_command(None, "repository")
        subcommands = repository_cmd.list_commands(None)
        for expected in ("list", "get", "create", "update", "delete"):
            self.assertIn(expected, subcommands)

    def test_version_group_registered(self) -> None:
        commands = cli_main.list_commands(None)
        self.assertIn("version", commands)
        version_cmd = cli_main.get_command(None, "version")
        subcommands = version_cmd.list_commands(None)
        for expected in ("list", "get", "create", "update", "delete"):
            self.assertIn(expected, subcommands)

    def test_release_group_registered(self) -> None:
        commands = cli_main.list_commands(None)
        self.assertIn("release", commands)
        release_cmd = cli_main.get_command(None, "release")
        subcommands = release_cmd.list_commands(None)
        for expected in ("check", "push"):
            self.assertIn(expected, subcommands)


# The end.
