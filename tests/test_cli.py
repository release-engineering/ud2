""
"Unit tests for CLI helper utilities and command callbacks."
""


import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import click
from click.testing import CliRunner

from pydantic import ValidationError

from ud2.cli import CLIState, cli, emit, load_model, pass_state, with_error_handling
from ud2.cli.product import register as register_products
from ud2.cli.repository import register as register_repositories
from ud2.cli.version import register as register_versions
from ud2.client import UDClient
from ud2.models import ProductCreate

from . import (make_paginated_products, make_paginated_repositories,
               make_product)


class TestHelperFunctions(unittest.TestCase):
    def test_load_model_parses_payload(self) -> None:
        payload = "eng_id: 7\nname: \"Sample\"\n"

        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(payload)
            path = Path(handle.name)

        try:
            model = load_model(str(path), ProductCreate)
        finally:
            path.unlink(missing_ok=True)

        self.assertIsInstance(model, ProductCreate)
        self.assertEqual(model.eng_id, 7)
        self.assertEqual(model.name, "Sample")

    def test_load_model_raises_click_exception_on_validation_errors(self) -> None:
        payload = "name: \"Missing Fields\"\n"

        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(payload)
            path = Path(handle.name)

        try:
            with self.assertRaises(click.ClickException) as caught:
                load_model(str(path), ProductCreate)
        finally:
            path.unlink(missing_ok=True)

        message = str(caught.exception)
        self.assertIn("Validation failed", message)
        self.assertIn("eng_id", message)

    def test_load_model_reraises_validation_error_in_debug_mode(self) -> None:
        state = CLIState(
            client=mock.Mock(spec=UDClient),
            yaml_output=False,
            debug=True,
        )
        command = click.Command("dummy")
        context = click.Context(command, obj=state)

        with context:
            with mock.patch("ud2.cli.load_yaml_payload", return_value={"name": "Sample"}):
                with self.assertRaises(ValidationError):
                    load_model("ignored", ProductCreate)

    def test_load_model_reports_nested_validation_errors(self) -> None:
        payload: Dict[str, Any] = {"name": "Nested"}
        validation_error = ValidationError.from_exception_data(
            "ProductCreate",
            [
                {
                    "type": "model_type",
                    "loc": (),
                    "msg": "Input should be a valid dictionary or instance of ProductCreate",
                    "input": payload,
                    "ctx": {
                        "class_name": "ProductCreate",
                        "errors": [
                            {
                                "type": "missing",
                                "loc": ("eng_id",),
                                "msg": "Field required",
                            },
                        ],
                    },
                },
            ],
        )

        with mock.patch("ud2.cli.load_yaml_payload", return_value=payload):
            with mock.patch.object(ProductCreate, "model_validate", side_effect=validation_error):
                with self.assertRaises(click.ClickException) as caught:
                    load_model("ignored", ProductCreate)

        message = str(caught.exception)
        self.assertIn("eng_id: Field required", message)
        self.assertIn("<root>: Input should be a valid dictionary or instance of ProductCreate", message)

    def test_with_error_handling_reraises_when_debug_enabled(self) -> None:
        @click.command()
        @with_error_handling
        @pass_state
        def failing_command(state: CLIState) -> None:
            raise RuntimeError("boom")

        debug_state = CLIState(
            client=mock.Mock(spec=UDClient),
            yaml_output=False,
            debug=True,
        )

        with click.Context(failing_command, obj=debug_state) as ctx:
            with self.assertRaises(RuntimeError):
                ctx.invoke(failing_command)

        normal_state = CLIState(
            client=mock.Mock(spec=UDClient),
            yaml_output=False,
            debug=False,
        )

        with click.Context(failing_command, obj=normal_state) as ctx:
            with self.assertRaises(click.ClickException) as caught:
                ctx.invoke(failing_command)

        self.assertEqual(str(caught.exception), "boom")


