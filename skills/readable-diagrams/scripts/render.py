"""Build a diagram spec and emit SVGs with embedded source metadata in one command.

    python3 -I render.py SPEC.py --doc DOC.md [--theme light|dark|both]
    python3 -I render.py SPEC.py --out DIR [--theme light|dark|both]

With --doc, the SVGs that DOC.md shows are written into readable-diagrams/<doc name>/ next to DOC.md,
such as docs/readable-diagrams/design/ for docs/design.md. Then the Markdown for each diagram is printed,
to paste into DOC.md. Each SVG carries both the Python source and the Mermaid text in the final <metadata>
block, and the SVGs are the final artifacts kept for publication.

--theme is light (white) unless it says dark or both. --out DIR is for a build without a doc: every file stays in DIR,
an SVG per diagram and theme plus a .mmd where there is Mermaid. Exit 1 with a plain message when a label does not fit,
2 for a usage mistake.
"""
import importlib.util
import os
import re
import shutil
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
    """Where the SVGs that a doc shows go: readable-diagrams/<doc name>/, next to the doc. Two docs in one folder share
    readable-diagrams/ and each keeps its pictures together in its own subfolder."""
    return os.path.join(os.path.dirname(doc), DIAGRAMS_DIR, doc_name(doc))


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
    """SPEC.py, then --doc DOC.md, --out DIR and --theme THEME, in any order."""
    opts = {"spec": None, "doc": None, "out": None, "theme": DEFAULT_THEME}
    rest = list(args)
    while rest:
        word = rest.pop(0)
        if word in ("--doc", "--out", "--theme"):
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
        return None, "use --doc or --out, not both"
    if opts["doc"] and not has_folder(opts["doc"]):
        return None, f"there is no folder for {opts['doc']}"
    return opts, None


def make_svg_folders(svg_dir):
    """Make svg_dir, and the folder above it when that is not there yet. Returns the folders this call made."""
    made = []
    for folder in (os.path.dirname(svg_dir), svg_dir):
        if folder and not os.path.isdir(folder):
            os.mkdir(folder)
            made.append(folder)
    return made


def embed_diagrams(diagrams, svg_dir, spec_text):
    """Embed each diagram's Python and Mermaid sources into the final SVG files."""
    made = make_svg_folders(svg_dir)
    try:
        for f in diagrams:
            for theme, svg_path in f["files"].items():
                try:
                    embed_spec.embed_file(svg_path, spec_text, diagramlib.mmd_text(f["mermaid"]))
                except (OSError, ValueError, embed_spec.SpecError) as err:
                    print(f"cannot put the spec and the Mermaid text into {svg_path}: {embed_spec.why(err)}")
                    return 1
        return 0
    finally:
        for folder in reversed(made):
            if not os.listdir(folder):
                os.rmdir(folder)


def tidy_folder(diagrams, svg_dir, themes):
    """Remove SVGs for themes this document no longer shows."""
    gone = []
    for f in diagrams:
        for theme, suffix in diagramlib.THEME_SUFFIX.items():
            shown = theme in themes
            path = os.path.join(svg_dir, f"{f['stem']}{suffix}.svg")
            if not shown and os.path.exists(path):
                os.remove(path)
                gone.append((path, theme))
    return gone


def keep_svgs(diagrams, svg_dir):
    """Save each final SVG beside the document, falling back to a numbered copy if replacement fails."""
    os.makedirs(svg_dir, exist_ok=True)
    for f in diagrams:
        for svg in f["files"].values():
            target = os.path.join(svg_dir, os.path.basename(svg))
            fd, temp = tempfile.mkstemp(prefix=".readable-diagram-", suffix=".svg", dir=svg_dir)
            try:
                with os.fdopen(fd, "wb") as output, open(svg, "rb") as source:
                    shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                try:
                    os.replace(temp, target)
                except OSError as err:
                    versioned = embed_spec.save_versioned(temp, target)
                    print(
                        f"warning: could not replace {target}: {err}; "
                        f"saved updated SVG as {versioned}",
                        file=sys.stderr,
                    )
            finally:
                if os.path.exists(temp):
                    os.remove(temp)


def print_blocks(diagrams, doc, themes):
    folder = f"{DIAGRAMS_DIR}/{doc_name(doc)}"
    print(f"\nThe Markdown for {doc}, one block per diagram. Paste each block where its picture goes:")
    for f in diagrams:
        block = diagramlib.picture_block(f["stem"], f["alt"], folder, f["mermaid"], themes)
        print(f"\n{f['stem']}:\n{block}", end="")


def build(opts, work):
    """Build the spec's SVGs in work, embed their source metadata, and print the Markdown."""
    doc, themes = opts["doc"], THEMES[opts["theme"]]
    try:
        diagrams = diagramlib.build(load_spec(opts["spec"]), work, themes)
    except diagramlib.DiagramError as err:
        print(f"diagram error: {err}")
        return 1
    kept = "" if doc else f" in {work}"
    print(f"built {len(diagrams)} diagram(s){kept}: " + ", ".join(f["stem"] for f in diagrams))
    svg_dir = diagrams_folder(doc) if doc else work
    failed = embed_diagrams(diagrams, svg_dir, embed_spec.read_text(opts["spec"]))
    if failed:
        return failed
    words = " and ".join(themes)
    print(f"{len(diagrams) * len(themes)} SVG(s), {words}, in {svg_dir}. Each final artifact embeds its source metadata.")
    if doc:
        try:
            keep_svgs(diagrams, svg_dir)
        except OSError as err:
            print(f"cannot save SVGs in {svg_dir}: {embed_spec.why(err)}")
            return 1
        for path, hidden in tidy_folder(diagrams, svg_dir, themes):
            print(f"removed {path}: {doc} no longer shows {hidden}")
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
