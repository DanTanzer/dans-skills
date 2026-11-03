# How readable-diagrams works

`readable-diagrams` is a skill for Claude Code, Anthropic's coding tool. A skill is a folder of instructions and scripts that Claude follows. This skill turns a short Python file into diagrams: PNG (Portable Network Graphics) pictures, one light and one dark.

Mermaid is a common text format for diagrams. GitHub draws Mermaid text by itself. You go from Mermaid's two drawings below to the skill's drawings of the same two diagrams: a data flow and a sequence. All four pictures show the same build.

## From this: Mermaid's own drawings

The data flow:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="sample/figures/data-flow-mermaid-dark.png">
  <img src="sample/figures/data-flow-mermaid.png" alt="The same data flow drawn by Mermaid's automatic layout: one long thin strip with small text.">
</picture>

Mermaid places every box by itself. Fitted to the page, the chart becomes one long strip with small text. The labels sit on grey patches on top of the lines. The last arrow loops back under the whole chart. There is no legend.

The sequence:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="sample/figures/build-sequence-mermaid-dark.png">
  <img src="sample/figures/build-sequence-mermaid.png" alt="The same build as a sequence drawn by Mermaid: every arrow looks the same, and every name repeats at the bottom.">
</picture>

Mermaid draws a sequence fairly well. Still, every arrow looks the same, so a file written and a request cannot be told apart. The vertical lines run through three of the labels. You are a box, like the programs. The long names fill their boxes edge to edge, and every name repeats at the bottom. There is no legend.

These pictures were made once for this page, with Mermaid `11.4.1` in Chrome, at the same width as the skill's pictures. Nothing in this repo remakes them. The skill itself never runs Mermaid.

## To this: the skill's drawings

The data flow:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="sample/figures/data-flow-dark.png">
  <img src="sample/figures/data-flow.png" alt="Data flow of one build. Claude writes spec.py, render.py reads it and writes the page, Chrome reads the page and writes the PNGs, and Claude looks at each PNG.">
</picture>

<details>
<summary>The same diagram as Mermaid text (open it to edit)</summary>

```mermaid
flowchart LR
  you(["You"])
  subgraph mac["YOUR MAC"]
    claude["Claude session + skill"] -->|writes| spec[("spec.py")]
    spec -->|reads| render["render.py + figlib"]
    render -->|writes| outdir[("out/: figures.html, .svg, .mmd")]
    outdir -->|reads| exporter["export_png.mjs + Chrome"]
    exporter -->|writes| pngs[("figures/*.png")]
    pngs -->|looks at each| claude
  end
  you -->|words| claude
  claude -->|report| you
```

</details>

The sequence, which is the whole build in order:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="sample/figures/build-sequence-dark.png">
  <img src="sample/figures/build-sequence.png" alt="One build, in order. Claude writes the spec and runs render.py. render.py draws every figure, then runs the exporter twice, light and dark. Claude looks at each PNG before it goes in a document.">
</picture>

<details>
<summary>The same diagram as Mermaid text (open it to edit)</summary>

```mermaid
sequenceDiagram
  participant U as You
  participant C as Claude (session + skill)
  participant R as render.py (Python + figlib)
  participant F as Files (on this Mac)
  participant X as Chrome (export_png.mjs)
  U->>C: "draw how the parts talk"
  C->>F: writes spec.py
  C->>R: render.py spec.py out
  R->>F: reads spec.py
  Note over R: draws every box and arrow,<br/>checks the text in each box
  R->>F: writes figures.html, svg, mmd
  R->>X: export: light, then dark
  X->>F: opens figures.html
  Note over X: one card per figure:<br/>its legend, then its SVG
  X->>F: writes light and dark PNGs
  R->>C: 2 figures, 4 PNGs
  C->>F: looks at each PNG once
  C->>U: the picture, in your doc
```

</details>

Every box, arrow and label sits where Claude put it. The legend inside each picture explains its arrows. Files are dashed boxes. Programs are solid boxes. A person is a pill. In the sequence, an arrow's colour says what moves: a file, or a request or report.

## TL;DR: the short version

1. Claude writes a small Python file, the spec. In a data flow, the spec places every box, arrow and label by hand. In a sequence, the spec lists the messages in order, and the code places them.
2. `render.py` turns the spec into SVG (Scalable Vector Graphics), using `figlib.py`. It checks that the text in boxes and sequences fits. It puts every figure on one web page.
3. `export_png.mjs` opens that page in the Mac's own Chrome. It photographs each figure twice: once light, once dark.
4. Claude looks at every picture. Then Claude pastes each picture into a document, with the Mermaid text folded underneath.

