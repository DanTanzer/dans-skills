# dans-skills

Claude Code skills by Dan Tanzer.

## What is in it

| Skill | What it does |
|---|---|
| `readable-diagrams` | Draws hand-laid-out SVG diagrams and embeds the authoritative Python spec and Mermaid source in each final SVG. Includes a one-time helper for recovering sources from legacy PNGs. |

Before and after, for the same data flow. Click a picture for the step-by-step walkthrough.

<table>
  <tr>
    <th>Before: Mermaid's own layout</th>
    <th>After: <code>readable-diagrams</code></th>
  </tr>
  <tr>
    <td>
      <a href="skills/readable-diagrams/HOW-IT-WORKS.md#from-this-mermaids-own-drawings">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcset="skills/readable-diagrams/sample/diagrams/data-flow-mermaid-dark.png">
          <img src="skills/readable-diagrams/sample/diagrams/data-flow-mermaid.png" width="400" alt="Before: the data flow drawn by Mermaid, one long thin strip with small text.">
        </picture>
      </a>
    </td>
    <td>
      <a href="skills/readable-diagrams/HOW-IT-WORKS.md#to-this-the-skills-drawings">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcset="skills/readable-diagrams/sample/diagrams/data-flow-dark.png">
          <img src="skills/readable-diagrams/sample/diagrams/data-flow.png" width="400" alt="After: the same data flow drawn by readable-diagrams, with a legend and every box placed by hand.">
        </picture>
      </a>
    </td>
  </tr>
</table>

## Install

```bash
claude plugin install dans-skills --marketplace DanTanzer/dans-skills
```

Then type `/reload-plugins` in the session. The one-step line needs Claude Code 2.1.275 or later. On an older version, run `claude plugin marketplace add DanTanzer/dans-skills`, then `claude plugin install dans-skills@dans-skills`.

### With the skills CLI

You can also install the skill with Vercel's [`skills`](https://github.com/vercel-labs/skills) CLI.

For all your projects:

```bash
npx skills add DanTanzer/dans-skills --skill readable-diagrams -a claude-code -g
```

For the repo you're in:

```bash
npx skills add DanTanzer/dans-skills --skill readable-diagrams -a claude-code
```

## Before the first picture

The SVG workflow uses Python's standard library and does not require `rsvg-convert`.

[`HOW-IT-WORKS.md`](skills/readable-diagrams/HOW-IT-WORKS.md) is a historical walkthrough of the legacy PNG workflow; the installed skill contains the current SVG-first instructions.

## Try it

Ask Claude in your own words. The SVGs are light (white) unless you ask for dark ones or both. They go in a `readable-diagrams/` folder next to the doc, with one subfolder for each doc, such as `readable-diagrams/design/` for `design.md`. Each SVG carries the Python spec and Mermaid source in metadata, so the SVG is the final artifact to keep.

To migrate legacy PNG diagrams in a folder, run `python3 -I scripts/migrate_png_to_svg.py PATH/TO/FOLDER` from the installed skill directory. It recovers embedded sources and generates an SVG when the matching SVG is missing. It leaves the PNG in place; only PNGs with readable-diagrams source metadata can be migrated. Run this only on PNGs whose embedded Python source you trust, because rendering executes that source. The helper is an import/migration path, not a way to synchronize later edits made directly to an SVG.

To draw the sample that comes with the skill:

```text
Draw the readable-diagrams sample.
```

To add a picture to a doc:

```text
Use readable-diagrams to add a picture of how the parts talk to @docs/design.md.
```

To redraw a Mermaid diagram by hand:

```text
Use readable-diagrams to redraw the Mermaid diagram in @README.md.
```

## How a picture gets made

Claude writes a small Python spec. The skill draws the spec as an SVG and embeds both the Python and Mermaid sources in the SVG metadata. The SVG is kept beside the doc, and the Mermaid text also sits under the picture in the doc, ready to edit. For later changes, update the Python spec and Mermaid together and rerender; editing the SVG image alone cannot update either source.

The data flow of one build, drawn by the skill:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="skills/readable-diagrams/sample/diagrams/data-flow-dark.png">
  <img src="skills/readable-diagrams/sample/diagrams/data-flow.png" width="800" alt="Data flow of one build for design.md. Claude writes design.spec.py, render.py builds an SVG for each diagram and theme, embeds the spec and Mermaid source in each SVG, and saves the SVGs beside design.md.">
</picture>

The same build, in order:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="skills/readable-diagrams/sample/diagrams/build-sequence-dark.png">
  <img src="skills/readable-diagrams/sample/diagrams/build-sequence.png" width="800" alt="One build, in order. Claude writes the spec in its scratch folder and runs render.py. render.py builds the SVGs, embeds the spec and Mermaid source in each, saves them beside the doc, and prints Markdown to paste into the doc.">
</picture>

[`HOW-IT-WORKS.md`](skills/readable-diagrams/HOW-IT-WORKS.md) walks through every step, with the Mermaid text for both pictures.

## Contributing

To fix a skill or add a new one, start with [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT. See [`LICENSE`](LICENSE).
