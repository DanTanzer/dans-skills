"""figlib: hand-laid-out SVG figures in one house style, for data flow and sequence pictures.

A figure is Python that places every box and arrow (a data flow) or a list of rows (a sequence). The library turns it
into SVG with one set of CSS tokens for light and dark, builds one HTML page that holds every figure with the arrow
legend, and writes the Mermaid fallback text. export_png.mjs then photographs each figure card from that page.

Why hand layout and not Mermaid: Mermaid places every box itself, so lines can cross and labels sit on top of
the lines, and it has no legend. A picture that people read again and again is worth placing by hand.

Standard library only. Every width check uses an average character width for Arial, so a label that clearly
overflows fails here, at build time; the look at each PNG catches one that is close.
"""
import html
import os
import re

# ====================================================================================== text measurement
# Widths of one character at each size, for Arial (words) and Menlo (names), which every Mac has.
# For Arial they sit near the median: measured in Chrome on the example's 115 labels, a label of eight or more
# characters runs 0.84 to 1.22 times its estimate. Menlo advances 0.6 em, so its three widths are exact.
# zt, the zone title, is bold capitals with 0.1 em letter-spacing, and sits near the top instead: measured in Chrome
# on 39 such titles, it runs 8.7 to 11.1 a character, median 10.0, and only 6 of the 39 run past 10.4.
CHAR_W = {"t": 6.2, "tb": 7.0, "ts": 5.6, "sm": 5.6, "tm": 8.4, "tmb": 9.0, "tmsm": 7.5, "zt": 10.4}


class FigureError(Exception):
    """A label does not fit, or a figure is malformed. The text names the label."""


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
        raise FigureError(f"{where or 'label'} {s!r} needs {need:.0f}px but has {room:.0f}px: shorten it or widen the box")


# ====================================================================================== SVG helpers
def esc(s):
    return html.escape(str(s), quote=True)


ARROW_KINDS = ("file", "ring", "say", "loc")


def svg_open(width, height, pfx, label, wide=False):
    markers = "".join(
        f'<marker id="ah-{k}-{pfx}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{s}" markerHeight="{s}" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" class="mk-{k}"/></marker>'
        for k, s in (("file", 5), ("ring", 5), ("say", 5), ("loc", 6))
    )
    return (f'<svg viewBox="0 0 {width} {height}" class="{"wide" if wide else ""}" role="img" aria-label="{esc(label)}">'
            f"<defs>{markers}</defs>")


def line(x1, y1, x2, y2, kind, pfx, both=False):
    if kind not in ARROW_KINDS:
        raise FigureError(f"unknown arrow kind {kind!r}; use one of {ARROW_KINDS}")
    start = f' marker-start="url(#ah-{kind}-{pfx})"' if both else ""
    return f'<line class="a a-{kind}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" marker-end="url(#ah-{kind}-{pfx})"{start}/>'


def text(x, y, s, cls="t", anchor="start", halo=False):
    classes = cls + (" halo" if halo else "")
    return f'<text class="{classes}" x="{x}" y="{y}" text-anchor="{anchor}">{esc(s)}</text>'


