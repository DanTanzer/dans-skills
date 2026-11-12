---
name: readable-diagrams
description: Draws data flow and sequence pictures as hand-laid-out SVG and exports them as PNGs, light, dark or both, with Mermaid text as the fallback under each picture. Use it whenever the user asks for a diagram, a figure, a picture, a data flow, a sequence, an architecture drawing, or "how the pieces talk", and whenever a design doc, a README or a guide needs a picture. Use it even when the user says "mermaid", because plain auto-laid-out Mermaid looks generic next to a picture placed by hand; give them both.
---

# readable-diagrams

A picture that a reader takes in at a glance is worth more than a page of text. Auto-laid-out Mermaid diagrams look fine, but Mermaid places every box itself: lines can cross, labels sit on top of the lines, and there is no legend. This skill is a method for placing every part by hand instead, so that every picture in a set matches the others without the next session having to rediscover the method.

The method in one line: place every box and arrow yourself in Python, write each diagram as a self-contained SVG for each theme the doc shows, draw each SVG as a PNG with `rsvg-convert`, and keep Mermaid only as the editable text under the picture.

## When to use it

Any time a picture of how parts talk to each other would help: a data flow (who writes what, where), a sequence (who says what to whom, in what order), or an architecture overview. Design docs, READMEs and guides often carry these. If the user asks for "a mermaid diagram", make the picture this way and give them the Mermaid text too; they get both.

Do not use it for charts of numbers (that is a chart, not a diagram), for one-off sketches in a chat reply (a short Mermaid block is fine there), or for a UI mock-up.

## What a finished diagram is

1. The PNGs the doc shows, in a subfolder next to the doc: `readable-diagrams/design/` for `design.md`, so `docs/readable-diagrams/design/` for `docs/design.md`. Two docs in one folder share `readable-diagrams/`, and each keeps its pictures together in its own subfolder. `<stem>.png` is light (white) and `<stem>-dark.png` is dark. The default is light; the doc gets dark or both when the user asks. Each is 1840 pixels wide (a 920 pixel card at 2x), with the arrow legend inside the picture. Each also carries the spec that drew it, as a `tEXt` chunk named `readable-diagrams-spec`: `render.py` puts it there on every export, so the picture and its source are committed together.
2. In the doc, the Markdown that `render.py` prints for each diagram. With both themes, a `<picture>` block that shows the dark PNG in dark mode; with one theme, a plain Markdown image. Then a closed `<details>` block with the same diagram as Mermaid text, so GitHub readers can edit it.
3. Nothing else is kept. The build writes the SVGs and the Mermaid text in a temporary folder, and `render.py` removes that folder when it ends. The spec lives inside the PNGs, so no copy of it stays on the laptop. The one exception is the option `--keep-svg`, off by default: it keeps each SVG beside its PNG.

## How to make one

Below, `scripts/` and `sample/` are in this skill's folder, and DOC.md is the user's document. Read `scripts/example_spec.py` first: it holds three diagrams of a small notes sync, and it is the template for a new set. SCRATCH is the session's scratch folder: a temporary place outside the project, where the spec lives while you work.

1. **Start from a spec.** For a new set, copy `example_spec.py` to `SCRATCH/<doc name>.spec.py`. For pictures that already exist, take the spec out of one of them and change it rather than starting over: `python3 -I scripts/embed_spec.py extract readable-diagrams/design/PICTURE.png SCRATCH`, with the PNG from the doc's own `readable-diagrams/<doc name>/` folder. It writes `SCRATCH/PICTURE.spec.py`, named after the picture, so pictures never share a spec file.
2. **Write the spec.** A spec defines `DIAGRAMS`, each with a `stem`, an `alt` sentence and either `svg` (a function that draws on a `Canvas`) or `seq` (a sequence dict). Decide the stems from the document's section names: `data-flow`, `sequence-1-set-up`, `sequence-2-open`. Give each box the height `diagramlib.box_height(title, lines)` returns: the exact height its text needs. A shorter box stops the build; boxes side by side can share the tallest.
3. **Build without pictures first.** `python3 -I scripts/render.py SCRATCH/<doc name>.spec.py --doc DOC.md --no-png`. Text in boxes, stores, pills, zone titles and sequences is width-checked at build time, so text that would overflow stops the build with the text named. Free labels placed with `label()` are not checked; step 5 catches them. Shorten the words or widen the box; never shrink the font. The default picture is light (white). Add `--theme dark` or `--theme both` only when the user asks for them; do not ask which one to make.
4. **Export.** `bash scripts/doctor.sh` to check the Mac; when `rsvg-convert` is missing, its → line says `brew install librsvg`. Then run the step 3 command without `--no-png`. `rsvg-convert` draws the PNGs the doc shows into `readable-diagrams/<doc name>/` next to the doc, each PNG takes the spec inside it, and the command prints the Markdown for each diagram. If `rsvg-convert` is missing, the build prints the doctor's report instead: do what its → lines say.
5. **Look at every PNG once.** Open each with the Read tool. You are looking for four things: two labels touching, a label past an edge, an arrow crossing text, and a file box whose last line rides its bottom edge. Then look at each elbow: when shifting one box left or right would let its arrow run straight, shift the box. Fix the spec and export again. One look per round is enough; the width checks catch the rest.
6. **Paste the Markdown.** Paste each diagram's Markdown where its picture goes, straight from the output; do not save it to a file. A sequence gets its Mermaid text from the build. A data flow gets a details block only when its diagram has `mermaid` text: write a short Mermaid flowchart by hand, or leave the block out.
7. **Commit the doc and its `readable-diagrams/<doc name>/` folder.** Every PNG carries the spec that drew it, so the source is committed with the pictures, and no other file is kept. A PNG drawn before the skill did this takes its spec with `python3 -I scripts/embed_spec.py embed PICTURE.png SCRATCH/<doc name>.spec.py`, which reads the PNG first and writes only when its spec is missing or different.