A build never goes online. Only the one-time install does. `doctor.sh --install` downloads `puppeteer` from npm, the package store for JavaScript. `puppeteer` is a library that drives Chrome from code. It brings 79 more packages with it.

## Step by step, with the sample

The sample in this folder builds the skill's two pictures above: the data flow and the sequence.

| Path | What it is |
|---|---|
| `sample/spec.py` | The input: two figures, in 89 lines of Python |
| `sample/figures/` | The pictures, copied from the build's `out/figures/`, plus Mermaid's drawings of both, for comparison |

### Step 1: Claude writes the spec

A spec is a Python file. figlib reads three names from it. Only `FIGURES` is required.

| Name | What it holds |
|---|---|
| `FIGURES` | One entry per picture |
| `TITLE` | The title of the page that holds the figures |
| `LEGEND` | New words for the four arrow meanings. Give all four. |

Each entry in `FIGURES` has a `stem`, which becomes the file name. It has an `alt`: one sentence for screen readers, with no double quotes. It also has one of two drawing kinds:

- **A data flow** is a Python function that places parts on a `Canvas`. The canvas is 1000 units wide. The top edge is y = 0, and larger y values sit lower. Claude chooses every x and every y.
- **A sequence** is a table of rows. Claude only lists the rows. figlib places them.

The start of the sample's data flow, then three of its parts:

```python
ROW_A, ROW_B, H = 120, 290, 410
COLS = (40, 370, 700)  # three columns, 260 wide, 70 apart: room for one arrow and one short label
W = 260
c = Canvas("flow", 1000, H, DATA_FLOW_ALT)

c.box(COLS[0], ROW_A, W, 72, "Claude session + skill", [("writes the spec, runs the build", "ts")])
c.store(COLS[1], ROW_A, W, 72, "spec.py", "every box and arrow, by hand")
c.arrow(COLS[0] + W, ROW_A + 36, COLS[1], ROW_A + 36, "file").label(335, ROW_A + 28, "writes", "middle")
```

The first four numbers of `box` and `store` are x, y, width and height. A `box` is a program. A `store` is a file. The `"ts"` makes a line small and grey.

`arrow` takes a start point, an end point and a kind. `.label` writes a word at its own x and y. `"middle"` centres that word on its x. The sample also uses a `zone`, the tinted panel for a machine, here YOUR MAC. It also uses a `pill`, which is a person.

An arrow has one of four kinds:

| Kind | Looks | Means |
|---|---|---|
| `file` | Teal, solid | A file is written or read |
| `ring` | Amber, dashed | A nudge that carries no content |
| `say` | Ink, solid | A person's words, or Claude's report |
| `loc` | Grey, dashed, thin | Data that stays on one machine |

In a data flow, the layout is the hard part. The layout is Claude's job. figlib checks and draws a data flow, but places nothing in it by itself.

A sequence is different: figlib places everything. Two rows of the sample's sequence:

```python
("msg", "C", "R", "render.py spec.py out", "say"),
("note", "R", ["draws every box and arrow,", "checks the text in each box"]),
```

A lifeline is the dashed line that runs down from each name. figlib spaces the lifelines evenly:

| Sequence measure | Value |
|---|---|
| First lifeline | x = 60 |
| Last lifeline | x = 910 |
| One message row | 44 units tall |
| One note | 66 units tall |

A message label must fit between its two lifelines.

### Step 2: run render.py

The Mac needs three things:

1. Python 3
2. Node `14.14` or newer, which runs JavaScript outside a browser and brings npm
3. Google Chrome, in `/Applications`

```bash
cd skills/readable-diagrams/scripts
bash doctor.sh                                 # checks the Mac, changes nothing
bash doctor.sh --install                       # once per copy of the skill
python3 -I render.py ../sample/spec.py out
```

The real output of the last command:

```text
built 2 figure(s) in out: data-flow, build-sequence
light: 2 PNG(s)
dark: 2 PNG(s)
PNGs in out/figures. Look at each one once before you ship it.
```

`doctor.sh` checks Python, Node, npm, Chrome, the two fonts and `puppeteer`. It prints one line per check, and a → line under anything missing. It changes nothing.

`doctor.sh --install` also installs `puppeteer` into `scripts/node_modules/`, inside the skill's own folder. It skips `puppeteer`'s own browser download. The export uses the Chrome already on the Mac.

