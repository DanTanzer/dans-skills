---
name: readable-diagrams
description: Draws data flow and sequence pictures as hand-laid-out SVGs, light (white) by default, or dark, or both, and embeds the exact Mermaid source and the authoritative Python source in each final SVG. Use it whenever the user asks for a diagram, a figure, a picture, a data flow, a sequence, an architecture drawing, or "how the pieces talk", and whenever a design doc, a README or a guide needs a picture. Use it even when the user says "mermaid", because plain auto-laid-out Mermaid looks generic next to a picture placed by hand; give them both.
---

# readable-diagrams

A picture that a reader takes in at a glance is worth more than a page of text. Auto-laid-out Mermaid diagrams look fine, but Mermaid places every box itself: lines can cross, labels sit on top of the lines, and there is no legend. This skill is a method for placing every part by hand instead, so that every picture in a set matches the others without the next session having to rediscover the method.

The method in one line: place every box and arrow yourself in Python, write each diagram as a self-contained SVG for each theme the doc shows, and embed both the exact Mermaid source and the authoritative Python source inside the final SVG metadata.

## When to use it

Any time a picture of how parts talk to each other would help: a data flow (who writes what, where), a sequence (who says what to whom, in what order), or an architecture overview. Design docs, READMEs and guides often carry these. If the user asks for "a mermaid diagram", make the picture this way and give them the Mermaid text too; they get both. If a later ask modifies or improves the image, update the same diagram's Mermaid source in the final SVG metadata and in the doc's Mermaid block so the editable text stays aligned with the shipped picture.

Do not use it for charts of numbers (that is a chart, not a diagram), for one-off sketches in a chat reply (a short Mermaid block is fine there), or for a UI mock-up.

## What a finished diagram is

1. The SVGs the doc shows, in a subfolder next to the doc: `readable-diagrams/design/` for `design.md`, so `docs/readable-diagrams/design/` for `docs/design.md`. Two docs in one folder share `readable-diagrams/`, and each keeps its pictures together in its own subfolder. `<stem>.svg` is light (white) and `<stem>-dark.svg` is dark. The default is light; the doc gets dark or both when the user asks. Each is a self-contained vector drawing with the arrow legend inside the picture. Each also carries its source in two parts as SVG metadata: the Python spec that drew it and the Mermaid text of that picture. `render.py` embeds both on every export, so the image is the whole wrapper: it alone gives back the editable text and the code that drew it, and the picture and its source are committed together.
2. In the doc, the Markdown that `render.py` prints for each diagram. With both themes, a `<picture>` block that shows the dark SVG in dark mode; with one theme, a plain Markdown image. Then a closed `<details>` block with the same diagram as Mermaid text, so GitHub readers can edit it.
3. Each document's final SVGs are kept in its `readable-diagrams/<doc name>/` folder. Only intermediate build files go in a temporary folder, which `render.py` removes when it ends. The spec and Mermaid text live inside the SVG metadata, so no separate source copies are required.

## How to make one

Below, `scripts/` and `sample/` are in this skill's folder, and DOC.md is the user's document. Read `scripts/example_spec.py` first: it holds three diagrams of a small notes sync, and it is the template for a new set. SCRATCH is the session's scratch folder: a temporary place outside the project, where the spec lives while you work.

1. **Start from a spec.** For a new set, copy `example_spec.py` to `SCRATCH/<doc name>.spec.py`. To recover sources from an existing SVG, run `python3 -I scripts/embed_spec.py extract readable-diagrams/design/PICTURE.svg SCRATCH`. It writes `SCRATCH/PICTURE.spec.py` and, when present, `SCRATCH/PICTURE.mmd`. For a legacy PNG folder, run `python3 -I scripts/migrate_png_to_svg.py PATH/TO/FOLDER`. The helper scans PNGs directly in that folder, recovers readable-diagrams metadata, writes the source files, and generates a matching SVG if one is missing. It leaves the PNGs in place. Rendering executes the recovered Python spec, so only migrate PNGs whose embedded source you trust.
2. **Write the spec.** A spec defines `DIAGRAMS`, each with a `stem`, an `alt` sentence and either `svg` (a function that draws on a `Canvas`) or `seq` (a sequence dict). Decide the stems from the document's section names: `data-flow`, `sequence-1-set-up`, `sequence-2-open`. Give each box the height `diagramlib.box_height(title, lines)` returns: the exact height its text needs. A shorter box stops the build; boxes side by side can share the tallest.
3. **Build the SVGs.** Run `python3 -I scripts/render.py SCRATCH/<doc name>.spec.py --doc DOC.md`. Text in boxes, stores, pills, zone titles and sequences is width-checked at build time. Free labels placed with `label()` are not checked, so inspect the rendered SVGs. The default theme is light; add `--theme dark` or `--theme both` only when the user asks.
4. **Inspect the final SVGs.** They are saved in `readable-diagrams/<doc name>/` next to the doc and each contains its Python and Mermaid sources as metadata. If replacing an SVG fails, the updated version is saved as `name (1).svg` (or the next available number), preserving the original. Check for touching labels, clipped text, arrows crossing text, and file boxes whose last line rides the bottom edge. Fix the spec and rerender if needed.
5. **Paste the Markdown.** Paste each diagram's Markdown where its picture goes, straight from the output. Keep the Mermaid block aligned with the rendered diagram.
6. **Keep later edits synchronized.** When a diagram changes, update the Python spec and Mermaid source together, then rerender so the SVG metadata and doc's Mermaid block match. Editing SVG artwork alone cannot update either source automatically.
7. **Commit the doc and its `readable-diagrams/<doc name>/` folder.** The SVG is the final artifact and keeps its sources in metadata. Legacy PNGs are migration inputs and are not deleted by the helper; do not treat them as the source of truth after migration.