class TestEmit(unittest.TestCase):
    def setUp(self) -> None:
        self.client = mock.Mock(spec=UDClient)

    def test_emit_yaml_outputs_yaml(self) -> None:
        state = CLIState(client=self.client, yaml_output=True, debug=False)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            emit({"key": "value"}, state)

        rendered = buffer.getvalue()
        self.assertIn("key: value", rendered)

    def test_emit_friendly_outputs_table(self) -> None:
        state = CLIState(client=self.client, yaml_output=False, debug=False)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            emit(
                [
                    {"id": 1, "name": "Alpha"},
                    {"id": 2, "name": "Beta"},
                ],
                state,
            )

        rendered = buffer.getvalue()
        self.assertIn("Alpha", rendered)
        self.assertIn("Beta", rendered)


class _CommandHarness:
    def __init__(self) -> None:
        self.client = mock.Mock(spec=UDClient)
        self.state = CLIState(client=self.client, yaml_output=False, debug=False)
        self.root = click.Group()
        register_products(self.root)
        register_versions(self.root)
        register_repositories(self.root)

    def invoke(self, command_path: str, **params: Any) -> None:
        parts = command_path.split()
        command = self.root
        for part in parts:
            command = command.get_command(None, part)
            if command is None:
                raise AssertionError(f"Command path not found: {command_path}")

        with click.Context(command, info_name=parts[-1], obj=self.state):
            command.callback(**params)


class TestProductCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = _CommandHarness()
        self.harness.client.list_products.return_value = make_paginated_products(products=[])
        self.harness.client.create_product.return_value = make_product(id=1, name="Created")

    def test_list_products_passes_query_parameters(self) -> None:
        self.harness.invoke(
            "products list",
            page=2,
            limit=5,
            sort="desc",
        )

        self.harness.client.list_products.assert_called_once_with(
            params={"page": 2, "limit": 5, "sort": "desc"},
        )

    def test_create_product_validates_payload(self) -> None:
        payload: Dict[str, Any] = {"eng_id": 3, "name": "Widget"}
        model = ProductCreate.model_validate(payload)

        with mock.patch("ud2.cli.product.load_model", return_value=model) as loader:
            self.harness.invoke("products create", payload_path="ignored")

        loader.assert_called_once_with("ignored", ProductCreate)
        self.harness.client.create_product.assert_called_once()


class TestVersionCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = _CommandHarness()
        self.harness.client.list_product_versions.return_value = []
        self.harness.client.delete_product_version.return_value = None

    def test_delete_version_emits_success(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            self.harness.invoke(
                "versions delete",
                product_id=5,
                version_id=2,
            )

        self.harness.client.delete_product_version.assert_called_once_with(5, 2)
        self.assertIn("Success.", buffer.getvalue())


class TestRepositoryCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = _CommandHarness()
        self.harness.client.list_repositories.return_value = make_paginated_repositories(repositories=[])

    def test_list_repositories_passes_query_parameters(self) -> None:
        self.harness.invoke(
            "repositories list",
            product_version_id=10,
            page=1,
            limit=25,
            sort="asc",
        )

        self.harness.client.list_repositories.assert_called_once_with(
            10,
            params={"page": 1, "limit": 25, "sort": "asc"},
        )


class TestCliStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_help_lists_resources(self) -> None:
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for resource in ("products", "versions", "repositories"):
            self.assertIn(resource, result.output)

    @mock.patch("ud2.cli._build_state")
    def test_products_list_invokes_client(self, build_state: mock.MagicMock) -> None:
        client = mock.Mock(spec=UDClient)
        client.list_products.return_value = make_paginated_products(products=[])
        build_state.return_value = CLIState(
            client=client,
            yaml_output=False,
            debug=False,
        )

        result = self.runner.invoke(cli, ["products", "list"])

        self.assertEqual(result.exit_code, 0, result.output)
        client.list_products.assert_called_once_with(params=None)


# The end.
