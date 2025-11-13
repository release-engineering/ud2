import unittest

from click.testing import CliRunner

from ud2.cli import cli


class TestCliStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_help_lists_resources(self) -> None:
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for resource in ("product", "version", "repository"):
            self.assertIn(resource, result.output)

    def test_subcommand_invocation_returns_stub(self) -> None:
        result = self.runner.invoke(cli, ["product", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("[stub] product:list", result.output)


if __name__ == "__main__":
    unittest.main()
