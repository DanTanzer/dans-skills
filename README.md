# dans-skills

Claude Code skills by Dan Tanzer.

## What is in it

| Skill | What it does |
|---|---|
| `readable-diagrams` | Draws data flow and sequence pictures as hand-laid-out SVG. Exports each as a light PNG, a dark PNG, or both. Keeps Mermaid text under each picture as a text fallback. |

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

The PNG export uses `rsvg-convert`, from librsvg. Install it once with Homebrew:

```bash
brew install librsvg
```

Before the first export, Claude runs the skill's `scripts/doctor.sh` to check the Mac.

[`HOW-IT-WORKS.md`](skills/readable-diagrams/HOW-IT-WORKS.md) walks through one build, step by step, with a small sample.

## Try it

Ask Claude in your own words. Claude asks whether the doc should show light pictures, dark ones, or both. The pictures go in a folder next to the doc, named after it.

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

## Contributing

To fix a skill or add a new one, start with [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT. See [`LICENSE`](LICENSE).
