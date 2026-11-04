"""diagramlib builds the example, every SVG is well-formed and complete on its own, every label fits, boxes get the exact
height their text needs, the doctor names rsvg-convert, a doc gets only the pictures it shows while every build file
stays in .readable-diagrams/ at the project root, which git ignores, and the Markdown block has the right shape for
one theme or both."""
import contextlib
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.dom.minidom

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
import diagramlib  # noqa: E402
import render  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(SCRIPTS), "sample", "spec.py")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def png_size(path):
    with open(path, "rb") as handle:
        return struct.unpack(">II", handle.read(24)[16:24])


def fake_bin(folder, **scripts):
    """A folder of stand-in commands: name=shell body. With /usr/bin and /bin after it, it makes a PATH."""
    os.makedirs(folder)
    for name, body in scripts.items():
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"#!/bin/sh\n{body}\n")
        os.chmod(path, 0o755)
    return f"{folder}:/usr/bin:/bin"


def run_doctor(path_value):
    env = dict(os.environ, PATH=path_value)
    return subprocess.run(["/bin/bash", os.path.join(SCRIPTS, "doctor.sh")], capture_output=True, text=True, env=env)


def fake_png(svg, png):
    """Stands in for rsvg-convert: writes a small file where the PNG goes."""
    with open(png, "wb") as handle:
        handle.write(b"drawn from " + os.path.basename(svg).encode())
    return subprocess.CompletedProcess(["rsvg-convert"], 0, "", "")


class ExampleBuildsTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.diagrams = diagramlib.build(render.load_spec(os.path.join(SCRIPTS, "example_spec.py")), self.out)

    def test_three_diagrams_each_with_a_light_and_a_dark_svg(self):
        self.assertEqual(["sync-data-flow", "sync-sequence-1-ask-and-answer", "sync-sequence-2-broadcast"], [f["stem"] for f in self.diagrams])
        names = os.listdir(self.out)
        for f in self.diagrams:
            self.assertIn(f"{f['stem']}.svg", names)
            self.assertIn(f"{f['stem']}-dark.svg", names)

    def test_every_svg_is_well_formed_xml(self):
        for f in self.diagrams:
            for path in f["files"].values():
                xml.dom.minidom.parseString(read(path))

    def test_each_svg_is_complete_on_its_own(self):
        for f in self.diagrams:
            for path in f["files"].values():
                svg = read(path)
                self.assertIn("<style>", svg)
                self.assertIn('<rect class="card"', svg)
                self.assertNotIn("var(", svg, f"{path}: a colour still names a token")
                self.assertIsNone(re.search(r"href=|@import|url\((?!#)", svg), f"{path}: reaches outside the file")

    def test_the_light_and_the_dark_svg_carry_their_own_colours(self):
        light, dark = (read(self.diagrams[0]["files"][theme]) for theme in ("light", "dark"))
        self.assertIn(f".card {{ fill: {diagramlib.THEMES['light']['--surface']};", light)
        self.assertIn(f".card {{ fill: {diagramlib.THEMES['dark']['--surface']};", dark)
        self.assertEqual(light.replace(diagramlib.theme_css("light"), ""), dark.replace(diagramlib.theme_css("dark"), ""))

    def test_the_legend_shows_only_the_arrow_kinds_a_diagram_draws(self):
        self.assertEqual(["file", "ring", "say", "loc"], diagramlib.used_kinds(self.diagrams[0]["svg"]))
        sample = diagramlib.build(render.load_spec(SAMPLE), tempfile.mkdtemp())[0]
        self.assertEqual(["file", "say"], diagramlib.used_kinds(sample["svg"]))
        svg = read(sample["files"]["light"])
        self.assertIn('class="lg-file"', svg)
        self.assertNotIn('class="lg-ring"', svg)

    def test_a_diagram_given_as_svg_text_with_its_own_size_still_makes_a_valid_card(self):
        spec = type("Spec", (), {"DIAGRAMS": [{"stem": "raw", "alt": "A line.", "svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="50" viewBox="0 0 1000 100">'
            '<line class="a a-file" x1="10" y1="50" x2="990" y2="50"/></svg>')}]})
        card = read(diagramlib.build(spec, tempfile.mkdtemp())[0]["files"]["light"])
        xml.dom.minidom.parseString(card)
        self.assertIn('<svg x="11" y="43.4" width="898" height="89.8"', card)

    def test_sequences_also_get_mermaid_without_semicolons(self):
        for stem in ("sync-sequence-1-ask-and-answer", "sync-sequence-2-broadcast"):
            mmd = read(os.path.join(self.out, f"{stem}.mmd"))
            self.assertTrue(mmd.startswith("sequenceDiagram"))
            self.assertNotIn(";", mmd)


