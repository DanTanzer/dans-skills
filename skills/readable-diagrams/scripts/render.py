"""Build a figure spec and export every figure as light and dark PNGs, in one command.

    python3 -I render.py SPEC.py OUT_DIR [--no-png]

SPEC.py is a Python file that defines FIGURES (see example_spec.py). OUT_DIR gets two SVGs per figure, <stem>.svg and
<stem>-dark.svg, each complete on its own, a .mmd where there is Mermaid, and figures/<stem>.png plus
figures/<stem>-dark.png, drawn from those SVGs by rsvg-convert. --no-png stops after the SVGs, for a quick check.
Exit 1 with a plain message when a label does not fit or the export fails.
"""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figlib  # noqa: E402


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


def load_spec(path):
    spec = importlib.util.spec_from_file_location("figure_spec", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(module)
    return module


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    spec_path, out_dir = argv[1], argv[2]
    want_png = "--no-png" not in argv
    try:
        figures = figlib.build(load_spec(spec_path), out_dir)
    except figlib.FigureError as err:
        print(f"figure error: {err}")
        return 1
    print(f"built {len(figures)} figure(s) in {out_dir}: " + ", ".join(f["stem"] for f in figures))
    if not want_png:
        return 0
    png_dir = os.path.join(out_dir, "figures")
    os.makedirs(png_dir, exist_ok=True)
    for f in figures:
        for svg in f["files"].values():
            png = os.path.join(png_dir, os.path.splitext(os.path.basename(svg))[0] + ".png")
            try:
                done = rasterize(svg, png)
            except FileNotFoundError:
                return stop_with_doctor("rsvg-convert was not found, so the PNG export cannot run.")
            if done.returncode != 0:
                print(f"rsvg-convert could not draw {svg}:\n{done.stderr.strip()[-2000:]}")
                return 1
    print(f"{2 * len(figures)} PNG(s), light and dark, in {png_dir}. Look at each one once before you ship it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
