import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)

import embed_spec  # noqa: E402
from tests.pngs import png_chunk, tiny_png  # noqa: E402
import migrate_png_to_svg  # noqa: E402


SPEC_TEXT = '''DIAGRAMS = [{
    "stem": "demo",
    "alt": "Demo diagram.",
    "svg": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50"><line class="a a-file" x1="10" y1="25" x2="90" y2="25"/></svg>'
}]
'''

MERMAID_TEXT = "flowchart LR\n  A --> B\n"


class MigratePngToSvgTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = self.tmp.name

    def make_png(self):
        png = tiny_png(
            png_chunk(b"tEXt", embed_spec.LEGACY_SPEC_KEYWORD + b"\x00" + SPEC_TEXT.encode("utf-8")),
            png_chunk(b"tEXt", embed_spec.LEGACY_MERMAID_KEYWORD + b"\x00" + MERMAID_TEXT.encode("utf-8")),
        )
        path = os.path.join(self.folder, "demo.png")
        with open(path, "wb") as handle:
            handle.write(png)
        return path

    def test_script_extracts_legacy_sources_and_generates_svg(self):
        png_path = self.make_png()
        code = migrate_png_to_svg.main([self.folder])
        self.assertEqual(0, code)
        self.assertTrue(os.path.exists(os.path.join(self.folder, "demo.spec.py")))
        self.assertTrue(os.path.exists(os.path.join(self.folder, "demo.mmd")))
        self.assertTrue(os.path.exists(os.path.join(self.folder, "demo.svg")))
        with open(os.path.join(self.folder, "demo.spec.py"), encoding="utf-8") as handle:
            self.assertEqual(SPEC_TEXT, handle.read())
        with open(os.path.join(self.folder, "demo.mmd"), encoding="utf-8") as handle:
            self.assertEqual(MERMAID_TEXT, handle.read())

    def test_script_ignores_folders_without_legacy_pngs(self):
        path = os.path.join(self.folder, "notes.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("hello")
        self.assertEqual(0, migrate_png_to_svg.main([self.folder]))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "notes.svg")))


if __name__ == "__main__":
    unittest.main()
