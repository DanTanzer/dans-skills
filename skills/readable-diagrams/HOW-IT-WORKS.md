# How readable-diagrams works

`readable-diagrams` creates hand-laid-out SVG diagrams from a Python spec. Each SVG contains the Python spec and Mermaid source in its metadata. The current workflow needs only Python's standard library.

## The workflow at a glance

1. Write a Python spec with one entry per diagram. A data-flow entry draws boxes and arrows on a `Canvas`. A sequence entry lists messages for the library to lay out.
2. Run `render.py`. It checks labels and box sizes, builds the SVGs, embeds the source, and saves the files.
3. Review the SVGs and the Markdown printed by the command. Paste the Markdown into the document. If the diagram has Mermaid source, the block includes it in a closed `<details>` section.
4. Commit the document and its `readable-diagrams/<document name>/` folder. The SVG is the final image and includes its source.

For example, from this skill's directory:

```bash
bash scripts/doctor.sh
python3 -I scripts/render.py sample/spec.py --out /tmp/readable-diagrams-sample --theme both
```

To save diagrams beside a document, use `--doc` instead of `--out`:

```bash
python3 -I scripts/render.py SCRATCH/design.spec.py --doc docs/design.md
```

This saves SVGs to `docs/readable-diagrams/design/` and prints Markdown for `docs/design.md`. The default theme is `light`; use `dark` or `both` when requested. A document render removes SVGs for themes the document no longer uses. With `--out`, SVGs and generated `.mmd` files stay in the selected directory.

## Where the source lives

Each final SVG contains its Python source and, if available, its Mermaid text in versioned metadata. The data is compressed, Base64-encoded, and checked with SHA-256. To extract the source without running it:

```bash
python3 -I scripts/embed_spec.py extract docs/readable-diagrams/design/data-flow.svg SCRATCH
```

This writes `data-flow.spec.py` and, if present, `data-flow.mmd` to `SCRATCH`. To update a diagram, edit both source files and rerender. Editing the SVG alone does not update either source.

## Migrating legacy PNGs

For a one-time migration, run:

```bash
python3 -I scripts/migrate_png_to_svg.py PATH/TO/FOLDER
```

The helper scans PNGs in that folder for legacy `readable-diagrams` metadata. When it finds a spec, it writes a `.spec.py` and optional `.mmd`, then creates an SVG if one is missing. It leaves the PNGs in place. Rendering runs the recovered Python spec, so review that code before migrating.

## Building and layout

The renderer uses Python's standard library and the local `diagramlib.py`. For document renders, it creates and removes a temporary build directory. The spec and Mermaid text are embedded in each SVG, so separate source files do not need to be committed.

Specs define `DIAGRAMS`, each with a lowercase `stem`, an `alt` sentence, and either:

- `svg`: a function that draws on a `Canvas` (data flow and architecture diagrams); or
- `seq`: a sequence description that the library lays out and also converts to Mermaid.

Use `diagramlib.box_height(title, lines)` to size boxes. The renderer checks text in boxes and sequence labels, but you still need to review free labels placed with `label()`. Keep diagrams about 1000 units wide. Add height rather than shrinking text. Each SVG contains its own CSS and theme colors.

Use these four arrow styles: teal solid for file movement, amber dashed for signals, ink solid for messages, and thin grey dashed for local-only movement. Use horizontal or vertical arrows when possible; use right-angle elbows when endpoints do not align. Each diagram includes a legend.

## Files

| File | Purpose |
|---|---|
| `scripts/diagramlib.py` | Canvas, layout checks, sequence rendering, Mermaid generation, and Markdown blocks |
| `scripts/render.py` | Builds and saves SVGs with embedded source metadata |
| `scripts/embed_spec.py` | Embeds or extracts SVG metadata; reads legacy PNG metadata for migration |
| `scripts/migrate_png_to_svg.py` | One-time recovery and SVG generation for legacy PNG folders |
| `scripts/doctor.sh` | Checks Python and warns when the expected fonts are not found |
| `sample/spec.py` | Worked example with one data flow and two sequences |
| `references/layout.md` | Coordinate guidance for adapting the sample layout |

Arial and Menlo are the expected fonts for the label-width checks. Missing fonts produce a warning, not a build failure. Review the SVG if your system uses different fonts.