Because the packages live inside the skill's folder, the install runs once per copy of the skill. An installed plugin is its own copy, so it needs its own install.

`puppeteer` does not have to live in the skill's folder. The doctor asks Node to load `puppeteer` from the scripts folder, the same way the export does. Node looks for a `node_modules` folder in the scripts folder and in every folder above it, so a `puppeteer` in your repo's own `node_modules` works too.

Add `--no-png` to stop after the SVG and the page. `SKILL.md` has Claude build that way first. Text that does not fit then shows up before Chrome starts.

Steps 3 to 5 all happen inside this one `render.py` command. `render.py` does four things:

1. It loads the spec file as a Python module.
2. It calls `figlib.build`, which writes the page, the SVG files and the Mermaid files (steps 3 and 4).
3. It runs `node export_png.mjs` twice: light, then dark (step 5).
4. It counts the PNGs each run reports. If one is missing, it stops with "export failed for light:" or "export failed for dark:".

When the export cannot run, `render.py` catches the error and runs `doctor.sh`. That happens when `puppeteer` or Node is missing, or when an export fails. It prints the doctor's report: the same lines the doctor prints on its own.

The `-I` flag runs Python in isolated mode. Isolated mode ignores your own Python settings, such as `PYTHONPATH`. So your settings cannot change which code runs. Isolated mode also leaves the script's folder off the import path. So `render.py` adds its own folder to the path. Without that step, `import figlib` would fail.

### Step 3: figlib draws the SVG, checks the text and writes the Mermaid text

SVG is a picture written as text: shapes and words, each with a position. Each canvas call adds a few SVG elements. So the `store` call from step 1 becomes this SVG (line breaks added):

```xml
<rect class="store" x="370" y="120" width="260" height="72" rx="8"/>
<text class="tm tb" x="386" y="152" text-anchor="start">spec.py</text>
<text class="t" x="386" y="180" text-anchor="start">every box and arrow, by hand</text>
```

The SVG holds no colours. The class names get their colours and fonts from the page in step 4. `store` is the dashed file box. `tm` sets the mono font, Menlo. `tb` sets bold.

Before figlib writes text into a box, a store, a pill, a zone title or a sequence, it checks that the text fits. The estimate is simple: the number of characters, times a width per character. For Arial the width is an average. For Menlo it is exact.

| Text class | Used for | Size, in units | Width per character, in units |
|---|---|---|---|
| `t` | Plain lines and sequence labels | 14 | 6.2, average |
| `tb` | Box titles | 15, bold | 7.0, average |
| `ts` | Small grey lines | 12.5 | 5.6, average |
| `tm tb` | File and folder names in a store | 15, bold Menlo | 9.0, exact |

These numbers are canvas units, though figlib's messages say px. In the PNG, one canvas unit is about 1.8 pixels.

If the estimate is wider than the room, the build stops and names the text. This is a real refusal, from a box line that is too long:

```text
figure error: box line 'Python: draws every SVG figure and checks every label width' needs 330px but has 228px: shorten it or widen the box
```

The fix is fewer words or a wider box, never a smaller font.

Two kinds of text skip the check. The first is a word placed with `label()`, such as every arrow word in the data flow. The second is a zone subtitle. figlib cannot know how much room a free word has. The look in step 6 is their only check.

figlib also writes the sequence as Mermaid text, in `out/build-sequence.mmd`. That text is the closed block under the sequence picture above.

A data flow gets a Mermaid file only when the spec gives one. figlib cannot write one itself. A canvas holds only shapes at positions, so it does not know which box an arrow joins. The sample gives its Mermaid text by hand, under the `"mermaid"` key.

### Step 4: one web page holds every figure

`out/figures.html` holds the arrow legend once, then every figure with its caption. Its style sheet (CSS, Cascading Style Sheets) gives each class a colour and a font.

Every colour is a token: a named colour with a light value and a dark value.

| Token | Used for | Light | Dark |
|---|---|---|---|
| `--surface` | The card behind the figure | `#FFFFFF` | `#141C26` |
| `--ink` | Text and `say` arrows | `#16202B` | `#E7EDF3` |
| `--file` | `file` arrows | `#0A7468` | `#3DD6C2` |
| `--ring` | `ring` arrows | `#B04F08` | `#F4B14F` |

The page switches to the dark values when the browser asks for dark mode. Words use Arial. File names use Menlo. Both fonts come with every Mac, so nothing is downloaded.