class FitChecksTest(unittest.TestCase):
    def test_a_message_label_too_long_for_its_gap_is_refused(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("msg", "A", "B", "x" * 200, "file")]}
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.render_sequence(seq)

    def test_a_box_line_too_long_is_refused(self):
        c = diagramlib.Canvas("t", 400, 200, "t")
        with self.assertRaises(diagramlib.DiagramError):
            c.box(10, 10, 100, 60, "ok", ["this line is far too long for a hundred pixel box"])

    def test_a_note_needs_exactly_two_lines(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("note", "A", ["only one line"])]}
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.render_sequence(seq)

    def test_mermaid_refuses_a_semicolon(self):
        seq = {"id": "x", "title": "t", "caption": "c", "lifelines": [("A", "A", "one"), ("B", "B", "two")],
               "rows": [("msg", "A", "B", "get; reply due", "file")]}
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.mermaid_sequence(seq)

    def test_unknown_arrow_kind_is_refused(self):
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.line(0, 0, 1, 1, "http", "p")


class BoxHeightTest(unittest.TestCase):
    SHAPES = [("title only", (), False), ("a title", ["one line", "two lines"], False),
              ("two\nlines", ["plain", ("small", "ts")], False), ("a title", ["a fact", "an aside"], True)]

    def test_box_height_is_the_least_height_a_box_accepts(self):
        for title, lines, muted in self.SHAPES:
            need = diagramlib.box_height(title, lines, muted)
            diagramlib.Canvas("b", 400, 300).box(10, 10, 200, need, title, lines, muted)
            with self.assertRaisesRegex(diagramlib.DiagramError, f"needs {need}px: box_height"):
                diagramlib.Canvas("b", 400, 300).box(10, 10, 200, need - 1, title, lines, muted)

    def test_at_that_height_the_last_line_sits_16_above_the_bottom(self):
        for title, lines, muted in self.SHAPES:
            need = diagramlib.box_height(title, lines, muted)
            svg = diagramlib.Canvas("b", 400, 300).box(10, 10, 200, need, title, lines, muted).svg()
            last = max(float(y) for y in re.findall(r'<text class="[^"]*" x="[\d.]+" y="([\d.]+)"', svg))
            self.assertEqual(16, 10 + need - last, title)


