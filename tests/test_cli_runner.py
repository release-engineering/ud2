import unittest
from unittest import mock

from click.testing import CliRunner

from ud2.cli import main as cli_main
from ud2.cli.util import CLIState
from ud2.client import UDClient
from ud2.config import UDConfig


class TestCliRunnerSmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    @mock.patch("ud2.cli.build_cli_state")
    def test_products_list_invokes_client(self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(cli_main, ["product", "list"])
        print(result.output)

        self.assertEqual(result.exit_code, 0, result.output)
        client.iter_products.assert_called_once_with(sort=None)


# The end.
