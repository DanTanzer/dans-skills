"""Build a diagram spec and draw its PNGs, in one command.

    python3 -I render.py SPEC.py --doc DOC.md [--theme light|dark|both] [--keep-svg] [--no-png]
    python3 -I render.py SPEC.py --out DIR [--theme light|dark|both] [--no-png]

With --doc, rsvg-convert draws the PNGs that DOC.md shows into readable-diagrams/<doc name>/ next to DOC.md, such as
docs/readable-diagrams/design/ for docs/design.md. Then the Markdown for each diagram is printed, to paste into DOC.md.
The spec and the picture's Mermaid text go inside every PNG (embed_spec.py), and the PNGs are all that is kept: the SVGs
and the .mmd files are built in a temporary folder that goes when the command ends. Both come back out of any PNG with
embed_spec.py extract. --keep-svg, off unless given, also keeps each SVG beside its PNG, and a build without it removes
the SVGs an earlier build kept, so a kept SVG never goes stale.

--theme is light (white) unless it says dark or both. --out DIR is for a build without a doc: every file stays in DIR,
an SVG per diagram and theme, a .mmd where there is Mermaid, and the PNGs. --no-png stops after the SVGs, for a quick
check of the text widths, and keeps nothing. Exit 1 with a plain message when a label does not fit or the export
fails, 2 for a usage mistake.
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # loading a spec leaves no __pycache__ folder beside it, or beside diagramlib

HERE = os.path.dirname(os.path.abspath(__file__))
DIAGRAMS_DIR = "readable-diagrams"
DEFAULT_THEME = "light"
sys.path.insert(0, HERE)
import diagramlib  # noqa: E402
import embed_spec  # noqa: E402

THEMES = {"light": ("light",), "dark": ("dark",), "both": diagramlib.BOTH}


def doc_name(doc):
    """The doc's file name without its extension. Anything but letters, digits, dots, underscores and hyphens becomes a
    hyphen, so a folder named after the doc works in a Markdown link."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.splitext(os.path.basename(doc))[0]).strip("-.")
    return name or "doc"


def has_folder(doc):
    return os.path.isdir(os.path.dirname(os.path.abspath(doc)))


def diagrams_folder(doc):
    """Where the PNGs that a doc shows go: readable-diagrams/<doc name>/, next to the doc. Two docs in one folder share
    readable-diagrams/ and each keeps its pictures together in its own subfolder."""
    return os.path.join(os.path.dirname(doc), DIAGRAMS_DIR, doc_name(doc))


def rasterize(svg, png):
    """rsvg-convert draws one SVG as a PNG at twice its size, so a 920-unit card becomes 1840 pixels wide."""
    return subprocess.run(["rsvg-convert", "--zoom", "2", "--output", png, svg], capture_output=True, text=True)


def doctor_report():
    """doctor.sh: the same report it prints when run on its own."""
    try:
        done = subprocess.run(["bash", os.path.join(HERE, "doctor.sh")], capture_output=True, text=True)
    except OSError as err:
        return f"the doctor could not run: {err}"
    return done.stdout.rstrip()


def stop_with_doctor(reason):
    print(f"{reason} The doctor says:\n")
    print(doctor_report())
    return 1


def cannot_make(folder, err):
    print(f"cannot make {folder}: {err.strerror or err}.")
    return 1


