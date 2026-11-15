# Contributing

## Repository layout

This repository contains the `dans-skills` marketplace and plugin. Each skill lives in its own folder under `skills/`.

| Level | Name | Defined by | Where the name shows |
|---|---|---|---|
| Repository | `dans-skills` | This GitHub repository | GitHub, and the clone's folder |
| Marketplace | `dans-skills` | `.claude-plugin/marketplace.json` | `claude plugin marketplace list` |
| Plugin | `dans-skills` | `.claude-plugin/plugin.json` | `dans-skills@dans-skills`, the id you install |
| Skill | `readable-diagrams` | `skills/readable-diagrams/SKILL.md` | `dans-skills:readable-diagrams` in Claude's skill list |

The marketplace lists the repository's plugin. Install the plugin to use its skills.

```text
dans-skills/                             repository, marketplace and plugin "dans-skills"
├── README.md                            for users: what the skills do, and how to install them
├── CONTRIBUTING.md                      this page
├── LICENSE                              MIT
├── .gitignore                           keeps caches and local tool state out of git
├── .claude-plugin/
│   ├── marketplace.json                 marks the repository as a marketplace that lists itself
│   └── plugin.json                      marks the repository as a plugin: name, author, repository
├── .githooks/
│   └── pre-commit                       runs the readable-diagrams quality gate before each commit
└── skills/
    └── readable-diagrams/               skill "readable-diagrams"
        ├── SKILL.md                     the instructions Claude reads when the skill runs
        ├── HOW-IT-WORKS.md              for people: the SVG workflow, step by step
        ├── .gitignore                   excludes Python caches from the skill folder
        ├── references/
        │   └── layout.md                layout numbers, read only when needed
        ├── sample/                      a small spec and the pictures it makes
        └── scripts/                     the code the skill runs
            ├── diagramlib.py            creates hand-laid-out SVGs with a consistent layout
            ├── render.py                builds final SVGs with embedded source metadata and prints Markdown
            ├── example_spec.py          a worked example with three diagrams; copy it to start a set
            ├── embed_spec.py            embeds/extracts SVG sources and reads legacy PNG metadata
            ├── migrate_png_to_svg.py    recovers sources from legacy PNGs and creates SVGs
            ├── doctor.sh                checks Python and warns when expected fonts are missing
            ├── quality-gate.sh          runs the readable-diagrams unit tests
            └── tests/
                ├── test_diagramlib.py   checks diagram layout, rendering, and generated SVGs
                ├── test_embed_spec.py   checks SVG source extraction and CLI behavior
                ├── test_svg_metadata.py checks SVG metadata encoding, extraction, and failure handling
                ├── test_migrate_png_to_svg.py checks legacy PNG migration
                ├── test_render_svg.py   checks document rendering and embedded sources
                └── pngs.py              small PNG fixtures for migration tests
```

The root `.gitignore` excludes Python caches and local tool files. Each skill also has a `.gitignore`, so it stays clean when copied elsewhere. To add a skill, create a folder under `skills/` with a `SKILL.md` and `.gitignore`.

## Run checks

```bash
claude plugin validate .
bash skills/readable-diagrams/scripts/quality-gate.sh
```

To run the tests automatically before each commit, enable the local hook once:

```bash
git config --local core.hooksPath .githooks
```

The hook runs the tests before each commit and blocks the commit if they fail. GitHub Actions runs the same tests on pull requests and pushes to `main`. To block merges when the tests fail, make `quality-gate / readable-diagrams tests` a required status check in the repository's branch rules.
