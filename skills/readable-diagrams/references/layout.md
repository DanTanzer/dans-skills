# Layout guide

This guide lists the measurements and layout patterns used in `example_spec.py`. Diagrams are 1000 units wide.

## The text sizes

| Class | Use | Size | Width per character |
|---|---|---|---|
| `tb` | a box title, a lifeline name, a person | 15px bold | 7.0 |
| `t` | a plain line, an arrow label | 14px | 6.2 |
| `ts` | a muted aside, a zone subtitle | 12.5px muted | 5.6 |
| `zt` | a zone title, uppercase, letter-spaced | 13px bold | 10.4 |
| `tm tb` | a file or folder name in a big store box | 15px mono bold | 9.03 |
| `tm tb sm` | a file name in a small store box | 12.5px mono bold | 7.53 |

`diagramlib.must_fit` uses these measurements. Arial widths are near the median, so labels at the limit may be slightly too long. Review those labels in the SVG. `zt` uses a wider estimate to leave space for the zone subtitle.

## Data flow layout

The example uses three 300-unit panels at x = 20, 350, and 680, with 30 units between them. The store zone spans the full width below. Panel rows, from top to bottom:

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

Use `box_height` to size the session and script boxes. The last line of text sits 16 units above the bottom edge.

For two machines, use 450-unit panels at x = 20 and 530. Flip the right panel so both scripts face the center. For four machines, use 230-unit panels at x = 20, 265, 510, and 755. Place local files below each script.

## Sequence layout

Place lifelines evenly between x = 60 and x = 910. Show a person without a subtitle as a pill. Each message row is 44 units high; each note is 66 units high and 250 units wide. Move a note inward when its lifeline is near an edge.

Gaps between neighbours for 4 and 5 lifelines, and the label length that fits:

| Lifelines | Gap | Characters between neighbours | Across two |
|---|---|---|---|
| 4 | 283 | 43 | 89 |
| 5 | 212 | 31 | 66 |

Keep each sequence focused on one process. If a flow has two parts, such as an exchange followed by a broadcast, use two diagrams. Split sequences longer than about 14 rows.

## Arrow kinds

| Kind | Looks | Means |
|---|---|---|
| `file` | teal, solid | a file is written or read, over any transport |
| `ring` | amber, dashed | a signal between sessions that carries no content |
| `say` | ink, solid | a person's words, or Claude's report back |
| `loc` | grey, dashed, thin | data that stays on one machine |

A two-headed arrow (`both=True`) means read and write, or a signal that goes in both directions.

## Elbows

Prefer straight arrows. Move boxes so the endpoints share an x or y coordinate. If that would disrupt the layout, use `elbow()` to draw right-angle bends. It accepts the same points, kind, and `both` options as `arrow()`.

| Shape | Call | Use it for |
|---|---|---|
| down, across, down | `elbow(x1, y1, x2, y2, kind)` | a box's bottom edge to the top edge of a box in a lower row |
| across, down, across | `elbow(x1, y1, x2, y2, kind, first="h")` | a box's side to the side of a box in another column |
| one bend, an L | `elbow(x1, y1, x2, y2, kind, at=y2)` | down from a box's bottom edge, then across into the side of a lower box |

Where the bend goes:

- The middle run sits in the gap between the two rows, or the two columns, never through a box and never along a box's edge. Halfway is the default; `at` moves it: a y for `first="v"`, an x for `first="h"`.
- Leave a box from the edge that faces the other box: the bottom or top edge between rows, a side between columns. End on the other box's edge, not short of it.
- Separate elbows that use the same gap by at least 12 units.
- The leg with the arrowhead is at least 16 long, so the head has room; a shorter one stops the build. With `both=True`, the first leg too.
- Label the longest leg: above a run across, beside a run down, as with a straight arrow.

`arrow()` rejects diagonal lines by default. Set `diagonal=True` only when the layout requires them, for example when several arrows connect to one box and elbows would overlap.

## SVG card dimensions

diagramlib builds one card per diagram and theme: the legend entries that diagram uses, then the diagram, on the surface colour with a one-unit border, 920 units wide. The diagram inside is 898 units wide, so a 1000-unit diagram draws at 0.898 scale. Legend entries are spaced 18 units apart and wrap to a second row when needed. The standalone SVG is transparent outside its rounded corners. A diagram that uses only `file` and `say` has a two-entry legend.