You can open `out/figures.html` in a browser to see every figure at once. Do not use the `.svg` files on their own. Without the page's style sheet, every box is black and every arrow is invisible. Nothing in the build reads the `.svg` files. Only the tests use them, to check that each figure is well-formed.

### Step 5: Chrome photographs each figure

`export_png.mjs` is a Node script. It uses `puppeteer` to drive Chrome with no window on screen.

For each theme, the script does five things:

1. It starts the Mac's Chrome on a hidden page, at twice the normal pixel density.
2. It tells the page that the screen is in light mode, or in dark mode.
3. It reads the `--surface` colour back from the page. The light value in the step 4 table proves light mode. The dark value proves dark mode. Any other value stops the export.
4. For each figure, it builds a card 920 pixels wide: the legend, cut down to the arrow kinds this figure uses, then the figure.
5. It photographs the card, then removes it. At twice the density, the PNG is 1840 pixels wide.

The light run writes `<stem>.png`, and the dark run writes `<stem>-dark.png`. The sample's pictures:

| Picture | Size in pixels |
|---|---|
| `data-flow.png` | 1840 × 846 |
| `build-sequence.png` | 1840 × 1370 |

Both sample figures use only two arrow kinds. So each legend shows only two entries.

### Step 6: Claude looks at every PNG once

`SKILL.md` tells Claude to open each PNG with its Read tool. The Read tool shows Claude the image itself. Claude looks for four faults:

1. Two labels touching
2. A label past an edge
3. An arrow crossing text
4. A box whose last line sits on its bottom edge

If Claude finds one, Claude changes the spec and builds again. The width check catches most overflows in boxes and sequences. This look catches the rest, including every free label.

### Step 7: the picture goes into a document

The build leaves the PNGs in `out/figures/`. Claude copies them into a `figures/` folder next to the document. For this page, that folder is `sample/figures/`.

Then Claude calls `figlib.picture_block` from Python. Claude pastes the Markdown it returns into the document:

```python
figlib.picture_block("data-flow", alt, mermaid, folder="sample/figures")
```

The block has two parts. A `<picture>` element shows the dark PNG in dark mode. In light mode it shows the light PNG. A closed `<details>` element holds the Mermaid text, and GitHub draws that text as a plain Mermaid chart.

Anyone can copy or edit the Mermaid text. Editing the text does not change the PNG. To change the picture, change the spec and build again.

The two skill pictures on this page are such blocks.

## What each file does

| File | Kind | Job |
|---|---|---|
| `SKILL.md` | Instructions for Claude | When to use the skill, the steps, and the style rules |
| `HOW-IT-WORKS.md` | Markdown | This page |
| `.gitignore` | git settings | Keeps what a build makes out of git, so a copied skill folder stays clean |
| `scripts/figlib.py` | Python, standard library only | The canvas, sequences, text checks, page, Mermaid text and picture block |
| `scripts/render.py` | Python | One command: build, then export light and dark |
| `scripts/export_png.mjs` | JavaScript, for Node | The photographer |
| `scripts/doctor.sh` | bash | Checks the Mac; `--install` installs `puppeteer` once per copy, without a browser download |
| `scripts/package.json` | JSON (a data file), for npm | The one dependency: `puppeteer` `19.11.1` |
| `scripts/example_spec.py` | Python | A bigger example: one data flow and two sequences |
| `scripts/tests/test_figlib.py` | Python | 18 tests: the example and the sample build, the checks refuse what they should, a zone subtitle stays clear of its title, the doctor finds `puppeteer` where Node does, and a relative output folder works |
| `references/layout.md` | Markdown | Coordinates and sizes for laying out a new figure |
| `sample/` | Python and PNG | The spec and pictures this page walks through |

## Known limits

- **The width check is an average, not a ceiling.** A long label at its limit can run up to about a fifth wider than its estimate. Step 6 catches it.
- **Free labels are not checked.** Words placed with `label()`, and zone subtitles, rely on step 6.
- **The defaults are for a Mac.** The export looks for Chrome in `/Applications`. Set `CHROME_PATH` to use a Chrome somewhere else. Menlo, the font for file names, comes only with macOS.
- **`puppeteer` `19.11.1` is old.** npm warns that versions before `24.15.0` are no longer supported. It still drives today's Chrome. Even so, an upgrade is due.
- **The `.svg` files show black boxes when opened alone.** Only the tests read them.
