"""embed_spec puts a spec into a PNG and gets it back: byte for byte, with every other chunk untouched, a second embed
replacing the first, another tEXt keyword left alone, and a plain message for a file that is not a PNG it can read."""
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
import embed_spec  # noqa: E402
from tests.pngs import chunks_of, png_chunk, tiny_png  # noqa: E402

SKILL = os.path.dirname(SCRIPTS)
SAMPLE_SPEC = os.path.join(SKILL, "sample", "spec.py")
SAMPLE_DIAGRAMS = os.path.join(SKILL, "sample", "diagrams")
MERMAID_PNG = os.path.join(SAMPLE_DIAGRAMS, "data-flow-mermaid.png")
SAMPLE_PICTURES = ("data-flow.png", "data-flow-dark.png", "build-sequence.png", "build-sequence-dark.png")
TOOL = os.path.join(SCRIPTS, "embed_spec.py")
SPEC_KEYWORD = b"readable-diagrams-spec"


def kinds(png):
    return [kind for kind, _ in chunks_of(png)]


class EmbedTest(unittest.TestCase):
    def test_the_text_comes_back_byte_for_byte(self):
        for text in ("x = 1\n", "x = 1", "a\r\nb\r\n", "label = 'ünï → ✓ —'\n"):
            with self.subTest(text=text):
                self.assertEqual(text, embed_spec.extract(embed_spec.embed(tiny_png(), text)))

    def test_the_text_sits_in_a_text_chunk_as_utf8(self):
        text = "a → b\n"
        (body,) = [whole[8:-4] for kind, whole in chunks_of(embed_spec.embed(tiny_png(), text)) if kind == b"tEXt"]
        self.assertEqual(SPEC_KEYWORD + b"\x00" + text.encode("utf-8"), body)

    def test_every_other_chunk_is_untouched_and_the_new_one_sits_just_before_iend(self):
        before = tiny_png()
        after = embed_spec.embed(before, "x = 1\n")
        self.assertEqual([b"IHDR", b"IDAT", b"tEXt", b"IEND"], kinds(after))
        old = chunks_of(before)
        new = chunks_of(after)
        self.assertEqual(old[:-1], new[:-2])
        self.assertEqual(old[-1], new[-1])

    def test_the_new_chunk_has_the_right_crc(self):
        (whole,) = [whole for kind, whole in chunks_of(embed_spec.embed(tiny_png(), "x = 1\n")) if kind == b"tEXt"]
        (stored,) = struct.unpack(">I", whole[-4:])
        self.assertEqual(zlib.crc32(whole[4:-4]), stored)

    def test_a_second_embed_replaces_the_first(self):
        twice = embed_spec.embed(embed_spec.embed(tiny_png(), "first\n"), "second\n")
        self.assertEqual("second\n", embed_spec.extract(twice))
        self.assertEqual(1, kinds(twice).count(b"tEXt"))
        self.assertEqual(embed_spec.embed(tiny_png(), "second\n"), twice)

    def test_embedding_the_same_text_again_changes_nothing(self):
        once = embed_spec.embed(tiny_png(), "x = 1\n")
        self.assertEqual(once, embed_spec.embed(once, "x = 1\n"))

    def test_a_png_that_holds_two_specs_ends_with_one(self):
        old = [png_chunk(b"tEXt", SPEC_KEYWORD + b"\x00" + text) for text in (b"old one\n", b"old two\n")]
        base = tiny_png(*old)
        self.assertEqual("old two\n", embed_spec.extract(base))
        after = embed_spec.embed(base, "new\n")
        self.assertEqual(1, kinds(after).count(b"tEXt"))
        self.assertEqual("new\n", embed_spec.extract(after))

    def test_a_text_chunk_with_another_keyword_stays(self):
        other = png_chunk(b"tEXt", b"Software\x00rsvg-convert")
        base = tiny_png(other)
        self.assertIsNone(embed_spec.extract(base))
        after = embed_spec.embed(base, "x = 1\n")
        self.assertIn((b"tEXt", other), chunks_of(after))
        self.assertEqual("x = 1\n", embed_spec.extract(after))

    def test_a_png_without_a_spec_gives_none(self):
        self.assertIsNone(embed_spec.extract(tiny_png()))

    def test_a_spec_that_a_latin1_tool_wrote_is_read(self):
        legacy = png_chunk(b"tEXt", SPEC_KEYWORD + b"\x00" + "café = 1\n".encode("latin-1"))
        self.assertEqual("café = 1\n", embed_spec.extract(tiny_png(legacy)))

    def test_bytes_that_are_not_a_png_are_refused(self):
        for call in (embed_spec.extract, lambda data: embed_spec.embed(data, "x = 1\n")):
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

    def test_embed_file_changes_the_png_in_place_and_leaves_nothing_beside_it(self):
        with open(self.png, "wb") as handle:
            handle.write(tiny_png())
        embed_spec.embed_file(self.png, "x = 1\n")
        self.assertEqual(["d.png"], os.listdir(self.tmp))
        self.assertEqual("x = 1\n", embed_spec.extract_file(self.png))

    def write_png(self, data):
        with open(self.png, "wb") as handle:
            handle.write(data)

    def test_a_png_that_already_holds_this_spec_is_not_written(self):
        self.write_png(embed_spec.embed(tiny_png(), "x = 1\n"))
        os.utime(self.png, (1_000_000_000, 1_000_000_000))
        with open(self.png, "rb") as handle:
            before = handle.read()
        self.assertFalse(embed_spec.embed_file(self.png, "x = 1\n"))
        self.assertEqual(1_000_000_000, int(os.path.getmtime(self.png)))
        with open(self.png, "rb") as handle:
            self.assertEqual(before, handle.read())

    def test_a_different_spec_takes_the_place_of_the_one_in_the_png(self):
        self.write_png(tiny_png())
        self.assertTrue(embed_spec.embed_file(self.png, "one\n"))
        self.assertTrue(embed_spec.embed_file(self.png, "two\n"))
        self.assertEqual("two\n", embed_spec.extract_file(self.png))
        with open(self.png, "rb") as handle:
            self.assertEqual(1, kinds(handle.read()).count(b"tEXt"))

    def test_a_png_that_holds_this_spec_twice_is_written_to_hold_it_once(self):
        twice = png_chunk(b"tEXt", SPEC_KEYWORD + b"\x00" + b"x = 1\n")
        self.write_png(tiny_png(twice, twice))
        self.assertTrue(embed_spec.embed_file(self.png, "x = 1\n"))
        with open(self.png, "rb") as handle:
            self.assertEqual(1, kinds(handle.read()).count(b"tEXt"))

    def test_a_file_that_is_not_a_png_is_left_as_it_was_and_named(self):
        with open(self.png, "wb") as handle:
            handle.write(b"not a png")
        with self.assertRaisesRegex(embed_spec.PngError, "d.png is not a PNG this can read"):
            embed_spec.embed_file(self.png, "x = 1\n")
        with open(self.png, "rb") as handle:
            self.assertEqual(b"not a png", handle.read())
        self.assertEqual(["d.png"], os.listdir(self.tmp))