class ElbowTest(unittest.TestCase):
    def path_d(self, svg):
        return re.search(r'<path class="a a-file" d="([^"]+)"', svg).group(1)

    def test_an_elbow_goes_down_across_halfway_then_down(self):
        svg = diagramlib.Canvas("e", 400, 300).elbow(10, 10, 200, 100, "file").svg()
        self.assertEqual("M10 10 L10 55 L200 55 L200 100", self.path_d(svg))
        self.assertIn('marker-end="url(#ah-file-e)"', svg)

    def test_first_h_goes_sideways_then_down_then_sideways(self):
        svg = diagramlib.Canvas("e", 400, 300).elbow(10, 10, 200, 100, "file", first="h").svg()
        self.assertEqual("M10 10 L105 10 L105 100 L200 100", self.path_d(svg))

    def test_at_an_ends_own_y_makes_one_bend(self):
        svg = diagramlib.Canvas("e", 400, 300).elbow(10, 10, 200, 100, "file", at=100).svg()
        self.assertEqual("M10 10 L10 100 L200 100", self.path_d(svg))

    def test_an_arrowhead_needs_a_last_leg_of_16(self):
        with self.assertRaisesRegex(diagramlib.DiagramError, "last leg is 5 long, but an arrowhead needs 16"):
            diagramlib.Canvas("e", 400, 300).elbow(10, 10, 200, 100, "file", at=95)
        with self.assertRaisesRegex(diagramlib.DiagramError, "first leg is 4 long"):
            diagramlib.Canvas("e", 400, 300).elbow(10, 10, 200, 100, "file", at=14, both=True)

    def test_a_diagonal_arrow_is_refused_unless_it_is_meant(self):
        with self.assertRaisesRegex(diagramlib.DiagramError, r"diagonal: move a box so the ends share an x or a y, or draw it with elbow\(\)"):
            diagramlib.Canvas("d", 400, 300).arrow(10, 10, 200, 100, "file")
        self.assertIn("<line", diagramlib.Canvas("d", 400, 300).arrow(10, 10, 200, 100, "file", diagonal=True).svg())

    def test_an_elbow_diagram_makes_a_valid_card_with_its_kind_in_the_legend(self):
        draw = diagramlib.Canvas("e", 1000, 300, "An elbow.").elbow(100, 40, 600, 250, "ring", both=True).svg
        diagram = diagramlib.build(type("Spec", (), {"DIAGRAMS": [{"stem": "e", "alt": "An elbow.", "svg": draw}]}),
                              tempfile.mkdtemp())[0]
        card = read(diagram["files"]["light"])
        xml.dom.minidom.parseString(card)
        self.assertEqual(["ring"], diagramlib.used_kinds(diagram["svg"]))
        self.assertIn('class="lg-ring"', card)


class ZoneTitleTest(unittest.TestCase):
    # Real widths, measured in rsvg-convert in the zone title style: Arial bold capitals, 13px, 0.1 em letter-spacing.
    MEASURED = {"MVP SHORTCUT": 118.1, "MOMENTUM": 87.1}

    def test_a_zone_subtitle_starts_clear_of_its_title(self):
        for title, real in self.MEASURED.items():
            svg = diagramlib.Canvas("z", 1000, 120, "z").zone(0, 0, 600, 100, title, "start here").svg()
            sub_x = float(re.search(r'<text class="ts" x="([\d.]+)"', svg).group(1))
            self.assertGreaterEqual(sub_x - 18 - real, 16, f"{title}: the subtitle starts too close")


class SampleBuildsTest(unittest.TestCase):
    def test_the_sample_builds_both_diagrams_with_mermaid(self):
        out = tempfile.mkdtemp()
        diagrams = diagramlib.build(render.load_spec(SAMPLE), out)
        self.assertEqual(["data-flow", "build-sequence"], [f["stem"] for f in diagrams])
        for f in diagrams:
            self.assertTrue(os.path.exists(os.path.join(out, f"{f['stem']}.mmd")))


class ThemeChoiceTest(unittest.TestCase):
    def test_one_theme_builds_only_that_themes_svg(self):
        out = tempfile.mkdtemp()
        diagrams = diagramlib.build(render.load_spec(SAMPLE), out, ("dark",))
        self.assertEqual([{"dark"}, {"dark"}], [set(f["files"]) for f in diagrams])
        self.assertEqual(["build-sequence-dark.svg", "data-flow-dark.svg"], sorted(n for n in os.listdir(out) if n.endswith(".svg")))

    def test_an_alt_text_with_a_quote_stops_the_build_before_any_file(self):
        spec = type("Spec", (), {"DIAGRAMS": [{"stem": "q", "alt": 'the "store"', "svg": diagramlib.Canvas("q", 100, 50).svg}]})
        out = tempfile.mkdtemp()
        with self.assertRaisesRegex(diagramlib.DiagramError, "alt text may not hold a quote"):
            diagramlib.build(spec, out)
        self.assertEqual([], os.listdir(out))


