"""embed_spec puts a diagram's two parts, its Python spec and its Mermaid text, into a PNG and gets them back: byte for
byte, with every other chunk untouched, each part replaced on its own, a Mermaid part that is left out removed, another
tEXt keyword left alone, and a plain message for a file that is not a PNG it can read."""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
import diagramlib  # noqa: E402
import embed_spec  # noqa: E402
import render  # noqa: E402
from tests.pngs import chunks_of, png_chunk, tiny_png  # noqa: E402

SKILL = os.path.dirname(SCRIPTS)
SAMPLE_SPEC = os.path.join(SKILL, "sample", "spec.py")
SAMPLE_DIAGRAMS = os.path.join(SKILL, "sample", "diagrams")
MERMAID_PNG = os.path.join(SAMPLE_DIAGRAMS, "data-flow-mermaid.png")
SAMPLE_PICTURES = {"data-flow.png": "data-flow", "data-flow-dark.png": "data-flow",
                   "build-sequence.png": "build-sequence", "build-sequence-dark.png": "build-sequence"}
TOOL = os.path.join(SCRIPTS, "embed_spec.py")
SPEC_KEYWORD = b"readable-diagrams-spec"
MERMAID_KEYWORD = b"readable-diagrams-mermaid"


def kinds(png):
    return [kind for kind, _ in chunks_of(png)]


