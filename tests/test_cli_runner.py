""
"Integration tests for the CLI using Click's CliRunner."
""


import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

from click.testing import CliRunner

from ud2.cli import CLIState, cli
from ud2.models import ProductCreate

from . import dump_model, make_paginated_products, make_product


class _DummyClient:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []

    def list_products(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append(("list_products", (), {"params": params}))
        products = [
            make_product(id=1, name='Alpha'),
            make_product(id=2, name='Beta'),
        ]
        page = make_paginated_products(
            products=products,
            limit=10,
            page=1,
            total=len(products),
            total_pages=1,
        )
        # Provide serialized payload to mimic HTTP responses.
        return dump_model(page)

    def create_product(self, payload: ProductCreate) -> Dict[str, Any]:
        self.calls.append(("create_product", (payload,), {}))
        return dump_model(make_product(id=payload.eng_id, name=payload.name))

    def delete_repository(self, product_version_id: int, repository_id: int) -> None:
        self.calls.append(
            (
                "delete_repository",
                (product_version_id, repository_id),
                {},
            ),
        )
        return None


class TestCliRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    @mock.patch("ud2.cli._build_state")
    def test_products_list_default_output(self, build_state: mock.MagicMock) -> None:
        client = _DummyClient()
        build_state.side_effect = lambda config, env, yaml_output, debug: CLIState(
            client=client,
            yaml_output=yaml_output,
            debug=debug,
        )

        result = self.runner.invoke(cli, ["products", "list"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Alpha", result.output)
        self.assertTrue(any(call[0] == "list_products" for call in client.calls))

    @mock.patch("ud2.cli._build_state")
    def test_products_list_yaml_output(self, build_state: mock.MagicMock) -> None:
        client = _DummyClient()
        build_state.side_effect = lambda config, env, yaml_output, debug: CLIState(
            client=client,
            yaml_output=yaml_output,
            debug=debug,
        )

        result = self.runner.invoke(
            cli,
            ["--yaml", "products", "list"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("data:", result.output)
        self.assertIn("id: 1", result.output)

    @mock.patch("ud2.cli._build_state")
    def test_products_create_uses_payload_file(self, build_state: mock.MagicMock) -> None:
        client = _DummyClient()
        build_state.side_effect = lambda config, env, yaml_output, debug: CLIState(
            client=client,
            yaml_output=yaml_output,
            debug=debug,
        )

        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("eng_id: 99\nname: \"Runner Product\"\n")
            path = Path(handle.name)

        try:
            result = self.runner.invoke(
                cli,
                ["products", "create", "--file", str(path)],
            )
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(
            any(call[0] == "create_product" for call in client.calls),
            msg="create_product was not invoked.",
        )

    @mock.patch("ud2.cli._build_state")
    def test_repositories_delete_reports_success(self, build_state: mock.MagicMock) -> None:
        client = _DummyClient()
        build_state.side_effect = lambda config, env, yaml_output, debug: CLIState(
            client=client,
            yaml_output=yaml_output,
            debug=debug,
        )

        result = self.runner.invoke(
            cli,
            ["repositories", "delete", "42", "7"],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Success.", result.output)
        self.assertIn(
            ("delete_repository", (42, 7), {}),
            client.calls,
        )


# The end.
