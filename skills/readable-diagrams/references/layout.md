# Layout cookbook

The numbers behind `example_spec.py`, so a new figure can start from them instead of from zero. All figures are 1000 units wide.

## The text sizes

| Class | Use | Size | Width per character |
|---|---|---|---|
| `tb` | a box title, a lifeline name, a person | 15px bold | 7.0 |
| `t` | a plain line, an arrow label | 14px | 6.2 |
| `ts` | a muted aside, a zone subtitle | 12.5px muted | 5.6 |
| `zt` | a zone title, uppercase, letter-spaced | 13px bold | 10.4 |
| `tm tb` | a file or folder name in a big store box | 15px mono bold | 9.03 |
| `tm tb sm` | a file name in a small store box | 12.5px mono bold | 7.53 |

`figlib.must_fit` uses these. For Arial they sit near the median width, so a label at its limit can run a little long; the look at each PNG catches that. `zt` is the exception: it sits near the widest capitals, because a subtitle that follows the title is placed by it.

## A data flow with machines across the top and a store across the bottom

The example places three 300-wide panels at x = 20, 350 and 680 with a 30 gap, and the store zone at the full width below. The rows inside a panel, from the top:

| Row | y | Height | What |
|---|---|---|---|
| ring bus | 22 | a line | dashed amber, with a two-headed stub down into each session |
| person pill | 40 | 36 | centred on the panel, `words` down and `report` up to the session box |
| panel top | 100 | | the zone rectangle starts; its title sits at y + 24 |
| session box | 134 | 84 | the bold title and two small lines |
| command and results | 218 to 278 | | two say arrows at x + 20 and x + 96 of the script box |
| script box | 278 | 148 | two-line bold title, three plain lines, one muted |
| local files | 278, 332, 386 | 44 each | 110 wide, dashed, mono name and one small line |
| panel bottom | 456 | | |
| file arrows | 426 to 560 | | down at script x + 20, up at x + 96, labels 40 below the script |
| store zone | 516 | 280 | title at y + 24 |
| row A | 560 | 70 | processes in the store zone: a server, a page |
| row B | 660 | 110 | the files: 380, 200 and 300 wide with 20 gaps |

The session and script heights come from `box_height`, the exact height their text needs: a box's last line sits 16 above its bottom edge.

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

## Elbows

A straight arrow is the first choice: move a box until the two ends share an x or a y. Look at the picture before you bend a line, because a box shifted a little left or right often lines the two ends up. When they cannot line up, because lining them up would break another row or column, the arrow is an elbow, not a diagonal. `elbow()` takes the same points, kind and `both` as `arrow()`, and draws the link with right-angle bends.

| Shape | Call | Use it for |
|---|---|---|
| down, across, down | `elbow(x1, y1, x2, y2, kind)` | a box's bottom edge to the top edge of a box in a lower row |
| across, down, across | `elbow(x1, y1, x2, y2, kind, first="h")` | a box's side to the side of a box in another column |
| one bend, an L | `elbow(x1, y1, x2, y2, kind, at=y2)` | down from a box's bottom edge, then across into the side of a lower box |

Where the bend goes:

- The middle run sits in the gap between the two rows, or the two columns, never through a box and never along a box's edge. Halfway is the default; `at` moves it: a y for `first="v"`, an x for `first="h"`.
- Leave a box from the edge that faces the other box: the bottom or top edge between rows, a side between columns. End on the other box's edge, not short of it.
- Two elbows through the same gap get lanes of their own, at least 12 apart, so they never merge into one line.
- The leg with the arrowhead is at least 16 long, so the head has room; a shorter one stops the build. With `both=True`, the first leg too.
- Label the longest leg: above a run across, beside a run down, as with a straight arrow.

`arrow()` refuses a diagonal. Pass `diagonal=True` only when the diagonal is the point, such as many arrows fanning into one box, where elbows would share legs.

## The export card

figlib builds one card per figure and theme: the legend entries that figure uses, then the figure, on the surface colour with a one-unit border, 920 wide. The figure inside is 898 wide, so a 1000-wide figure draws at 0.898. Legend entries flow like words, 18 apart, and wrap to a second row when they need it. `rsvg-convert --zoom 2` draws the card at 1840 pixels, transparent outside its rounded corners. A figure that uses only `file` and `say` gets a two-entry legend.
