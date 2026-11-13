import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)

import embed_spec  # noqa: E402


class RenderSvgTest(unittest.TestCase):
    def test_doc_render_keeps_final_svg_with_embedded_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = os.path.join(folder, "design.md")
            spec = os.path.join(folder, "design.spec.py")
            with open(doc, "w", encoding="utf-8") as handle:
                handle.write("# Design\n")
            with open(spec, "w", encoding="utf-8") as handle:
                handle.write(
                    """DIAGRAMS = [{
    "stem": "demo",
    "alt": "Demo diagram.",
    "svg": '<svg viewBox="0 0 100 50"><line class="a a-file" x1="10" y1="25" x2="90" y2="25"/></svg>',
    "mermaid": "flowchart LR\\n  A --> B",
}]
"""
                )

            done = subprocess.run(
                [sys.executable, "-I", os.path.join(SCRIPTS, "render.py"), spec, "--doc", doc],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

            svg = os.path.join(folder, "readable-diagrams", "design", "demo.svg")
            self.assertTrue(os.path.exists(svg))
            with open(spec, encoding="utf-8") as handle:
                python_source = handle.read()
            self.assertEqual(
                {
                    "python": python_source,
                    "mermaid": "flowchart LR\n  A --> B\n",
                },
                embed_spec.extract_sources(svg),
            )


if __name__ == "__main__":
    unittest.main()