# ====================================================================================== a canvas for data flow pictures
class Canvas:
    """Places the parts of a data flow picture. Coordinates are in a 1000-wide box unless width says otherwise.

    Parts: zone (a machine or the store, a tinted panel with an uppercase title), box (a process, white with an ink edge,
    a bold title and plain lines), store (a file or folder, dashed, a mono name and two plain lines), pill (a person),
    arrow (file, ring, say or loc) and label. Every part checks that its text fits.
    """

    def __init__(self, pfx, width=1000, height=800, label="", wide=True):
        self.pfx, self.width, self.height = pfx, width, height
        self.el = [svg_open(width, height, pfx, label, wide=wide)]

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
        small muted size; muted_last makes the last line small, which is the usual shape: a title, facts, one aside."""
        self.el.append(f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
        ty = y + 26
        for part in title.split("\n"):
            must_fit(part, w - 32, "tb", "box title")
            self.el.append(text(x + 16, ty, part, "tb"))
            ty += 22
        ty += 2
        for i, item in enumerate(lines):
            s, cls = item if isinstance(item, tuple) else (item, "ts" if (muted_last and i == len(lines) - 1) else "t")
            must_fit(s, w - 32, cls, "box line")
            self.el.append(text(x + 16, ty, s, cls))
            ty += 20 if cls == "t" else 18
        if ty - 14 > y + h:
            raise FigureError(f"box {title!r} is {h}px tall but its text needs {ty - 14 - y}px")
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

    def arrow(self, x1, y1, x2, y2, kind, both=False):
        self.el.append(line(x1, y1, x2, y2, kind, self.pfx, both))
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
        raise FigureError("a sequence needs at least two lifelines")
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
                raise FigureError(f"a message from {src} to itself cannot be drawn: {label!r}; use a note")
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
                raise FigureError(f"a note holds exactly two lines, got {lines!r}")
            for s in lines:
                must_fit(s, note_w - 16, "t", "note")
            x = min(max(xs[at], note_w // 2 + 8), width - note_w // 2 - 8)
            body.append(f'<rect class="note" x="{x - note_w // 2}" y="{cur + 6}" width="{note_w}" height="50" rx="8"/>')
            body.append(text(x, cur + 27, lines[0], "t", "middle"))
            body.append(text(x, cur + 45, lines[1], "t", "middle"))
            cur += 66
        else:
            raise FigureError(f"unknown row {row!r}")
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
                raise FigureError(f"Mermaid reads ; and # as syntax: rewrite {label!r}")
            lines.append(f"  {src}{'-->>' if kind in ('ring', 'loc') else '->>'}{dst}: {label}")
        else:
            _, at, texts = row
            lines.append(f"  Note over {at}: {'<br/>'.join(texts)}")
    return "\n".join(lines)


# ====================================================================================== the page and its style
TOKENS_LIGHT = {
    "--bg": "#F3F5F8", "--surface": "#FFFFFF", "--panel": "#E8EDF3", "--ink": "#16202B", "--muted": "#475466", "--line": "#B4BFCC",
    "--file": "#0A7468", "--ring": "#B04F08", "--person-fill": "#E3E6FB", "--person-line": "#4A4FC2", "--code-bg": "#E6ECF3", "--store-zone": "#EAF4F2",
}
TOKENS_DARK = {
    "--bg": "#0D131A", "--surface": "#141C26", "--panel": "#1A2431", "--ink": "#E7EDF3", "--muted": "#A3B0BF", "--line": "#364354",
    "--file": "#3DD6C2", "--ring": "#F4B14F", "--person-fill": "#222A52", "--person-line": "#9EA3F2", "--code-bg": "#1B2531", "--store-zone": "#11262A",
}


def _css_block(tokens):
    return "".join(f"{k}:{v};" for k, v in tokens.items())


CSS = f"""
:root {{ {_css_block(TOKENS_LIGHT)}
  --font-body: Arial, sans-serif;
  --font-mono: Menlo, monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ {_css_block(TOKENS_DARK)} color-scheme: dark; }} }}
