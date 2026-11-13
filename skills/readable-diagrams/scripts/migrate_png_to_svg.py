#!/usr/bin/env python3
"""One-time migration helper for older readable-diagrams PNG outputs.

When a directory still contains PNGs from the old workflow, this script looks for the
legacy embedded source metadata, writes the matching .spec.py and .mmd files, then
regenerates the SVG output so the project can move to the SVG-only flow without manual
copy/paste.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import embed_spec  # noqa: E402


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def find_pngs(folder):
    seen = []
    for path in sorted(Path(folder).iterdir()):
        if path.is_file() and path.suffix.lower() == ".png":
            seen.append(path)
    return seen


def write_sources(png_path):
    try:
        payload = embed_spec.legacy_extract_sources(str(png_path))
    except ValueError:
        return None

    stem = png_path.stem
    spec_path = png_path.with_name(f"{stem}.spec.py")
    mmd_path = png_path.with_name(f"{stem}.mmd")
    wrote = False

    if spec_path.exists():
        existing = embed_spec.read_text(str(spec_path))
        if existing != payload["python"]:
            write_text(spec_path, payload["python"])
            wrote = True
    else:
        write_text(spec_path, payload["python"])
        wrote = True

    if "mermaid" in payload:
        if mmd_path.exists():
            existing = embed_spec.read_text(str(mmd_path))
            if existing != payload["mermaid"]:
                write_text(mmd_path, payload["mermaid"])
                wrote = True
        else:
            write_text(mmd_path, payload["mermaid"])
            wrote = True

    return spec_path, wrote


def render_svg(spec_path):
    render_py = HERE / "render.py"
    out_dir = spec_path.parent
    cmd = [sys.executable, "-I", str(render_py), str(spec_path), "--out", str(out_dir)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stdout, file=sys.stderr)
        print(done.stderr, file=sys.stderr)
        raise RuntimeError(f"render.py failed for {spec_path}")
    return done.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pull embedded source out of legacy PNGs and regenerate the SVGs.")
    parser.add_argument("path", nargs="?", default=".", help="Folder to scan for legacy PNGs. Defaults to the current directory.")
    args = parser.parse_args(argv)

    folder = Path(args.path).resolve()
    if not folder.exists():
        raise FileNotFoundError(f"{folder} does not exist")
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory")

    found = False
    for png in find_pngs(folder):
        result = write_sources(png)
        if result is None:
            continue
        spec_path, _ = result
        if not (spec_path.parent / f"{png.stem}.svg").exists():
            render_svg(spec_path)
        found = True

    if not found:
        print(f"no legacy readable-diagrams PNGs found in {folder}")
        return 0
    print(f"migrated legacy PNGs in {folder}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:
        print(f"migrate_png_to_svg.py: {err}", file=sys.stderr)
        raise SystemExit(1)
