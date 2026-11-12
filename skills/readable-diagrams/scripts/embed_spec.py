"""Keep a diagram's spec inside the PNG it drew.

The spec that draws a doc's pictures is a scratch file, so the Python behind a shipped PNG would be lost with it. This
puts the spec's text into the PNG itself, as a PNG tEXt chunk named readable-diagrams-spec: the way image tools carry
their settings. Commit the PNG and its spec comes with it. No pixel changes: one chunk goes in just before IEND, and the
image draws the same before and after.

    python3 -I embed_spec.py embed DIAGRAM.png SPEC.py    put SPEC.py in DIAGRAM.png, in place
    python3 -I embed_spec.py extract DIAGRAM.png [DIR]    write the spec to DIR/DIAGRAM.spec.py (DIR is this folder)

render.py runs embed for every PNG it draws, so a rebuilt picture carries the spec that drew it. Run embed yourself for
a picture drawn before. Run extract to get a spec back: the PNG holds the only copy.

Extract names the file after the picture, data-flow.png to data-flow.spec.py, so pictures that share a folder never
share a spec file. It reads before it writes, like embed: a file that already holds the spec is left alone, and a file
that holds something else stops the extract, so edits in it are never lost.

Embed reads before it writes, and a PNG never holds two specs. A PNG that already holds exactly this spec, once, is not
written at all. One that holds a different spec gets the new one in its place. One that holds two or more ends with one.
Only tEXt chunks named readable-diagrams-spec are read or changed.

The text is stored as UTF-8. The PNG standard says Latin-1 for tEXt; the two agree on plain ASCII, and extract reads
either. Exit 1 with a plain message on stderr when the file is not a PNG this can read, holds no spec, or would
overwrite a different file, 2 for a usage mistake.
"""
import os
import struct
import sys
import zlib

sys.dont_write_bytecode = True

SIGNATURE = b"\x89PNG\r\n\x1a\n"
KEYWORD = b"readable-diagrams-spec"
USAGE = "usage: embed_spec.py embed DIAGRAM.png SPEC.py | embed_spec.py extract DIAGRAM.png [DIR]"


class SpecError(Exception):
    """A problem to tell the person at the keyboard in plain words."""


class PngError(SpecError):
    """The bytes are not a PNG this can work on."""


def read_text(path):
    """A spec file's text, with its line endings as they are."""
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def chunk(kind, body):
    """One PNG chunk: the body's length, the type, the body, and a CRC (cyclic redundancy check) over type and body."""
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def walk(png):
    """The chunks of a PNG up to IEND, each as (start, end, type, body): start and end are the chunk's bytes in png."""
    if png[:8] != SIGNATURE:
        raise PngError("it does not start with the PNG signature")
    chunks, at = [], 8
    while at < len(png):
        if at + 12 > len(png):
            raise PngError("a chunk is cut short")
        (size,) = struct.unpack(">I", png[at:at + 4])
        end = at + 12 + size
        if end > len(png):
            raise PngError("a chunk is cut short")
        kind = png[at + 4:at + 8]
        chunks.append((at, end, kind, png[at + 8:at + 8 + size]))
        if kind == b"IEND":
            return chunks
        at = end
    raise PngError("it has no IEND chunk")


def holds_a_spec(kind, body):
    """True for a tEXt chunk whose keyword is readable-diagrams-spec."""
    keyword, nul, _ = body.partition(b"\x00")
    return kind == b"tEXt" and nul == b"\x00" and keyword == KEYWORD


def embed(png, text):
    """png (bytes) with text as its spec: any spec chunk it held goes, and a new one comes in just before IEND."""
    chunks = walk(png)
    iend_at = chunks[-1][0]
    kept = [png[start:end] for start, end, kind, body in chunks[:-1] if not holds_a_spec(kind, body)]
    return b"".join([SIGNATURE, *kept, chunk(b"tEXt", KEYWORD + b"\x00" + text.encode("utf-8")), png[iend_at:]])


def decode(raw):
    """A spec chunk's text: UTF-8, or Latin-1 when a tool wrote it that way."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def specs_in(png):
    """The text of every spec chunk in png (bytes), in the order they sit."""
    return [decode(body.partition(b"\x00")[2]) for _, _, kind, body in walk(png) if holds_a_spec(kind, body)]


def extract(png):
    """The spec text in png (bytes), or None when it holds none. The last spec chunk wins."""
    found = specs_in(png)
    return found[-1] if found else None


def png_error(path, err):
    return PngError(f"{path} is not a PNG this can read: {err}")


def embed_file(path, text):
    """Put text in the PNG at path, in place, and return True. Read first: a PNG that already holds exactly this spec,
    once, is not written at all, and the answer is False. Otherwise the new file is written beside it and moved over
    it, so a failure leaves the PNG as it was and nothing else behind."""
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        if specs_in(data) == [text]:
            return False
        data = embed(data, text)
    except PngError as err:
        raise png_error(path, err) from None
    temp = path + ".embedding"
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return True


def extract_file(path):
    """The spec text in the PNG at path, or None when it holds none."""
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        return extract(data)
    except PngError as err:
        raise png_error(path, err) from None


def spec_name(png_path):
    """The file a PNG's spec goes to: the PNG's own name with .spec.py, so two pictures never share a file."""
    return os.path.splitext(os.path.basename(png_path))[0] + ".spec.py"


def extract_to(png_path, folder="."):
    """Write the spec in the PNG at png_path to folder/<PNG name>.spec.py. Returns (path, wrote). Read first: a file
    that already holds this spec is left as it is (wrote is False), and a file that holds something else stops the
    extract, so edits in it are never lost."""
    text = extract_file(png_path)
    if text is None:
        raise SpecError(f"{png_path} holds no readable-diagrams spec")
    path = os.path.join(folder, spec_name(png_path))
    if os.path.exists(path):
        if read_text(path) == text:
            return path, False
        raise SpecError(f"{path} already exists and holds something else: move it or delete it, then extract again")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return path, True


def why(err):
    if isinstance(err, OSError):
        return f"{err.filename}: {err.strerror}" if err.filename else str(err)
    return str(err)


def main(argv):
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "embed" and len(args) == 2:
        png, spec = args
        try:
            wrote = embed_file(png, read_text(spec))
        except (OSError, UnicodeDecodeError, SpecError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        print(f"put {spec} into {png}" if wrote else f"{png} already holds {spec}; nothing changed")
        return 0
    if command == "extract" and len(args) in (1, 2):
        try:
            path, wrote = extract_to(*args)
        except (OSError, UnicodeDecodeError, SpecError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        print(f"put the spec of {args[0]} into {path}" if wrote
              else f"{path} already holds the spec of {args[0]}; nothing changed")
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
