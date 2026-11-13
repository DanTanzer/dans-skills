"""diagramlib: hand-laid-out SVG diagrams in one house style, for data flow and sequence pictures.

A diagram is Python that places every box and arrow (a data flow) or a list of rows (a sequence). The library turns it
into one self-contained SVG per theme, light and dark: the diagram on its card, under the legend entries for the arrow
kinds it uses, with the house style inside the file. Any SVG reader draws such a file the same way, and render.py
turns each one into a PNG with rsvg-convert. diagramlib also writes the Mermaid fallback text.

Why hand layout and not Mermaid: Mermaid places every box itself, so lines can cross and labels sit on top of
the lines, and it has no legend. A picture that people read again and again is worth placing by hand.

Standard library only. Every width check uses an average character width for Arial, so a label that clearly
overflows fails here, at build time; the look at each PNG catches one that is close.
"""
import html
import math
import os
import re

# ====================================================================================== text measurement
# Widths of one character at each size, for Arial (words) and Menlo (names), which every Mac has.
# For Arial they sit near the median: measured in Chrome on the example's 115 labels, a label of eight or more
# characters runs 0.84 to 1.22 times its estimate. Menlo advances 0.602 em, so its three widths are exact.
# zt, the zone title, is bold capitals with 0.1 em letter-spacing, and sits near the top instead: measured in Chrome
# on 39 such titles, it runs 8.7 to 11.1 a character, median 10.0, and only 6 of the 39 run past 10.4.
# rsvg-convert, which draws the PNGs now, lays text out exactly as Chrome did: on 145 labels and titles, every advance
# matches Chrome's within 0.05 percent, except that a letter-spaced title ends 1.3 sooner: rsvg adds no space after
# the last letter. So these widths stand.
CHAR_W = {"t": 6.2, "tb": 7.0, "ts": 5.6, "sm": 5.6, "tm": 8.43, "tmb": 9.03, "tmsm": 7.53, "zt": 10.4}

# Arial's advance for each printable ASCII character, space to tilde, in 1/2048 em, read from Arial.ttf. Only the
# legend uses these: its entries sit 18 apart like words, so it needs each text's real width, not an average.
ARIAL_ADVANCE = dict(zip(map(chr, range(32, 127)), map(int, (
    "569 569 727 1139 1139 1821 1366 391 682 682 797 1196 569 682 569 569 1139 1139 1139 1139 1139 1139 1139 1139 "
    "1139 1139 569 569 1196 1196 1196 1139 2079 1366 1366 1479 1479 1366 1251 1593 1479 569 1024 1366 1139 1706 1479 "
    "1593 1366 1593 1479 1366 1251 1479 1366 1933 1366 1366 1251 569 569 569 961 1139 682 1139 1139 1024 1139 1139 "
    "569 1139 1139 455 455 1024 455 1706 1139 1139 1139 1139 682 1024 569 1139 1024 1479 1024 1024 1024 684 532 684 "
    "1196").split())))


def arial_width(s, size=14):
    """The width of s in Arial at size, from the font's own advances. A character outside ASCII counts as 0.6 em."""
    return round(sum(ARIAL_ADVANCE.get(ch, 1229) for ch in s) * size / 2048, 1)


class DiagramError(Exception):
    """A label does not fit, or a diagram is malformed. The text names the label."""


def width_of(s, cls="t"):
    """A safe pixel width of s in the text class cls (t, tb, ts, sm, tm, tmb, zt)."""
    parts = cls.split()
    if "tm" in parts:
        key = "tmsm" if "sm" in parts else "tmb" if "tb" in parts else "tm"
    elif "tb" in parts:
        key = "tb"
    elif "zt" in parts:
        key = "zt"
    elif "sm" in parts:
        key = "sm"
    elif "ts" in parts:
        key = "ts"
    else:
        key = "t"
    return round(len(s) * CHAR_W[key], 1)


def must_fit(s, room, cls="t", where=""):
    need = width_of(s, cls)
    if need > room:
        raise DiagramError(f"{where or 'label'} {s!r} needs {need:.0f}px but has {room:.0f}px: shorten it or widen the box")