class DocFolderTest(unittest.TestCase):
    """A doc's folder gets the pictures the doc shows and nothing else. Every build file stays in .readable-diagrams/ at
    the root of the doc's git project, which ignores everything in it."""

    def setUp(self):
        self.project = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project, ".git"))
        self.build = os.path.join(self.project, ".readable-diagrams")
        self.docs = os.path.join(self.project, "docs")
        os.makedirs(self.docs)
        self.doc = os.path.join(self.docs, "Design Notes.md")
        write(self.doc, "# Design notes\n")
        self.pictures = os.path.join(self.docs, "Design-Notes-diagrams")

    def run_render(self, *args):
        with mock.patch.object(render, "rasterize", fake_png), contextlib.redirect_stdout(io.StringIO()) as said:
            code = render.main(["render.py", *args])
        return code, said.getvalue()

    def spec_in_runtime(self, doc=None):
        code, said = self.run_render("where", doc or self.doc)
        self.assertEqual(0, code, said)
        spec = os.path.join(said.strip(), "spec.py")
        shutil.copy(SAMPLE, spec)
        return spec

    def test_where_makes_the_docs_folder_in_readable_diagrams_at_the_project_root(self):
        code, said = self.run_render("where", self.doc)
        folder = said.strip()
        self.assertEqual(0, code)
        self.assertEqual(os.path.join(self.build, "docs", "Design Notes.md"), folder)
        self.assertTrue(os.path.isdir(folder))
        self.assertEqual(folder, self.run_render("where", self.doc)[1].strip())
        other = os.path.join(self.project, "specs", "Design Notes.md")
        self.assertEqual(os.path.join(self.build, "specs", "Design Notes.md"), render.runtime_folder(other))

    def test_the_project_root_is_the_nearest_folder_with_git(self):
        worktree = os.path.join(self.project, "worktrees", "branch")
        os.makedirs(os.path.join(worktree, "docs"))
        write(os.path.join(worktree, ".git"), "gitdir: elsewhere\n")
        self.assertEqual(worktree, render.project_root(os.path.join(worktree, "docs", "a.md")))
        self.assertEqual(self.project, render.project_root(self.doc))
        loose = tempfile.mkdtemp()
        self.assertEqual(os.path.join(loose, ".readable-diagrams", "a.md"), render.runtime_folder(os.path.join(loose, "a.md")))

    def test_readable_diagrams_ignores_everything_in_it(self):
        self.spec_in_runtime()
        self.assertEqual("*", read(os.path.join(self.build, ".gitignore")).splitlines()[-1])
        self.assertEqual([".git", ".readable-diagrams", "docs"], sorted(os.listdir(self.project)))
        self.assertEqual(["Design Notes.md"], os.listdir(self.docs))

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_git_sees_the_doc_and_its_pictures_and_nothing_else(self):
        project = tempfile.mkdtemp()
        git = ["git", "-c", f"core.excludesFile={os.devnull}"]
        subprocess.run(git + ["init", "-q"], cwd=project, check=True, capture_output=True)
        doc = os.path.join(project, "docs", "design.md")
        os.makedirs(os.path.dirname(doc))
        write(doc, "# Design\n")
        code, said = self.run_render(self.spec_in_runtime(doc), "--doc", doc, "--theme", "light")
        self.assertEqual(0, code, said)
        status = subprocess.run(git + ["status", "--porcelain", "--untracked-files=all"], cwd=project, check=True,
                                capture_output=True, text=True).stdout
        self.assertEqual(["?? docs/design-diagrams/build-sequence.png", "?? docs/design-diagrams/data-flow.png",
                          "?? docs/design.md"], sorted(status.splitlines()))
        self.assertTrue(os.path.isfile(os.path.join(project, ".readable-diagrams", "docs", "design.md", "data-flow.svg")))

    def test_where_refuses_a_doc_in_a_folder_that_is_not_there(self):
        code, said = self.run_render("where", os.path.join(self.project, "typo", "a.md"))
        self.assertEqual(2, code)
        self.assertIn("there is no folder for", said)
        self.assertFalse(os.path.exists(self.build))

    def test_the_doc_folder_gets_its_pictures_and_nothing_else(self):
        spec = self.spec_in_runtime()
        code, said = self.run_render(spec, "--doc", self.doc, "--theme", "light")
        self.assertEqual(0, code, said)
        self.assertEqual(["Design Notes.md", "Design-Notes-diagrams"], sorted(os.listdir(self.docs)))
        self.assertEqual(["build-sequence.png", "data-flow.png"], sorted(os.listdir(self.pictures)))
        kept = sorted(os.listdir(os.path.dirname(spec)))
        self.assertEqual(["build-sequence.mmd", "build-sequence.svg", "data-flow.mmd", "data-flow.svg", "spec.py"], kept)
        self.assertIn("](Design-Notes-diagrams/data-flow.png)", said)
        self.assertNotIn("<picture>", said)

    def test_both_themes_give_a_picture_with_the_dark_source(self):
        code, said = self.run_render(self.spec_in_runtime(), "--doc", self.doc, "--theme", "both")
        self.assertEqual(0, code, said)
        self.assertEqual(4, len(os.listdir(self.pictures)))
        self.assertIn('srcset="Design-Notes-diagrams/data-flow-dark.png"', said)

    def test_a_theme_change_removes_only_this_specs_other_theme(self):
        spec = self.spec_in_runtime()
        self.run_render(spec, "--doc", self.doc, "--theme", "both")
        with open(os.path.join(self.pictures, "other-dark.png"), "wb") as handle:
            handle.write(b"not ours")
        code, said = self.run_render(spec, "--doc", self.doc, "--theme", "light")
        self.assertEqual(0, code, said)
        self.assertEqual(["build-sequence.png", "data-flow.png", "other-dark.png"], sorted(os.listdir(self.pictures)))
        self.assertIn("data-flow-dark.png: " + self.doc + " now shows light only", said)

    def test_a_doc_without_a_theme_stops_and_asks(self):
        code, said = self.run_render(self.spec_in_runtime(), "--doc", self.doc)
        self.assertEqual(2, code)
        self.assertIn("--theme light, --theme dark or --theme both? Ask the user once", said)
        self.assertFalse(os.path.exists(self.pictures))

    def test_a_failed_export_leaves_nothing_next_to_the_doc(self):
        spec = self.spec_in_runtime()
        with mock.patch.object(render, "rasterize", side_effect=FileNotFoundError), \
                mock.patch.object(render, "doctor_report", return_value="(the report)"), \
                contextlib.redirect_stdout(io.StringIO()):
            code = render.main(["render.py", spec, "--doc", self.doc, "--theme", "both"])
        self.assertEqual(1, code)
        self.assertEqual(["Design Notes.md"], os.listdir(self.docs))


