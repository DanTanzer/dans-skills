"""figlib builds the example, every SVG is well-formed, every label fits, and the Markdown block has the right shape."""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.dom.minidom

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
import figlib  # noqa: E402
import render  # noqa: E402

# A stand-in for puppeteer: enough for Node to find it, load it and read its version.
FAKE_PUPPETEER = {
    "package.json": '{"name": "puppeteer", "version": "0.0.0-test", "exports": {".": {"import": "./index.mjs", "require": "./index.cjs"}}}',
    "index.mjs": "export default {};\n",
    "index.cjs": "module.exports = {};\n",
}


def fake_puppeteer(node_modules):
    folder = os.path.join(node_modules, "puppeteer")
    os.makedirs(folder)
    for name, body in FAKE_PUPPETEER.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8") as handle:
            handle.write(body)


def doctor_copy(scripts_dir):
    """A copy of doctor.sh in scripts_dir, so the doctor asks Node from there."""
    os.makedirs(scripts_dir)
    shutil.copy(os.path.join(SCRIPTS, "doctor.sh"), scripts_dir)
    return os.path.join(scripts_dir, "doctor.sh")


class ExampleBuildsTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.spec = render.load_spec(os.path.join(SCRIPTS, "example_spec.py"))
        self.figures = figlib.build(self.spec, self.out)

    def test_three_figures_with_svg_and_html(self):
        self.assertEqual(["sync-data-flow", "sync-sequence-1-ask-and-answer", "sync-sequence-2-broadcast"], [f["stem"] for f in self.figures])
        names = sorted(os.listdir(self.out))
        self.assertIn("figures.html", names)
        for f in self.figures:
            self.assertIn(f"{f['stem']}.svg", names)

    def test_every_svg_is_well_formed_xml(self):
        for f in self.figures:
            with open(os.path.join(self.out, f"{f['stem']}.svg"), encoding="utf-8") as handle:
                xml.dom.minidom.parseString(handle.read())

    def test_sequences_also_get_mermaid_without_semicolons(self):
        for stem in ("sync-sequence-1-ask-and-answer", "sync-sequence-2-broadcast"):
            with open(os.path.join(self.out, f"{stem}.mmd"), encoding="utf-8") as handle:
                mmd = handle.read()
            self.assertTrue(mmd.startswith("sequenceDiagram"))
            self.assertNotIn(";", mmd)

    def test_the_page_holds_the_legend_and_one_figure_card_per_figure(self):
        with open(os.path.join(self.out, "figures.html"), encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn('class="legend"', page)
        self.assertEqual(3, page.count('<figure data-png="'))
        self.assertNotIn("https://", page)


class FitChecksTest(unittest.TestCase):
    def test_a_message_label_too_long_for_its_gap_is_refused(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("msg", "A", "B", "x" * 200, "file")]}
        with self.assertRaises(figlib.FigureError):
            figlib.render_sequence(seq)

    def test_a_box_line_too_long_is_refused(self):
        c = figlib.Canvas("t", 400, 200, "t")
        with self.assertRaises(figlib.FigureError):
            c.box(10, 10, 100, 60, "ok", ["this line is far too long for a hundred pixel box"])

    def test_a_note_needs_exactly_two_lines(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("note", "A", ["only one line"])]}
        with self.assertRaises(figlib.FigureError):
            figlib.render_sequence(seq)

    def test_mermaid_refuses_a_semicolon(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("msg", "A", "B", "get; reply due", "file")]}
        with self.assertRaises(figlib.FigureError):
            figlib.mermaid_sequence(seq)

    def test_unknown_arrow_kind_is_refused(self):
        with self.assertRaises(figlib.FigureError):
            figlib.line(0, 0, 1, 1, "http", "p")


class ZoneTitleTest(unittest.TestCase):
    # Real widths, measured in Chrome in the zone title style: Arial bold capitals, 13px, 0.1 em letter-spacing.
    MEASURED = {"MVP SHORTCUT": 119.4, "MOMENTUM": 88.4}

    def test_a_zone_subtitle_starts_clear_of_its_title(self):
        for title, real in self.MEASURED.items():
            svg = figlib.Canvas("z", 1000, 120, "z").zone(0, 0, 600, 100, title, "start here").svg()
            sub_x = float(re.search(r'<text class="ts" x="([\d.]+)"', svg).group(1))
            self.assertGreaterEqual(sub_x - 18 - real, 16, f"{title}: the subtitle starts too close")


