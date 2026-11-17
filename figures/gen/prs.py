"""Timeline of the pull requests by topic: opened to merged, open ones running past the day the record was read."""
import datetime as dt
import math

from svgkit import Svg, legend, measure, num, table_html

ID = "prs"
NARROW = True
POST = "failure-class-data"

BAR = 8     # bar thickness
PITCH = 16  # lane pitch: bar plus gap
HEAD = 8    # width of the arrowhead of an open pull request, drawn past the read day
START = dt.date(2026, 10, 25)
WEEKS = [dt.date(2026, 10, 25), dt.date(2026, 11, 1), dt.date(2026, 11, 8)]


def _day(s):
    return (dt.date.fromisoformat(s) - START).days


def _fmt(s):
    d = dt.date.fromisoformat(s)
    return f"{d.day} {d.strftime('%b')}"


def _days(dates):
    """'12 and 13 Nov' for dates of one month, else each date in full."""
    ds = sorted({dt.date.fromisoformat(s) for s in dates})
    if len({(d.year, d.month) for d in ds}) == 1:
        days = [str(d.day) for d in ds]
        head = ", ".join(days[:-1])
        return f"{head} and {days[-1]} {ds[0].strftime('%b')}" if head else _fmt(ds[0].isoformat())
    full = [_fmt(d.isoformat()) for d in ds]
    return ", ".join(full[:-1]) + " and " + full[-1] if len(full) > 1 else full[0]


def _rows(d):
    """Topics ordered by their first pull request, each with its pull requests packed into lanes."""
    end = _day(d["read"]) + 1
    by = {t: [] for t in d["topics"]}
    for p in d["prs"]:
        by[p["topic"]].append(p)
    rows = []
    for t, prs in by.items():
        prs.sort(key=lambda p: (p["created"], p["number"]))
        lanes = []  # last end per lane
        placed = []
        for p in prs:
            a = _day(p["created"])
            b = _day(p["merged"]) + 1 if p["merged"] else end
            i = next((i for i, last in enumerate(lanes) if last <= a), len(lanes))
            if i == len(lanes):
                lanes.append(b)
            else:
                lanes[i] = b
            placed.append((p, a, b, i))
        merged = sum(1 for p in prs if p["state"] == "merged")
        opened = len(prs) - merged
        count = ", ".join(s for s in (f"{merged} merged" if merged else "", f"{opened} open" if opened else "") if s)
        rows.append({"topic": t, "prs": placed, "lanes": len(lanes), "count": count, "first": prs[0]["created"]})
    rows.sort(key=lambda r: (r["first"], r["topic"]))
    return rows, end


def _tip(p, read):
    when = f"merged {_fmt(p['merged'])}" if p["merged"] else f"open on {_fmt(read)}"
    return f"{p['repo']} #{p['number']}: {p['title']} (opened {_fmt(p['created'])}, {when})"


def _desc(d):
    c = d["counts"]
    first = min(p["created"] for p in d["prs"])
    still = [p["created"] for p in d["prs"] if p["state"] == "open"]
    return (f"Of the {len(d['prs'])} pull requests opened from {_fmt(first)} to {_fmt(d['read'])}, "
            f"{c['merged']} merged within days; the {c['open']} still open were all opened on {_days(still)}, "
            f"among them the decision-model and retry changes.")


