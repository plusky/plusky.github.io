"""Diagram: llama-server splits its context into slots, and two real prompts against one slot."""
from gen._diagram import SLACK, check, lines
from svgkit import Svg, list_html, measure, wrap

ID = "slots"
NARROW = True
POST = "failure-class-data"

TITLE = "One context, eight slots"
DESC = ("With --parallel, llama-server can divide --ctx-size among its slots, so each request gets a fraction of "
        "the context you configured.")
CTX, PAR = 262144, 8
SLOT = CTX // PAR
RESERVE = 2048
PROMPTS = [(32300, "32.3k tokens", "in the reserve, failed"), (35300, "35.3k tokens", "2.5k over, failed")]
NOTE = ("The script cuts the prompt by characters, assuming 2.5 characters per token. "
        "Real prompts measure a median of 2.28, so they hold about 10% more tokens than it estimates.")
BAR = 22


def _mixed(g, x, y, parts, where, maxw):
    """Run of (text, cls) pieces on one baseline."""
    cx = x
    for s, cls in parts:
        g.text(cx, y, s, cls)
        cx += measure(s, cls) * (1 if cls == "t-mono" else SLACK) + 4
    if cx - x > maxw:
        check("".join(p for p, _ in parts), "t", 0, where)
    return cx


def _context_bar(g, y, width):
    sw = (width - 2 * (PAR - 1)) / PAR
    for i in range(PAR):
        g.bar(i * (sw + 2), y, sw, 24, "c-focus" if i == 0 else "c-ctl-soft", end="right", r=0)
    return sw


def render(data, width):
    narrow = width < 540
    W, slot_w = (360, 300) if narrow else (720, 560)
    s = Svg(ID, W, 0, TITLE, DESC)
    g = s.g()
    where = f"{ID}@{W}"
    if narrow:
        y = 14
        lines(g, 0, y, [("--ctx-size 262144", "t-mono")], W, where)
        _mixed(g, 0, y + 18, [("divided by", "t"), ("--parallel 8", "t-mono")], where, W)
        lines(g, 0, y + 36, [("= 8 slots of 32,768 tokens", "t-strong")], W, where)
        y += 48
    else:
        y = 14
        _mixed(g, 0, y, [("--ctx-size 262144", "t-mono"), ("divided by", "t"), ("--parallel 8", "t-mono")], where, 420)
        g.text(W, y, "= 8 slots of 32,768 tokens", "t-strong", anchor="end")
        y += 12
    sw = _context_bar(g, y, W)
    if not narrow:
        g.text(8, y + 16.5, "slot 1", "t-on")
    # zoom from slot 1 to the drawn slot
    zy = y + 24 + 34
    g.line(0, y + 24, 0, zy, "leader")
    g.line(sw, y + 24, slot_w, zy, "leader")
    sc = slot_w / SLOT
    res_x = (SLOT - RESERVE) * sc
    g.rect(0, zy, res_x - 2, 24, "c-ctl-soft")
    g.bar(res_x, zy, slot_w - res_x, 24, "c-ctl", end="right")
    g.text(0, zy + 40, "one slot: 32,768 tokens", "t")
    lab_y = zy + 58 if narrow else zy + 40
    g.text(slot_w - 6, lab_y, "2,048 kept for the replies", "t", anchor="end")
    if not narrow:
        check("one slot: 32,768 tokens   2,048 kept for the replies", "t", slot_w - 6, where)
    gap = (zy + 27, lab_y + 6)

    py = lab_y + 22
    pitch = 46 if narrow else 36
    top = zy - 6
    for i, (n, label, verdict) in enumerate(PROMPTS):
        by = py + i * pitch + (18 if narrow else 0)
        if narrow:
            g.text(0, by - 7, f"{label}: {verdict}", "t")
            check(f"{label}: {verdict}", "t", W, where)
        end = n * sc
        if end <= slot_w:
            g.bar(0, by, end, BAR, "c-focus", end="right")
        else:
            g.rect(0, by, slot_w - 1, BAR, "c-focus")
            g.bar(slot_w + 1, by, end - slot_w - 1, BAR, "c-focus flow", end="right")
        if not narrow:
            g.text(10, by + 15.5, label, "t-on")
            g.text(max(end, slot_w) + 10, by + 15.5, verdict, "t")
            check(verdict, "t", W - max(end, slot_w) - 10, where)
    bottom = py + (len(PROMPTS) - 1) * pitch + BAR + (18 if narrow else 0)
    # reserve start and slot end, through the prompts
    for x, cls in ((res_x - 1, "grid"), (slot_w + 0.5, "ref")):
        g.line(x, top, x, gap[0], cls)
        g.line(x, gap[1], x, bottom + 6, cls)
    if not narrow:
        g.text(slot_w + 10, zy + 16.5, "slot ends", "t-muted")

    ny = bottom + 34
    note = wrap(NOTE, W / SLACK, "t")
    lines(g, 0, ny, [(ln, "t") for ln in note], W, where)
    s.height = ny + 18 * (len(note) - 1) + 6
    return s


ITEMS = [
    "The benchmark server ran llama-server with --ctx-size 262144 and --parallel 8.",
    "It divided the context into 8 equal slots of 32,768 tokens; each request got one slot.",
    "The script keeps 2,048 tokens of a slot for the three replies.",
    ("Two real prompts against one slot:", [
        "32.3k tokens: inside the slot, but in the part kept for the replies. The request failed.",
        "35.3k tokens: 2.5k tokens over the slot. The request failed.",
    ]),
    ("The script cuts the prompt by characters, assuming 2.5 characters per token. Real prompts measure a median "
    "of 2.28 characters per token, so they hold about 10% more tokens than it estimates (2.5 / 2.28 = 1.10)."),
]


def table(data):
    return list_html(ITEMS)
