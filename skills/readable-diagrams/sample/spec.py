"""A small sample: the skill's own pipeline, drawn by the skill. One data flow and one sequence.

With SKILL as this skill's folder and SCRATCH as a temporary folder:
    python3 -I SKILL/scripts/render.py SKILL/sample/spec.py --out SCRATCH/sample --theme both
../HOW-IT-WORKS.md walks through every step of that build.
"""
from diagramlib import Canvas

# New words for one of the four arrow meanings, for this set. The others keep their defaults.
LEGEND = {"say": "a request or a report"}

# ====================================================================================== the data flow
# Processes are solid boxes, files are dashed boxes. Row A runs left to right, row B runs right to left.
ROW_A, ROW_B, H = 120, 290, 410
COLS = (40, 370, 700)  # three columns, 260 wide, 70 apart: room for one arrow and one short label
W = 260

DATA_FLOW_ALT = ("Data flow of one build for design.md. Claude writes design.spec.py, render.py builds an SVG for each "
                 "diagram and theme, embeds the Python and Mermaid sources, and saves the final SVGs in "
                 "readable-diagrams/design next to design.md.")

DATA_FLOW_MERMAID = """flowchart LR
  you(["You"])
  subgraph mac["YOUR MAC"]
    claude["Claude session + skill"] -->|writes| spec[("design.spec.py")]
    spec -->|reads| render["render.py + diagramlib"]
    render -->|writes| build[("a temporary folder: SVGs and .mmd")]
    build -->|saves| svgs[("readable-diagrams/design/: final SVGs with source metadata")]
    svgs -->|references| doc[("design.md: SVG links and Mermaid blocks")]
    doc -->|inspects| claude
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
    c.store(COLS[1], ROW_A, W, 72, "design.spec.py", "every box and arrow, by hand")
    c.box(COLS[2], ROW_A, W, 72, "render.py + diagramlib", [("Python: draws SVG, checks widths", "ts")])
    c.arrow(COLS[0] + W, ROW_A + 36, COLS[1], ROW_A + 36, "file").label(335, ROW_A + 28, "writes", "middle")
    c.arrow(COLS[1] + W, ROW_A + 36, COLS[2], ROW_A + 36, "file").label(665, ROW_A + 28, "reads", "middle")
    # down the right side, then row B, right to left
    c.arrow(830, ROW_A + 72, 830, ROW_B, "file").label(840, ROW_A + 126, "writes")
    c.store(COLS[2], ROW_B, W, 72, "temporary folder", "SVGs and Mermaid text")
    c.store(COLS[1], ROW_B, W, 72, "readable-diagrams/design/", "final SVGs with source metadata")
    c.store(COLS[0], ROW_B, W, 72, "design.md", "SVG links and Mermaid blocks")
    c.arrow(COLS[2], ROW_B + 36, COLS[1] + W, ROW_B + 36, "file").label(665, ROW_B + 28, "saves", "middle")
    c.arrow(COLS[1], ROW_B + 36, COLS[0] + W, ROW_B + 36, "file").label(335, ROW_B + 28, "links", "middle")
    # and back up the left side: Claude checks the final SVGs before sharing them
    c.arrow(170, ROW_B, 170, ROW_A + 72, "file").label(180, ROW_A + 126, "inspects")
    return c.svg()


# ====================================================================================== the sequence
LIFELINES = [("U", "You", ""), ("C", "Claude", "session + skill"), ("R", "render.py", "Python + diagramlib"),
             ("F", "Files", "on this Mac")]

BUILD = {
    "id": "build", "title": "One build, in order", "lifelines": LIFELINES,
    "caption": "Claude writes the spec in its scratch folder and runs render.py. The command builds SVGs, embeds their "
               "Python and Mermaid sources, saves the final files, and prints Markdown for the document.",
    "rows": [
        ("msg", "U", "C", "\"draw how the parts talk\"", "say"),
        ("msg", "C", "F", "writes design.spec.py in SCRATCH", "file"),
        ("msg", "C", "R", "render.py --doc docs/design.md", "say"),
        ("msg", "R", "F", "reads design.spec.py", "file"),
        ("note", "R", ["draws diagrams and checks text,", "builds one SVG per theme"]),
        ("msg", "R", "F", "embeds Python + Mermaid metadata", "file"),
        ("msg", "R", "F", "saves final SVGs next to the doc", "file"),
        ("msg", "R", "F", "removes the temporary files", "file"),
        ("msg", "R", "C", "prints Markdown for the doc", "say"),
        ("msg", "C", "F", "inspects SVGs, updates the doc", "file"),
        ("msg", "C", "U", "the doc and its diagrams", "say"),
    ],
}

DIAGRAMS = [
    {"stem": "data-flow", "alt": DATA_FLOW_ALT, "svg": data_flow, "mermaid": DATA_FLOW_MERMAID},
    {"stem": "build-sequence", "alt": f"{BUILD['title']}. {BUILD['caption']}", "seq": BUILD},
]
