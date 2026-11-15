---
name: readable-diagrams
description: Creates hand-laid-out data flow and sequence diagrams from Python specs. Produces standalone SVGs in light or dark themes and embeds the Python spec and Mermaid source in each SVG. Use for diagrams in design docs, READMEs, and guides. Provide both the SVG and Mermaid source when asked for Mermaid.
---

# readable-diagrams

Use this skill to create hand-laid-out SVG diagrams with a consistent style and editable sources. Mermaid's automatic layout can cause crossing lines or overlapping labels, and it does not add a legend.

The Python spec controls each diagram's layout. Every final SVG contains the Python spec and Mermaid source in its metadata.

## When to use it

Use it when a diagram would clarify a data flow, a sequence, or a system architecture. If the user asks for a Mermaid diagram, provide both the SVG and its Mermaid source. When changing a diagram, update the Python spec and Mermaid source together, then rerender the SVG and update the Mermaid block in the document.

Do not use it for data charts, one-off sketches in chat replies, or UI mockups.

## Deliverables

1. **Final SVGs.** Save each document's SVGs in `readable-diagrams/<doc name>/` beside the document. For example, `docs/design.md` uses `docs/readable-diagrams/design/`. `<stem>.svg` is light; `<stem>-dark.svg` is dark. Light is the default. Each SVG is self-contained and includes its Python and Mermaid sources in metadata.
2. **Document content.** Paste the Markdown that `render.py` prints. For both themes, it includes a `<picture>` block that selects the dark SVG in dark mode. For one theme, it uses a Markdown image. If Mermaid source is available, the block also includes it in a closed `<details>` section.
3. **Build files.** `render.py` uses a temporary folder for intermediate files and removes it when finished. No separate source files need to be committed; the SVG contains both sources.

## How to make one

In the steps below, `scripts/` and `sample/` are in this skill's folder, and `DOC.md` is the document being updated. Start with `scripts/example_spec.py`, which contains three diagrams of a notes-sync system. `SCRATCH` is a temporary folder outside the project for the working spec.

1. **Start with a spec.** For new diagrams, copy `example_spec.py` to `SCRATCH/<doc name>.spec.py`. To extract sources from an SVG, run `python3 -I scripts/embed_spec.py extract readable-diagrams/design/PICTURE.svg SCRATCH`. This writes `SCRATCH/PICTURE.spec.py` and, if present, `SCRATCH/PICTURE.mmd`. To migrate legacy PNGs, run `python3 -I scripts/migrate_png_to_svg.py PATH/TO/FOLDER`. It scans PNGs in that folder for embedded metadata, writes the recovered sources, and creates an SVG if one is missing. It leaves the PNGs in place. Rendering runs the recovered Python spec, so review that code before migrating.
2. **Write the spec.** Define `DIAGRAMS` with one entry per diagram. Each entry needs a `stem`, an `alt` sentence, and either `svg` (a function that draws on a `Canvas`) or `seq` (a sequence dictionary). Use descriptive stems such as `data-flow`, `sequence-1-set-up`, or `sequence-2-open`. Set each box height with `diagramlib.box_height(title, lines)`. If a box is too short, the build fails; boxes on the same row can use a shared height.
3. **Build the SVGs.** Run `python3 -I scripts/render.py SCRATCH/<doc name>.spec.py --doc DOC.md`. The renderer checks text in boxes, stores, people markers, zone titles, and sequences. It does not check free labels placed with `label()`, so review those in the SVG. Light is the default theme; use `--theme dark` or `--theme both` when requested.
4. **Review the SVGs.** They are saved in `readable-diagrams/<doc name>/` and include the Python and Mermaid sources. If the renderer cannot replace an SVG, it saves a numbered copy such as `name (1).svg` and keeps the original. Check for overlapping labels, clipped text, arrows crossing text, and text close to box edges. Update the spec and rerender if needed.
5. **Update the document.** Paste each Markdown block where the diagram belongs. Keep the Mermaid text consistent with the SVG.
6. **Keep sources in sync.** For later edits, update the Python spec and Mermaid source, then rerender. Editing SVG artwork alone does not update either source.
7. **Commit the document and its `readable-diagrams/<doc name>/` folder.** The SVG is the published file. Migration leaves legacy PNGs in place; use the SVG as the current version.

To change themes later, rerun with the new `--theme`. The build removes SVGs for themes the document no longer uses.

## The sample

`sample/spec.py` contains one data flow and one sequence. To render it in both themes, run `python3 -I SKILL/scripts/render.py SKILL/sample/spec.py --out SCRATCH/sample --theme both`, where `SKILL` is this skill's folder and `SCRATCH` is a temporary folder. Show the four generated SVGs and open them if possible.

## Diagram style

Use these guidelines to keep diagrams consistent and readable:

- **Use the four arrow styles consistently.** Teal solid means file movement. Amber dashed means a signal. Ink solid means a message. Thin grey dashed means local-only movement. The legend includes only the styles used in each diagram.
- **Prefer horizontal and vertical arrows.** Move boxes to align arrow endpoints. If they cannot align, use `elbow()` for right-angle bends. Use `diagonal=True` only when needed. See `references/layout.md` for examples.
- **Keep repeated panels aligned.** When multiple machines perform the same steps, use the same positions and sizes for their panels.
- **Keep box text concise.** Use a bold title and one or two short lines. Use a monospaced font for file and folder names.
- **Use a lavender pill for a person.** Use boxes for processes and files.
- **Place free labels carefully.** `label()` positions text beside an arrow and can add a white background when text crosses a line. The build does not check free-label widths, so inspect them in the SVG.
- **Use clear zone titles.** Use an uppercase title and a short subtitle, such as `DESKTOP  owner and host`.
- **Support light and dark themes.** Colors are defined for both themes. Review both SVGs when the document shows both.
- **Use Arial for text and Menlo for file names.** The width checks use these fonts.

## Layout guidelines

- Use one message or one two-line note per sequence row. With five lifelines, labels between adjacent lifelines fit about 31 characters; labels spanning two gaps fit about 66. Put longer text in a note.
- Mermaid reads `;` and `#` as syntax. The build refuses them in a label; write `,` instead.
- For a shared store, place each machine's script so its file arrows reach the store without crossing other arrows. The example shows one layout.
- Avoid drawing a ring between every pair of sessions. Use one dashed bus above the machines with a two-headed connection to each session.
- Keep diagrams 1000 units wide. Add height instead of increasing the width.
- Build and inspect before changing coordinates. Note what needs adjustment, update the spec, and rerender.

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
| `references/layout.md` | Layout values and guidance for adapting the sample |
| `HOW-IT-WORKS.md` | A step-by-step guide to the SVG workflow |
| `sample/` | A small spec and the pictures it makes: the skill's own pipeline, drawn by the skill |

The SVG workflow needs no network access or external service.