class RealPngTest(unittest.TestCase):
    def test_a_real_png_without_a_spec_takes_the_sample_spec_and_keeps_its_pixels(self):
        # Mermaid drew this one, not the skill: a real file from another PNG encoder, with no spec in it.
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "data-flow-mermaid.png")
            shutil.copy(MERMAID_PNG, png)
            spec = embed_spec.read_text(SAMPLE_SPEC)
            with open(png, "rb") as handle:
                before = chunks_of(handle.read())
            self.assertTrue(embed_spec.embed_file(png, spec))
            with open(png, "rb") as handle:
                data = handle.read()
        after = chunks_of(data)
        self.assertEqual(before[:-1], after[:-2])
        self.assertEqual(before[-1], after[-1])
        self.assertEqual(len(before) + 1, len(after))
        self.assertEqual(spec, embed_spec.extract(data))

    def test_the_sample_pictures_carry_the_current_sample_spec(self):
        # Edit sample/spec.py and these fail until the four pictures are drawn again: render.py puts the spec in them.
        spec = embed_spec.read_text(SAMPLE_SPEC)
        for name in SAMPLE_PICTURES:
            with self.subTest(picture=name), open(os.path.join(SAMPLE_DIAGRAMS, name), "rb") as handle:
                self.assertEqual([spec], embed_spec.specs_in(handle.read()))

    def test_embedding_the_spec_a_sample_picture_already_holds_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "data-flow.png")
            shutil.copy(os.path.join(SAMPLE_DIAGRAMS, "data-flow.png"), png)
            with open(png, "rb") as handle:
                before = handle.read()
            self.assertFalse(embed_spec.embed_file(png, embed_spec.read_text(SAMPLE_SPEC)))
            with open(png, "rb") as handle:
                self.assertEqual(before, handle.read())


class ExtractToTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.out)

    def picture(self, name, text=None):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as handle:
            handle.write(tiny_png() if text is None else embed_spec.embed(tiny_png(), text))
        return path

    def test_the_file_is_named_after_the_picture(self):
        self.assertEqual("data-flow.spec.py", embed_spec.spec_name("docs/readable-diagrams/design/data-flow.png"))
        self.assertEqual("data-flow-dark.spec.py", embed_spec.spec_name("data-flow-dark.png"))

    def test_the_spec_is_written_byte_for_byte_to_a_file_named_after_the_picture(self):
        text = "# a \u2192 b\r\nDIAGRAMS = []\n"
        path, wrote = embed_spec.extract_to(self.picture("data-flow.png", text), self.out)
        self.assertEqual((os.path.join(self.out, "data-flow.spec.py"), True), (path, wrote))
        with open(path, "rb") as handle:
            self.assertEqual(text.encode("utf-8"), handle.read())

    def test_two_pictures_in_one_folder_give_two_files(self):
        embed_spec.extract_to(self.picture("a.png", "A = 1\n"), self.out)
        embed_spec.extract_to(self.picture("b.png", "B = 2\n"), self.out)
        self.assertEqual(["a.spec.py", "b.spec.py"], sorted(os.listdir(self.out)))
        self.assertEqual("A = 1\n", embed_spec.read_text(os.path.join(self.out, "a.spec.py")))
        self.assertEqual("B = 2\n", embed_spec.read_text(os.path.join(self.out, "b.spec.py")))

    def test_a_file_that_already_holds_the_spec_is_left_alone(self):
        png = self.picture("a.png", "A = 1\n")
        path, _ = embed_spec.extract_to(png, self.out)
        os.utime(path, (1_000_000_000, 1_000_000_000))
        self.assertEqual((path, False), embed_spec.extract_to(png, self.out))
        self.assertEqual(1_000_000_000, int(os.path.getmtime(path)))

    def test_a_file_that_holds_something_else_stops_the_extract_and_stays_as_it_was(self):
        existing = os.path.join(self.out, "a.spec.py")
        with open(existing, "w", encoding="utf-8") as handle:
            handle.write("my edits\n")
        with self.assertRaisesRegex(embed_spec.SpecError, "already exists and holds something else"):
            embed_spec.extract_to(self.picture("a.png", "A = 1\n"), self.out)
        self.assertEqual("my edits\n", embed_spec.read_text(existing))

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
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.out)
        with open(self.png, "wb") as handle:
            handle.write(tiny_png())

    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, "-I", TOOL, *args], capture_output=True, cwd=cwd)

    def embedded(self, text=b"# a \xe2\x86\x92 b\r\nDIAGRAMS = []\n"):
        with open(self.spec, "wb") as handle:
            handle.write(text)
        done = self.run_tool("embed", self.png, self.spec)
        self.assertEqual(0, done.returncode, done.stderr)
        return text

    def test_embed_then_extract_gives_the_spec_file_back_byte_for_byte_named_after_the_picture(self):
        text = self.embedded()
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(["d.spec.py"], os.listdir(self.out))
        with open(os.path.join(self.out, "d.spec.py"), "rb") as handle:
            self.assertEqual(text, handle.read())

    def test_extract_without_a_folder_writes_into_the_current_folder(self):
        text = self.embedded()
        done = self.run_tool("extract", self.png, cwd=self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        with open(os.path.join(self.out, "d.spec.py"), "rb") as handle:
            self.assertEqual(text, handle.read())

    def test_two_pictures_in_one_folder_never_share_a_spec_file(self):
        self.embedded()
        other = os.path.join(self.tmp, "e.png")
        shutil.copy(self.png, other)
        self.assertEqual(0, self.run_tool("extract", self.png, self.out).returncode)
        self.assertEqual(0, self.run_tool("extract", other, self.out).returncode)
        self.assertEqual(["d.spec.py", "e.spec.py"], sorted(os.listdir(self.out)))

    def test_extracting_twice_says_so_and_a_different_file_in_the_way_stops_it(self):
        self.embedded()
        self.run_tool("extract", self.png, self.out)
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn(b"already holds the spec", done.stdout)
        target = os.path.join(self.out, "d.spec.py")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("my edits\n")
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(1, done.returncode)
        self.assertIn(b"already exists and holds something else", done.stderr)
        self.assertEqual("my edits\n", embed_spec.read_text(target))

    def test_embedding_twice_says_so_and_changes_nothing(self):
        self.embedded()
        with open(self.png, "rb") as handle:
            once = handle.read()
        done = self.run_tool("embed", self.png, self.spec)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn(b"already holds", done.stdout)
        with open(self.png, "rb") as handle:
            self.assertEqual(once, handle.read())

    def test_extract_of_a_png_without_a_spec_says_so_on_stderr_and_writes_nothing(self):
        done = self.run_tool("extract", self.png, self.out)
        self.assertEqual(1, done.returncode)
        self.assertEqual([], os.listdir(self.out))
        self.assertIn(b"holds no readable-diagrams spec", done.stderr)

    def test_embed_into_something_that_is_not_a_png_names_the_file(self):
        with open(self.spec, "w", encoding="utf-8") as handle:
            handle.write("DIAGRAMS = []\n")
        with open(self.png, "wb") as handle:
            handle.write(b"not a png")
        done = self.run_tool("embed", self.png, self.spec)
        self.assertEqual(1, done.returncode)
        self.assertIn(self.png.encode() + b" is not a PNG this can read", done.stderr)

    def test_a_usage_mistake_exits_2(self):
        done = self.run_tool()
        self.assertEqual(2, done.returncode)
        self.assertIn(b"usage:", done.stderr)


if __name__ == "__main__":
    unittest.main()