class DoctorTest(unittest.TestCase):
    def test_a_missing_rsvg_convert_is_named_with_the_brew_command_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = run_doctor(fake_bin(os.path.join(tmp, "bin"), brew="exit 0"))
        self.assertEqual(1, done.returncode)
        self.assertIn("✗  rsvg-convert not found; it draws each SVG as a PNG", done.stdout)
        self.assertIn("→ brew install librsvg", done.stdout)

    def test_an_installed_rsvg_convert_is_named_with_its_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = run_doctor(fake_bin(os.path.join(tmp, "bin"), **{"rsvg-convert": 'echo "rsvg-convert version 9.8.7"'}))
        self.assertIn("✓  rsvg-convert 9.8.7", done.stdout)
        self.assertNotIn("brew install librsvg", done.stdout)


class RenderShowsTheDoctorTest(unittest.TestCase):
    def test_a_missing_rsvg_convert_prints_the_doctor_report(self):
        with tempfile.TemporaryDirectory() as out, mock.patch.object(render, "rasterize", side_effect=FileNotFoundError), \
                contextlib.redirect_stdout(io.StringIO()) as said:
            code = render.main(["render.py", os.path.join(SCRIPTS, "example_spec.py"), "--out", out])
        self.assertEqual(1, code)
        self.assertIn("rsvg-convert was not found, so the PNG export cannot run. The doctor says:", said.getvalue())
        self.assertIn("readable-diagrams doctor: can this Mac export pictures?", said.getvalue())