def keywords(png):
    """The keyword of each tEXt chunk, in the order the chunks sit."""
    return [whole[8:-4].partition(b"\x00")[0] for kind, whole in chunks_of(png) if kind == b"tEXt"]


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_bytes(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def sample_mermaids():
    """Each sample diagram's Mermaid text as its .mmd file holds it, by stem: built from sample/spec.py as render.py
    builds it."""
    with tempfile.TemporaryDirectory() as tmp:
        diagrams = diagramlib.build(render.load_spec(SAMPLE_SPEC), tmp)
    return {f["stem"]: diagramlib.mmd_text(f["mermaid"]) for f in diagrams}


class EmbedTest(unittest.TestCase):
    def test_the_spec_comes_back_byte_for_byte(self):
        for text in ("x = 1\n", "x = 1", "a\r\nb\r\n", "label = 'ünï → ✓ —'\n"):
            with self.subTest(text=text):
                self.assertEqual(text, embed_spec.extract(embed_spec.embed(tiny_png(), text)))

    def test_the_mermaid_text_comes_back_byte_for_byte_beside_the_spec(self):
        for mermaid in ("flowchart LR\n  a --> b\n", "a --> b", "x\r\ny\r\n", "A -->|ünï → ✓| B\n"):
            with self.subTest(mermaid=mermaid):
                png = embed_spec.embed(tiny_png(), "x = 1\n", mermaid)
                self.assertEqual(mermaid, embed_spec.extract_mermaid(png))
                self.assertEqual("x = 1\n", embed_spec.extract(png))

    def test_both_parts_sit_in_text_chunks_as_utf8(self):
        python, mermaid = "a → b\n", "A -->|→| B\n"
        bodies = [whole[8:-4] for kind, whole in chunks_of(embed_spec.embed(tiny_png(), python, mermaid))
                  if kind == b"tEXt"]
        self.assertEqual([SPEC_KEYWORD + b"\x00" + python.encode("utf-8"),
                          MERMAID_KEYWORD + b"\x00" + mermaid.encode("utf-8")], bodies)

    def test_every_other_chunk_is_untouched_and_the_new_ones_sit_just_before_iend_python_first(self):
        before = tiny_png()
        after = embed_spec.embed(before, "x = 1\n", "a --> b\n")
        self.assertEqual([b"IHDR", b"IDAT", b"tEXt", b"tEXt", b"IEND"], kinds(after))
        self.assertEqual([SPEC_KEYWORD, MERMAID_KEYWORD], keywords(after))
        old = chunks_of(before)
        new = chunks_of(after)
        self.assertEqual(old[:-1], new[:-3])
        self.assertEqual(old[-1], new[-1])

    def test_each_new_chunk_has_the_right_crc(self):
        wholes = [whole for kind, whole in chunks_of(embed_spec.embed(tiny_png(), "x = 1\n", "a --> b\n"))
                  if kind == b"tEXt"]
        self.assertEqual(2, len(wholes))
        for whole in wholes:
            (stored,) = struct.unpack(">I", whole[-4:])
            self.assertEqual(zlib.crc32(whole[4:-4]), stored)

    def test_a_second_embed_replaces_the_first(self):
        twice = embed_spec.embed(embed_spec.embed(tiny_png(), "first\n", "a\n"), "second\n", "b\n")
        self.assertEqual("second\n", embed_spec.extract(twice))
        self.assertEqual("b\n", embed_spec.extract_mermaid(twice))
        self.assertEqual([SPEC_KEYWORD, MERMAID_KEYWORD], keywords(twice))
        self.assertEqual(embed_spec.embed(tiny_png(), "second\n", "b\n"), twice)

    def test_each_part_is_replaced_on_its_own(self):
        base = embed_spec.embed(tiny_png(), "py one\n", "mmd one\n")
        new_mermaid = embed_spec.embed(base, "py one\n", "mmd two\n")
        new_python = embed_spec.embed(base, "py two\n", "mmd one\n")
        self.assertEqual(("py one\n", "mmd two\n"),
                         (embed_spec.extract(new_mermaid), embed_spec.extract_mermaid(new_mermaid)))
        self.assertEqual(("py two\n", "mmd one\n"),
                         (embed_spec.extract(new_python), embed_spec.extract_mermaid(new_python)))
        for png in (new_mermaid, new_python):
            self.assertEqual([SPEC_KEYWORD, MERMAID_KEYWORD], keywords(png))

    def test_embedding_the_same_parts_again_changes_nothing(self):
        once = embed_spec.embed(tiny_png(), "x = 1\n", "a --> b\n")
        self.assertEqual(once, embed_spec.embed(once, "x = 1\n", "a --> b\n"))

    def test_a_png_with_no_mermaid_text_given_holds_none(self):
        png = embed_spec.embed(tiny_png(), "x = 1\n")
        self.assertEqual([SPEC_KEYWORD], keywords(png))
        self.assertIsNone(embed_spec.extract_mermaid(png))

    def test_a_mermaid_part_the_call_leaves_out_is_removed(self):
        both = embed_spec.embed(tiny_png(), "x = 1\n", "a --> b\n")
        without = embed_spec.embed(both, "x = 1\n")
        self.assertIsNone(embed_spec.extract_mermaid(without))
        self.assertEqual(embed_spec.embed(tiny_png(), "x = 1\n"), without)

    def test_a_png_that_holds_two_specs_ends_with_one(self):
        old = [png_chunk(b"tEXt", SPEC_KEYWORD + b"\x00" + text) for text in (b"old one\n", b"old two\n")]
        base = tiny_png(*old)
        self.assertEqual("old two\n", embed_spec.extract(base))
        after = embed_spec.embed(base, "new\n")
        self.assertEqual([SPEC_KEYWORD], keywords(after))
        self.assertEqual("new\n", embed_spec.extract(after))

    def test_a_png_that_holds_two_mermaid_parts_ends_with_one(self):
        old = [png_chunk(b"tEXt", MERMAID_KEYWORD + b"\x00" + text) for text in (b"old one\n", b"old two\n")]
        base = tiny_png(*old)
        self.assertEqual("old two\n", embed_spec.extract_mermaid(base))
        after = embed_spec.embed(base, "x = 1\n", "new\n")
        self.assertEqual([SPEC_KEYWORD, MERMAID_KEYWORD], keywords(after))
        self.assertEqual("new\n", embed_spec.extract_mermaid(after))

    def test_a_text_chunk_with_another_keyword_stays(self):
        other = png_chunk(b"tEXt", b"Software\x00rsvg-convert")
        base = tiny_png(other)
        self.assertIsNone(embed_spec.extract(base))
        self.assertIsNone(embed_spec.extract_mermaid(base))
        after = embed_spec.embed(base, "x = 1\n", "a --> b\n")
        self.assertIn((b"tEXt", other), chunks_of(after))
        self.assertEqual("x = 1\n", embed_spec.extract(after))

    def test_a_png_without_our_parts_gives_none(self):
        self.assertIsNone(embed_spec.extract(tiny_png()))
        self.assertIsNone(embed_spec.extract_mermaid(tiny_png()))

    def test_a_png_that_holds_only_a_spec_still_reads_and_takes_a_mermaid_part_beside_it(self):
        # What a PNG held before it carried Mermaid text, and what a proof of concept's PNGs hold: one spec chunk.
        base = tiny_png(png_chunk(b"tEXt", SPEC_KEYWORD + b"\x00" + b"spec only\n"))
        self.assertEqual("spec only\n", embed_spec.extract(base))
        self.assertIsNone(embed_spec.extract_mermaid(base))
        after = embed_spec.embed(base, "spec only\n", "a --> b\n")
        self.assertEqual([SPEC_KEYWORD, MERMAID_KEYWORD], keywords(after))
        self.assertEqual(("spec only\n", "a --> b\n"), (embed_spec.extract(after), embed_spec.extract_mermaid(after)))

    def test_a_part_that_a_latin1_tool_wrote_is_read(self):
        for keyword, read in ((SPEC_KEYWORD, embed_spec.extract), (MERMAID_KEYWORD, embed_spec.extract_mermaid)):
            with self.subTest(keyword=keyword):
                legacy = png_chunk(b"tEXt", keyword + b"\x00" + "café = 1\n".encode("latin-1"))
                self.assertEqual("café = 1\n", read(tiny_png(legacy)))

    def test_bytes_that_are_not_a_png_are_refused(self):
        calls = (embed_spec.extract, embed_spec.extract_mermaid, lambda data: embed_spec.embed(data, "x = 1\n"))
        for call in calls:
            with self.assertRaisesRegex(embed_spec.PngError, "PNG signature"):
                call(b"GIF89a" + bytes(40))

    def test_a_png_that_stops_early_is_refused(self):
        with self.assertRaisesRegex(embed_spec.PngError, "no IEND"):
            embed_spec.embed(tiny_png()[:-12], "x = 1\n")
        with self.assertRaisesRegex(embed_spec.PngError, "cut short"):
            embed_spec.embed(tiny_png()[:-5], "x = 1\n")


class FileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.png = os.path.join(self.tmp, "d.png")

    def write_png(self, data):
        write_bytes(self.png, data)

    def parts(self):
        data = read_bytes(self.png)
        return embed_spec.extract(data), embed_spec.extract_mermaid(data), keywords(data)

    def test_embed_file_changes_the_png_in_place_and_leaves_nothing_beside_it(self):
        self.write_png(tiny_png())
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n", "a --> b\n"))
        self.assertEqual(["d.png"], os.listdir(self.tmp))
        self.assertEqual(("x = 1\n", "a --> b\n", [SPEC_KEYWORD, MERMAID_KEYWORD]), self.parts())

    def test_a_png_that_already_holds_these_parts_is_not_written(self):
        for mermaid in ("a --> b\n", None):
            with self.subTest(mermaid=mermaid):
                self.write_png(embed_spec.embed(tiny_png(), "x = 1\n", mermaid))
                os.utime(self.png, (1_000_000_000, 1_000_000_000))
                before = read_bytes(self.png)
                self.assertFalse(embed_spec.embed_file(self.png, "x = 1\n", mermaid))
                self.assertEqual(1_000_000_000, int(os.path.getmtime(self.png)))
                self.assertEqual(before, read_bytes(self.png))

    def test_a_different_spec_takes_the_place_of_the_one_in_the_png_and_the_mermaid_part_stays(self):
        self.write_png(tiny_png())
        self.assertTrue(embed_spec.embed_file(self.png, "one\n", "a --> b\n"))
        self.assertTrue(embed_spec.embed_file(self.png, "two\n", "a --> b\n"))
        self.assertEqual(("two\n", "a --> b\n", [SPEC_KEYWORD, MERMAID_KEYWORD]), self.parts())

    def test_a_different_mermaid_text_takes_the_place_of_the_one_in_the_png_and_the_spec_stays(self):
        self.write_png(tiny_png())
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n", "a --> b\n"))
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n", "a --> c\n"))
        self.assertEqual(("x = 1\n", "a --> c\n", [SPEC_KEYWORD, MERMAID_KEYWORD]), self.parts())

    def test_a_png_that_holds_the_spec_but_not_the_mermaid_text_gets_it(self):
        self.write_png(embed_spec.embed(tiny_png(), "x = 1\n"))
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n", "a --> b\n"))
        self.assertEqual(("x = 1\n", "a --> b\n", [SPEC_KEYWORD, MERMAID_KEYWORD]), self.parts())

    def test_a_stale_mermaid_part_goes_when_the_picture_has_none(self):
        self.write_png(embed_spec.embed(tiny_png(), "x = 1\n", "a --> b\n"))
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n"))
        self.assertEqual(("x = 1\n", None, [SPEC_KEYWORD]), self.parts())

    def test_a_png_that_holds_a_part_twice_is_written_to_hold_it_once(self):
        twice = [png_chunk(b"tEXt", keyword + b"\x00" + text) for keyword, text in
                 ((SPEC_KEYWORD, b"x = 1\n"), (SPEC_KEYWORD, b"x = 1\n"), (MERMAID_KEYWORD, b"a --> b\n"),
                  (MERMAID_KEYWORD, b"a --> b\n"))]
        self.write_png(tiny_png(*twice))
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n", "a --> b\n"))
        self.assertEqual(("x = 1\n", "a --> b\n", [SPEC_KEYWORD, MERMAID_KEYWORD]), self.parts())

    def test_a_file_that_is_not_a_png_is_left_as_it_was_and_named(self):
        write_bytes(self.png, b"not a png")
        with self.assertRaisesRegex(embed_spec.PngError, "d.png is not a PNG this can read"):
            embed_spec.embed_file(self.png, "x = 1\n", "a --> b\n")
        self.assertEqual(b"not a png", read_bytes(self.png))
        self.assertEqual(["d.png"], os.listdir(self.tmp))


class RealPngTest(unittest.TestCase):
    def test_a_real_png_without_our_parts_takes_the_sample_parts_and_keeps_its_pixels(self):
        # Mermaid drew this one, not the skill: a real file from another PNG encoder, with nothing of ours in it.
        spec = embed_spec.read_text(SAMPLE_SPEC)
        mermaid = sample_mermaids()["data-flow"]
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "data-flow-mermaid.png")
            shutil.copy(MERMAID_PNG, png)
            before = chunks_of(read_bytes(png))
            self.assertTrue(embed_spec.embed_file(png, spec, mermaid))
            data = read_bytes(png)
        after = chunks_of(data)
        self.assertEqual(before[:-1], after[:-3])
        self.assertEqual(before[-1], after[-1])
        self.assertEqual(len(before) + 2, len(after))
        self.assertEqual((spec, mermaid), (embed_spec.extract(data), embed_spec.extract_mermaid(data)))

    def test_the_sample_pictures_carry_the_current_sample_spec_and_their_own_mermaid_text(self):
        # Edit sample/spec.py and these fail until the four pictures are drawn again: render.py puts both parts in them.
        spec = embed_spec.read_text(SAMPLE_SPEC)
        mermaids = sample_mermaids()
        for name, stem in SAMPLE_PICTURES.items():
            data = read_bytes(os.path.join(SAMPLE_DIAGRAMS, name))
            with self.subTest(picture=name):
                self.assertEqual([spec], embed_spec.specs_in(data))
                self.assertEqual([mermaids[stem]], embed_spec.mermaids_in(data))

    def test_embedding_the_parts_a_sample_picture_already_holds_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "data-flow.png")
            shutil.copy(os.path.join(SAMPLE_DIAGRAMS, "data-flow.png"), png)
            before = read_bytes(png)
            self.assertFalse(embed_spec.embed_file(png, embed_spec.read_text(SAMPLE_SPEC),
                                                   sample_mermaids()["data-flow"]))
            self.assertEqual(before, read_bytes(png))


class ExtractToTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.out)

    def picture(self, name, text=None, mermaid=None):
        path = os.path.join(self.tmp, name)
        write_bytes(path, tiny_png() if text is None else embed_spec.embed(tiny_png(), text, mermaid))
        return path

    def at(self, name):
        return os.path.join(self.out, name)

    def test_the_files_are_named_after_the_picture(self):
        self.assertEqual("data-flow.spec.py", embed_spec.spec_name("docs/readable-diagrams/design/data-flow.png"))
        self.assertEqual("data-flow-dark.spec.py", embed_spec.spec_name("data-flow-dark.png"))
        self.assertEqual("data-flow.mmd", embed_spec.mermaid_name("docs/readable-diagrams/design/data-flow.png"))
        self.assertEqual("data-flow-dark.mmd", embed_spec.mermaid_name("data-flow-dark.png"))

    def test_a_png_with_a_spec_alone_writes_that_one_file_byte_for_byte(self):
        text = "# a → b\r\nDIAGRAMS = []\n"
        found = embed_spec.extract_to(self.picture("data-flow.png", text), self.out)
        self.assertEqual([(self.at("data-flow.spec.py"), True)], found)
        self.assertEqual(["data-flow.spec.py"], os.listdir(self.out))
        self.assertEqual(text.encode("utf-8"), read_bytes(self.at("data-flow.spec.py")))

    def test_a_png_with_both_parts_writes_both_files_byte_for_byte(self):
        python, mermaid = "# a → b\r\nDIAGRAMS = []\n", "flowchart LR\r\n  a --> b\r\n"
        found = embed_spec.extract_to(self.picture("data-flow.png", python, mermaid), self.out)
        self.assertEqual([(self.at("data-flow.spec.py"), True), (self.at("data-flow.mmd"), True)], found)
        self.assertEqual(python.encode("utf-8"), read_bytes(self.at("data-flow.spec.py")))
        self.assertEqual(mermaid.encode("utf-8"), read_bytes(self.at("data-flow.mmd")))

    def test_pictures_in_one_folder_never_share_a_file(self):
        embed_spec.extract_to(self.picture("a.png", "A = 1\n", "a --> b\n"), self.out)
        embed_spec.extract_to(self.picture("b.png", "B = 2\n"), self.out)
        self.assertEqual(["a.mmd", "a.spec.py", "b.spec.py"], sorted(os.listdir(self.out)))
        self.assertEqual("A = 1\n", embed_spec.read_text(self.at("a.spec.py")))
        self.assertEqual("a --> b\n", embed_spec.read_text(self.at("a.mmd")))
        self.assertEqual("B = 2\n", embed_spec.read_text(self.at("b.spec.py")))

    def test_files_that_already_hold_the_text_are_left_alone(self):
        png = self.picture("a.png", "A = 1\n", "a --> b\n")
        embed_spec.extract_to(png, self.out)
        for name in ("a.spec.py", "a.mmd"):
            os.utime(self.at(name), (1_000_000_000, 1_000_000_000))
        found = embed_spec.extract_to(png, self.out)
        self.assertEqual([(self.at("a.spec.py"), False), (self.at("a.mmd"), False)], found)
        for name in ("a.spec.py", "a.mmd"):
            self.assertEqual(1_000_000_000, int(os.path.getmtime(self.at(name))))

    def test_each_file_is_judged_on_its_own(self):
        png = self.picture("a.png", "A = 1\n", "a --> b\n")
        with open(self.at("a.spec.py"), "w", encoding="utf-8") as handle:
            handle.write("A = 1\n")
        found = embed_spec.extract_to(png, self.out)
        self.assertEqual([(self.at("a.spec.py"), False), (self.at("a.mmd"), True)], found)
        self.assertEqual("a --> b\n", embed_spec.read_text(self.at("a.mmd")))

    def test_a_spec_file_that_holds_something_else_stops_the_extract_and_stays_as_it_was(self):
        with open(self.at("a.spec.py"), "w", encoding="utf-8") as handle:
            handle.write("my edits\n")
        with self.assertRaisesRegex(embed_spec.SpecError, "already exists and holds something else"):
            embed_spec.extract_to(self.picture("a.png", "A = 1\n", "a --> b\n"), self.out)
        self.assertEqual("my edits\n", embed_spec.read_text(self.at("a.spec.py")))
        self.assertEqual(["a.spec.py"], os.listdir(self.out))

    def test_a_mermaid_file_that_holds_something_else_stops_the_extract_before_any_file_is_written(self):
        with open(self.at("a.mmd"), "w", encoding="utf-8") as handle:
            handle.write("my edits\n")
        with self.assertRaisesRegex(embed_spec.SpecError, r"a\.mmd already exists and holds something else"):
            embed_spec.extract_to(self.picture("a.png", "A = 1\n", "a --> b\n"), self.out)
        self.assertEqual("my edits\n", embed_spec.read_text(self.at("a.mmd")))
        self.assertEqual(["a.mmd"], os.listdir(self.out))

    def test_a_picture_without_a_spec_writes_nothing(self):
        with self.assertRaisesRegex(embed_spec.SpecError, "holds no readable-diagrams spec"):
            embed_spec.extract_to(self.picture("x.png"), self.out)
        self.assertEqual([], os.listdir(self.out))


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.png = os.path.join(self.tmp, "d.png")
        self.spec = os.path.join(self.tmp, "design.spec.py")
        self.mmd = os.path.join(self.tmp, "d.mmd")
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.out)
        write_bytes(self.png, tiny_png())

    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, cwd=cwd)

    def embedded(self, python=b"# a \xe2\x86\x92 b\r\nDIAGRAMS = []\n", mermaid=None):
        write_bytes(self.spec, python)
        args = [self.png, self.spec]
        if mermaid is not None:
            write_bytes(self.mmd, mermaid)
            args.append(self.mmd)
        done = self.run_tool("embed", *args)
        self.assertEqual(0, done.returncode, done.stderr)
        return done

    def test_embed_then_extract_gives_the_spec_file_back_byte_for_byte_named_after_the_picture(self):
        python = b"# a \xe2\x86\x92 b\r\nDIAGRAMS = []\n"
        self.embedded(python)
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(["d.spec.py"], os.listdir(self.out))
        self.assertEqual(python, read_bytes(os.path.join(self.out, "d.spec.py")))

    def test_embed_with_a_mermaid_file_then_extract_gives_both_files_back_byte_for_byte(self):
        python, mermaid = b"# a \xe2\x86\x92 b\r\nDIAGRAMS = []\n", b"flowchart LR\r\n  a --> b\r\n"
        done = self.embedded(python, mermaid)
        self.assertIn(b"put " + self.spec.encode() + b" and " + self.mmd.encode() + b" into " + self.png.encode(),
                      done.stdout)
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(["d.mmd", "d.spec.py"], sorted(os.listdir(self.out)))
        self.assertEqual(python, read_bytes(os.path.join(self.out, "d.spec.py")))
        self.assertEqual(mermaid, read_bytes(os.path.join(self.out, "d.mmd")))

    def test_extract_without_a_folder_writes_into_the_current_folder(self):
        self.embedded(mermaid=b"a --> b\n")
        python = read_bytes(self.spec)
        done = self.run_tool("extract", self.png, cwd=self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(["d.mmd", "d.spec.py"], sorted(os.listdir(self.out)))
        self.assertEqual(python, read_bytes(os.path.join(self.out, "d.spec.py")))

    def test_two_pictures_in_one_folder_never_share_a_spec_file(self):
        self.embedded()
        other = os.path.join(self.tmp, "e.png")
        shutil.copy(self.png, other)
        self.assertEqual(0, self.run_tool("extract", self.png, self.out).returncode)
        self.assertEqual(0, self.run_tool("extract", other, self.out).returncode)
        self.assertEqual(["d.spec.py", "e.spec.py"], sorted(os.listdir(self.out)))

    def test_extracting_twice_says_so_and_a_different_file_in_the_way_stops_it(self):
        self.embedded(mermaid=b"a --> b\n")
        self.run_tool("extract", self.png, self.out)
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(2, done.stdout.count(b"already holds that text"))
        target = os.path.join(self.out, "d.mmd")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("my edits\n")
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(1, done.returncode)
        self.assertIn(b"already exists and holds something else", done.stderr)
        self.assertEqual("my edits\n", embed_spec.read_text(target))

    def test_embedding_twice_says_so_and_changes_nothing(self):
        self.embedded(mermaid=b"a --> b\n")
        once = read_bytes(self.png)
        done = self.run_tool("embed", self.png, self.spec, self.mmd)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn(b"already holds", done.stdout)
        self.assertEqual(once, read_bytes(self.png))

    def test_embedding_without_a_mermaid_file_removes_the_mermaid_part_a_picture_held(self):
        self.embedded(mermaid=b"a --> b\n")
        done = self.run_tool("embed", self.png, self.spec)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIsNone(embed_spec.extract_mermaid(read_bytes(self.png)))

    def test_a_mermaid_file_that_is_not_there_is_named_and_the_png_stays_as_it_was(self):
        write_bytes(self.spec, b"DIAGRAMS = []\n")
        before = read_bytes(self.png)
        done = self.run_tool("embed", self.png, self.spec, self.mmd)
        self.assertEqual(1, done.returncode)
        self.assertIn(self.mmd.encode(), done.stderr)
        self.assertEqual(before, read_bytes(self.png))

    def test_extract_of_a_png_without_a_spec_says_so_on_stderr_and_writes_nothing(self):
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(1, done.returncode)
        self.assertEqual([], os.listdir(self.out))
        self.assertIn(b"holds no readable-diagrams spec", done.stderr)

    def test_embed_into_something_that_is_not_a_png_names_the_file(self):
        write_bytes(self.spec, b"DIAGRAMS = []\n")
        write_bytes(self.png, b"not a png")
        done = self.run_tool("embed", self.png, self.spec)
        self.assertEqual(1, done.returncode)
        self.assertIn(self.png.encode() + b" is not a PNG this can read", done.stderr)

    def test_a_usage_mistake_exits_2(self):
        for args in ((), ("embed", self.png), ("extract",)):
            with self.subTest(args=args):
                done = self.run_tool(*args)
                self.assertEqual(2, done.returncode)
                self.assertIn(b"usage:", done.stderr)


if __name__ == "__main__":
    unittest.main()
