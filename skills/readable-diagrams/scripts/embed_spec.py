"""Keep a diagram's source inside the PNG it drew: the Python that drew it, and its Mermaid text.

The spec that draws a doc's pictures is a scratch file, so the Python behind a shipped PNG would be lost with it. This
puts two parts into the PNG itself, as PNG tEXt chunks, the way image tools carry their settings: the spec's Python
(chunk readable-diagrams-spec) and the Mermaid text of that picture (chunk readable-diagrams-mermaid, only for a picture
that has Mermaid text). The image is the whole wrapper: it alone gives back the editable text and the code that drew
it. Commit the PNG and both come with it. No pixel changes: the chunks go in just before IEND, the Python first, and
the image draws the same before and after.

    python3 -I embed_spec.py embed DIAGRAM.png SPEC.py [DIAGRAM.mmd]   put the parts in DIAGRAM.png, in place
    python3 -I embed_spec.py extract DIAGRAM.png [DIR]                 write DIAGRAM.spec.py, and DIAGRAM.mmd when the
                                                                       PNG holds Mermaid, to DIR (this folder if none)

render.py runs embed for every PNG it draws, so a rebuilt picture carries the spec that drew it and its own Mermaid
text. Run embed yourself for a picture drawn before. Run extract to get the parts back: the PNG holds the only copy.

Extract names each file after the picture, data-flow.png to data-flow.spec.py and data-flow.mmd, so pictures that share
a folder never share a file. It reads before it writes, like embed: a file that already holds the text is left alone,
and a file that holds something else stops the extract before any file is written, so edits in it are never lost.

Embed reads before it writes, and a PNG never holds two of one part. A PNG that already holds exactly these parts, once
each, is not written at all. A part that differs is replaced. A Mermaid part that the call leaves out is removed, so the
two parts always belong together. One that holds two or more of a part ends with one. Only tEXt chunks named
readable-diagrams-spec or readable-diagrams-mermaid are read or changed.

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
SPEC_KEYWORD = b"readable-diagrams-spec"
MERMAID_KEYWORD = b"readable-diagrams-mermaid"
KEYWORDS = (SPEC_KEYWORD, MERMAID_KEYWORD)
USAGE = "usage: embed_spec.py embed DIAGRAM.png SPEC.py [DIAGRAM.mmd] | embed_spec.py extract DIAGRAM.png [DIR]"


class SpecError(Exception):
    """A problem to tell the person at the keyboard in plain words."""


class PngError(SpecError):
    """The bytes are not a PNG this can work on."""


def read_text(path):
    """A text file's text, with its line endings as they are."""
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


def keyword_of(kind, body):
    """The keyword of a tEXt chunk, or None for any other chunk."""
    keyword, nul, _ = body.partition(b"\x00")
    return keyword if kind == b"tEXt" and nul == b"\x00" else None


def text_chunk(keyword, text):
    """A tEXt chunk: the keyword, a NUL, then the text as UTF-8."""
    return chunk(b"tEXt", keyword + b"\x00" + text.encode("utf-8"))


def embed(png, python, mermaid=None):
    """png (bytes) with python as its spec and mermaid as its Mermaid text. Every chunk of ours it held goes, and the
    new ones come in just before IEND, the Python first. mermaid None leaves the PNG with no Mermaid part."""
    chunks = walk(png)
    iend_at = chunks[-1][0]
    kept = [png[start:end] for start, end, kind, body in chunks[:-1] if keyword_of(kind, body) not in KEYWORDS]
    ours = [text_chunk(SPEC_KEYWORD, python)]
    if mermaid is not None:
        ours.append(text_chunk(MERMAID_KEYWORD, mermaid))
    return b"".join([SIGNATURE, *kept, *ours, png[iend_at:]])