To change the theme later, render again with the new `--theme`. The build removes stale SVGs for themes the doc no longer shows. No raster conversion is part of the SVG workflow.

## The sample

`sample/spec.py` draws this skill's own pipeline, in one data flow and one sequence. When the user asks for the sample, run it with its files kept in the scratch folder: `python3 -I SKILL/scripts/render.py SKILL/sample/spec.py --out SCRATCH/sample --theme both`, with this skill's folder as SKILL. Then show the user the four SVGs in `SCRATCH/sample/`, and open them if you can.

## The house style, and why

These are not decoration. Each one came from something that made a picture hard to read.

- **Four arrow kinds, four meanings, one legend.** Teal solid is a file written or read. Amber dashed is a ring, a nudge that carries no content. Ink solid is a person's words or Claude's report. Grey dashed and thin is data that stays on one machine. diagramlib puts the legend inside every picture, trimmed to the kinds that picture uses, so the picture explains itself when it is pasted somewhere else. Give a new kind of movement one of these four meanings rather than inventing a fifth colour.
- **A straight line first, an elbow second, a diagonal never.** First place the boxes so each arrow runs straight across or straight down: move a box before you bend a line. When two ends still share neither x nor y, draw an elbow with `elbow()`: out of one box, across the gap, into the other, with right-angle bends. A diagonal through a picture of rows and columns reads as noise, so `arrow()` refuses one unless the spec passes `diagonal=True`. `references/layout.md` says where the bend goes.
- **The same panel repeated.** When three machines do the same thing, draw three identical panels at the same y positions. The eye learns one and reuses it. The example does this with fixed constants for every row.
- **Two lines per box: what it is, then what it does.** A bold title and one or two plain lines. File and folder names in the mono face, in dashed boxes, so a file never looks like a process.
- **People are pills, not boxes.** The lavender pill marks a person. Everything else is a machine or a file.
- **Short labels, placed by hand.** A label sits beside its arrow, with a white halo when it crosses a line. diagramlib does not width-check these free labels, so check them in the SVG. When any text does not fit, cut words, not the font.
- **Zones carry an uppercase title and a plain subtitle.** `DESKTOP  owner and host`. The subtitle is the one fact a reader needs about the zone.
- **Both themes, by tokens.** Every colour is a CSS token with a light and a dark value. The dark SVG is a real dark rendering, not an inversion. When the doc shows both, look at the dark one first: many readers work in dark mode.
- **Arial for words, Menlo for names.** Both come with every Mac, so no font is downloaded, and the width checks are measured for them.

## Layout rules that save a round trip

- A sequence row is one message or one two-line note. With five lifelines, a message between neighbours gets about 31 characters; across two lifelines, about 66. Put a long thought in a note, not in an arrow label.
- Mermaid reads `;` and `#` as syntax. The build refuses them in a label; write `,` instead.
- The machine that holds the shared store often needs its script mirrored (local files on the inside, script on the outside) so its file arrows reach the store without crossing anything. The example shows the pattern.
- A ring between every pair of sessions makes a web. Draw one dashed bus above the machines with a two-headed stub into each session instead.
- Keep the picture 1000 units wide. Grow height, never width, so the text stays the same size as the other diagrams.
- Build first, look second. If you are tempted to nudge a number and re-export to see, write down what you saw and change the spec once.

## Files

| File | What |
|---|---|
| `scripts/diagramlib.py` | The library: text widths, box heights, the canvas for data flows, the sequence renderer, the Mermaid writer, the tokens, the card with its legend, and the Markdown picture block |
| `scripts/example_spec.py` | A complete worked example: one data flow and two sequences |
| `scripts/render.py` | Builds and saves SVGs with embedded Python and Mermaid metadata, and prints the Markdown for a doc |
| `scripts/embed_spec.py` | Embeds or extracts Python and Mermaid sources in SVG metadata; can still read legacy PNG metadata for migration |
| `scripts/migrate_png_to_svg.py` | One-time folder helper that recovers sources from legacy PNGs and creates SVGs when missing |
| `scripts/tests/test_render_svg.py` | Checks that document renders keep final SVGs with their embedded sources |
| `scripts/tests/test_svg_metadata.py` | Checks metadata round-trips, corruption handling, extraction safety, and numbered save fallback |
| `scripts/tests/test_migrate_png_to_svg.py` | Checks legacy PNG source recovery and SVG generation |
| `references/layout.md` | The coordinate cookbook: where the rows sit in the example, and how to adapt them to two, three or four machines |
| `HOW-IT-WORKS.md` | For people: the whole process, step by step, built around the sample |
| `sample/` | A small spec and the pictures it makes: the skill's own pipeline, drawn by the skill |

The SVG workflow needs no network access, rasterizer, or external service.
