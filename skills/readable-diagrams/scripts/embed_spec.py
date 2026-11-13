"""Embed a diagram's source inside its SVG, and recover it later.

The exact Mermaid source and the authoritative Python source are stored as versioned,
namespace-scoped metadata entries in the final SVG so the diagram remains self-contained.
A metadata payload uses gzip + Base64 plus the SHA-256 of the original UTF-8 bytes.

    python3 -I embed_spec.py embed DIAGRAM.svg SPEC.py [DIAGRAM.mmd]
    python3 -I embed_spec.py extract DIAGRAM.svg [DIR]
"""
import base64
import gzip
import hashlib
import os
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

SVG = "http://www.w3.org/2000/svg"
DS = "https://github.com/DanTanzer/dans-skills"
ET.register_namespace("", SVG)
ET.register_namespace("ds", DS)

MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
USAGE = "usage: embed_spec.py embed DIAGRAM.svg SPEC.py [DIAGRAM.mmd] | embed_spec.py extract DIAGRAM.svg [DIR]"


class SpecError(Exception):
    """A problem to tell the person at the keyboard in plain words."""


class PngError(SpecError):
    """A PNG file that is not valid for legacy metadata extraction."""


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
LEGACY_SPEC_KEYWORD = b"readable-diagrams-spec"
LEGACY_MERMAID_KEYWORD = b"readable-diagrams-mermaid"
LEGACY_KEYWORDS = (LEGACY_SPEC_KEYWORD, LEGACY_MERMAID_KEYWORD)


def read_text(path):
    """A text file's text, with its line endings as they are."""
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def stem_of(svg_path):
    return os.path.splitext(os.path.basename(svg_path))[0]


def spec_name(svg_path):
    return stem_of(svg_path) + ".spec.py"


def mermaid_name(svg_path):
    return stem_of(svg_path) + ".mmd"


def encode_source(source):
    raw = source.encode("utf-8")
    payload = base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii")
    return payload, hashlib.sha256(raw).hexdigest()


def legacy_walk(png):
    if png[:8] != PNG_SIGNATURE:
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


def legacy_keyword_of(kind, body):
    keyword, nul, _ = body.partition(b"\x00")
    return keyword if kind == b"tEXt" and nul == b"\x00" else None


def legacy_texts_in(png, keyword):
    return [
        body.partition(b"\x00")[2].decode("utf-8", errors="latin-1")
        for _, _, kind, body in legacy_walk(png)
        if legacy_keyword_of(kind, body) == keyword
    ]


def legacy_extract(png):
    found = legacy_texts_in(png, LEGACY_SPEC_KEYWORD)
    return found[-1] if found else None


def legacy_extract_mermaid(png):
    found = legacy_texts_in(png, LEGACY_MERMAID_KEYWORD)
    return found[-1] if found else None


def legacy_extract_sources(path):
    with open(path, "rb") as handle:
        png = handle.read()
    try:
        python = legacy_extract(png)
        mermaid = legacy_extract_mermaid(png)
    except PngError as err:
        raise ValueError(f"{path} is not a PNG this can read: {err}") from None
    if python is None:
        raise ValueError(f"{path} holds no readable-diagrams spec")
    result = {"python": python}
    if mermaid is not None:
        result["mermaid"] = mermaid
    return result


def metadata_node(root):
    metadata = root.find(f"{{{SVG}}}metadata")
    if metadata is None:
        metadata = ET.Element(f"{{{SVG}}}metadata")
        root.insert(0, metadata)
    return metadata


def _tag(name):
    return f"{{{DS}}}{name}"


