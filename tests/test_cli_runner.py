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


# The end.
