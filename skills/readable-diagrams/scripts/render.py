"""Build a figure spec and export every figure as light and dark PNGs, in one command.

    python3 -I render.py SPEC.py OUT_DIR [--no-png]

SPEC.py is a Python file that defines FIGURES (see example_spec.py). OUT_DIR gets figures.html, one .svg and .mmd per
figure, and figures/<stem>.png plus figures/<stem>-dark.png. --no-png stops after the SVG and HTML, for a quick check
or for a machine without Chrome. Exit 1 with a plain message when a label does not fit or the export fails.
"""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTER = os.path.join(HERE, "export_png.mjs")
sys.path.insert(0, HERE)
import figlib  # noqa: E402


def export(page, png_dir, theme):
    """Runs export_png.mjs for one theme. Node runs in this folder, so both paths go to it in full: a relative path
    would point inside the scripts folder instead of the folder the command was run from."""
    command = ["node", EXPORTER, os.path.abspath(page), os.path.abspath(png_dir), theme]
    return subprocess.run(command, capture_output=True, text=True, cwd=HERE)


def cannot_load_puppeteer(stderr):
    """True when Node says export_png.mjs cannot find puppeteer from where it sits."""
    return "ERR_MODULE_NOT_FOUND" in stderr and "'puppeteer'" in stderr


def doctor_report():
    """doctor.sh in check mode: the same report it prints when run on its own."""
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
    page = os.path.join(out_dir, "figures.html")
    png_dir = os.path.join(out_dir, "figures")
    for theme in ("light", "dark"):
        try:
            done = export(page, png_dir, theme)
        except FileNotFoundError:
            return stop_with_doctor("node was not found, so the PNG export cannot run.")
        if done.returncode != 0 and cannot_load_puppeteer(done.stderr):
            return stop_with_doctor("The PNG export cannot run yet.")
        wrote = [ln for ln in done.stdout.splitlines() if ln.startswith("wrote")]
        if done.returncode != 0 or len(wrote) != len(figures):
            print(f"export failed for {theme}:")
            print(done.stdout[-2000:])
            print(done.stderr[-2000:])
            return stop_with_doctor("The export failed.")
        print(f"{theme}: {len(wrote)} PNG(s)")
    print(f"PNGs in {png_dir}. Look at each one once before you ship it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
