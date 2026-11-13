import os
import tempfile
import unittest
from unittest import mock

from xml.etree import ElementTree as ET

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, SCRIPTS)

import embed_spec  # noqa: E402


class SvgMetadataTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = os.path.join(self.tempdir.name, "example.svg")

    def write_svg(self, body=None):
        svg = body or '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">
  <rect width="100" height="50"/>
</svg>
'''
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(svg)
        return self.path

    def test_round_trip_and_idempotent_update(self):
        self.write_svg()
        python = "VALUE = 'a → b\n'\nprint(VALUE)\n"
        mermaid = "flowchart LR\n  A -->|ok| B\n"

        self.assertTrue(embed_spec.embed_file(self.path, python, mermaid))
        extracted = embed_spec.extract_sources(self.path)
        self.assertEqual(python, extracted["python"])
        self.assertEqual(mermaid, extracted["mermaid"])

        before = os.path.getmtime(self.path)
        self.assertFalse(embed_spec.embed_file(self.path, python, mermaid))
        self.assertEqual(before, os.path.getmtime(self.path))

    def test_failed_replace_saves_non_overwriting_version(self):
        self.write_svg()
        with open(self.path, "rb") as handle:
            original = handle.read()
        first_version = os.path.join(self.tempdir.name, "example (1).svg")
        with open(first_version, "wb") as handle:
            handle.write(b"existing version")

        with mock.patch.object(embed_spec.os, "replace", side_effect=OSError("locked")):
            self.assertTrue(embed_spec.embed_file(self.path, "VALUE = 1\n", "A --> B\n"))

        second_version = os.path.join(self.tempdir.name, "example (2).svg")
        with open(self.path, "rb") as handle:
            self.assertEqual(original, handle.read())
        with open(first_version, "rb") as handle:
            self.assertEqual(b"existing version", handle.read())
        self.assertEqual(
            {"python": "VALUE = 1\n", "mermaid": "A --> B\n"},
            embed_spec.extract_sources(second_version),
        )

    def test_failed_replace_saves_as_first_version_when_available(self):
        self.write_svg()
        with mock.patch.object(embed_spec.os, "replace", side_effect=OSError("locked")):
            self.assertTrue(embed_spec.embed_file(self.path, "VALUE = 1\n", "A --> B\n"))

        first_version = os.path.join(self.tempdir.name, "example (1).svg")
        self.assertEqual(
            {"python": "VALUE = 1\n", "mermaid": "A --> B\n"},
            embed_spec.extract_sources(first_version),
        )

    def test_bad_metadata_fails_clearly(self):
        self.write_svg()
        embed_spec.embed_file(self.path, "x = 1\n", "A --> B\n")

        root = ET.parse(self.path).getroot()
        metadata = root.find('{http://www.w3.org/2000/svg}metadata')
        mermaid = metadata.find('{https://github.com/DanTanzer/dans-skills}mermaid')
        mermaid.set('sha256', '0' * 64)
        ET.ElementTree(root).write(self.path, encoding='utf-8', xml_declaration=True)

        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            embed_spec.extract_sources(self.path)

    def test_missing_metadata_is_rejected(self):
        self.write_svg()
        with self.assertRaisesRegex(ValueError, 'missing SVG metadata'):
            embed_spec.extract_sources(self.path)

    def test_mermaid_metadata_is_optional(self):
        self.write_svg()
        self.assertTrue(embed_spec.embed_file(self.path, "VALUE = 1\n"))
        self.assertEqual({"python": "VALUE = 1\n"}, embed_spec.extract_sources(self.path))

    def test_invalid_svg_fails_with_a_clear_error(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("not SVG")
        with self.assertRaisesRegex(ValueError, "not valid SVG XML"):
            embed_spec.embed_file(self.path, "VALUE = 1\n")

    def test_extraction_is_safe_and_non_executing(self):
        self.write_svg()
        python = "import os\nprint('this should only be returned as text')\n"
        embed_spec.embed_file(self.path, python, "A --> B\n")
        data = embed_spec.extract_sources(self.path)
        self.assertIn("import os", data["python"])
        self.assertIn("print('this should only be returned as text')", data["python"])
        self.assertIsInstance(data["python"], str)


if __name__ == "__main__":
    unittest.main()
