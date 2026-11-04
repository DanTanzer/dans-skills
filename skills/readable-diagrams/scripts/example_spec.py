"""A worked example: three figures of a small notes sync. To start a new set, copy this file into the doc's runtime
folder as spec.py (SKILL.md, step 2). To build this example on its own, from the skill's folder:

    python3 -I scripts/render.py scripts/example_spec.py --out runtime/example

A spec defines FIGURES: a list of dicts with stem (the PNG name), alt (one sentence a screen reader gets, no quotes)
and either svg (a callable that returns SVG, for a data flow drawn on a Canvas) or seq (a sequence dict).
LEGEND, optional, renames any of the four arrow meanings for this set. box_height gives a box the exact height
its text needs.
"""
from figlib import Canvas, box_height

# ====================================================================================== the data flow
# One panel per machine across the top, the store across the bottom, a ring bus above the machines. Fixed y positions
# keep the three panels identical, which is what makes the picture readable: the eye learns one panel and reuses it.
PANELS = (("a", 20, "LAPTOP A", ""), ("b", 350, "LAPTOP B", ""), ("host", 680, "DESKTOP", "owner and host"))
BUS_Y, PILL_Y, PANEL_Y, PANEL_H = 22, 40, 100, 356
CLAUDE_Y, SCRIPT_Y = 134, 278
SESSION = ("Claude session + skill", [("turns a request into one command", "ts"), ("hook: prints the unread count", "ts")])
SESSION_H = box_height(*SESSION)  # 84: a bold title and two small lines
SCRIPT_TITLE, SCRIPT_LINES = "sync\nscript", ["protocol", "checks", "status"]
SCRIPT_H = box_height(SCRIPT_TITLE, SCRIPT_LINES + ["this folder"], muted_last=True)  # 148: two bold lines, four more
STORE_Y, ROW_A, ROW_B, H = 516, 560, 660, 812

DFD_ALT = ("Data flow of a notes sync. Three machines each run a Claude session and the sync script. The two laptops "
           "reach the store through the sync server on the desktop. The desktop writes the folder directly. "
           "The web page is served from the same folder. Rings pass between sessions and never touch the store.")


def sync_data_flow():
    c = Canvas("sync", 1000, H, DFD_ALT)
    # the ring bus: a dashed line above the machines, a stub with two heads down into each Claude session
    c.raw(f'<line class="a a-ring" x1="60" y1="{BUS_Y}" x2="720" y2="{BUS_Y}"/>')
    c.label(390, BUS_Y - 6, "ring: session to session, a nudge only", "middle", "ts", halo=True)
    for key, px, title, sub in PANELS:
        host = key == "host"
        c.zone(px, PANEL_Y, 300, PANEL_H, title, sub, sub_anchor="end")
        c.pill(px + 150, PILL_Y)
        c.arrow(px + 125, PILL_Y + 36, px + 125, CLAUDE_Y, "say")
        c.arrow(px + 175, CLAUDE_Y, px + 175, PILL_Y + 36, "say")
        c.label(px + 117, PILL_Y + 56, "words", "end")
        c.label(px + 183, PILL_Y + 56, "report")
        c.arrow(px + 40, BUS_Y, px + 40, CLAUDE_Y, "ring", both=True)
        c.box(px + 16, CLAUDE_Y, 268, SESSION_H, *SESSION)
        # the desktop is mirrored: its script sits on the right so its file arrows reach the folder, not the server
        sx = px + 170 if host else px + 16
        lx = px + 24 if host else px + 172
        down, up = sx + 20, sx + 96
        c.arrow(down, CLAUDE_Y + SESSION_H, down, SCRIPT_Y, "say")
        c.arrow(up, SCRIPT_Y, up, CLAUDE_Y + SESSION_H, "say")
        if host:
            c.label(down - 10, CLAUDE_Y + 108, "command", "end")
            c.label(up - 10, CLAUDE_Y + 108, "results", "end")
        else:
            c.label(down + 10, CLAUDE_Y + 108, "command")
            c.label(up + 8, CLAUDE_Y + 108, "results")
        c.box(sx, SCRIPT_Y, 116, SCRIPT_H, SCRIPT_TITLE, SCRIPT_LINES + ["this folder" if host else "HTTP store"], muted_last=True)
        for i, (name, sub2, both) in enumerate((("machine.json", "name, server", False), ("read list", "ids shown", True), ("stamp", "last activity", True))):
            y = SCRIPT_Y + 54 * i
            c.store(lx, y, 110, 44, name, sub2)
            if host:
                c.arrow(sx, y + 22, lx + 110, y + 22, "loc", both)
            else:
                c.arrow(sx + 116, y + 22, lx, y + 22, "loc", both)
        bottom = ROW_B if host else ROW_A
        c.arrow(down, SCRIPT_Y + SCRIPT_H, down, bottom, "file")
        c.arrow(up, bottom, up, SCRIPT_Y + SCRIPT_H, "file")
        ly = SCRIPT_Y + SCRIPT_H + 40
        if host:
            c.label(down - 10, ly, "writes", "end").label(down - 10, ly + 18, "the folder", "end").label(up - 10, ly, "reads it", "end")
        else:
            c.label(down - 10, ly, "put", "end").label(up + 10, ly, "list, get,").label(up + 10, ly + 18, "receipt")
    # the store
    c.zone(20, STORE_Y, 960, H - STORE_Y - 16, "THE STORE", "on the desktop, reached over the network: one folder, one server, one web page", kind="store")
    c.box(40, ROW_A, 520, 70, "sync server", ["HTTP: put, list, get, receipt. Private network only. Plain files underneath."], muted_last=True)
    c.pill(615, ROW_A + 17, "You", 70)
    c.arrow(650, ROW_A + 35, 700, ROW_A + 35, "say")
    c.box(700, ROW_A, 140, 70, "web page", ["read-only, browser"], muted_last=True)
    c.store(40, ROW_B, 380, 110, "notes/<folder>/<note>.md", "one file per note", "written whole, never edited")
    c.store(440, ROW_B, 200, 110, "config.json", "the members and settings", "the owner writes it")
    c.store(660, ROW_B, 300, 110, "devices/  seen/", "one file per machine in each", "who is online, who has seen what")
    c.arrow(200, ROW_A + 70, 200, ROW_B, "file", both=True)
    c.arrow(765, ROW_B, 765, ROW_A + 70, "file")
    c.label(775, ROW_B - 10, "reads", "start", "ts")
    return c.svg()