:root[data-theme="dark"] {{ {_css_block(TOKENS_DARK)} color-scheme: dark; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 17px; line-height: 1.6; margin: 0; padding: 32px 16px 72px; }}
.wrap {{ max-width: 920px; margin: 0 auto; }}
h1, h3 {{ line-height: 1.2; margin: 0; }} h3 {{ margin-top: 2rem; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 1.2rem 0 0.8rem; font-size: 0.95rem; }}
.legend span {{ display: inline-flex; align-items: center; gap: 8px; }}
.legend svg {{ width: 44px; height: 14px; flex: none; }}
figure {{ margin: 1rem 0 0; }}
.frame {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }}
.frame svg {{ display: block; width: 100%; min-width: 820px; height: auto; }}
.frame svg.wide {{ min-width: 900px; }}
figcaption {{ color: var(--muted); font-size: 0.97rem; margin-top: 0.6rem; max-width: 68ch; }}
svg text {{ font-family: var(--font-body); fill: var(--ink); }}
svg .t {{ font-size: 14px; }} svg .tb {{ font-size: 15px; font-weight: 700; }} svg .sm {{ font-size: 12.5px; }}
svg .ts {{ font-size: 12.5px; fill: var(--muted); }} svg .tm {{ font-family: var(--font-mono); }}
svg .zt {{ font-size: 13px; font-weight: 700; letter-spacing: 0.1em; fill: var(--muted); }}
svg .halo {{ paint-order: stroke fill; stroke: var(--surface); stroke-width: 5px; stroke-linejoin: round; }}
svg .zone {{ fill: var(--panel); stroke: var(--line); stroke-width: 1.5; }}
svg .store-zone {{ fill: var(--store-zone); stroke: var(--file); }}
svg .box {{ fill: var(--surface); stroke: var(--ink); stroke-width: 1.8; }}
svg .store {{ fill: var(--surface); stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 6 4; }}
svg .person {{ fill: var(--person-fill); stroke: var(--person-line); stroke-width: 1.8; }}
svg .hd {{ fill: var(--panel); stroke: var(--ink); stroke-width: 1.6; }}
svg .note {{ fill: var(--panel); stroke: var(--line); stroke-width: 1.4; }}
svg .life {{ stroke: var(--line); stroke-width: 1.5; stroke-dasharray: 4 5; }}
svg .a {{ fill: none; stroke-width: 2.2; }}
svg .a-file {{ stroke: var(--file); }} svg .a-ring {{ stroke: var(--ring); stroke-dasharray: 7 5; }}
svg .a-say {{ stroke: var(--ink); }} svg .a-loc {{ stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 5 4; }}
svg .mk-file {{ fill: var(--file); }} svg .mk-ring {{ fill: var(--ring); }} svg .mk-say {{ fill: var(--ink); }} svg .mk-loc {{ fill: var(--muted); }}
.lg-file {{ stroke: var(--file); stroke-width: 2.4; }} .lg-ring {{ stroke: var(--ring); stroke-width: 2.4; stroke-dasharray: 7 5; }}
.lg-say {{ stroke: var(--ink); stroke-width: 2.4; }} .lg-loc {{ stroke: var(--muted); stroke-width: 1.6; stroke-dasharray: 5 4; }}
"""

# The four arrow meanings. A figure uses the ones it needs; the exporter keeps only those in the picture's legend.
LEGEND_TEXT = {"file": "a file written or read", "ring": "a ring (a nudge only)", "say": "a person's words, or Claude's report", "loc": "kept on one machine only"}


def legend_html(texts=None):
    texts = texts or LEGEND_TEXT
    parts = "".join(
        f'<span><svg viewBox="0 0 44 14" aria-hidden="true"><line class="lg-{k}" x1="2" y1="7" x2="42" y2="7"/></svg>{esc(texts[k])}</span>'
        for k in ARROW_KINDS
    )
    return f'<div class="legend" aria-label="How to read the arrows">{parts}</div>'


def render_page(figures, title="Figures", legend_texts=None):
    """figures: [{stem, alt, svg, heading}]. One page the exporter photographs figure by figure."""
    o = ["<!doctype html><meta charset=\"utf-8\">", f"<title>{esc(title)}</title>", f"<style>{CSS}</style>",
         '<div class="wrap">', f"<h1>{esc(title)}</h1>", legend_html(legend_texts)]
    for f in figures:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", f["stem"]):
            raise FigureError(f"stem {f['stem']!r}: use lower-case letters, digits and hyphens")
        if f.get("heading"):
            o.append(f"<h3>{esc(f['heading'])}</h3>")
        o.append(f'<figure data-png="{f["stem"]}"><div class="frame">{f["svg"]}</div><figcaption>{esc(f["alt"])}</figcaption></figure>')
    o.append("</div>")
    return "\n".join(o) + "\n"


# ====================================================================================== embedding in Markdown
def picture_block(stem, alt, mermaid=None, folder="figures"):
    """The Markdown that shows a figure: the dark PNG in dark mode, the light one otherwise, then the Mermaid text closed."""
    if re.search(r'["\n]', alt):
        raise FigureError("alt text may not hold a quote or a line break")
    out = (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{folder}/{stem}-dark.png">\n'
           f'  <img src="{folder}/{stem}.png" alt="{alt}">\n</picture>\n')
    if mermaid:
        out += ("\n<details>\n<summary>The same diagram as Mermaid text (open it to edit)</summary>\n\n"
                f"```mermaid\n{mermaid}\n```\n\n</details>\n")
    return out


# ====================================================================================== building from a spec
def build(spec, out_dir):
    """spec: a module or object with FIGURES, a list of dicts, each with stem, alt and either svg (a string or a
    callable) or seq (a sequence dict, drawn and also written as Mermaid). Optional heading and mermaid.
    Writes out_dir/figures.html, one .svg per figure and one .mmd where there is Mermaid. Returns the figure list."""
    os.makedirs(out_dir, exist_ok=True)
    figures = []
    for f in spec.FIGURES:
        entry = {"stem": f["stem"], "alt": f["alt"], "heading": f.get("heading", "")}
        if "seq" in f:
            entry["svg"] = render_sequence(f["seq"])
            entry["mermaid"] = mermaid_sequence(f["seq"])
        else:
            entry["svg"] = f["svg"]() if callable(f["svg"]) else f["svg"]
            entry["mermaid"] = f.get("mermaid", "")
        figures.append(entry)
    page = render_page(figures, getattr(spec, "TITLE", "Figures"), getattr(spec, "LEGEND", None))
    with open(os.path.join(out_dir, "figures.html"), "w", encoding="utf-8") as handle:
        handle.write(page)
    for entry in figures:
        with open(os.path.join(out_dir, f"{entry['stem']}.svg"), "w", encoding="utf-8") as handle:
            handle.write(entry["svg"].replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1))
        if entry["mermaid"]:
            with open(os.path.join(out_dir, f"{entry['stem']}.mmd"), "w", encoding="utf-8") as handle:
                handle.write(entry["mermaid"] + "\n")
    return figures
