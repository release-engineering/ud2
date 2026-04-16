"""
CLI tests for release check and push commands.
"""

import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from ud2.cli import main as cli_main
from ud2.cli.release import resolve_release_path
from ud2.cli.util import CLIState
from ud2.client import UDClient
from ud2.config import UDConfig

from tests import make_product, make_repository


def _make_state():
    return CLIState(
        config=mock.Mock(spec=UDConfig),
        client=mock.Mock(spec=UDClient),
        yaml_output=False,
        debug=False,
    )


class TestReleaseInitCli(unittest.TestCase):
    @mock.patch('ud2.cli.build_cli_state')
    def test_init_creates_manifest_with_product_id(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'release.yaml', '--product-id', '123',
                 '--version', '1.0.0'],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Created', result.output)
            self.assertTrue(Path('release.yaml').exists())
            content = Path('release.yaml').read_text()
            self.assertIn('id: 123', content)
            self.assertIn('version: 1.0.0', content)
            self.assertIn('repositories: []', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_resolves_product_eng_id_via_api(self, build_state):
        state = _make_state()
        state.client.list_products.return_value = [
            make_product(id=42, eng_id=4001, name='Atlas'),
        ]
        build_state.return_value = state
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-eng-id', '4001',
                 '--version', '1.0',
                 '--architecture', 'x86_64', '--platform', 'linux'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('id: 42', content)
            self.assertIn('architecture: x86_64', content)
            self.assertIn('platform: linux', content)
            state.client.list_products.assert_called_once()

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_resolves_product_name_via_api(self, build_state):
        state = _make_state()
        state.client.list_products.return_value = [
            make_product(id=7, eng_id=100, name='Atlas'),
        ]
        build_state.return_value = state
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-name', 'atlas',
                 '--version', '1.0'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('id: 7', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_resolves_product_code_via_api(self, build_state):
        state = _make_state()
        state.client.list_products.return_value = [
            make_product(id=3, eng_id=200, name='X', product_code='DEMO'),
        ]
        build_state.return_value = state
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-code', 'demo',
                 '--version', '1.0'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('id: 3', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_eng_id_ambiguous_warns_and_picks_largest_id(self, build_state):
        state = _make_state()
        state.client.list_products.return_value = [
            make_product(id=5, eng_id=4001, name='A'),
            make_product(id=10, eng_id=4001, name='B'),
        ]
        build_state.return_value = state
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-eng-id', '4001',
                 '--version', '1.0'],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Warning:', result.stderr)
            self.assertIn('10', Path('r.yaml').read_text())

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_no_match_eng_id(self, build_state):
        state = _make_state()
        state.client.list_products.return_value = [
            make_product(id=1, eng_id=99, name='Other'),
        ]
        build_state.return_value = state
        runner = CliRunner()
        result = runner.invoke(
            cli_main,
            ['release', 'init', 'r.yaml', '--product-eng-id', '4001',
             '--version', '1.0'],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('engineering ID', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_rejects_multiple_product_specifiers(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        result = runner.invoke(
            cli_main,
            ['release', 'init', 'r.yaml', '--product-id', '1',
             '--product-name', 'Atlas', '--version', '1.0'],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('exactly one', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_fails_if_file_exists_without_force(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('existing.yaml').write_text('product:\n  id: 1\n')
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'existing.yaml', '--product-id', '1',
                 '--version', '1.0'],
            )
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn('exists', result.output)
            self.assertIn('--force', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_force_overwrites(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('r.yaml').write_text('product:\n  id: 1\n')
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-id', '999',
                 '--version', '2.0', '--force'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('id: 999', content)
            self.assertIn('2.0', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_requires_product_spec(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        result = runner.invoke(
            cli_main,
            ['release', 'init', 'r.yaml', '--version', '1.0'],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('exactly one', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_sets_dirname_when_releasefile_is_directory(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('Product-1.0').mkdir()
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'Product-1.0', '--product-id', '123',
                 '--version', '1.0.0'],
            )
            self.assertEqual(result.exit_code, 0)
            content = (Path('Product-1.0') / 'ud-release.yml').read_text()
            self.assertIn('dirname: Product-1.0', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_dirname_override(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'release.yaml', '--product-id', '123',
                 '--version', '1.0.0', '--dirname', 'my-prefix'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('release.yaml').read_text()
            self.assertIn('dirname: my-prefix', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_init_flat_manifest_has_no_dirname_in_output(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli_main,
                ['release', 'init', 'release.yaml', '--product-id', '123',
                 '--version', '1.0.0'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('release.yaml').read_text()
            self.assertNotIn('dirname:', content)


class TestReleaseAddCli(unittest.TestCase):
    @mock.patch('ud2.cli.build_cli_state')
    def test_add_with_file_computes_checksums(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('artifact.bin').write_bytes(b'hello')
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--file', 'artifact.bin',
                 '--desc', 'Test artifact'],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Added', result.output)
            content = Path('r.yaml').read_text()
            self.assertIn('description: Test artifact', content)
            self.assertIn('fileName: artifact.bin', content)
            self.assertIn('fileSize: 5', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_with_explicit_metadata(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            sha = '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
            md5 = '5d41402abc4b2a76b9719d911017c592'
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--desc', 'Manual entry',
                 '--file-name', 'm.bin', '--file-size', '5',
                 '--sha256', sha, '--md5', md5],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('description: Manual entry', content)
            self.assertIn('fileName: m.bin', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_requires_desc_with_file(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--file', 'a.bin'],
            )
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn('--desc', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_joins_dirname_and_basename(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-id', '1',
                 '--version', '1.0', '--dirname', 'Prod'],
            )
            Path('artifact.bin').write_bytes(b'hello')
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--file', 'artifact.bin',
                 '--desc', 'Test artifact'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('fileName: Prod/artifact.bin', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_explicit_file_name_skips_dirname_join(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-id', '1',
                 '--version', '1.0', '--dirname', 'Prod'],
            )
            Path('artifact.bin').write_bytes(b'hello')
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--file', 'artifact.bin',
                 '--file-name', 'other.bin', '--desc', 'Test artifact'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('fileName: other.bin', content)
            self.assertNotIn('Prod/', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_uses_as_given_file_path_when_no_dirname(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli_main,
                ['release', 'init', 'r.yaml', '--product-id', '1',
                 '--version', '1.0'],
            )
            Path('nested').mkdir()
            Path('nested/foo.bin').write_bytes(b'x')
            result = runner.invoke(
                cli_main,
                ['release', 'add', 'r.yaml', '--file', 'nested/foo.bin',
                 '--desc', 'Nested'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('fileName: nested/foo.bin', content)


class TestReleaseEditCli(unittest.TestCase):
    @mock.patch('ud2.cli.build_cli_state')
    def test_edit_by_file_name(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'Original'])
            result = runner.invoke(
                cli_main,
                ['release', 'edit', 'r.yaml', '--file-name', 'a.bin',
                 '--desc', 'Updated'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('description: Updated', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_edit_by_index(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'First'])
            result = runner.invoke(
                cli_main,
                ['release', 'edit', 'r.yaml', '--by-index', '0',
                 '--desc', 'Edited'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('description: Edited', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_edit_dry_run_skips_write(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'Original'])
            result = runner.invoke(
                cli_main,
                ['release', 'edit', 'r.yaml', '--file-name', 'a.bin',
                 '--desc', 'Would change', '--dry-run'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('description: Original', content)
            self.assertNotIn('Would change', content)


class TestReleaseRemoveCli(unittest.TestCase):
    @mock.patch('ud2.cli.build_cli_state')
    def test_remove_by_file_name(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'To remove'])
            result = runner.invoke(
                cli_main,
                ['release', 'remove', 'r.yaml', '--file-name', 'a.bin'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('repositories: []', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_remove_by_index(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'To remove'])
            result = runner.invoke(
                cli_main,
                ['release', 'remove', 'r.yaml', '--by-index', '0'],
            )
            self.assertEqual(result.exit_code, 0)
            content = Path('r.yaml').read_text()
            self.assertIn('repositories: []', content)

    @mock.patch('ud2.cli.build_cli_state')
    def test_remove_dry_run_skips_write(self, build_state):
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli_main, ['release', 'init', 'r.yaml',
                        '--product-id', '1', '--version', '1.0'])
            Path('a.bin').write_bytes(b'x')
            runner.invoke(cli_main, ['release', 'add', 'r.yaml',
                        '--file', 'a.bin', '--desc', 'To remove'])
            result = runner.invoke(
                cli_main,
                ['release', 'remove', 'r.yaml', '--file-name', 'a.bin',
                 '--dry-run'],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Would remove', result.output)
            content = Path('r.yaml').read_text()
            self.assertIn('To remove', content)


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

    @mock.patch('ud2.cli.release.apply_release')
    @mock.patch('ud2.cli.build_cli_state')
    def test_push_plain_output_lists_created_and_updated_repository_ids(
            self, build_state, apply_release):
        from ud2.models import Product, Version

        client = mock.Mock(spec=UDClient)
        apply_release.return_value = {
            'product': Product(id=1, eng_id=100, name='Test Product'),
            'version': Version(id=2, productId=1, version='1.0'),
            'created': [
                make_repository(id=10, description='New artifact'),
            ],
            'updated': [
                make_repository(id=20, description='Updated artifact'),
            ],
        }

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['release', 'push', str(self.releasefile)],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        apply_release.assert_called_once()
        self.assertIn('Created repositories:', result.output)
        self.assertIn('[ID: 10] New artifact', result.output)
        self.assertIn('Updated repositories:', result.output)
        self.assertIn('[ID: 20] Updated artifact', result.output)


class TestResolveReleasePath(unittest.TestCase):
    """Unit tests for resolve_release_path helper."""

    def test_file_path_unchanged(self):
        """File path is returned as-is."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('release.yaml').write_text('product: {}\nversion: {}\n')
            resolved = resolve_release_path(Path('release.yaml'))
            self.assertEqual(resolved, Path('release.yaml'))

    def test_directory_resolves_to_ud_release_yml(self):
        """Directory resolves to dir/ud-release.yml when present."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('myproduct').mkdir()
            (Path('myproduct') / 'ud-release.yml').write_text(
                'product: {}\nversion: {}\nrepositories: []\n',
            )
            resolved = resolve_release_path(Path('myproduct'))
            self.assertEqual(
                resolved,
                Path('myproduct') / 'ud-release.yml',
            )

    def test_directory_without_ud_release_yml_raises(self):
        """Directory without ud-release.yml raises ClickException."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('emptydir').mkdir()
            with self.assertRaises(Exception) as ctx:
                resolve_release_path(Path('emptydir'))
            self.assertIn('ud-release.yml', str(ctx.exception))


class TestReleaseDirectoryLookup(unittest.TestCase):
    """CLI tests for directory-based release manifest lookup."""

    @mock.patch('ud2.cli.release.check_release')
    @mock.patch('ud2.cli.build_cli_state')
    def test_check_with_directory_succeeds(self, build_state, check_release):
        """Check accepts directory path, resolves to dir/ud-release.yml."""
        build_state.return_value = _make_state()
        check_release.return_value = {
            'product': {'status': 'found', 'product': mock.Mock()},
            'version': {'status': 'found', 'version': mock.Mock()},
            'repos': [],
            'errors': [],
            'in_sync': True,
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            mydir = Path('mydir').resolve()
            mydir.mkdir()
            (mydir / 'ud-release.yml').write_text(
                'product:\n  id: 1\nversion:\n  version: "1.0"\nrepositories: []\n',
            )
            result = runner.invoke(
                cli_main,
                ['release', 'check', str(mydir)],
            )
            self.assertEqual(result.exit_code, 0)
            check_release.assert_called_once()

    @mock.patch('ud2.cli.build_cli_state')
    def test_check_directory_without_ud_release_yml_fails(self, build_state):
        """Check with directory lacking ud-release.yml fails."""
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path('nodir').mkdir()
            result = runner.invoke(
                cli_main,
                ['release', 'check', 'nodir'],
            )
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn('ud-release.yml', result.output)

    @mock.patch('ud2.cli.build_cli_state')
    def test_add_with_directory_path(self, build_state):
        """Add accepts directory path, resolves to dir/ud-release.yml."""
        build_state.return_value = _make_state()
        runner = CliRunner()
        with runner.isolated_filesystem():
            projdir = Path('projdir').resolve()
            projdir.mkdir()
            (projdir / 'ud-release.yml').write_text(
                'product:\n  id: 1\nversion:\n  version: "1.0"\nrepositories: []\n',
            )
            (projdir / 'artifact.bin').write_bytes(b'hello')
            result = runner.invoke(
                cli_main,
                ['release', 'add', str(projdir), '--file', 'projdir/artifact.bin',
                 '--desc', 'Test artifact'],
            )
            self.assertEqual(result.exit_code, 0)
            content = (projdir / 'ud-release.yml').read_text()
            self.assertIn('description: Test artifact', content)
            self.assertIn('fileName: projdir/artifact.bin', content)


# The end.