# ====================================================================================== the sequences
LIFELINES = [("U", "You", ""), ("D", "Desktop", "Claude and script"), ("S", "Store", "folder and server"),
             ("A", "Laptop A", "Claude and script"), ("B", "Laptop B", "Claude and script")]

ASK = {
    "id": "ask", "title": "Ask a question, get the answer", "lifelines": LIFELINES,
    "caption": "A message is one HTTP put that the store turns into one file, with a real receipt. The ring only says where to look.",
    "rows": [
        ("msg", "U", "D", "\"ask laptop A for a note\"", "say"),
        ("note", "D", ["the script checks the text", "before it leaves the machine"]),
        ("msg", "D", "S", "put question, to laptop A", "file"),
        ("msg", "S", "D", "stored, receipt yes", "file"),
        ("msg", "D", "A", "ring: a question is waiting", "ring"),
        ("msg", "A", "S", "list since last seen", "file"),
        ("msg", "S", "A", "the question file", "file"),
        ("note", "A", ["header checked, read list", "updated, seen marker sent"]),
        ("msg", "A", "S", "put answer, to desktop", "file"),
        ("msg", "A", "D", "ring: an answer is waiting", "ring"),
        ("msg", "D", "S", "list, get the answer", "file"),
        ("msg", "D", "U", "shows the answer", "say"),
    ],
}

BROADCAST = {
    "id": "broadcast", "title": "A broadcast, and a late catch-up", "lifelines": LIFELINES,
    "caption": "A broadcast names who answers. A reply goes to one machine, so fan-out is one per message. A machine nobody rang catches up at its next prompt.",
    "rows": [
        ("msg", "U", "D", "\"tell all, laptop A answers\"", "say"),
        ("msg", "D", "S", "note to all, A replies", "file"),
        ("msg", "D", "A", "ring: a note is waiting", "ring"),
        ("msg", "D", "B", "ring: a note is waiting", "ring"),
        ("msg", "B", "S", "list, get the note", "file"),
        ("note", "B", ["reply due: no, not asked.", "reads it, answers nothing"]),
        ("msg", "A", "S", "list, get the note", "file"),
        ("note", "A", ["reply due: yes.", "the answer goes to the desktop"]),
        ("msg", "A", "S", "put answer, to desktop", "file"),
        ("msg", "A", "D", "ring: an answer is waiting", "ring"),
        ("note", "B", ["an hour later you type", "a prompt on laptop B"]),
        ("msg", "B", "S", "hook: count unread", "file"),
        ("msg", "S", "B", "1 unread, 0 waiting", "file"),
        ("msg", "B", "S", "receive: list, get", "file"),
    ],
}

FIGURES = [
    {"stem": "sync-data-flow", "alt": DFD_ALT, "svg": sync_data_flow},
    {"stem": "sync-sequence-1-ask-and-answer", "alt": f"{ASK['title']}. {ASK['caption']}", "seq": ASK},
    {"stem": "sync-sequence-2-broadcast", "alt": f"{BROADCAST['title']}. {BROADCAST['caption']}", "seq": BROADCAST},
]