class RenderPathsTest(unittest.TestCase):
    def test_a_relative_out_folder_reaches_rsvg_convert_as_given(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs, os.path.isfile(command[-1]), os.path.isdir(os.path.dirname(command[-2]))))
            return subprocess.CompletedProcess(command, 0, "", "")

        start = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with mock.patch.object(render.subprocess, "run", fake_run), contextlib.redirect_stdout(io.StringIO()):
                    code = render.main(["render.py", os.path.join(SCRIPTS, "example_spec.py"), "--out", "out"])
            finally:
                os.chdir(start)
        self.assertEqual(0, code)
        self.assertEqual(6, len(calls))
        for command, kwargs, svg_there, png_folder_there in calls:
            self.assertEqual(["rsvg-convert", "--zoom", "2", "--output"], command[:4])
            self.assertTrue(command[-1].startswith(os.path.join("out", "sync-")) and command[-1].endswith(".svg"))
            self.assertEqual("out", os.path.dirname(command[-2]))
            self.assertTrue(svg_there and png_folder_there, command)
            self.assertNotIn("cwd", kwargs)

    @unittest.skipUnless(shutil.which("rsvg-convert"), "needs rsvg-convert: brew install librsvg")
    def test_rsvg_convert_draws_each_svg_as_an_1840_wide_png(self):
        with tempfile.TemporaryDirectory() as out, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, render.main(["render.py", SAMPLE, "--out", out]))
            pngs = sorted(n for n in os.listdir(out) if n.endswith(".png"))
            self.assertEqual(["build-sequence-dark.png", "build-sequence.png", "data-flow-dark.png", "data-flow.png"], pngs)
            for name in pngs:
                self.assertEqual(1840, png_size(os.path.join(out, name))[0], name)
            light, dark = (read_bytes(os.path.join(out, n)) for n in ("data-flow.png", "data-flow-dark.png"))
        self.assertNotEqual(light, dark)

    def test_an_out_folder_inside_readable_diagrams_gets_the_gitignore_and_others_do_not(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            sample = os.path.join(tmp, ".readable-diagrams", "sample")
            self.assertEqual(0, render.main(["render.py", SAMPLE, "--out", sample, "--no-png"]))
            self.assertEqual("*", read(os.path.join(tmp, ".readable-diagrams", ".gitignore")).splitlines()[-1])
            self.assertEqual(0, render.main(["render.py", SAMPLE, "--out", os.path.join(tmp, "out"), "--no-png"]))
            self.assertFalse(os.path.exists(os.path.join(tmp, "out", ".gitignore")))

    def test_loading_a_spec_leaves_no_python_cache_beside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = os.path.join(tmp, "spec.py")
            shutil.copy(SAMPLE, spec)
            render.load_spec(spec)
            self.assertEqual(["spec.py"], os.listdir(tmp))


class PictureBlockTest(unittest.TestCase):
    def test_both_themes_dark_source_then_light_img_then_closed_mermaid(self):
        block = diagramlib.picture_block("x-y", "Alt text.", "doc-diagrams", "sequenceDiagram\n  A->>B: hi")
        self.assertIn('srcset="doc-diagrams/x-y-dark.png"', block)
        self.assertIn('src="doc-diagrams/x-y.png" alt="Alt text."', block)
        self.assertIn("<details>", block)
        self.assertIn("```mermaid\nsequenceDiagram", block)

    def test_one_theme_is_a_plain_markdown_image_of_that_themes_png(self):
        self.assertEqual("![A \\[b\\] c.](d/x.png)\n", diagramlib.picture_block("x", "A [b] c.", "d", None, ("light",)))
        self.assertEqual("![Alt.](d/x-dark.png)\n", diagramlib.picture_block("x", "Alt.", "d", None, ("dark",)))

    def test_alt_text_may_not_hold_a_quote(self):
        with self.assertRaises(diagramlib.DiagramError):
            diagramlib.picture_block("x", 'say "hi"', "d")


if __name__ == "__main__":
    unittest.main()
