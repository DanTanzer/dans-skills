"""A PNG small enough to build by hand, for the tests that need a file that really is a PNG. Built apart from embed_spec,
so a mistake there cannot hide in the tests' own files."""
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_chunk(kind, body):
    """One chunk: length, type, body, CRC."""
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def tiny_png(*extra):
    """A valid 2 x 2 grey PNG: IHDR, one IDAT, any extra chunks given as bytes, then IEND."""
    header = struct.pack(">IIBBBBB", 2, 2, 8, 0, 0, 0, 0)
    pixels = zlib.compress(b"\x00\x10\x20" + b"\x00\x30\x40")
    return SIGNATURE + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", pixels) + b"".join(extra) + png_chunk(b"IEND", b"")


def chunks_of(png):
    """[(type, the whole chunk's bytes)] in order, by plain parsing."""
    found, at = [], 8
    while at < len(png):
        (size,) = struct.unpack(">I", png[at:at + 4])
        found.append((png[at + 4:at + 8], png[at:at + 12 + size]))
        at += 12 + size
    return found
