# Contributing

## Repository layout

The repository, its marketplace and its one plugin all share one name: `dans-skills`. Each skill is a folder under `skills/`.

| Level | Name | Defined by | Where the name shows |
|---|---|---|---|
| Repository | `dans-skills` | This GitHub repository | GitHub, and the clone's folder |
| Marketplace | `dans-skills` | `.claude-plugin/marketplace.json` | `claude plugin marketplace list` |
| Plugin | `dans-skills` | `.claude-plugin/plugin.json` | `dans-skills@dans-skills`, the id you install |
| Skill | `readable-diagrams` | `skills/readable-diagrams/SKILL.md` | `dans-skills:readable-diagrams` in Claude's skill list |

A marketplace is a catalog of plugins. A plugin is what you install and turn on. A skill is one set of instructions that Claude follows. Here the marketplace lists one plugin, the repository itself, and that plugin carries every skill.

```text
dans-skills/                         repository, marketplace and plugin "dans-skills"
├── README.md                        for users: what the skills do, and how to install them
├── CONTRIBUTING.md                  this page
├── LICENSE                          MIT
├── .gitignore                       keeps caches and local tool state out of git
├── .claude-plugin/
│   ├── marketplace.json             marks the repository as a marketplace that lists itself
│   └── plugin.json                  marks the repository as a plugin: name, author, repository
└── skills/
    └── readable-diagrams/           skill "readable-diagrams"
        ├── SKILL.md                 the instructions Claude reads when the skill runs
        ├── HOW-IT-WORKS.md          for people: one build, step by step
        ├── .gitignore               keeps Python caches out of git, so a copied skill stays clean
        ├── references/
        │   └── layout.md            layout numbers, read only when needed
        ├── sample/                  a small spec and the pictures it makes
        └── scripts/                 the code the skill runs
            ├── figlib.py            the drawing library: hand-laid-out SVG in one house style
            ├── render.py            one command: builds a spec, draws its PNGs with rsvg-convert, prints the Markdown
            ├── example_spec.py      a worked example with three figures; copy it to start a set
            ├── doctor.sh            checks the Mac: Python, rsvg-convert and the fonts
            └── tests/
                └── test_figlib.py   checks the example and the sample build, and the text checks refuse what they should
```

The `.gitignore` at the top keeps Python caches and local tool folders out of git. Each skill also keeps its own `.gitignore`, so a skill folder copied on its own stays clean. A new skill is a new folder under `skills/`, with its own `SKILL.md` and its own `.gitignore`.

## Check a change

```bash
claude plugin validate .
cd skills/readable-diagrams/scripts && python3 -m unittest discover -s tests -t .
```
