---
name: readable-diagrams
description: Draws data flow and sequence pictures as hand-laid-out SVG and exports them as light and dark PNGs, with Mermaid text as the fallback under each picture. Use it whenever the user asks for a diagram, a figure, a picture, a data flow, a sequence, an architecture drawing, or "how the pieces talk", and whenever a design doc, a README or a guide needs a picture. Use it even when the user says "mermaid", because plain auto-laid-out Mermaid looks generic next to a picture placed by hand; give them both.
---

# readable-diagrams

A picture that a reader takes in at a glance is worth more than a page of text. Auto-laid-out Mermaid diagrams look fine, but Mermaid places every box itself: lines can cross, labels sit on top of the lines, and there is no legend. This skill is a method for placing every part by hand instead, so that every picture in a set matches the others without the next session having to rediscover the method.

The method in one line: place every box and arrow yourself in Python, render through one HTML page with the house tokens, photograph each figure with the Mac's own Chrome in both themes, and keep Mermaid only as the editable text under the picture.

## When to use it

Any time a picture of how parts talk to each other would help: a data flow (who writes what, where), a sequence (who says what to whom, in what order), or an architecture overview. Design docs, READMEs and guides often carry these. If the user asks for "a mermaid diagram", make the picture this way and give them the Mermaid text too; they get both.

Do not use it for charts of numbers (that is a chart, not a figure), for one-off sketches in a chat reply (a short Mermaid block is fine there), or for a UI mock-up.

## What a finished figure is

1. A light PNG and a dark PNG, named `<stem>.png` and `<stem>-dark.png`, in a `figures` folder next to the Markdown that shows them. 1840 pixels wide (a 920 pixel card at 2x), each with the arrow legend inside the picture.
2. In the Markdown, a `<picture>` block that shows the dark one in dark mode, then a closed `<details>` block with the same diagram as Mermaid text, so GitHub readers can edit it. `figlib.picture_block` writes this.
3. The spec that drew it, kept with the document's build script, so the picture can be changed later without redrawing it.

## How to make one

The scripts live in `scripts/` next to this file. Read `scripts/example_spec.py` first: it holds three figures of a small notes sync, and it is the template for a new set.

1. **Write the spec.** Copy `example_spec.py` to your working folder and replace its content. A spec defines `FIGURES`, each with a `stem`, an `alt` sentence and either `svg` (a function that draws on a `Canvas`) or `seq` (a sequence dict). Decide the stems from the document's section names: `data-flow`, `sequence-1-set-up`, `sequence-2-open`.
2. **Build without pictures first.** `python3 -I scripts/render.py SPEC.py OUT --no-png`. Text in boxes, stores, pills, zone titles and sequences is width-checked at build time, so text that would overflow stops the build with the text named. Free labels placed with `label()` are not checked; step 4 catches them. Shorten the words or widen the box; never shrink the font.
3. **Export.** `bash scripts/doctor.sh` to check the Mac, and `bash scripts/doctor.sh --install` once per copy of the skill (it installs the exporter next to the scripts, with no browser download), then `python3 -I scripts/render.py SPEC.py OUT`. It writes `OUT/figures/*.png` in both themes. If the export cannot run, it prints the doctor's report instead: do what its → lines say. `puppeteer` can also sit in a `node_modules` folder higher up, such as the repo's own; the doctor asks Node, so it finds what the export finds.
4. **Look at every PNG once.** Open each with the Read tool. You are looking for four things: two labels touching, a label past an edge, an arrow crossing text, and a box whose last line rides its bottom edge. Fix the spec and export again. One look per round is enough; the width checks catch the rest.
5. **Embed.** Copy the PNGs into the document's `figures` folder and put the `<picture>` block from `figlib.picture_block(stem, alt, mermaid)` where the picture goes. The Mermaid text for a sequence comes from the build (`OUT/<stem>.mmd`); for a data flow, write a short Mermaid flowchart by hand, or leave the details block out.
6. **Keep the spec.** Commit the spec beside the document's other sources, and commit the PNGs with it.

## The house style, and why

These are not decoration. Each one came from something that made a picture hard to read.

- **Four arrow kinds, four meanings, one legend.** Teal solid is a file written or read. Amber dashed is a ring, a nudge that carries no content. Ink solid is a person's words or Claude's report. Grey dashed and thin is data that stays on one machine. The exporter puts the legend inside every picture, trimmed to the kinds that picture uses, so the picture explains itself when it is pasted somewhere else. Give a new kind of movement one of these four meanings rather than inventing a fifth colour.
- **The same panel repeated.** When three machines do the same thing, draw three identical panels at the same y positions. The eye learns one and reuses it. The example does this with fixed constants for every row.
- **Two lines per box: what it is, then what it does.** A bold title and one or two plain lines. File and folder names in the mono face, in dashed boxes, so a file never looks like a process.
- **People are pills, not boxes.** The lavender pill marks a person. Everything else is a machine or a file.
- **Short labels, placed by hand.** A label sits beside its arrow, with a white halo when it crosses a line. figlib does not width-check these free labels, so check them in the PNG. When any text does not fit, cut words, not the font.
- **Zones carry an uppercase title and a plain subtitle.** `DESKTOP  owner and host`. The subtitle is the one fact a reader needs about the zone.
- **Both themes, by tokens.** Every colour is a CSS token with a light and a dark value. The dark PNG is a real dark rendering, not an inversion. Many readers work in dark mode, so look at the dark one first.
- **Arial for words, Menlo for names.** Both come with every Mac, so the export needs no download, and the width checks are measured for them.

## Layout rules that save a round trip

- A sequence row is one message or one two-line note. With five lifelines, a message between neighbours gets about 31 characters; across two lifelines, about 66. Put a long thought in a note, not in an arrow label.
- Mermaid reads `;` and `#` as syntax. The build refuses them in a label; write `,` instead.
- The machine that holds the shared store often needs its script mirrored (local files on the inside, script on the outside) so its file arrows reach the store without crossing anything. The example shows the pattern.
- A ring between every pair of sessions makes a web. Draw one dashed bus above the machines with a two-headed stub into each session instead.
- Keep the picture 1000 units wide. Grow height, never width, so the text stays the same size as the other figures.
- Build first, look second. If you are tempted to nudge a number and re-export to see, write down what you saw and change the spec once.

## Files

| File | What |
|---|---|
| `scripts/figlib.py` | The library: text widths, the canvas for data flows, the sequence renderer, the Mermaid writer, the page, the tokens and the Markdown picture block |
| `scripts/example_spec.py` | A complete worked example: one data flow and two sequences |
| `scripts/render.py` | One command: build the spec, export light and dark |
| `scripts/export_png.mjs` | The Chrome photographer, driven by `render.py` |
| `scripts/doctor.sh` | Checks Python, Node, Chrome, the fonts and puppeteer; `--install` installs puppeteer once, no browser download |
| `scripts/tests/test_figlib.py` | Builds the example and the sample, checks the SVG is well-formed, checks the width rules refuse what they should |
| `references/layout.md` | The coordinate cookbook: where the rows sit in the example, and how to adapt them to two, three or four machines |
| `HOW-IT-WORKS.md` | For people: the whole process, step by step, built around the sample |
| `sample/` | A small spec and the pictures it makes: the skill's own pipeline, drawn by the skill |

Nothing here needs the network. The exporter runs no Mermaid and no external service.
