"""Where the class labels come from: people, the gold set by ticket, and the silver set labelled with hindsight."""
import math

from svgkit import Svg, measure, table_html, wrap
from svgkit.text import CAP

ID = "labels"
NARROW = True

BAR = 28
GAP = 2
CLS = {"product": "c-product", "test": "c-test", "infra": "c-infra", "unclear": "c-ctl", "unknown": "c-ctl-soft"}
NAME = {"product": "product bug", "test": "test issue", "infra": "infrastructure", "unclear": "unclear"}


def _n(v):
    return f"{v:,}"


def _header(g, y, width, big, rest):
    """A big number followed by its words, wrapped beside it; returns the y below it."""
    base = y + CAP * 22
    g.text(0, base, big, "t-big")
    x = measure(big, "t-big") + 8
    lines = wrap(rest, width - x, "t-strong")
    g.text(x, base, lines, "t-strong")
    return base + (len(lines) - 1) * 13 * 1.3 + 12


def _tip(g, text, x, y, w, h, width):
    """A tip whose hit area is at least 24 px wide and tall, kept inside [0, width]."""
    if w < 24:
        x, w = x - (24 - w) / 2, 24
    if h < 24:
        y, h = y - (24 - h) / 2, 24
    x = min(max(x, 0), width - w)
    return g.tip(text, hit=(x, y, w, h), min_size=0)


def _split(x0, width, parts):
    """Boxes (x, w, part) for the non-zero parts of a bar from x0 over width, 2 px apart."""
    vals = [p[0] for p in parts if p[0]]
    avail = width - GAP * (len(vals) - 1)
    x, out = x0, []
    for p in parts:
        if p[0]:
            w = avail * p[0] / sum(vals)
            out.append((x, w, p))
            x += w + GAP
    return out


def _segments(g, y, x0, width, parts, full):
    """A tall segmented bar: parts [(value, cls, tip)], each its own block with 4 px corners and its amount inside."""
    for x, w, (v, cls, tip) in _split(x0, width, parts):
        t = _tip(g, tip, x, y, w, BAR, full)
        t.rect(x, y, w, BAR, cls, rx=4)
        label = _n(v)
        # white on the greys is below 4.5:1 in the light theme, so those amounts are left to the tip and the text
        txt = "t-strong" if cls == "band" else None if cls.startswith("c-ctl") else "t-on"
        if txt and measure(label, txt) + 12 <= w:
            g.text(x + 6, y + BAR / 2, label, txt, "start", "middle")


def _legend(g, y, width):
    items = [("c-product", NAME["product"]), ("c-test", NAME["test"]), ("c-infra", NAME["infra"]),
             ("c-ctl-soft", "class unknown"), ("c-ctl", "unclear or another team"), (None, "ticket that does not map cleanly")]
    row_h = 21
    cx, cy = 0, y
    for cls, name in items:
        w = 16 + 6 + measure(name, "t")
        if cx > 0 and cx + w > width:
            cx, cy = 0, cy + row_h
        mid = cy + row_h / 2
        if cls:
            g.rect(cx + 3, mid - 5, 10, 10, cls, rx=2)
        else:
            g.rect(cx + 4, mid - 4, 8, 8, "s-ctl", rx=1)
        g.text(cx + 22, mid, name, "t", "start", "middle")
        cx += w + 18
    return cy + row_h


