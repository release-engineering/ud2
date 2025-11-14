"""
Unit tests for the loader module.
"""


import io
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest import TestCase

from ud2.loader import load_yaml, pretty_yaml
from ud2.models.compat import BaseModel


class SampleModel(BaseModel):
    """
    Minimal model used to exercise loader validation.
    """

    name: str
    count: int


class TestLoader(TestCase):
    def test_load_yaml_returns_parsed_mapping(self) -> None:

        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            path = Path(handle.name)
            handle.write(
                "name: widgets\n"
                "count: 3\n"
            )
            handle.flush()

            data = load_yaml(path)

        self.assertIsInstance(data, dict)
        self.assertEqual(data["name"], "widgets")
        self.assertEqual(data["count"], 3)


    def test_load_yaml_validates_model_when_provided(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            path = Path(handle.name)
            handle.write(
                "name: sample\n"
                "count: 5\n"
            )
            handle.flush()

            model = load_yaml(path, model=SampleModel)

        self.assertIsInstance(model, SampleModel)
        self.assertEqual(model.name, "sample")
        self.assertEqual(model.count, 5)


    def test_pretty_yaml_serializes_models_and_lists(self) -> None:
        buffer = io.StringIO()
        payload = {
            "items": [
                SampleModel(name="widget", count=2),
                {"name": "gizmo", "count": 7},
            ],
        }

        pretty_yaml(payload, out=buffer)

        rendered = buffer.getvalue()
        self.assertIn("items:", rendered)
        self.assertIn("name: widget", rendered)
        self.assertIn("count: 2", rendered)
        self.assertIn("name: gizmo", rendered)
        self.assertIn("count: 7", rendered)


# The end.
