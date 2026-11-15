import os
import re
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import diagramlib  # noqa: E402
import embed_spec  # noqa: E402
import render  # noqa: E402

SAMPLE = os.path.join(SKILL, "sample", "spec.py")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class DiagramBuildTest(unittest.TestCase):
    def test_sample_builds_complete_svg_and_mermaid_files(self):
        with tempfile.TemporaryDirectory() as out:
            diagrams = diagramlib.build(render.load_spec(SAMPLE), out)
            self.assertEqual(["data-flow", "build-sequence"], [item["stem"] for item in diagrams])
            self.assertEqual(
                ["build-sequence-dark.svg", "build-sequence.svg", "data-flow-dark.svg", "data-flow.svg"],
                sorted(name for name in os.listdir(out) if name.endswith(".svg")),
            )
            for item in diagrams:
                self.assertTrue(os.path.isfile(os.path.join(out, f"{item['stem']}.mmd")))
                for path in item["files"].values():
                    svg = read(path)
                    xml.dom.minidom.parseString(svg)
                    self.assertIn("<style>", svg)
                    self.assertNotIn("var(", svg)
                    self.assertNotRegex(svg, r"href=|@import|url\((?!#)")

    def test_only_arrow_kinds_used_in_the_diagram_appear_in_its_legend(self):
        spec = type("Spec", (), {"DIAGRAMS": [{
            "stem": "flow",
            "alt": "A data flow.",
            "svg": lambda: diagramlib.Canvas("flow", 1000, 100, "A data flow.").arrow(
                100, 50, 900, 50, "file"
            ).svg(),
        }]})
        with tempfile.TemporaryDirectory() as out:
            diagram = diagramlib.build(spec, out)[0]
            svg = read(diagram["files"]["light"])
        self.assertIn('class="lg-file"', svg)
        self.assertNotIn('class="lg-ring"', svg)

    def test_one_theme_builds_only_that_theme(self):
        with tempfile.TemporaryDirectory() as out:
            diagrams = diagramlib.build(render.load_spec(SAMPLE), out, ("dark",))
            self.assertEqual([{"dark"}, {"dark"}], [set(item["files"]) for item in diagrams])
            self.assertEqual(
                ["build-sequence-dark.svg", "data-flow-dark.svg"],
                sorted(name for name in os.listdir(out) if name.endswith(".svg")),
            )

    def test_diagonal_arrows_need_explicit_permission(self):
        canvas = diagramlib.Canvas("test", 400, 300)
        with self.assertRaisesRegex(diagramlib.DiagramError, "diagonal"):
            canvas.arrow(10, 10, 200, 100, "file")
        self.assertIn("<line", canvas.arrow(10, 10, 200, 100, "file", diagonal=True).svg())

    def test_elbow_uses_right_angle_bends(self):
        svg = diagramlib.Canvas("test", 400, 300).elbow(10, 10, 200, 100, "file").svg()
        path = re.search(r'<path class="a a-file" d="([^"]+)"', svg).group(1)
        self.assertEqual("M10 10 L10 55 L200 55 L200 100", path)

    def test_box_height_is_the_minimum_that_fits_its_text(self):
        title, lines = "A title", ["first line", "second line"]
        height = diagramlib.box_height(title, lines)
        canvas = diagramlib.Canvas("test", 400, 300)
        canvas.box(10, 10, 200, height, title, lines)
        with self.assertRaisesRegex(diagramlib.DiagramError, "box_height"):
            canvas.box(10, 10, 200, height - 1, title, lines)

    def test_overlong_box_lines_and_sequence_labels_are_rejected(self):
        with self.assertRaisesRegex(diagramlib.DiagramError, "needs"):
            diagramlib.Canvas("test", 400, 300).box(
                10, 10, 100, 60, "Title", ["a line that cannot fit in this box"]
            )
        sequence = {
            "id": "test",
            "title": "Test",
            "caption": "Test sequence.",
            "lifelines": [("A", "A", "one"), ("B", "B", "two")],
            "rows": [("msg", "A", "B", "x" * 200, "file")],
        }
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.render_sequence(sequence)

    def test_sequence_notes_need_two_lines_and_mermaid_labels_reject_semicolons(self):
        lifelines = [("A", "A", "one"), ("B", "B", "two")]
        note = {"id": "test", "title": "Test", "caption": "Test.", "lifelines": lifelines,
                "rows": [("note", "A", ["one line"])]}
        with self.assertRaisesRegex(diagramlib.DiagramError, "exactly two lines"):
            diagramlib.render_sequence(note)
        message = {"id": "test", "title": "Test", "caption": "Test.", "lifelines": lifelines,
                   "rows": [("msg", "A", "B", "get; reply due", "file")]}
        with self.assertRaisesRegex(diagramlib.DiagramError, "reads ; and # as syntax"):
            diagramlib.mermaid_sequence(message)

    def test_unknown_arrow_kind_is_rejected(self):
        with self.assertRaisesRegex(diagramlib.DiagramError, "unknown"):
            diagramlib.line(0, 0, 100, 0, "http", "test")

    def test_zone_subtitle_starts_clear_of_its_title(self):
        measured_title_widths = {"MVP SHORTCUT": 118.1, "MOMENTUM": 87.1}
        for title, title_width in measured_title_widths.items():
            svg = diagramlib.Canvas("test", 1000, 120, "Test").zone(
                0, 0, 600, 100, title, "start here"
            ).svg()
            subtitle_x = float(re.search(r'<text class="ts" x="([\d.]+)"', svg).group(1))
            self.assertGreaterEqual(subtitle_x - 18 - title_width, 16, title)


