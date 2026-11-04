"""Build a figure spec and draw its PNGs, in one command.

    python3 -I render.py where DOC.md
    python3 -I render.py SPEC.py --doc DOC.md --theme light|dark|both [--no-png]
    python3 -I render.py SPEC.py --out DIR [--theme light|dark|both] [--no-png]

where prints DOC.md's runtime folder, and makes it. Runtime folders live in this skill's runtime/ folder, which git
ignores. DOC.md's spec goes in its runtime folder, as spec.py.

With --doc, every build file goes in DOC.md's runtime folder: an SVG per figure and theme, and a .mmd where there is
Mermaid. rsvg-convert draws only the PNGs that DOC.md shows, into <doc name>-diagrams/ next to DOC.md. Then the
Markdown for each figure is printed, to paste into DOC.md. --theme is required with --doc, because only the user knows
which pictures the doc should show.

With --out instead, everything goes in DIR, in both themes unless --theme says otherwise. --no-png stops after the
SVGs, for a quick check. Exit 1 with a plain message when a label does not fit or the export fails, 2 for a usage
mistake.
"""
import hashlib
import importlib.util
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True  # loading a spec leaves no __pycache__ folder beside it, or beside figlib

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(os.path.dirname(HERE), "runtime")
sys.path.insert(0, HERE)
import figlib  # noqa: E402

THEMES = {"light": ("light",), "dark": ("dark",), "both": figlib.BOTH}


def doc_name(doc):
    """The doc's file name without its extension. Anything but letters, digits, dots, underscores and hyphens becomes a
    hyphen, so a folder named after the doc works in a Markdown link."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.splitext(os.path.basename(doc))[0]).strip("-.")
    return name or "doc"


def runtime_folder(doc):
    """The doc's own folder in runtime/: its name, then 8 characters of a hash of its full path, so two docs with the
    same name in different folders never share a spec."""
    digest = hashlib.sha1(os.path.realpath(doc).encode("utf-8")).hexdigest()[:8]
    return os.path.join(RUNTIME, f"{doc_name(doc)}-{digest}")


def diagrams_folder(doc):
    """Where the PNGs that a doc shows go: <doc name>-diagrams, next to the doc."""
    return os.path.join(os.path.dirname(doc), f"{doc_name(doc)}-diagrams")


def make_folder(path):
    """Make path. Inside runtime/, also make sure runtime/ ignores itself, so it stays out of git even when this
    skill's own .gitignore was not copied with the skill."""
    os.makedirs(path, exist_ok=True)
    runtime = os.path.realpath(RUNTIME)
    if os.path.commonpath([os.path.realpath(path), runtime]) == runtime:
        ignore = os.path.join(RUNTIME, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="utf-8") as handle:
                handle.write("# render.py makes everything in this folder. None of it belongs in git.\n*\n")


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
    print(f"cannot make {folder}: {err.strerror or err}. Ask the user where the build files may go, and pass that "
          "folder as --out.")
    return 1


def load_spec(path):
    spec = importlib.util.spec_from_file_location("figure_spec", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(module)
    return module


def parse(args):
    """SPEC.py, then --doc DOC.md, --out DIR, --theme THEME and --no-png, in any order. Returns (options, None), or
    (None, what is wrong)."""
    opts = {"spec": None, "doc": None, "out": None, "theme": None, "png": True}
    rest = list(args)
    while rest:
        word = rest.pop(0)
        if word == "--no-png":
            opts["png"] = False
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
    if opts["theme"] is not None and opts["theme"] not in THEMES:
        return None, f"--theme is light, dark or both, not {opts['theme']!r}"
    if opts["doc"] and not opts["theme"]:
        return None, (f"which pictures should {opts['doc']} show: --theme light, --theme dark or --theme both? "
                      "Ask the user once, then run this again with the answer.")
    if not opts["doc"] and not opts["out"]:
        return None, "say where the files go: --doc DOC.md, or --out DIR"
    if opts["doc"] and not os.path.isdir(os.path.dirname(os.path.abspath(opts["doc"]))):
        return None, f"there is no folder for {opts['doc']}"
    return opts, None


def where(args):
    """render.py where DOC.md: print DOC.md's runtime folder, and make it."""
    if len(args) != 1:
        print("usage: render.py where DOC.md")
        return 2
    folder = runtime_folder(args[0])
    try:
        make_folder(folder)
    except OSError as err:
        return cannot_make(folder, err)
    print(folder)
    return 0


def draw_pngs(figures, png_dir):
    """rsvg-convert draws each figure's SVGs as PNGs in png_dir. When this call made png_dir and the export fails
    before a PNG is in it, the empty folder goes again, so a failed export leaves nothing next to the doc."""
    made = not os.path.isdir(png_dir)
    os.makedirs(png_dir, exist_ok=True)
    try:
        for f in figures:
            for theme, svg in f["files"].items():
                png = os.path.join(png_dir, f"{f['stem']}{figlib.THEME_SUFFIX[theme]}.png")
                try:
                    done = rasterize(svg, png)
                except FileNotFoundError:
                    return stop_with_doctor("rsvg-convert was not found, so the PNG export cannot run.")
                if done.returncode != 0:
                    print(f"rsvg-convert could not draw {svg}:\n{done.stderr.strip()[-2000:]}")
                    return 1
        return 0
    finally:
        if made and not os.listdir(png_dir):
            os.rmdir(png_dir)


def drop_other_theme(figures, png_dir, themes):
    """After a theme change, remove this spec's PNGs in the theme the doc no longer shows. Returns their paths."""
    gone = []
    for f in figures:
        for theme, suffix in figlib.THEME_SUFFIX.items():
            path = os.path.join(png_dir, f"{f['stem']}{suffix}.png")
            if theme not in themes and os.path.exists(path):
                os.remove(path)
                gone.append(path)
    return gone


def print_blocks(figures, doc, png_dir, themes):
    folder = os.path.basename(png_dir)
    print(f"\nThe Markdown for {doc}, one block per figure. Paste each block where its picture goes:")
    for f in figures:
        block = figlib.picture_block(f["stem"], f["alt"], folder, f["mermaid"], themes)
        print(f"\n{f['stem']}:\n{block}", end="")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[1] == "where":
        return where(argv[2:])
    opts, mistake = parse(argv[1:])
    if mistake:
        print(f"render.py: {mistake}")
        return 2
    doc, themes = opts["doc"], THEMES[opts["theme"] or "both"]
    out = opts["out"] or runtime_folder(doc)
    try:
        make_folder(out)
    except OSError as err:
        return cannot_make(out, err)
    try:
        figures = figlib.build(load_spec(opts["spec"]), out, themes)
    except figlib.FigureError as err:
        print(f"figure error: {err}")
        return 1
    print(f"built {len(figures)} figure(s) in {out}: " + ", ".join(f["stem"] for f in figures))
    if not opts["png"]:
        return 0
    png_dir = diagrams_folder(doc) if doc else out
    failed = draw_pngs(figures, png_dir)
    if failed:
        return failed
    words = " and ".join(themes)
    print(f"{len(figures) * len(themes)} PNG(s), {words}, in {png_dir}. Look at each one once before you ship it.")
    if doc:
        for path in drop_other_theme(figures, png_dir, themes):
            print(f"removed {path}: {doc} now shows {words} only")
        print_blocks(figures, doc, png_dir, themes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
