"""A small sample: the skill's own pipeline, drawn by the skill. One data flow and one sequence.

From the skill's folder:  python3 -I scripts/render.py sample/spec.py --out runtime/sample
../HOW-IT-WORKS.md walks through every step of that build.
"""
from figlib import Canvas

# New words for one of the four arrow meanings, for this set. The others keep their defaults.
LEGEND = {"say": "a request or a report"}

# ====================================================================================== the data flow
# Processes are solid boxes, files are dashed boxes. Row A runs left to right, row B runs right to left.
ROW_A, ROW_B, H = 120, 290, 410
COLS = (40, 370, 700)  # three columns, 260 wide, 70 apart: room for one arrow and one short label
W = 260

DATA_FLOW_ALT = ("Data flow of one build for design.md. Claude writes spec.py, render.py reads it and writes an SVG for "
                 "each figure and theme in the skill's runtime folder, rsvg-convert draws each SVG as a PNG in "
                 "design-diagrams next to design.md, and Claude looks at each PNG.")

DATA_FLOW_MERMAID = """flowchart LR
  you(["You"])
  subgraph mac["YOUR MAC"]
    claude["Claude session + skill"] -->|writes| spec[("spec.py")]
    spec -->|reads| render["render.py + figlib"]
    render -->|writes| runtime[("runtime/: an .svg per theme, .mmd")]
    runtime -->|reads| exporter["rsvg-convert"]
    exporter -->|writes| pngs[("design-diagrams/: the PNGs design.md shows")]
    pngs -->|looks at each| claude
  end
  you -->|words| claude
  claude -->|report| you"""


def data_flow():
    c = Canvas("flow", 1000, H, DATA_FLOW_ALT)
    c.zone(20, 76, 960, H - 92, "YOUR MAC", "everything runs here, nothing goes online", sub_anchor="end")
    c.pill(200, 16)
    c.arrow(180, 52, 180, ROW_A, "say").label(172, 92, "words", "end")
    c.arrow(220, ROW_A, 220, 52, "say").label(228, 92, "report")
    # row A, left to right: who writes the spec, the spec, who reads it
    c.box(COLS[0], ROW_A, W, 72, "Claude session + skill", [("writes the spec, runs the build", "ts")])
    c.store(COLS[1], ROW_A, W, 72, "spec.py", "every box and arrow, by hand")
    c.box(COLS[2], ROW_A, W, 72, "render.py + figlib", [("Python: draws SVG, checks widths", "ts")])
    c.arrow(COLS[0] + W, ROW_A + 36, COLS[1], ROW_A + 36, "file").label(335, ROW_A + 28, "writes", "middle")
    c.arrow(COLS[1] + W, ROW_A + 36, COLS[2], ROW_A + 36, "file").label(665, ROW_A + 28, "reads", "middle")
    # down the right side, then row B, right to left
    c.arrow(830, ROW_A + 72, 830, ROW_B, "file").label(840, ROW_A + 126, "writes")
    c.store(COLS[2], ROW_B, W, 72, "runtime/", "an .svg per theme, and .mmd")
    c.box(COLS[1], ROW_B, W, 72, "rsvg-convert", [("librsvg: one PNG per SVG", "ts")])
    c.store(COLS[0], ROW_B, W, 72, "design-diagrams/", "the PNGs design.md shows")
    c.arrow(COLS[2], ROW_B + 36, COLS[1] + W, ROW_B + 36, "file").label(665, ROW_B + 28, "reads", "middle")
    c.arrow(COLS[1], ROW_B + 36, COLS[0] + W, ROW_B + 36, "file").label(335, ROW_B + 28, "writes", "middle")
    # and back up the left side: Claude looks at every picture before it goes in a document
    c.arrow(170, ROW_B, 170, ROW_A + 72, "file").label(180, ROW_A + 126, "looks at each")
    return c.svg()


# ====================================================================================== the sequence
LIFELINES = [("U", "You", ""), ("C", "Claude", "session + skill"), ("R", "render.py", "Python + figlib"),
             ("F", "Files", "on this Mac"), ("X", "rsvg-convert", "from librsvg")]

BUILD = {
    "id": "build", "title": "One build, in order", "lifelines": LIFELINES,
    "caption": "Claude asks which pictures the doc shows, writes the spec in the doc's runtime folder and runs "
               "render.py. render.py draws an SVG for each figure and theme, then runs rsvg-convert once for each, "
               "which writes the PNG next to the doc. Claude looks at each PNG, then pastes the Markdown into the doc.",
    "rows": [
        ("msg", "U", "C", "\"draw how the parts talk\"", "say"),
        ("msg", "C", "U", "light, dark or both?", "say"),
        ("msg", "U", "C", "both", "say"),
        ("msg", "C", "F", "writes spec.py in runtime/", "file"),
        ("msg", "C", "R", "render.py --doc --theme both", "say"),
        ("msg", "R", "F", "reads spec.py", "file"),
        ("note", "R", ["draws every box and arrow,", "checks the text in each box"]),
        ("msg", "R", "F", "writes an svg per theme, mmd", "file"),
        ("msg", "R", "X", "rsvg-convert, once per svg", "say"),
        ("note", "X", ["at twice the size: 920", "units become 1840 pixels"]),
        ("msg", "X", "F", "reads an svg, writes its PNG", "file"),
        ("msg", "R", "C", "4 PNGs, the Markdown", "say"),
        ("msg", "C", "F", "looks at each PNG once", "file"),
        ("msg", "C", "U", "the pictures, in your doc", "say"),
    ],
}

FIGURES = [
    {"stem": "data-flow", "alt": DATA_FLOW_ALT, "svg": data_flow, "mermaid": DATA_FLOW_MERMAID},
    {"stem": "build-sequence", "alt": f"{BUILD['title']}. {BUILD['caption']}", "seq": BUILD},
]