class RenderTest(unittest.TestCase):
    def make_spec(self, folder):
        spec = os.path.join(folder, "design.spec.py")
        with open(spec, "w", encoding="utf-8") as handle:
            handle.write(
                """DIAGRAMS = [{
    "stem": "demo",
    "alt": "Demo diagram.",
    "svg": '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50"><line class="a a-file" x1="10" y1="25" x2="90" y2="25"/></svg>',
    "mermaid": "flowchart LR\\n  A --> B",
}]
"""
            )
        return spec

    def test_doc_render_keeps_only_final_svg_with_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = os.path.join(folder, "design.md")
            with open(doc, "w", encoding="utf-8") as handle:
                handle.write("# Design\n")
            spec = self.make_spec(folder)

            done = subprocess.run(
                [sys.executable, "-I", os.path.join(SCRIPTS, "render.py"), spec, "--doc", doc],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            svg = os.path.join(folder, "readable-diagrams", "design", "demo.svg")
            self.assertEqual(["demo.svg"], os.listdir(os.path.dirname(svg)))
            self.assertEqual(
                {"python": read(spec), "mermaid": "flowchart LR\n  A --> B\n"},
                embed_spec.extract_sources(svg),
            )
            self.assertIn("readable-diagrams/design/demo.svg", done.stdout)
            self.assertIn("```mermaid", done.stdout)

    def test_out_render_supports_both_themes_without_raster_files(self):
        with tempfile.TemporaryDirectory() as folder:
            spec = self.make_spec(folder)
            out = os.path.join(folder, "out")
            done = subprocess.run(
                [
                    sys.executable, "-I", os.path.join(SCRIPTS, "render.py"),
                    spec, "--out", out, "--theme", "both",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual(["demo-dark.svg", "demo.mmd", "demo.svg"], sorted(os.listdir(out)))
            for name in ("demo.svg", "demo-dark.svg"):
                self.assertEqual("flowchart LR\n  A --> B\n", embed_spec.extract_sources(os.path.join(out, name))["mermaid"])


class DoctorTest(unittest.TestCase):
    def test_build_check_does_not_require_rsvg_convert_or_homebrew(self):
        with tempfile.TemporaryDirectory() as folder:
            python = os.path.join(folder, "python3")
            with open(python, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\necho 'Python 3.12.0'\n")
            os.chmod(python, 0o755)
            env = dict(os.environ, PATH=folder)
            done = subprocess.run(
                ["/bin/bash", os.path.join(SCRIPTS, "doctor.sh")],
                capture_output=True,
                text=True,
                env=env,
            )

        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("Python 3.12.0", done.stdout)
        self.assertNotIn("rsvg-convert", done.stdout)
        self.assertNotIn("librsvg", done.stdout)


class PictureBlockTest(unittest.TestCase):
    def test_both_themes_reference_svg_and_include_mermaid(self):
        block = diagramlib.picture_block(
            "data-flow", "Data flow.", "readable-diagrams/design",
            "flowchart LR\n  A --> B", diagramlib.BOTH,
        )
        self.assertIn('srcset="readable-diagrams/design/data-flow-dark.svg"', block)
        self.assertIn('src="readable-diagrams/design/data-flow.svg" alt="Data flow."', block)
        self.assertIn("```mermaid\nflowchart LR\n  A --> B\n```", block)

    def test_single_theme_is_a_markdown_svg_image(self):
        self.assertEqual(
            "![Data flow.](diagrams/data-flow.svg)\n",
            diagramlib.picture_block("data-flow", "Data flow.", "diagrams", themes=("light",)),
        )
        self.assertEqual(
            "![Data flow.](diagrams/data-flow-dark.svg)\n",
            diagramlib.picture_block("data-flow", "Data flow.", "diagrams", themes=("dark",)),
        )


if __name__ == "__main__":
    unittest.main()
