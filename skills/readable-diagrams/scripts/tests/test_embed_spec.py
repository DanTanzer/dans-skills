import contextlib
import io
import os
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, SCRIPTS)

import embed_spec  # noqa: E402


class EmbedSpecCommandTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.svg = os.path.join(self.tempdir.name, "diagram.svg")
        with open(self.svg, "w", encoding="utf-8") as handle:
            handle.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        self.python = "VALUE = 'source text'\n"
        self.mermaid = "flowchart LR\n  A --> B\n"

    def test_embed_and_extract_commands_round_trip_svg_sources(self):
        spec = os.path.join(self.tempdir.name, "diagram.spec.py")
        mmd = os.path.join(self.tempdir.name, "diagram.mmd")
        out = os.path.join(self.tempdir.name, "out")
        os.mkdir(out)
        for path, text in ((spec, self.python), (mmd, self.mermaid)):
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, embed_spec.main(["embed_spec.py", "embed", self.svg, spec, mmd]))
            self.assertEqual(0, embed_spec.main(["embed_spec.py", "extract", self.svg, out]))

        self.assertEqual(self.python, embed_spec.read_text(os.path.join(out, "diagram.spec.py")))
        self.assertEqual(self.mermaid, embed_spec.read_text(os.path.join(out, "diagram.mmd")))

    def test_extract_does_not_overwrite_different_source_files(self):
        embed_spec.embed_file(self.svg, self.python, self.mermaid)
        spec = os.path.join(self.tempdir.name, "diagram.spec.py")
        with open(spec, "w", encoding="utf-8") as handle:
            handle.write("edited = True\n")

        with self.assertRaisesRegex(embed_spec.SpecError, "already exists and holds something else"):
            embed_spec.extract_to(self.svg, self.tempdir.name)

        self.assertEqual("edited = True\n", embed_spec.read_text(spec))
        self.assertFalse(os.path.exists(os.path.join(self.tempdir.name, "diagram.mmd")))

    def test_extract_reports_missing_svg_metadata(self):
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(1, embed_spec.main(["embed_spec.py", "extract", self.svg]))
        self.assertIn("missing SVG metadata", stderr.getvalue())

    def test_usage_mistake_returns_two(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, embed_spec.main(["embed_spec.py"]))


if __name__ == "__main__":
    unittest.main()