def decode(raw):
    """A part's text: UTF-8, or Latin-1 when a tool wrote it that way."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def texts_in(png, keyword):
    """The text of every tEXt chunk named keyword in png (bytes), in the order they sit."""
    return [decode(body.partition(b"\x00")[2]) for _, _, kind, body in walk(png) if keyword_of(kind, body) == keyword]


def specs_in(png):
    return texts_in(png, SPEC_KEYWORD)


def mermaids_in(png):
    return texts_in(png, MERMAID_KEYWORD)


def extract(png):
    """The spec text in png (bytes), or None when it holds none. The last spec chunk wins."""
    found = specs_in(png)
    return found[-1] if found else None


def extract_mermaid(png):
    """The Mermaid text in png (bytes), or None when it holds none. The last Mermaid chunk wins."""
    found = mermaids_in(png)
    return found[-1] if found else None


def png_error(path, err):
    return PngError(f"{path} is not a PNG this can read: {err}")


def read_png(path):
    """The bytes of the PNG at path, once they are known to be a PNG this can read."""
    with open(path, "rb") as handle:
        data = handle.read()
    try:
        walk(data)
    except PngError as err:
        raise png_error(path, err) from None
    return data


def embed_file(path, python, mermaid=None):
    """Put python, and mermaid when given, in the PNG at path, in place, and return True. Read first: a PNG that already
    holds exactly these parts, once each, is not written at all, and the answer is False. Otherwise the new file is
    written beside it and moved over it, so a failure leaves the PNG as it was and nothing else behind."""
    data = read_png(path)
    if specs_in(data) == [python] and mermaids_in(data) == ([] if mermaid is None else [mermaid]):
        return False
    data = embed(data, python, mermaid)
    temp = path + ".embedding"
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return True


def stem_of(png_path):
    return os.path.splitext(os.path.basename(png_path))[0]


def spec_name(png_path):
    """The file a PNG's spec goes to: the PNG's own name with .spec.py, so two pictures never share a file."""
    return stem_of(png_path) + ".spec.py"


def mermaid_name(png_path):
    """The file a PNG's Mermaid text goes to: the PNG's own name with .mmd."""
    return stem_of(png_path) + ".mmd"


def extract_to(png_path, folder="."):
    """Write what the PNG at png_path holds into folder: its spec to <PNG name>.spec.py and, when it holds Mermaid text,
    that to <PNG name>.mmd. Returns [(path, wrote)], one for each file. Read first, file by file: a file that already
    holds the text is left as it is (wrote is False). A file that holds something else stops the extract before any
    file is written, so edits in it are never lost."""
    data = read_png(png_path)
    python, mermaid = extract(data), extract_mermaid(data)
    if python is None:
        raise SpecError(f"{png_path} holds no readable-diagrams spec")
    files = [(os.path.join(folder, spec_name(png_path)), python)]
    if mermaid is not None:
        files.append((os.path.join(folder, mermaid_name(png_path)), mermaid))
    for path, text in files:
        if os.path.exists(path) and read_text(path) != text:
            raise SpecError(f"{path} already exists and holds something else: move it or delete it, then extract again")
    found = []
    for path, text in files:
        wrote = not os.path.exists(path)
        if wrote:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
        found.append((path, wrote))
    return found


def why(err):
    if isinstance(err, OSError):
        return f"{err.filename}: {err.strerror}" if err.filename else str(err)
    return str(err)


def main(argv):
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "embed" and len(args) in (2, 3):
        png, spec, *mmd = args
        try:
            wrote = embed_file(png, read_text(spec), read_text(mmd[0]) if mmd else None)
        except (OSError, UnicodeDecodeError, SpecError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        parts = " and ".join([spec, *mmd])
        print(f"put {parts} into {png}" if wrote else f"{png} already holds {parts}; nothing changed")
        return 0
    if command == "extract" and len(args) in (1, 2):
        try:
            found = extract_to(*args)
        except (OSError, UnicodeDecodeError, SpecError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        for path, wrote in found:
            print(f"wrote {path}" if wrote else f"{path} already holds that text; nothing changed")
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
