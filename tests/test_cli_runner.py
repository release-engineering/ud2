import tempfile
import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from ud2.cli import main as cli_main
from ud2.cli.util import CLIState
from ud2.client import UDClient
from ud2.config import UDConfig
from ud2.models import Product, Repository, Version


class TestCliRunnerSmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    @mock.patch("ud2.cli.build_cli_state")
    def test_products_list_invokes_client(self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_products.return_value = ()

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(cli_main, ["product", "list"])

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_products.assert_called_once_with(sort=None)

    @mock.patch("ud2.cli.build_cli_state")
    def test_product_create_with_inline_options_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.create_product.return_value = Product(
            id=1, eng_id=101, name="Test Product",
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["product", "create", "--name", "Test Product", "--eng-id", "101"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.create_product.assert_called_once()
        payload = client.create_product.call_args[0][0]
        self.assertEqual(payload.name, "Test Product")
        self.assertEqual(payload.eng_id, 101)

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_create_with_inline_options_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.create_product_version.return_value = Version(
            id=1, productId=5, version="1.0",
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "create", "5", "--version", "1.0"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.create_product_version.assert_called_once()
        payload = client.create_product_version.call_args[0][1]
        self.assertEqual(payload.version, "1.0")

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_list_numeric_product_id_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_product_versions.return_value = []

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "list", "42"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_product_versions.assert_called_once_with(42)
        client.list_products.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_list_product_code_resolves_via_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_products.return_value = [
            Product(id=7, eng_id=100, name="Widget", product_code="DEMO"),
        ]
        client.list_product_versions.return_value = []

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "list", "demo"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_products.assert_called_once_with()
        client.list_product_versions.assert_called_once_with(7)

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_list_not_found_polite_message(
            self, build_state: mock.MagicMock) -> None:
        import requests

        client = mock.Mock(spec=UDClient)
        err = requests.HTTPError()
        err.response = mock.Mock(status_code=404, text='')
        client.list_product_versions.side_effect = err

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "list", "99"],
        )

        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn('No product was found', result.output)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_list_numeric_version_id_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_repositories.return_value = [
            Repository(
                id=8,
                description='Sample',
                fileName='sample.bin',
                fileSize=100,
                sha256='b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9',
                md5='5eb63bbbe01eeed093cb22bb8f5acdc3',
                issues=[],
                visibility='hidden',
                classifier=[],
            ),
        ]

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['repository', 'list', '42'],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_repositories.assert_called_once_with(
            product_version_id=42,
            sort=None,
        )
        self.assertIn('Sample', result.output)
        self.assertRegex(result.output, r'\bH\b')

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_list_product_code_and_version_resolves_version_id(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_products.return_value = [
            Product(id=7, eng_id=100, name='Widget', product_code='data.grid'),
        ]
        client.list_product_versions.return_value = [
            Version(id=12345, productId=7, version='1.2.3'),
        ]
        client.list_repositories.return_value = []

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['repository', 'list', 'data.grid', '1.2.3'],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_products.assert_called_once_with()
        client.list_product_versions.assert_called_once_with(7)
        client.list_repositories.assert_called_once_with(
            product_version_id=12345,
            sort=None,
        )

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_list_product_code_version_not_found(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_products.return_value = [
            Product(id=7, eng_id=100, name='Widget', product_code='data.grid'),
        ]
        client.list_product_versions.return_value = [
            Version(id=999, productId=7, version='9.9.9'),
        ]

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ['repository', 'list', 'data.grid', '1.2.3'],
        )

        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn("No version '1.2.3' found for product 'data.grid'.", result.output)
        client.list_repositories.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_create_with_file_artifact_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.create_repository.return_value = Repository(
            id=1,
            description="Test",
            fileName="test.bin",
            fileSize=11,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )
        client.get_product_version.return_value = Version(
            id=1,
            productId=5,
            version="1.0",
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"hello world")
            path = Path(f.name)

        try:
            result = self.runner.invoke(
                cli_main,
                [
                    "repository",
                    "create",
                    "1",
                    "--file",
                    str(path),
                    "--desc",
                    "Test artifact",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            client.create_repository.assert_called_once()
            payload = client.create_repository.call_args[0][1]
            self.assertEqual(payload.description, "Test artifact")
            self.assertEqual(payload.file_name, path.name)
            self.assertEqual(payload.file_size, 11)
            self.assertEqual(
                payload.sha256,
                "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            )
            self.assertIn("Product ID: 5", result.output)
            self.assertIn("Version ID: 1", result.output)
        finally:
            path.unlink(missing_ok=True)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_create_requires_file_or_yaml(self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["repository", "create", "1", "--desc", "Test"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--file", result.output)
        client.create_repository.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_create_with_long_desc_file_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.create_repository.return_value = Repository(
            id=1,
            description="Test",
            fileName="test.bin",
            fileSize=11,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as artifact_f:
            artifact_f.write(b"hello world")
            artifact_path = Path(artifact_f.name)
        with tempfile.NamedTemporaryFile(
                delete=False, suffix=".html", mode='w', encoding='utf-8') as desc_f:
            desc_f.write("<p>Release notes HTML content</p>")
            desc_path = Path(desc_f.name)

        try:
            result = self.runner.invoke(
                cli_main,
                [
                    "repository",
                    "create",
                    "1",
                    "--file",
                    str(artifact_path),
                    "--desc",
                    "Test artifact",
                    "--long-desc-file",
                    str(desc_path),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            client.create_repository.assert_called_once()
            payload = client.create_repository.call_args[0][1]
            self.assertEqual(
                payload.long_description,
                "<p>Release notes HTML content</p>",
            )
        finally:
            artifact_path.unlink(missing_ok=True)
            desc_path.unlink(missing_ok=True)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_update_with_long_desc_file_invokes_client(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_repository.return_value = Repository(
            id=1,
            description="Existing",
            fileName="old.bin",
            fileSize=10,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )
        client.update_repository.return_value = Repository(
            id=1,
            description="Existing",
            fileName="old.bin",
            fileSize=10,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        with tempfile.NamedTemporaryFile(
                delete=False, suffix=".html", mode='w', encoding='utf-8') as desc_f:
            desc_f.write("<div>Updated long description from file</div>")
            desc_path = Path(desc_f.name)

        try:
            result = self.runner.invoke(
                cli_main,
                [
                    "repository",
                    "update",
                    "1",
                    "--long-desc-file",
                    str(desc_path),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            client.get_repository.assert_called_once_with(1)
            client.update_repository.assert_called_once()
            payload = client.update_repository.call_args[0][1]
            self.assertEqual(
                payload.long_description,
                "<div>Updated long description from file</div>",
            )
        finally:
            desc_path.unlink(missing_ok=True)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_create_long_desc_file_takes_precedence_over_inline(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.create_repository.return_value = Repository(
            id=1,
            description="Test",
            fileName="test.bin",
            fileSize=11,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )

        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as artifact_f:
            artifact_f.write(b"hello world")
            artifact_path = Path(artifact_f.name)
        with tempfile.NamedTemporaryFile(
                delete=False, suffix=".html", mode='w', encoding='utf-8') as desc_f:
            desc_f.write("From file")
            desc_path = Path(desc_f.name)

        try:
            result = self.runner.invoke(
                cli_main,
                [
                    "repository",
                    "create",
                    "1",
                    "--file",
                    str(artifact_path),
                    "--desc",
                    "Test",
                    "--long-desc",
                    "Inline text",
                    "--long-desc-file",
                    str(desc_path),
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            payload = client.create_repository.call_args[0][1]
            self.assertEqual(payload.long_description, "From file")
        finally:
            artifact_path.unlink(missing_ok=True)
            desc_path.unlink(missing_ok=True)

    @mock.patch("ud2.cli.build_cli_state")
    def test_product_create_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["product", "create", "--name", "Dry Run Product", "--eng-id", "99",
             "--dry-run"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("eng_id: 99", result.output)
        self.assertIn("name: Dry Run Product", result.output)
        client.create_product.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_product_update_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product.return_value = Product(
            id=1, eng_id=100, name="Existing",
        )
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["product", "update", "1", "--name", "Updated Name", "--dry-run"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("name: Updated Name", result.output)
        client.get_product.assert_called_once_with(1)
        client.update_product.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_create_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "create", "1", "--version", "2.0", "--dry-run"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("version:", result.output)
        self.assertIn("2.0", result.output)
        client.create_product_version.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_update_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product_version.return_value = Version(
            id=1, product_id=1, version="1.0",
        )
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "update", "1", "--version", "2.0", "--dry-run"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("version:", result.output)
        self.assertIn("2.0", result.output)
        client.get_product_version.assert_called_once_with(1)
        client.update_product_version.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_create_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"hello world")
            path = Path(f.name)

        try:
            result = self.runner.invoke(
                cli_main,
                [
                    "repository",
                    "create",
                    "1",
                    "--file",
                    str(path),
                    "--desc",
                    "Dry run artifact",
                    "--dry-run",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("description: Dry run artifact", result.output)
            self.assertIn("file_name:", result.output)
            self.assertIn("file_size: 11", result.output)
            client.create_repository.assert_not_called()
        finally:
            path.unlink(missing_ok=True)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_update_dry_run_prints_yaml_skips_api(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_repository.return_value = Repository(
            id=1,
            description="Existing",
            fileName="old.bin",
            fileSize=10,
            sha256="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
        )
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["repository", "update", "1", "--desc", "Updated desc", "--dry-run"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("description: Updated desc", result.output)
        client.get_repository.assert_called_once_with(1)
        client.update_repository.assert_not_called()

    @staticmethod
    def _sample_repository(rid: int = 5) -> Repository:
        return Repository(
            id=rid,
            description="Sample",
            fileName="sample.bin",
            fileSize=100,
            sha256=(
                "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
            ),
            md5="5eb63bbbe01eeed093cb22bb8f5acdc3",
            issues=[],
            visibility="visible",
            classifier=[],
            productVersionId=2,
        )

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_delete_force_skips_confirm(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_repository.return_value = self._sample_repository()
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["repository", "delete", "5", "--force"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.get_repository.assert_called_once_with(5)
        client.delete_repository.assert_called_once_with(5)

    @mock.patch("ud2.cli.build_cli_state")
    def test_repository_delete_confirm_y_invokes_delete(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_repository.return_value = self._sample_repository()
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["repository", "delete", "5"],
            input="y\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.get_repository.assert_called_once_with(5)
        client.delete_repository.assert_called_once_with(5)

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_delete_blocked_when_repositories_exist(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product_version.return_value = Version(
            id=3, productId=1, version="1.0",
        )
        client.list_repositories.return_value = [self._sample_repository()]
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "delete", "3", "--force"],
        )

        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn("repository file(s) still associated", result.output)
        client.delete_product_version.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_version_delete_force_deletes_when_no_repositories(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product_version.return_value = Version(
            id=3, productId=1, version="1.0",
        )
        client.list_repositories.return_value = []
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["version", "delete", "3", "--force"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.get_product_version.assert_called_once_with(3)
        client.list_repositories.assert_called_once_with(3)
        client.delete_product_version.assert_called_once_with(3)

    @mock.patch("ud2.cli.build_cli_state")
    def test_product_delete_blocked_when_versions_exist(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product.return_value = Product(
            id=10, eng_id=200, name="Widget",
        )
        client.list_product_versions.return_value = [
            Version(id=1, productId=10, version="1.0"),
        ]
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["product", "delete", "10", "--force"],
        )

        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn("version(s) still exist", result.output)
        client.delete_product.assert_not_called()

    @mock.patch("ud2.cli.build_cli_state")
    def test_product_delete_force_deletes_when_no_versions(
            self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.get_product.return_value = Product(
            id=10, eng_id=200, name="Widget",
        )
        client.list_product_versions.return_value = []
        build_state.return_value = CLIState(
            config=mock.Mock(spec=UDConfig),
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(
            cli_main,
            ["product", "delete", "10", "--force"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        client.get_product.assert_called_once_with(10)
        client.list_product_versions.assert_called_once_with(10)
        client.delete_product.assert_called_once_with(10)


# The end.