# ====================================================================================== SVG helpers
def esc(s):
    return html.escape(str(s), quote=True)


ARROW_KINDS = ("file", "ring", "say", "loc")


def svg_open(width, height, pfx, label):
    markers = "".join(
        f'<marker id="ah-{k}-{pfx}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{s}" markerHeight="{s}" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" class="mk-{k}"/></marker>'
        for k, s in (("file", 5), ("ring", 5), ("say", 5), ("loc", 6))
    )
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}"><defs>{markers}</defs>'


def _heads(kind, pfx, both):
    if kind not in ARROW_KINDS:
        raise DiagramError(f"unknown arrow kind {kind!r}; use one of {ARROW_KINDS}")
    start = f' marker-start="url(#ah-{kind}-{pfx})"' if both else ""
    return f' marker-end="url(#ah-{kind}-{pfx})"{start}'


def line(x1, y1, x2, y2, kind, pfx, both=False):
    return f'<line class="a a-{kind}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{_heads(kind, pfx, both)}/>'


ELBOW_END_LEG = 16  # an arrowhead is about 11 units long; the leg it sits on needs room for it and a little line


def elbow_points(x1, y1, x2, y2, first="v", at=None):
    """The corners of an elbow from (x1, y1) to (x2, y2). first="v": straight down or up, across at y=at, then straight
    into the end. first="h": sideways, down or up at x=at, then sideways in. at is halfway unless given; at equal to
    an end's own y (or x) leaves a single bend, an L. Legs of no length are dropped."""
    if first not in ("v", "h"):
        raise DiagramError(f'elbow first={first!r}: use "v" (leave straight down or up) or "h" (leave sideways)')
    if first == "v":
        at = (y1 + y2) / 2 if at is None else at
        corners = [(x1, y1), (x1, at), (x2, at), (x2, y2)]
    else:
        at = (x1 + x2) / 2 if at is None else at
        corners = [(x1, y1), (at, y1), (at, y2), (x2, y2)]
    points = [corners[0]]
    for p in corners[1:]:
        if p != points[-1]:
            points.append(p)
    if len(points) < 2:
        raise DiagramError(f"elbow from ({x1}, {y1}) to ({x2}, {y2}): the two ends are the same point")
    return points


def elbow_path(points, kind, pfx, both=False):
    """An arrow along points, with a right-angle bend at each point between the first and the last."""
    legs = [abs(bx - ax) + abs(by - ay) for (ax, ay), (bx, by) in zip(points, points[1:])]
    ends = [("last", legs[-1])] + ([("first", legs[0])] if both else [])
    for which, length in ends:
        if length < ELBOW_END_LEG:
            raise DiagramError(f"elbow from {points[0]} to {points[-1]}: its {which} leg is {length:g} long, but an "
                              f"arrowhead needs {ELBOW_END_LEG}: move the bend with at=")
    d = " ".join(f"{'M' if i == 0 else 'L'}{round(x, 1):g} {round(y, 1):g}" for i, (x, y) in enumerate(points))
    return f'<path class="a a-{kind}" d="{d}"{_heads(kind, pfx, both)}/>'


def text(x, y, s, cls="t", anchor="start", halo=False):
    classes = cls + (" halo" if halo else "")
    return f'<text class="{classes}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(s)}</text>'


# ====================================================================================== the text inside a box
BOX_BOTTOM = 16  # the last line's baseline sits this far above a box's bottom edge


def _box_rows(title, lines, muted_last):
    """Each line of a box, in order, as (how far its baseline sits below the box's top, text, class, what it is).
    The title's lines are 22 apart, the first 26 down; plain lines follow 20 apart, small ones 18."""
    rows, y = [], 26
    for part in title.split("\n"):
        rows.append((y, part, "tb", "box title"))
        y += 22
    y += 2
    for i, item in enumerate(lines):
        s, cls = item if isinstance(item, tuple) else (item, "ts" if (muted_last and i == len(lines) - 1) else "t")
        rows.append((y, s, cls, "box line"))
        y += 20 if cls == "t" else 18
    return rows