def render(d, width):
    narrow = width < 540
    h, gold, silver = d["human"], d["gold"], d["silver"]
    hc = h["by_class"]
    infra_silver = silver["by_class"]["infra"]

    svg = Svg(ID, width, None,
              "Where the class labels come from: people, the gold set and the silver set",
              f"People labelled {h['set_by_person']} of {_n(h['failed_with_bug_reference'])} failed jobs with a "
              f"bug reference, and none of the {h['set_by_person_public_ticket']} with a public ticket is infrastructure; "
              f"the {gold['jobs']} gold jobs come from "
              f"{gold['tickets']} tickets, one of them {gold['clusters'][0]['jobs']} jobs; all {infra_silver} "
              f"infrastructure labels come from the {silver['jobs']}-job silver set labelled by a frontier model with hindsight.")
    g = svg.g()

    y = _legend(g, 0, width) + 14

    # Row 1: of all bug references, the few a person set, zoomed and split by class.
    unknown = hc["unknown_ticket_not_public"]
    by_class = [
        (hc["product"], CLS["product"], f"Set by a person, product bug: {hc['product']} jobs"),
        (hc["test"], CLS["test"], f"Set by a person, test issue: {hc['test']} jobs"),
        (unknown, CLS["unknown"], f"Set by a person, ticket that is not public, class unknown: {unknown} jobs"),
        (hc["ticket_other_team"], CLS["unclear"],
         f"Set by a person, ticket of another team: {hc['ticket_other_team']} jobs"),
    ]
    y = _header(g, y, width, str(h["set_by_person"]),
                f"of {_n(h['failed_with_bug_reference'])} failed jobs with a bug reference in "
                f"{h['window_days']} days were labelled by a person") + 10
    (bx, bw, _), (px, pw, _) = _split(0, width, [(h["bots_or_carry_over"],), (h["set_by_person"],)])
    t = _tip(g, f"Set by a bot or carried over: {_n(h['bots_or_carry_over'])} jobs", bx, y, bw, BAR, width)
    t.rect(bx, y, bw, BAR, "band", rx=4)
    g.text(bx + 6, y + BAR / 2, _n(h["bots_or_carry_over"]), "t-strong", "start", "middle")
    inside = "set by a bot or carried over"
    lx = bx + 6 + measure(_n(h["bots_or_carry_over"]), "t-strong") + 5
    if lx + measure(inside, "t") + 6 <= bx + bw:
        g.text(lx, y + BAR / 2, inside, "t", "start", "middle")
    t = _tip(g, f"Set by a person: {h['set_by_person']} jobs", px, y, pw, BAR, width)
    for x, w, (_, cls, _) in _split(px, pw, by_class):
        t.rect(x, y, w, BAR, cls, rx=min(4, w / 2))
    top = y + BAR
    zy = top + 40
    g.line(px, top + 1, 0, zy - 2, "leader")
    g.line(px + pw, top + 1, width, zy - 2, "leader")
    _segments(g, zy, 0, width, by_class, width)
    y = zy + BAR + 8
    note = wrap(f"None of the {h['set_by_person_public_ticket']} with a public ticket is infrastructure.", width, "t-strong")
    g.text(0, y, note, "t-strong", "start", "top")
    y += len(note) * 17
    small = wrap(f"{unknown} point to a ticket that is not public, so their class is unknown; "
                 f"{hc['ticket_other_team']} point to another team's ticket.", width, "t-muted")
    g.text(0, y, small, "t-muted", "start", "top")
    y += len(small) * 16 + 12
    g.line(0, y, width, y, "grid")
    y += 16

    # Row 2: the gold set, one column of squares per ticket, largest first.
    y = _header(g, y, width, str(gold["jobs"]), f"jobs in the gold set, from {gold['tickets']} tickets") + 6
    clusters = gold["clusters"]
    cols = 1 if narrow else 2
    s, sg = 8, 2
    cw = cols * s + (cols - 1) * sg
    cgap = (width - len(clusters) * cw) / (len(clusters) - 1)
    rows = max(math.ceil(c["jobs"] / cols) for c in clusters)
    label_h = 18
    base = y + label_h + rows * (s + sg) - sg
    for i, c in enumerate(clusters):
        cx = i * (cw + cgap)
        nrows = math.ceil(c["jobs"] / cols)
        ctop = base - nrows * (s + sg) + sg
        tip = (f"Ticket {i + 1} of {gold['tickets']}: {c['jobs']} {'job' if c['jobs'] == 1 else 'jobs'}, "
               f"{NAME[c['class']]}{', does not map cleanly onto the three classes' if c['doubtful'] else ''}")
        # in the narrow layout neighbouring hit areas overlap; every ticket is also in the table
        t = _tip(g, tip, cx, ctop, cw, base - ctop, width)
        for j in range(c["jobs"]):
            qx = cx + (cw - s) / 2 if c["jobs"] == 1 else cx + (j % cols) * (s + sg)
            qy = base - (j // cols + 1) * (s + sg) + sg
            if c["doubtful"]:
                t.rect(qx + 1, qy + 1, s - 2, s - 2, "s-ctl", rx=1)
            else:
                t.rect(qx, qy, s, s, CLS[c["class"]], rx=1)
        if i < 4:
            g.text(max(cx + cw / 2, measure(str(c["jobs"])) / 2), ctop - 5, str(c["jobs"]), "t", "middle", "bottom")
    y = base + 10
    note = wrap(f"No ticket is labelled infrastructure. {gold['doubtful_tickets']} of the {gold['tickets']} tickets, with "
                f"{gold['doubtful_jobs']} of the {gold['jobs']} jobs, do not map cleanly onto the three classes"
                + (f", including the largest ({clusters[0]['jobs']} jobs)." if clusters[0]["doubtful"] else "."),
                width, "t-muted")
    g.text(0, y, note, "t-muted", "start", "top")
    y += len(note) * 16 + 12
    g.line(0, y, width, y, "grid")
    y += 16

    # Row 3: the silver set by class.
    y = _header(g, y, width, str(silver["jobs"]), "jobs in the silver set, labelled by a frontier model with hindsight") + 10
    sb, fb = silver["by_class"], silver["confident_by_class"]
    rule = silver["confident_rule"].replace(">=", "at least")
    parts = []
    for k in ("product", "test", "infra", "unclear"):
        tip = f"Silver set, {NAME[k]}: {sb[k]} jobs"
        if k in fb:
            tip += f", {fb[k]} of them confident ({rule})"
        parts.append((sb[k], CLS[k], tip))
    _segments(g, y, 0, width, parts, width)
    y += BAR + 8
    note = wrap(f"The only infrastructure labels: {infra_silver} jobs. {sb['unclear']} stay unclear.",
                width, "t-strong")
    g.text(0, y, note, "t-strong", "start", "top")
    y += (len(note) - 1) * 17 + 13

    svg.height = math.ceil(y + 4)
    return svg


def table(d):
    h, gold, silver = d["human"], d["gold"], d["silver"]
    hc = h["by_class"]
    rows = [
        ("Bug references", "failed jobs with a bug reference", _n(h["failed_with_bug_reference"]),
         f"{h['window_days']} days"),
        ("Bug references", "set by a bot or carried over", _n(h["bots_or_carry_over"]), ""),
        ("Bug references", "set by a person", h["set_by_person"], f"{h['distinct_references']} distinct references"),
        ("Set by a person", "product bug", hc["product"], ""),
        ("Set by a person", "test issue", hc["test"], ""),
        ("Set by a person", "class unknown", hc["unknown_ticket_not_public"], "ticket that is not public"),
        ("Set by a person", "ticket of another team", hc["ticket_other_team"], ""),
        ("Set by a person", "infrastructure", hc["infra"],
         f"none of the {h['set_by_person_public_ticket']} with a public ticket"),
        ("Gold set", "all jobs", gold["jobs"], f"{gold['tickets']} tickets"),
    ]
    for k in ("product", "test"):
        rows.append(("Gold set", NAME[k], gold["by_class"][k], f"{gold['tickets_by_class'][k]} tickets"))
    rows.append(("Gold set", "do not map cleanly onto the three classes", gold["doubtful_jobs"],
                 f"{gold['doubtful_tickets']} tickets"))
    for i, c in enumerate(gold["clusters"]):
        rows.append(("Gold set", f"ticket {i + 1}", c["jobs"],
                     NAME[c["class"]] + (", does not map cleanly" if c["doubtful"] else "")))
    rows.append(("Silver set", "all jobs", silver["jobs"], "labelled by a frontier model with hindsight"))
    rule = silver["confident_rule"].replace(">=", "at least")
    for k in ("product", "test", "infra", "unclear"):
        fb = silver["confident_by_class"].get(k)
        rows.append(("Silver set", NAME[k], silver["by_class"][k],
                     f"{fb} confident ({rule})" if fb is not None else ""))
    caption = ("Where the class labels come from: bug references set by people, the gold set by ticket "
               "(largest first) and the silver set labelled by a frontier model with hindsight")
    return table_html(["Source", "Part", "Jobs", "Note"], rows, caption)