def load_spec(path):
    spec = importlib.util.spec_from_file_location("diagram_spec", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(module)
    return module


def parse(args):
    """SPEC.py, then --doc DOC.md, --out DIR, --theme THEME, --keep-svg and --no-png, in any order. Returns
    (options, None), or (None, what is wrong)."""
    opts = {"spec": None, "doc": None, "out": None, "theme": DEFAULT_THEME, "png": True, "keep_svg": False}
    rest = list(args)
    while rest:
        word = rest.pop(0)
        if word == "--no-png":
            opts["png"] = False
        elif word == "--keep-svg":
            opts["keep_svg"] = True
        elif word in ("--doc", "--out", "--theme"):
            if not rest:
                return None, f"{word} needs a value"
            opts[word[2:]] = rest.pop(0)
        elif word.startswith("-") or opts["spec"]:
            return None, f"unexpected {word!r}"
        else:
            opts["spec"] = word
    if not opts["spec"]:
        return None, "name the spec first: render.py SPEC.py ..."
    if opts["theme"] not in THEMES:
        return None, f"--theme is light, dark or both, not {opts['theme']!r}"
    if not opts["doc"] and not opts["out"]:
        return None, "say where the files go: --doc DOC.md, or --out DIR"
    if opts["doc"] and opts["out"]:
        return None, "use --doc or --out, not both: --keep-svg keeps each SVG beside the doc's pictures"
    if opts["doc"] and not has_folder(opts["doc"]):
        return None, f"there is no folder for {opts['doc']}"
    return opts, None


def make_png_folders(png_dir):
    """Make png_dir, and the folder above it when that is not there yet. Returns the folders this call made."""
    made = []
    for folder in (os.path.dirname(png_dir), png_dir):
        if folder and not os.path.isdir(folder):
            os.mkdir(folder)
            made.append(folder)
    return made


def draw_pngs(diagrams, png_dir, spec_text):
    """rsvg-convert draws each diagram's SVGs as PNGs in png_dir, and each PNG takes spec_text as its spec and its own
    diagram's Mermaid text, when it has any. A folder this call made goes again when the export fails before a PNG is
    in it, so a failed export leaves nothing next to the doc."""
    made = make_png_folders(png_dir)
    try:
        for f in diagrams:
            for theme, svg in f["files"].items():
                png = os.path.join(png_dir, f"{f['stem']}{diagramlib.THEME_SUFFIX[theme]}.png")
                try:
                    done = rasterize(svg, png)
                except FileNotFoundError:
                    return stop_with_doctor("rsvg-convert was not found, so the PNG export cannot run.")
                if done.returncode != 0:
                    print(f"rsvg-convert could not draw {svg}:\n{done.stderr.strip()[-2000:]}")
                    return 1
                try:
                    embed_spec.embed_file(png, spec_text, diagramlib.mmd_text(f["mermaid"]))
                except (OSError, embed_spec.PngError) as err:
                    print(f"cannot put the spec and the Mermaid text into the PNG: {embed_spec.why(err)}")
                    return 1
        return 0
    finally:
        for folder in reversed(made):
            if not os.listdir(folder):
                os.rmdir(folder)


def tidy_folder(diagrams, png_dir, themes, keep_svg):
    """Leave png_dir holding what this build chose. This spec's PNGs and SVGs in a theme the doc no longer shows go, and
    so do its SVGs in a theme the doc shows when keep_svg is off. Returns (path, why) for each file removed."""
    gone = []
    for f in diagrams:
        for theme, suffix in diagramlib.THEME_SUFFIX.items():
            shown = theme in themes
            for ext, keep in (("png", shown), ("svg", shown and keep_svg)):
                path = os.path.join(png_dir, f"{f['stem']}{suffix}.{ext}")
                if not keep and os.path.exists(path):
                    os.remove(path)
                    gone.append((path, None if shown else theme))
    return gone


def keep_svgs(diagrams, png_dir):
    """Copy each SVG from the build folder to png_dir, beside its PNG, under the same name."""
    for f in diagrams:
        for svg in f["files"].values():
            shutil.copyfile(svg, os.path.join(png_dir, os.path.basename(svg)))


def print_blocks(diagrams, doc, themes):
    folder = f"{DIAGRAMS_DIR}/{doc_name(doc)}"
    print(f"\nThe Markdown for {doc}, one block per diagram. Paste each block where its picture goes:")
    for f in diagrams:
        block = diagramlib.picture_block(f["stem"], f["alt"], folder, f["mermaid"], themes)
        print(f"\n{f['stem']}:\n{block}", end="")


def build(opts, work):
    """Build the spec's SVGs in work, then draw the PNGs, put the spec and the Mermaid text in each, and print the
    Markdown."""
    doc, themes = opts["doc"], THEMES[opts["theme"]]
    try:
        diagrams = diagramlib.build(load_spec(opts["spec"]), work, themes)
    except diagramlib.DiagramError as err:
        print(f"diagram error: {err}")
        return 1
    kept = "" if doc else f" in {work}"
    print(f"built {len(diagrams)} diagram(s){kept}: " + ", ".join(f["stem"] for f in diagrams))
    if not opts["png"]:
        return 0
    png_dir = diagrams_folder(doc) if doc else work
    failed = draw_pngs(diagrams, png_dir, embed_spec.read_text(opts["spec"]))
    if failed:
        return failed
    words = " and ".join(themes)
    print(f"{len(diagrams) * len(themes)} PNG(s), {words}, in {png_dir}. Look at each one once before you ship it.")
    if doc:
        if opts["keep_svg"]:
            keep_svgs(diagrams, png_dir)
        for path, hidden in tidy_folder(diagrams, png_dir, themes, opts["keep_svg"]):
            print(f"removed {path}: " + (f"{doc} now shows {words} only" if hidden else "--keep-svg is off"))
        print_blocks(diagrams, doc, themes)
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    opts, mistake = parse(argv[1:])
    if mistake:
        print(f"render.py: {mistake}")
        return 2
    doc = opts["doc"]
    if doc:
        work = tempfile.mkdtemp(prefix="readable-diagrams-")
    else:
        work = opts["out"]
        try:
            os.makedirs(work, exist_ok=True)
        except OSError as err:
            return cannot_make(work, err)
    try:
        return build(opts, work)
    finally:
        if doc:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