def save_versioned(temp_path, svg_path):
    """Save a complete SVG beside the original without overwriting an existing version."""
    folder, filename = os.path.split(svg_path)
    stem, extension = os.path.splitext(filename)
    version = 1
    while True:
        version_path = os.path.join(folder, f"{stem} ({version}){extension}")
        try:
            fd = os.open(version_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            version += 1
            continue

        target = os.fdopen(fd, "wb")
        try:
            with target:
                with open(temp_path, "rb") as source:
                    shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
        except Exception:
            if os.path.exists(version_path):
                os.remove(version_path)
            raise
        return version_path


def embed_sources(svg_path, mermaid_source, python_source):
    """Write mermaid and python metadata into the SVG at svg_path, replacing prior payloads when present."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    metadata = metadata_node(root)

    for name, source in {"mermaid": mermaid_source, "python": python_source}.items():
        tag = _tag(name)
        matches = [node for node in list(metadata) if node.tag == tag]
        for node in matches[1:]:
            metadata.remove(node)
        if matches:
            metadata.remove(matches[0])
        if source is None:
            continue
        encoded, checksum = encode_source(source)
        elem = ET.SubElement(metadata, tag)
        elem.set("version", "1")
        elem.set("encoding", "gzip+base64")
        elem.set("sha256", checksum)
        elem.text = encoded

    try:
        out = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    except Exception as err:
        raise SpecError(f"cannot write metadata for {svg_path}: {err}") from None

    temp = svg_path + ".embedding"
    try:
        with open(temp, "wb") as handle:
            handle.write(out)
        try:
            os.replace(temp, svg_path)
            saved_path = svg_path
        except OSError as err:
            saved_path = save_versioned(temp, svg_path)
            print(
                f"warning: could not replace {svg_path}: {err}; "
                f"saved updated SVG as {saved_path}",
                file=sys.stderr,
            )
        return saved_path
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def extract_sources(svg_path):
    """Return the embedded Mermaid and Python sources as a dict."""
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError as err:
        raise ValueError(f"{svg_path} is not valid SVG XML: {err}") from None

    metadata = root.find(f"{{{SVG}}}metadata")
    if metadata is None:
        raise ValueError(f"{svg_path} is missing SVG metadata")

    result = {}
    for name in ("mermaid", "python"):
        elem = metadata.find(_tag(name))
        if elem is None:
            raise ValueError(f"Missing {name} source in {svg_path}")
        if elem.get("encoding") != "gzip+base64":
            raise ValueError(f"Unsupported encoding for {name} in {svg_path}")
        if elem.get("version") not in (None, "1"):
            raise ValueError(f"Unsupported version for {name} in {svg_path}")

        text = elem.text or ""
        try:
            blob = base64.b64decode(text, validate=True)
        except Exception as err:
            raise ValueError(f"Malformed base64 data for {name} in {svg_path}: {err}") from None
        if len(blob) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"{name} payload in {svg_path} is too large")
        try:
            raw = gzip.decompress(blob)
        except Exception as err:
            raise ValueError(f"Malformed compressed data for {name} in {svg_path}: {err}") from None
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"{name} payload in {svg_path} is too large after decompression")
        expected = elem.get("sha256")
        actual = hashlib.sha256(raw).hexdigest()
        if expected != actual:
            raise ValueError(f"{name} checksum mismatch in {svg_path}")
        try:
            result[name] = raw.decode("utf-8")
        except UnicodeDecodeError as err:
            raise ValueError(f"{name} payload in {svg_path} is not valid UTF-8: {err}") from None
    return result


def extract(svg_path):
    """Return the Python source embedded in svg_path."""
    return extract_sources(svg_path)["python"]


def extract_mermaid(svg_path):
    """Return the Mermaid source embedded in svg_path, if any."""
    return extract_sources(svg_path).get("mermaid")


def _parse_xml_bytes(data):
    try:
        return ET.fromstring(data)
    except ET.ParseError as err:
        raise ValueError(f"invalid XML: {err}") from None


def embed(data, python, mermaid=None):
    """Backward-compatible helper that accepts SVG XML bytes or legacy PNG bytes."""
    if isinstance(data, (bytes, bytearray)):
        chunk = bytes(data)
        if chunk.startswith(b"<"):
            root = _parse_xml_bytes(chunk)
            metadata = metadata_node(root)
            for name, source in {"mermaid": mermaid, "python": python}.items():
                tag = _tag(name)
                matches = [node for node in list(metadata) if node.tag == tag]
                for node in matches[1:]:
                    metadata.remove(node)
                if matches:
                    metadata.remove(matches[0])
                if source is None:
                    continue
                encoded, checksum = encode_source(source)
                elem = ET.SubElement(metadata, tag)
                elem.set("version", "1")
                elem.set("encoding", "gzip+base64")
                elem.set("sha256", checksum)
                elem.text = encoded
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        raise TypeError("embed() accepts SVG XML bytes or a file path, not raw PNG data in this SVG-only build")
    if isinstance(data, str):
        return embed_file(data, python, mermaid)
    raise TypeError(f"embed() accepts SVG XML/bytes or a path, not {type(data)!r}")


def extract(data):
    """Backward-compatible helper that accepts a path or SVG XML bytes."""
    if isinstance(data, (bytes, bytearray)):
        chunk = bytes(data)
        if chunk.startswith(b"<"):
            return extract_sources_from_root(_parse_xml_bytes(chunk))["python"]
        raise TypeError("extract() accepts SVG XML bytes or a file path, not raw PNG data in this SVG-only build")
    return extract_sources(data)["python"]


def extract_mermaid_data(data):
    if isinstance(data, (bytes, bytearray)):
        chunk = bytes(data)
        if chunk.startswith(b"<"):
            return extract_sources_from_root(_parse_xml_bytes(chunk)).get("mermaid")
        raise TypeError("extract_mermaid() accepts SVG XML bytes or a file path, not raw PNG data in this SVG-only build")
    return extract_sources(data).get("mermaid")


def extract_sources_from_root(root):
    metadata = root.find(f"{{{SVG}}}metadata")
    if metadata is None:
        raise ValueError("Missing SVG metadata")
    result = {}
    for name in ("mermaid", "python"):
        elem = metadata.find(_tag(name))
        if elem is None:
            raise ValueError(f"Missing {name} source")
        if elem.get("encoding") != "gzip+base64":
            raise ValueError(f"Unsupported encoding for {name}")
        if elem.get("version") not in (None, "1"):
            raise ValueError(f"Unsupported version for {name}")
        text = elem.text or ""
        try:
            blob = base64.b64decode(text, validate=True)
        except Exception as err:
            raise ValueError(f"Malformed base64 data for {name}: {err}") from None
        if len(blob) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"{name} payload is too large")
        try:
            raw = gzip.decompress(blob)
        except Exception as err:
            raise ValueError(f"Malformed compressed data for {name}: {err}") from None
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"{name} payload is too large after decompression")
        if elem.get("sha256") != hashlib.sha256(raw).hexdigest():
            raise ValueError(f"{name} checksum mismatch")
        result[name] = raw.decode("utf-8")
    return result


def embed_file(path, python, mermaid=None):
    """Persist python and optional mermaid in an SVG at path, returning True if the file changed."""
    with open(path, "rb") as handle:
        before = handle.read()
    try:
        current = extract_sources(path)
    except ValueError:
        current = {}
    desired_python = python
    desired_mermaid = mermaid
    if current.get("python") == desired_python and current.get("mermaid") == desired_mermaid:
        return False
    saved_path = embed_sources(path, desired_mermaid, desired_python)
    if saved_path != path:
        return True
    with open(path, "rb") as handle:
        after = handle.read()
    return before != after


def extract_to(svg_path, folder="."):
    """Write the extracted source files beside the SVG. Returns [(path, wrote)] for each file."""
    sources = extract_sources(svg_path)
    python = sources["python"]
    files = [(os.path.join(folder, spec_name(svg_path)), python)]
    if "mermaid" in sources:
        files.append((os.path.join(folder, mermaid_name(svg_path)), sources["mermaid"]))
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
        svg, spec, *mmd = args
        try:
            wrote = embed_file(svg, read_text(spec), read_text(mmd[0]) if mmd else None)
        except (OSError, UnicodeDecodeError, SpecError, ValueError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        parts = " and ".join([spec, *mmd])
        print(f"saved {parts} as SVG metadata" if wrote else f"{svg} already holds {parts}; nothing changed")
        return 0
    if command == "extract" and len(args) in (1, 2):
        try:
            found = extract_to(*args)
        except (OSError, UnicodeDecodeError, SpecError, ValueError) as err:
            print(f"embed_spec.py: {why(err)}", file=sys.stderr)
            return 1
        for path, wrote in found:
            print(f"wrote {path}" if wrote else f"{path} already holds that text; nothing changed")
        return 0
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