def box_height(title, lines=(), muted_last=False):
    """The exact height a box needs for this title and these lines, with the same arguments as Canvas.box.
    Its last line then sits 16 above the bottom edge, about as far as the title's capitals sit below the top edge.
    A box can be taller; boxes side by side in one row can share the largest of their heights."""
    return _box_rows(title, lines, muted_last)[-1][0] + BOX_BOTTOM


# ====================================================================================== a canvas for data flow pictures
class Canvas:
    """Places the parts of a data flow picture. Coordinates are in a 1000-wide box unless width says otherwise.

    Parts: zone (a machine or the store, a tinted panel with an uppercase title), box (a process, white with an ink edge,
    a bold title and plain lines), store (a file or folder, dashed, a mono name and two plain lines), pill (a person),
    arrow (file, ring, say or loc, straight across or straight down), elbow (the same kinds, with right-angle bends)
    and label. Every part checks that its text fits.
    """

    def __init__(self, pfx, width=1000, height=800, label=""):
        self.pfx, self.width, self.height = pfx, width, height
        self.el = [svg_open(width, height, pfx, label)]

    def zone(self, x, y, w, h, title, sub="", kind="mac", sub_anchor="start"):
        cls = "zone store-zone" if kind == "store" else "zone"
        self.el.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/>')
        must_fit(title, w - 36, "zt", "zone title")
        self.el.append(text(x + 18, y + 24, title, "zt"))
        if sub:
            if sub_anchor == "end":
                self.el.append(text(x + w - 16, y + 24, sub, "ts", "end"))
            else:
                # 24 after the estimate leaves even the widest-lettered title about 19 clear of its subtitle
                self.el.append(text(x + 18 + width_of(title, "zt") + 24, y + 24, sub, "ts"))
        return self

    def box(self, x, y, w, h, title, lines=(), muted_last=False):
        """A process box. title may hold a newline for two bold lines. A line is plain text, or (text, "ts") for the
        small muted size; muted_last makes the last line small, which is the usual shape: a title, facts, one aside.
        box_height(title, lines, muted_last) gives the exact h the text needs; a shorter box is refused."""
        need = box_height(title, lines, muted_last)
        if h < need:
            raise DiagramError(f"box {title!r} is {h}px tall but its text needs {need}px: box_height() gives the height")
        self.el.append(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
        for dy, s, cls, where in _box_rows(title, lines, muted_last):
            must_fit(s, w - 32, cls, where)
            self.el.append(text(x + 16, y + dy, s, cls))
        return self

    def store(self, x, y, w, h, name, l1="", l2=""):
        """A file or folder: dashed edge, mono name, up to two plain lines."""
        self.el.append(f'<rect class="store" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
        small = h < 60
        must_fit(name, (w - 12) if small else (w - 24), "tm tb sm" if small else "tm tb", "store name")
        if small:
            self.el.append(text(x + 10, y + 19, name, "tm tb sm"))
            if l1:
                must_fit(l1, w - 20, "ts", "store line")
                self.el.append(text(x + 10, y + 36, l1, "ts"))
        else:
            self.el.append(text(x + 16, y + 32, name, "tm tb"))
            if l1:
                must_fit(l1, w - 32, "t", "store line")
                self.el.append(text(x + 16, y + 60, l1, "t"))
            if l2:
                must_fit(l2, w - 32, "ts", "store line")
                self.el.append(text(x + 16, y + 82, l2, "ts"))
        return self

    def pill(self, cx, y, label="You", w=90):
        """A person: a rounded pill in the person colour."""
        must_fit(label, w - 20, "tb", "pill")
        self.el.append(f'<rect class="person" x="{cx - w // 2}" y="{y}" width="{w}" height="36" rx="18"/>')
        self.el.append(text(cx, y + 24, label, "tb", "middle"))
        return self

    def arrow(self, x1, y1, x2, y2, kind, both=False, diagonal=False):
        """A straight arrow, the first choice: place the boxes so the two ends share an x or a y. Two points that share
        neither make a diagonal, which reads as noise in a picture of rows and columns: the build refuses one unless
        diagonal=True says it is meant. When the boxes cannot line up, elbow() draws the link with right-angle bends."""
        if x1 != x2 and y1 != y2 and not diagonal:
            raise DiagramError(f"arrow from ({x1}, {y1}) to ({x2}, {y2}) is diagonal: move a box so the ends share an x "
                              "or a y, or draw it with elbow(); pass diagonal=True only when the diagonal is meant")
        self.el.append(line(x1, y1, x2, y2, kind, self.pfx, both))
        return self

    def elbow(self, x1, y1, x2, y2, kind, first="v", at=None, both=False):
        """An arrow with right-angle bends, for two points that share neither x nor y. first="v" (the default) leaves
        straight down or up, runs across at y=at, then goes straight into the end: one row to the next. first="h"
        leaves sideways, runs down or up at x=at, then goes sideways in: one column to the next. at is halfway unless
        given; set it to the end's own y (or x) for a single bend. references/layout.md says where the bend goes."""
        self.el.append(elbow_path(elbow_points(x1, y1, x2, y2, first, at), kind, self.pfx, both))
        return self

    def label(self, x, y, s, anchor="start", cls="t", halo=False):
        self.el.append(text(x, y, s, cls, anchor, halo))
        return self

    def raw(self, svg_fragment):
        self.el.append(svg_fragment)
        return self

    def svg(self):
        return "".join(self.el + ["</svg>"])


# ====================================================================================== sequence pictures
def _lifeline_x(n, width):
    """Evenly spread lifelines: the first near the left edge (the person is narrow), the rest sharing the width."""
    if n < 2:
        raise DiagramError("a sequence needs at least two lifelines")
    left, right = 60, width - 90
    step = (right - left) / (n - 1)
    return [round(left + i * step) for i in range(n)]


def render_sequence(seq, width=1000):
    """seq: id, title, caption, lifelines [(key, name, sub)], rows.

    A row is ("msg", src, dst, label, kind) with kind file, ring, say or loc, or ("note", at, [line, line]).
    A lifeline whose sub is empty is drawn as the person pill. Labels must fit between their two lifelines,
    notes must fit their box, and a note near an edge is pulled inside the picture.
    """
    keys = [k for k, _, _ in seq["lifelines"]]
    xs = dict(zip(keys, _lifeline_x(len(keys), width)))
    heads = {k: (name, sub) for k, name, sub in seq["lifelines"]}
    pfx = f"s-{seq['id']}"
    top, head_h, note_w = 8, 54, 250
    cur = top + head_h + 14
    body = []
    for row in seq["rows"]:
        if row[0] == "msg":
            _, src, dst, label, kind = row
            if src == dst:
                raise DiagramError(f"a message from {src} to itself cannot be drawn: {label!r}; use a note")
            x1, x2 = xs[src], xs[dst]
            must_fit(label, abs(x2 - x1) - 14, "t", f"message {src}->{dst}")
            direction = 1 if x2 > x1 else -1
            y = cur + 30
            body.append(line(x1 + 3 * direction, y, x2 - 3 * direction, y, kind, pfx))
            body.append(text((x1 + x2) / 2, y - 9, label, "t", "middle", halo=True))
            cur += 44
        elif row[0] == "note":
            _, at, lines = row
            if len(lines) != 2:
                raise DiagramError(f"a note holds exactly two lines, got {lines!r}")
            for s in lines:
                must_fit(s, note_w - 16, "t", "note")
            x = min(max(xs[at], note_w // 2 + 8), width - note_w // 2 - 8)
            body.append(f'<rect class="note" x="{x - note_w // 2}" y="{cur + 6}" width="{note_w}" height="50" rx="8"/>')
            body.append(text(x, cur + 27, lines[0], "t", "middle"))
            body.append(text(x, cur + 45, lines[1], "t", "middle"))
            cur += 66
        else:
            raise DiagramError(f"unknown row {row!r}")
    height = cur + 10
    el = [svg_open(width, height, pfx, f"{seq['title']}. {seq['caption']}")]
    for k in keys:
        el.append(f'<line class="life" x1="{xs[k]}" y1="{top + head_h}" x2="{xs[k]}" y2="{height - 6}"/>')
    for k in keys:
        name, sub = heads[k]
        w = 90 if not sub else 160
        must_fit(name, w - 16, "tb", "lifeline name")
        if sub:
            must_fit(sub, w - 12, "ts", "lifeline sub")
        x = xs[k]
        el.append(f'<rect class="{"person" if not sub else "hd"}" x="{x - w // 2}" y="{top}" width="{w}" height="{head_h}" rx="10"/>')
        if sub:
            el.append(text(x, top + 24, name, "tb", "middle"))
            el.append(text(x, top + 43, sub, "ts", "middle"))
        else:
            el.append(text(x, top + 33, name, "tb", "middle"))
    el.extend(body)
    el.append("</svg>")
    return "".join(el)


def mermaid_sequence(seq):
    """The same sequence as Mermaid text, for the closed block under the picture. GitHub draws it."""
    lines = ["sequenceDiagram"]
    for k, name, sub in seq["lifelines"]:
        shown = f"{name} ({sub})" if sub else name
        lines.append(f"  participant {k} as {shown}")
    for row in seq["rows"]:
        if row[0] == "msg":
            _, src, dst, label, kind = row
            if ";" in label or "#" in label:
                raise DiagramError(f"Mermaid reads ; and # as syntax: rewrite {label!r}")
            lines.append(f"  {src}{'-->>' if kind in ('ring', 'loc') else '->>'}{dst}: {label}")
        else:
            _, at, texts = row
            lines.append(f"  Note over {at}: {'<br/>'.join(texts)}")
    return "\n".join(lines)


# ====================================================================================== the house style
# Every colour is a token with a light and a dark value. STYLE names the tokens; theme_css puts one theme's values in,
# so a finished SVG holds plain colours and needs nothing from outside the file.
THEMES = {
    "light": {"--surface": "#FFFFFF", "--panel": "#E8EDF3", "--ink": "#16202B", "--muted": "#475466", "--line": "#B4BFCC",
              "--file": "#0A7468", "--ring": "#B04F08", "--person-fill": "#E3E6FB", "--person-line": "#4A4FC2",
              "--store-zone": "#EAF4F2"},
    "dark": {"--surface": "#141C26", "--panel": "#1A2431", "--ink": "#E7EDF3", "--muted": "#A3B0BF", "--line": "#364354",
             "--file": "#3DD6C2", "--ring": "#F4B14F", "--person-fill": "#222A52", "--person-line": "#9EA3F2",
             "--store-zone": "#11262A"},
}

STYLE = """
text { font-family: Arial, sans-serif; fill: var(--ink); }
.t { font-size: 14px; } .tb { font-size: 15px; font-weight: 700; } .sm { font-size: 12.5px; }
.ts { font-size: 12.5px; fill: var(--muted); } .tm { font-family: Menlo, monospace; }
.zt { font-size: 13px; font-weight: 700; letter-spacing: 0.1em; fill: var(--muted); }
.halo { paint-order: stroke fill; stroke: var(--surface); stroke-width: 5px; stroke-linejoin: round; }
.card { fill: var(--surface); stroke: var(--line); stroke-width: 1; }
.zone { fill: var(--panel); stroke: var(--line); stroke-width: 1.5; }
.store-zone { fill: var(--store-zone); stroke: var(--file); }
.box { fill: var(--surface); stroke: var(--ink); stroke-width: 1.8; }
.store { fill: var(--surface); stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 6 4; }
.person { fill: var(--person-fill); stroke: var(--person-line); stroke-width: 1.8; }
.hd { fill: var(--panel); stroke: var(--ink); stroke-width: 1.6; }
.note { fill: var(--panel); stroke: var(--line); stroke-width: 1.4; }
.life { stroke: var(--line); stroke-width: 1.5; stroke-dasharray: 4 5; }
.a { fill: none; stroke-width: 2.2; }
.a-file { stroke: var(--file); } .a-ring { stroke: var(--ring); stroke-dasharray: 7 5; }
.a-say { stroke: var(--ink); } .a-loc { stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 5 4; }
.mk-file { fill: var(--file); } .mk-ring { fill: var(--ring); } .mk-say { fill: var(--ink); } .mk-loc { fill: var(--muted); }
.lg-file { stroke: var(--file); stroke-width: 2.4; } .lg-ring { stroke: var(--ring); stroke-width: 2.4; stroke-dasharray: 7 5; }
.lg-say { stroke: var(--ink); stroke-width: 2.4; } .lg-loc { stroke: var(--muted); stroke-width: 1.6; stroke-dasharray: 5 4; }
"""


def theme_css(theme):
    """STYLE with one theme's colours in place of the token names."""
    tokens = THEMES[theme]
    return re.sub(r"var\((--[a-z-]+)\)", lambda m: tokens[m.group(1)], STYLE)


# ====================================================================================== the card: legend and diagram
# The four arrow meanings. A diagram's legend shows only the kinds it uses.
LEGEND_TEXT = {"file": "a file written or read", "ring": "a ring (a nudge only)", "say": "a person's words, or Claude's report", "loc": "kept on one machine only"}

CARD_W = 920       # units; the PNG is twice this, 1840 pixels
DIAGRAM_W = 898     # the diagram inside the card: a 1-unit edge, then 10 on each side
LEGEND_ROW = 22.4  # one legend row; rows are 6 apart, and the entries in a row 18 apart


def used_kinds(svg):
    """The arrow kinds a diagram draws, in legend order."""
    return [k for k in ARROW_KINDS if re.search(rf'class="[^"]*\ba-{k}\b', svg)]


def legend_svg(kinds, texts, top=15):
    """The legend entries for kinds, flowed into rows like words: a 44-wide swatch of the arrow, 8 of space, then the
    words. Rows start 18 inside the card's edge. Returns the SVG and the y where the last row ends."""
    left, right = 1 + 18, CARD_W - 1 - 18
    x, y, parts = left, top, []
    for k in kinds:
        w = 52 + arial_width(texts[k])
        if x > left and x + w > right:
            x, y = left, y + LEGEND_ROW + 6
        parts.append(f'<line class="lg-{k}" x1="{x + 2}" y1="{round(y + 11.2, 1)}" x2="{x + 42}" y2="{round(y + 11.2, 1)}"/>')
        parts.append(text(x + 52, round(y + 16, 1), texts[k]))
        x = round(x + w + 18, 1)
    return "".join(parts), y + LEGEND_ROW


def _placed(svg, x, y, width):
    """The diagram's own svg element, placed at x, y and drawn width wide. Its viewBox keeps its units, so every
    coordinate in the diagram stays as the spec wrote it. A size or place the element already had gives way to these.
    Returns the element and its drawn height."""
    svg = svg.strip()
    head = re.match(r"<svg\b[^>]*>", svg)
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head.group(0)) if head else None
    if not box:
        raise DiagramError('a diagram must start with <svg viewBox="0 0 WIDTH HEIGHT">')
    height = round(float(box.group(2)) * width / float(box.group(1)), 2)
    rest = re.sub(r'\s(?:x|y|width|height)="[^"]*"', "", head.group(0))[len("<svg"):]
    return f'<svg x="{x}" y="{y}" width="{width}" height="{height}"{rest}' + svg[head.end():], height


def card(svg, theme, legend_texts=None, label=""):
    """One diagram as a self-contained SVG in one theme: its own style sheet, the card behind everything, the legend
    entries for the arrow kinds the diagram uses, then the diagram. 920 units wide, so rsvg-convert --zoom 2 gives
    1840 pixels. Outside the card's rounded corners the picture is transparent."""
    if theme not in THEMES:
        raise DiagramError(f"theme {theme!r}: use one of {tuple(THEMES)}")
    kinds = used_kinds(svg)
    legend, legend_end = legend_svg(kinds, legend_texts or LEGEND_TEXT) if kinds else ("", 5)
    diagram, diagram_h = _placed(svg, 11, round(legend_end + 6, 1), DIAGRAM_W)
    height = math.ceil(legend_end + 6 + diagram_h + 10 + 1)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{height}" viewBox="0 0 {CARD_W} {height}"'
            f' role="img" aria-label="{esc(label)}"><style>{theme_css(theme)}</style>'
            f'<rect class="card" x="0.5" y="0.5" width="{CARD_W - 1}" height="{height - 1}" rx="9.5"/>'
            f"{legend}{diagram}</svg>\n")


# ====================================================================================== embedding in Markdown
THEME_SUFFIX = {"light": "", "dark": "-dark"}  # <stem>.svg and <stem>-dark.svg, and the PNGs made from them
BOTH = ("light", "dark")


def check_alt(alt):
    if re.search(r'["\n]', alt):
        raise DiagramError(f"alt text may not hold a quote or a line break: {alt[:60]!r}")


def picture_block(stem, alt, folder, mermaid=None, themes=BOTH):
    """The Markdown that shows a diagram, then its Mermaid text in a closed block. With both themes, a <picture> that
    shows the dark SVG in dark mode and the light one otherwise. With one theme, a plain Markdown image of the SVG."""
    check_alt(alt)
    if set(themes) == set(BOTH):
        out = (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{folder}/{stem}-dark.svg">\n'
               f'  <img src="{folder}/{stem}.svg" alt="{alt}">\n</picture>\n')
    else:
        (theme,) = themes
        shown = alt.replace("[", "\\[").replace("]", "\\]")
        out = f"![{shown}]({folder}/{stem}{THEME_SUFFIX[theme]}.svg)\n"
    if mermaid:
        out += ("\n<details>\n<summary>The same diagram as Mermaid text (open it to edit)</summary>\n\n"
                f"```mermaid\n{mermaid}\n```\n\n</details>\n")
    return out


# ====================================================================================== building from a spec
def mmd_text(mermaid):
    """The text of a diagram's .mmd file: its Mermaid and a final newline, or None for a diagram with no Mermaid text.
    The file and the copy inside each PNG are this one text."""
    return mermaid + "\n" if mermaid else None


def build(spec, out_dir, themes=BOTH):
    """spec: a module or object with DIAGRAMS, a list of dicts, each with stem, alt and either svg (a string or a
    callable) or seq (a sequence dict, drawn and also written as Mermaid). Optional: mermaid, and LEGEND on the spec,
    new words for any of the four arrow meanings.
    Writes out_dir/<stem>.svg for light and out_dir/<stem>-dark.svg for dark, for each theme in themes, each complete
    on its own, and <stem>.mmd where there is Mermaid. Returns the diagram list; each entry's "files" maps each theme
    built to its SVG file."""
    os.makedirs(out_dir, exist_ok=True)
    legend_texts = {**LEGEND_TEXT, **(getattr(spec, "LEGEND", None) or {})}
    diagrams = []
    for f in spec.DIAGRAMS:
        stem = f["stem"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", stem):
            raise DiagramError(f"stem {stem!r}: use lower-case letters, digits and hyphens")
        check_alt(f["alt"])
        if "seq" in f:
            svg, mermaid = render_sequence(f["seq"]), mermaid_sequence(f["seq"])
        else:
            svg, mermaid = f["svg"]() if callable(f["svg"]) else f["svg"], f.get("mermaid", "")
        files = {}
        for theme in themes:
            files[theme] = os.path.join(out_dir, f"{stem}{THEME_SUFFIX[theme]}.svg")
            with open(files[theme], "w", encoding="utf-8") as handle:
                handle.write(card(svg, theme, legend_texts, f["alt"]))
        mmd = mmd_text(mermaid)
        if mmd:
            with open(os.path.join(out_dir, f"{stem}.mmd"), "w", encoding="utf-8") as handle:
                handle.write(mmd)
        diagrams.append({"stem": stem, "alt": f["alt"], "svg": svg, "mermaid": mermaid, "files": files})
    return diagrams