class SampleBuildsTest(unittest.TestCase):
    def test_the_sample_builds_both_figures_with_mermaid(self):
        out = tempfile.mkdtemp()
        spec = render.load_spec(os.path.join(os.path.dirname(SCRIPTS), "sample", "spec.py"))
        figures = figlib.build(spec, out)
        self.assertEqual(["data-flow", "build-sequence"], [f["stem"] for f in figures])
        for f in figures:
            self.assertTrue(os.path.exists(os.path.join(out, f"{f['stem']}.mmd")))


class DoctorTest(unittest.TestCase):
    def test_a_missing_chrome_is_named_with_its_fix_and_fails(self):
        env = dict(os.environ, CHROME_PATH="/nonexistent/chrome")
        done = subprocess.run(["bash", os.path.join(SCRIPTS, "doctor.sh")], capture_output=True, text=True, env=env)
        self.assertEqual(1, done.returncode)
        self.assertIn("not found at /nonexistent/chrome", done.stdout)
        self.assertIn("→ install Google Chrome", done.stdout)

    @unittest.skipUnless(shutil.which("node"), "the puppeteer check needs Node")
    def test_a_puppeteer_in_a_folder_above_the_scripts_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.realpath(tmp)
            fake_puppeteer(os.path.join(repo, "node_modules"))
            doctor = doctor_copy(os.path.join(repo, ".claude", "skills", "readable-diagrams", "scripts"))
            done = subprocess.run(["bash", doctor], capture_output=True, text=True)
        self.assertIn(f"puppeteer   0.0.0-test, in {repo}/node_modules", done.stdout)

    @unittest.skipUnless(shutil.which("node"), "the puppeteer check needs Node")
    def test_a_puppeteer_node_cannot_find_is_named_with_one_install_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            doctor = doctor_copy(os.path.join(os.path.realpath(tmp), "scripts"))
            done = subprocess.run(["bash", doctor], capture_output=True, text=True)
        self.assertEqual(1, done.returncode)
        self.assertIn("puppeteer   Node cannot find it from the scripts folder", done.stdout)
        self.assertIn(f"→ bash {doctor} --install", done.stdout)


class RenderShowsTheDoctorTest(unittest.TestCase):
    def test_a_puppeteer_node_cannot_load_prints_the_doctor_report(self):
        node_says = "Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'puppeteer' imported from /x/export_png.mjs"
        failed = subprocess.CompletedProcess([], 1, "", node_says)
        with tempfile.TemporaryDirectory() as out, mock.patch.object(render, "export", return_value=failed), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            code = render.main(["render.py", os.path.join(SCRIPTS, "example_spec.py"), out])
        self.assertEqual(1, code)
        self.assertIn("The PNG export cannot run yet. The doctor says:", said.getvalue())
        self.assertIn("readable-diagrams doctor: can this Mac export pictures?", said.getvalue())


class RenderPathsTest(unittest.TestCase):
    def test_a_relative_out_folder_reaches_the_exporter_in_full(self):
        calls = []

        def node_run(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, "wrote a\nwrote b\nwrote c\n", "")

        start = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.realpath(tmp)
            try:
                os.chdir(work)
                with mock.patch.object(render.subprocess, "run", node_run), contextlib.redirect_stdout(io.StringIO()):
                    code = render.main(["render.py", os.path.join(SCRIPTS, "example_spec.py"), "out"])
            finally:
                os.chdir(start)
        self.assertEqual(0, code)
        self.assertEqual(2, len(calls))
        for command, kwargs in calls:
            self.assertEqual(os.path.join(work, "out", "figures.html"), command[2])
            self.assertEqual(os.path.join(work, "out", "figures"), command[3])
            self.assertEqual(render.HERE, kwargs["cwd"])


class PictureBlockTest(unittest.TestCase):
    def test_dark_source_then_light_img_then_closed_mermaid(self):
        block = figlib.picture_block("x-y", "Alt text.", "sequenceDiagram\n  A->>B: hi")
        self.assertIn('srcset="figures/x-y-dark.png"', block)
        self.assertIn('src="figures/x-y.png" alt="Alt text."', block)
        self.assertIn("<details>", block)
        self.assertIn("```mermaid\nsequenceDiagram", block)

    def test_alt_text_may_not_hold_a_quote(self):
        with self.assertRaises(figlib.FigureError):
            figlib.picture_block("x", 'say "hi"')


if __name__ == "__main__":
    unittest.main()
