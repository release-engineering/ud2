"""
Unit tests for shared CLI helpers.
"""

import unittest

from click import ClickException

from ud2.cli.util import parse_content_types, resplit
from ud2.models.enums import ContentType


class TestResplit(unittest.TestCase):
    def test_empty_args(self):
        self.assertEqual(resplit(), [])

    def test_single_value(self):
        self.assertEqual(resplit('TUSC-1234'), ['TUSC-1234'])

    def test_comma_separated_value(self):
        self.assertEqual(
            resplit('TUSC-1234, TUSC-5678'),
            ['TUSC-1234', 'TUSC-5678'],
        )

    def test_multiple_values(self):
        self.assertEqual(
            resplit('TUSC-1234', 'TUSC-5678'),
            ['TUSC-1234', 'TUSC-5678'],
        )

    def test_combined_repeatable_and_comma_separated(self):
        self.assertEqual(
            resplit('TUSC-1,TUSC-2', 'TUSC-3'),
            ['TUSC-1', 'TUSC-2', 'TUSC-3'],
        )


class TestParseContentTypes(unittest.TestCase):
    def test_defaults_to_distribution(self):
        self.assertEqual(
            parse_content_types(default=[ContentType.DISTRIBUTION.value]),
            ['DISTRIBUTION'],
        )

    def test_upper_cases_values(self):
        self.assertEqual(
            parse_content_types('distribution', 'bugfix'),
            ['DISTRIBUTION', 'BUGFIX'],
        )

    def test_resplits_comma_separated_and_repeatable(self):
        self.assertEqual(
            parse_content_types('distribution,bugfix', 'security'),
            ['DISTRIBUTION', 'BUGFIX', 'SECURITY'],
        )

    def test_rejects_invalid_value(self):
        with self.assertRaises(ClickException) as ctx:
            parse_content_types('distribution', 'invalid')
        self.assertIn('Invalid content type', str(ctx.exception))


# The end.
