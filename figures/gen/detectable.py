"""Smallest difference a paired comparison can show, against the number of labelled tickets."""
import math

from svgkit import Labeler, Linear, Svg, axis_x, axis_y, labels_width, measure, nice_ticks, table_html, text_box, tick_labels, wrap

ID = "detectable"
NARROW = True

R = 5
BAND_NOTE = "too small to show with that many tickets"


def _pts(v):
    return f"{v:g}"


def _mark_lines(m, first):
    head = f"{m['tickets']} tickets" + (": what I had" if first else "")
    return [head, f"{_pts(m['points'])} points"]


def _tip(m, first):
    s = f"{m['tickets']} tickets: smallest difference that shows is about {_pts(m['points'])} points"
    return s + (" (what I had)" if first else "")


def render(d, width):
    narrow = width < 540
    curve, marks = d["curve"], d["marks"]
    m0 = marks[0]
    svg = Svg(ID, width, None,
              "Smallest detectable difference against the number of labelled tickets",
              f"With {m0['tickets']} labelled tickets a paired comparison can show a difference of about "
              f"{_pts(m0['points'])} points and nothing smaller; {_pts(marks[1]['points'])} points would need "
              f"{marks[1]['tickets']} tickets, {_pts(marks[2]['points'])} points {marks[2]['tickets']}.")
    back, front = svg.g(), svg.g()

    yticks = nice_ticks(0, max(c["points"] for c in curve), 5)
    ylabels = tick_labels(yticks)
    left = labels_width(ylabels) + 8
    xmax = nice_ticks(0, curve[-1]["tickets"], 6)[-1]
    right = width - 2 - measure(tick_labels([xmax])[0], "t-muted") / 2
    top = 30
    plot_h = 220 if narrow else 260
    base = top + plot_h
    x = Linear((0, xmax), (left, right))
    y = Linear((0, yticks[-1]), (base, top))

    xy = [(x(c["tickets"]), y(c["points"])) for c in curve]
    back.polyline([(xy[0][0], base)] + xy + [(xy[-1][0], base)], "band", close=True)
    axis_y(back, y, yticks, left, ylabels, grid_to=right, title="smallest detectable difference, points")
    xt = x.ticks(4 if narrow else 6)
    bottom = axis_x(back, x, xt, base, title="labelled tickets")
    front.polyline(xy, "s-focus")

    lab = Labeler((left + 2, top - 8, right, base - 2))
    # Sampled curve points keep labels off the line.
    for (xa, ya), (xb, yb) in zip(xy, xy[1:]):
        n = max(1, int(math.hypot(xb - xa, yb - ya) // 4))
        for i in range(n + 1):
            px, py = xa + (xb - xa) * i / n, ya + (yb - ya) * i / n
            lab.block((px - 2, py - 2, px + 2, py + 2))
    pos = [(x(m["tickets"]), y(m["points"])) for m in marks]
    for px, py in pos:
        lab.block((px - R - 2, py - R - 2, px + R + 2, py + R + 2))

    for i, (m, (px, py)) in enumerate(zip(marks, pos)):
        lines = _mark_lines(m, i == 0)
        g = front.g()
        off = R + 6
        cands = [(px + off, py - off, "start", "bottom"), (px + off + 4, py - off - 14, "start", "bottom"),
                 (px, py - off - 4, "middle", "bottom"), (px - off, py - off, "end", "bottom")]
        placed = None
        for cx, cy, a, b in cands:
            # Two lines: the head in t-strong, the value in t below it.
            hb = text_box(cx, cy - 17, lines[0], "t-strong", a, b)
            vb = text_box(cx, cy, lines[1], "t", a, b)
            box = (min(hb[0], vb[0]), hb[1], max(hb[2], vb[2]), vb[3])
            if lab.free(box):
                lab.block(box)
                placed = (cx, cy, a, b)
                break
        if placed is None:
            raise ValueError(f"{ID}@{width}: no room for the label of {m['tickets']} tickets")
        cx, cy, a, b = placed
        g.text(cx, cy - 17, lines[0], "t-strong", a, b)
        g.text(cx, cy, lines[1], "t", a, b)
        front.tip(_tip(m, i == 0), hit=(px - R, py - R, 2 * R, 2 * R)).circle(px, py, R, "c-focus")

    # The band note sits low in the shaded area, where the curve leaves the most room.
    note = wrap(BAND_NOTE, 150, "t") if narrow else [BAND_NOTE]
    cands = [(x(t), base - 10, "start", "bottom") for t in range(30, 200, 5)]
    for cx, cy, a, b in cands:
        cy -= (len(note) - 1) * 13 * 1.3
        if lab.place(front,[(cx, cy, a, b)], note, "t"):
            break
    else:
        raise ValueError(f"{ID}@{width}: no room for the band note")

    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    marked = {m["tickets"]: m for m in d["marks"]}
    rows = []
    for t in sorted({c["tickets"] for c in d["curve"]} | set(marked)):
        c = next((c for c in d["curve"] if c["tickets"] == t), None)
        if t in marked:
            m = marked[t]
            exact = d["z"] * d["spread"] / math.sqrt(t) * 100
            note = ("what I had, " if m is d["marks"][0] else "") + f"about {_pts(m['points'])}"
            rows.append((t, f"{exact:.1f}", note))
        else:
            rows.append((t, f"{c['points']:.1f}", ""))
    caption = (f"Smallest difference in percentage points that a paired comparison can show, by number of "
               f"labelled tickets: {d['z']} for the confidence wanted, times {d['spread']} for how much paired "
               f"answers vary per ticket, divided by the square root of the tickets; marked rows are the points "
               f"drawn in the figure, with the rounded value shown there")
    return table_html(["Tickets", "Smallest detectable difference (points)", "Marked"], rows, caption)
