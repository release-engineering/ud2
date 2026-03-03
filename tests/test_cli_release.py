"""
CLI tests for release check and push commands.
"""

import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from ud2.cli import main as cli_main
from ud2.cli.util import CLIState
from ud2.client import UDClient
from ud2.config import UDConfig


class TestReleaseCheckCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.releasefile = Path(__file__).parent / 'fixtures' / 'release_example.yaml'

    @mock.patch('ud2.cli.release.check_release')
    @mock.patch('ud2.cli.build_cli_state')
    def test_check_invokes_check_release(self, build_state, check_release):
        from ud2.models import Release

        client = mock.Mock(spec=UDClient)
        check_release.return_value = {
            'product': {'status': 'not_found', 'product': None},
            'version': {'status': 'unknown', 'version': None},
            'repos': [],
            'errors': ['Product not found'],
            'in_sync': False,
        }

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['release', 'check', str(self.releasefile)],
        )

        self.assertEqual(result.exit_code, 1)
        check_release.assert_called_once()
        call_args = check_release.call_args
        self.assertIsInstance(call_args[0][1], Release)


class TestReleasePushCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.releasefile = Path(__file__).parent / 'fixtures' / 'release_example.yaml'

    @mock.patch('ud2.cli.release.apply_release')
    @mock.patch('ud2.cli.build_cli_state')
    def test_push_upload_raises_error(self, build_state, apply_release):
        from ud2.release import ReleaseError

        client = mock.Mock(spec=UDClient)
        apply_release.side_effect = ReleaseError(
            'Upload support not yet implemented.',
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['release', 'push', str(self.releasefile), '--upload'],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('not yet implemented', result.output)


# The end.
