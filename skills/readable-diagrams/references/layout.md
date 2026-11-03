# Layout cookbook

The numbers behind `example_spec.py`, so a new figure can start from them instead of from zero. All figures are 1000 units wide.

## The text sizes

| Class | Use | Size | Width per character |
|---|---|---|---|
| `tb` | a box title, a lifeline name, a person | 15px bold | 7.0 |
| `t` | a plain line, an arrow label | 14px | 6.2 |
| `ts` | a muted aside, a zone subtitle | 12.5px muted | 5.6 |
| `zt` | a zone title, uppercase, letter-spaced | 13px bold | 10.4 |
| `tm tb` | a file or folder name in a big store box | 15px mono bold | 9.0 |
| `tm tb sm` | a file name in a small store box | 12.5px mono bold | 7.5 |

`figlib.must_fit` uses these. For Arial they sit near the median width, so a label at its limit can run a little long; the look at each PNG catches that. `zt` is the exception: it sits near the widest capitals, because a subtitle that follows the title is placed by it.

## A data flow with machines across the top and a store across the bottom

The example places three 300-wide panels at x = 20, 350 and 680 with a 30 gap, and the store zone at the full width below. The rows inside a panel, from the top:

| Row | y | Height | What |
|---|---|---|---|
| ring bus | 22 | a line | dashed amber, with a two-headed stub down into each session |
| person pill | 40 | 36 | centred on the panel, `words` down and `report` up to the session box |
| panel top | 100 | | the zone rectangle starts; its title sits at y + 24 |
| session box | 134 | 72 | the bold title and two small lines |
| command and results | 206 to 278 | | two say arrows at x + 20 and x + 96 of the script box |
| script box | 278 | 140 | two-line bold title, three plain lines, one muted |
| local files | 278, 332, 386 | 44 each | 110 wide, dashed, mono name and one small line |
| panel bottom | 456 | | |
| file arrows | 418 to 560 | | down at script x + 20, up at x + 96, labels 40 below the script |
| store zone | 516 | 280 | title at y + 24 |
| row A | 560 | 70 | processes in the store zone: a server, a page |
| row B | 660 | 110 | the files: 380, 200 and 300 wide with 20 gaps |

Two machines: use 450-wide panels at x = 20 and 530, and mirror the right panel so both scripts face the middle. Four machines: 230-wide panels at x = 20, 265, 510 and 755, with the local files below the script instead of beside it.

## A sequence

Lifelines are spread evenly between x = 60 and x = 910. The person, the lifeline with no subtitle, is drawn as the pill. Each message row takes 44 units and each note 66. A note is 250 wide and is pulled inside the picture when its lifeline is near an edge.

Gaps between neighbours for 4 and 5 lifelines, and the label length that fits:

| Lifelines | Gap | Characters between neighbours | Across two |
|---|---|---|---|
| 4 | 283 | 43 | 89 |
| 5 | 212 | 31 | 66 |

Keep one story per sequence. When a flow has two parts (an exchange, then a broadcast), make two figures. A sequence longer than about 14 rows is two figures.

## Arrow kinds

| Kind | Looks | Means |
|---|---|---|
| `file` | teal, solid | a file is written or read, over any transport |
| `ring` | amber, dashed | a nudge between sessions that carries no content |
| `say` | ink, solid | a person's words, or Claude's report back |
| `loc` | grey, dashed, thin | data that stays on one machine |

A two-headed arrow (`both=True`) means read and write, or a nudge that goes either way.

## The export card

The exporter builds one card per figure: the legend entries that figure uses, then the SVG, on the surface colour with a one-pixel border, 920 wide, photographed at 2x with a transparent outside. A figure that uses only `file` and `say` gets a two-entry legend.