def render(d, width):
    narrow = width < 540
    rows, end = _rows(d)
    c = d["counts"]
    read = d["read"]
    svg = Svg(ID, width, None,
              f"Pull requests by topic, {_fmt(min(p['created'] for p in d['prs']))} to {_fmt(read)} 2026",
              _desc(d))
    back, marks, front = svg.g(), svg.g(), svg.g()

    lh = legend(front, [("c-ctl", f"merged ({c['merged']})"), ("c-focus", f"open on {_fmt(read)} ({c['open']})")],
                0, 0, width)
    top = lh + 14

    if narrow:
        x0 = 0
    else:
        x0 = max(max(measure(r["topic"], "t-strong"), measure(r["count"], "t-muted")) for r in rows) + 16
    x1 = width - 1 - HEAD  # end of the read day; open bars carry an arrowhead beyond it
    day = (x1 - x0) / end

    def x(v):
        return x0 + v * day

    # Hit targets tile the lanes; the outer lanes of a row also take the padding and half the row gap,
    # so every lane at the edge of a row gets 24 px.
    gap = 16 if narrow else 12
    y = top
    bounds = []
    for r in rows:
        lanes_h = r["lanes"] * PITCH - (PITCH - BAR)
        if narrow:
            name_w = measure(r["topic"], "t-strong")
            front.text(x0, y, r["topic"], "t-strong", "start", "top")
            front.text(x0 + name_w + 6, y, r["count"], "t-muted", "start", "top")
            ly = y + 13 + 8
            row_h = 13 + 8 + lanes_h + 4
            hit_top = ly - 12
        else:
            row_h = max(lanes_h + 12, 34)
            label_y = y + row_h / 2
            front.text(0, label_y - 2, r["topic"], "t-strong", "start", "bottom")
            front.text(0, label_y + 2, r["count"], "t-muted", "start", "top")
            ly = y + (row_h - lanes_h) / 2
            hit_top = y - gap / 2
        hit_bottom = y + row_h + gap / 2
        for p, a, b, i in r["prs"]:
            bx, bw = x(a) + 1, x(b) - x(a) - 2
            by = ly + i * PITCH
            h0 = hit_top if i == 0 else by - (PITCH - BAR) / 2
            h1 = hit_bottom if i == r["lanes"] - 1 else by + BAR + (PITCH - BAR) / 2
            hx, hw = (bx, bw) if bw >= 24 else (bx + bw / 2 - 12, 24)
            if not p["merged"]:
                hw = width - hx
            g = marks.tip(_tip(p, read), hit=(hx, h0, hw, h1 - h0), min_size=0)
            if p["merged"]:
                g.bar(bx, by, bw, BAR, "c-ctl", "right")
            else:
                g.path(f"M{num(bx)} {num(by)}H{num(x1)}V{num(by - 2)}L{num(width - 1)} {num(by + BAR / 2)}"
                       f"L{num(x1)} {num(by + BAR + 2)}V{num(by + BAR)}H{num(bx)}Z", "c-focus")
        bounds.append((y, y + row_h))
        y += row_h + gap
    base = y - gap + 8

    for (_, b0), (a1, _) in zip(bounds, bounds[1:]):
        back.line(0 if narrow else x0, (b0 + a1) / 2, x1, (b0 + a1) / 2, "grid")
    # Ticks sit at the start of their day, the read day included; the axis end is the end of the read day.
    bottom = base
    for w in WEEKS + [dt.date.fromisoformat(read)]:
        xx = x(_day(w.isoformat()))
        back.line(xx, top - 4, xx, base, "grid")
        s = _fmt(w.isoformat())
        if xx < 1:
            t = front.text(xx, base + 6, s, "t-muted", "start", "top")
        else:
            half = measure(s, "t-muted") / 2
            t = front.text(min(xx, width - half), base + 6, s, "t-muted", "middle", "top")
        bottom = max(bottom, t.box[3])
    back.line(x1, top - 4, x1, base, "axis")
    back.line(x0, base, x1, base, "axis")
    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    prs = sorted(d["prs"], key=lambda p: (p["created"], p["repo"], p["number"]))
    rows = [(f"#{p['number']}", p["repo"], p["title"], p["topic"], p["state"], _fmt(p["created"]),
             _fmt(p["merged"]) if p["merged"] else "") for p in prs]
    c = d["counts"]
    caption = (f"{len(prs)} pull requests opened from {_fmt(prs[0]['created'])} to {_fmt(d['read'])} 2026: "
               f"{c['merged']} merged, {c['open']} open on {_fmt(d['read'])}")
    return table_html(["Number", "Repository", "Title", "Topic", "State", "Opened", "Merged"], rows, caption)