To change the theme later, export again with the new `--theme`: the build removes the doc's PNGs in the theme it no longer shows. To keep the SVGs, add `--keep-svg`: each SVG stays beside its PNG, under the same name. It is off by default, and a build without it removes the SVGs an earlier build kept, so a kept SVG never goes stale. Add it only when the user asks.

## The sample

`sample/spec.py` draws this skill's own pipeline, in one data flow and one sequence. When the user asks for the sample, run it with its files kept in the scratch folder: `python3 -I SKILL/scripts/render.py SKILL/sample/spec.py --out SCRATCH/sample --theme both`, with this skill's folder as SKILL. Then show the user the four PNGs in `SCRATCH/sample/`, and open them if you can.

## The house style, and why

These are not decoration. Each one came from something that made a picture hard to read.

- **Four arrow kinds, four meanings, one legend.** Teal solid is a file written or read. Amber dashed is a ring, a nudge that carries no content. Ink solid is a person's words or Claude's report. Grey dashed and thin is data that stays on one machine. diagramlib puts the legend inside every picture, trimmed to the kinds that picture uses, so the picture explains itself when it is pasted somewhere else. Give a new kind of movement one of these four meanings rather than inventing a fifth colour.
- **A straight line first, an elbow second, a diagonal never.** First place the boxes so each arrow runs straight across or straight down: move a box before you bend a line. When two ends still share neither x nor y, draw an elbow with `elbow()`: out of one box, across the gap, into the other, with right-angle bends. A diagonal through a picture of rows and columns reads as noise, so `arrow()` refuses one unless the spec passes `diagonal=True`. `references/layout.md` says where the bend goes.
- **The same panel repeated.** When three machines do the same thing, draw three identical panels at the same y positions. The eye learns one and reuses it. The example does this with fixed constants for every row.
- **Two lines per box: what it is, then what it does.** A bold title and one or two plain lines. File and folder names in the mono face, in dashed boxes, so a file never looks like a process.
- **People are pills, not boxes.** The lavender pill marks a person. Everything else is a machine or a file.
- **Short labels, placed by hand.** A label sits beside its arrow, with a white halo when it crosses a line. diagramlib does not width-check these free labels, so check them in the PNG. When any text does not fit, cut words, not the font.
- **Zones carry an uppercase title and a plain subtitle.** `DESKTOP  owner and host`. The subtitle is the one fact a reader needs about the zone.
- **Both themes, by tokens.** Every colour is a CSS token with a light and a dark value. The dark PNG is a real dark rendering, not an inversion. When the doc shows both, look at the dark one first: many readers work in dark mode.
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
| `scripts/render.py` | One command: a build writes the SVGs and the Mermaid text in a temporary folder, draws the doc's PNGs with `rsvg-convert` into `readable-diagrams/<doc name>/`, puts the spec inside each PNG, prints the Markdown and removes the temporary folder |
| `scripts/embed_spec.py` | Puts a spec inside a PNG as a `tEXt` chunk and gets it back: `embed PNG SPEC.py` reads before it writes and a PNG never holds two specs; `extract PNG [DIR]` writes the spec byte for byte to `<PNG name>.spec.py`, so pictures in one folder never share a file |
| `scripts/doctor.sh` | Checks Python, `rsvg-convert` and the fonts; names the Homebrew command for anything missing |
| `scripts/tests/test_diagramlib.py` | Builds the example and the sample, checks each SVG is well-formed and complete on its own, checks the width and height rules refuse what they should, and checks a doc gets its pictures in `readable-diagrams/<doc name>/`, light by default, each carrying its spec once, with no build file kept |
| `scripts/tests/test_embed_spec.py` | Checks the spec comes back byte for byte, the pixels and every other chunk stay untouched, a second embed replaces the first, a PNG that already holds the spec is not written, the four sample pictures carry the current sample spec, and a file that is not a PNG gets a plain message |
| `references/layout.md` | The coordinate cookbook: where the rows sit in the example, and how to adapt them to two, three or four machines |
| `HOW-IT-WORKS.md` | For people: the whole process, step by step, built around the sample |
| `sample/` | A small spec and the pictures it makes: the skill's own pipeline, drawn by the skill |

Nothing here needs the network once `rsvg-convert` is installed. The export runs no Mermaid and no external service.
