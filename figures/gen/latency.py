"""Seconds per decision request against input tokens, one panel per thread setting, with the timeout."""
import math

from svgkit import Labeler, Linear, Svg, axis_x, axis_y, labels_width, measure, table_html, text_box, tick_labels

ID = "latency"
NARROW = True
POST = "failure-class-data"

ORDER = ["t8b16-2q", "t16b32-2q", "t8b16", "t16b32"]  # columns: threads; rows: questions
YMAX = 500
XMAX = 50000
RIGHT = 22
WORDS = {2: "two", 4: "four"}
ON = "on_128"  # the fit's estimates over the confirmation requests
N_FIT = int(ON.split("_")[1])


def _threads(d, s):
    return d["settings"][s].split(",")[0]


def _questions(d, s):
    return d["settings"][s].split(",")[-1].strip()


def _name(d, s):
    return f"{_threads(d, s)}, {_questions(d, s)}"


def _secs(v):
    return f"{v:.1f}"


def _bursts(d):
    """Each burst placed at the input tokens of the chosen-setting request it repeats."""
    chosen = [p for p in d["points"] if p["setting"] == d["chosen"]]
    out = []
    for b in d["bursts"]:
        match = [p for p in chosen if p["secs"] == b["alone_s"]]
        if len(match) != 1:
            raise ValueError(f"{ID}: burst alone time {b['alone_s']} matches {len(match)} requests")
        out.append({**b, "tokens": match[0]["tokens"]})
    return out


def _hardware(d):
    return d["hardware"].split(" (")[0]


def _sub(d, s):
    o = d["fits"][s][ON]
    return (f"fitted over {N_FIT} requests: median {o['median']} s, "
            f"{o['over_300'] or 'none'} over {d['timeout_s']} s")


def _desc(d):
    chosen, timeout = d["chosen"], d["timeout_s"]
    four = chosen.removesuffix("-2q")
    pts4 = [p["secs"] for p in d["points"] if p["setting"] == four]
    o = d["fits"][chosen][ON]
    burst = " or ".join(WORDS[n] for n in sorted({b["at_once"] for b in d["bursts"] if b["secs"] > timeout}))
    return (f"With {_threads(d, chosen)} and {_questions(d, chosen)} per request, a linear fit over the {N_FIT} "
            f"confirmation requests estimates a median of {o['median']} seconds and "
            f"{o['over_300'] or 'none'} over the {timeout}-second limit. Measured: with {_questions(d, four)} the "
            f"slowest of {len(pts4)} timed requests took {_secs(max(pts4))} seconds on the longest prompt, and "
            f"some requests sent {burst} at once went over the limit.")


def _burst_mark(g, px, py, n):
    """2 at once: an open ring; 4 at once: an open diamond. Both keep a surface fill so lines do not show through."""
    if n == 2:
        g.circle(px, py, 4.5, "bg", ring=False)
        g.circle(px, py, 4.5, "s-focus", ring=False)
    else:
        g.polyline([(px, py - 6), (px + 6, py), (px, py + 6), (px - 6, py)], "bg", close=True)
        g.polyline([(px, py - 6), (px + 6, py), (px, py + 6), (px - 6, py)], "s-focus", close=True)


def _legend(g, items, x, y, width):
    """Swatches of mixed kinds with names, wrapping within width; returns the height."""
    row_h = 21
    cx, cy = x, y
    for kind, cls, name in items:
        sw = 0 if kind == "none" else 22
        w = sw + measure(name)
        if cx > x and cx + w > x + width:
            cx, cy = x, cy + row_h
        mid = cy + row_h / 2
        if kind == "dotline":
            g.line(cx, mid, cx + 16, mid, "s-" + cls[2:])
            g.circle(cx + 8, mid, 4, cls)
        elif kind == "burst":
            _burst_mark(g, cx + 8, mid, cls)
        g.text(cx + sw, mid, name, "t", "start", "middle")
        cx += w + 18
    return cy + row_h - y


def _panel(svg, d, s, x0, x1, top, ph, ylabels_on, xlabels_on, xtitle, bursts):
    chosen = s == d["chosen"]
    fill, stroke = ("c-focus", "s-focus") if chosen else ("c-ctl", "s-ctl")
    fit = d["fits"][s]
    back, mid, front = svg.g(), svg.g(), svg.g()

    front.text(x0, top, _name(d, s) + (" (chosen)" if chosen else ""), "t-strong" if chosen else "t", "start", "top")
    front.text(x0, top + 19, _sub(d, s), "t-strong" if chosen else "t-muted", "start", "top")

    pt = top + 44
    base = pt + ph
    x = Linear((0, XMAX), (x0, x1))
    y = Linear((0, YMAX), (base, pt))
    yt = [0, 100, 200, 300, 400, 500]
    if ylabels_on:
        axis_y(back, y, yt, x0, tick_labels(yt[:-1]) + [f"{yt[-1]} s"], grid_to=x1)
    else:
        for t in yt:
            back.line(x0, y(t), x1, y(t), "grid")
    xt = list(range(0, XMAX + 1, 10000))
    bottom = base
    if xlabels_on:
        bottom = axis_x(back, x, xt, base, title="input tokens" if xtitle else None)
    else:
        back.line(x0, base, x1, base, "axis")

    lab = Labeler((x0, pt, x1, base))
    ly = y(d["timeout_s"])
    back.line(x0, ly, x1, ly, "ref")
    lab.block((x0, ly - 1, x1, ly + 1))

    pts = sorted((p for p in d["points"] if p["setting"] == s), key=lambda p: p["tokens"])
    t0, t1 = pts[0]["tokens"], pts[-1]["tokens"]
    f = lambda t: fit["intercept_s"] + fit["s_per_1000_tokens"] * t / 1000
    mid.line(x(t0), y(f(t0)), x(t1), y(f(t1)), stroke)

    for p in pts:
        px, py = x(p["tokens"]), y(p["secs"])
        tip = f"{_name(d, s)}, {p['tokens']:,} tokens: {_secs(p['secs'])} s measured"
        front.tip(tip, hit=(px - 4, py - 4, 8, 8)).circle(px, py, 4, fill)
        lab.block((px - 5, py - 5, px + 5, py + 5))

    if chosen:
        for t in sorted({b["tokens"] for b in bursts}):
            px = x(t)
            # (y, radius) from the request alone up through its bursts, joined mark edge to mark edge
            stack = [(y(next(p["secs"] for p in pts if p["tokens"] == t)), 5)]
            stack += sorted(((y(b["secs"]), 6) for b in bursts if b["tokens"] == t), reverse=True)
            for (ya, ra), (yb, rb) in zip(stack, stack[1:]):
                if (ya - ra) - (yb + rb) >= 4:
                    mid.line(px, ya - ra, px, yb + rb, "leader")
                    lab.block((px - 1, yb + rb, px + 1, ya - ra))
        for b in bursts:
            px, py = x(b["tokens"]), y(b["secs"])
            tip = (f"{b['at_once']} requests at once, {b['tokens']:,} tokens: {_secs(b['secs'])} s "
                   f"({_secs(b['alone_s'])} s alone)")
            _burst_mark(front.tip(tip, hit=(px - 6, py - 6, 12, 12)), px, py, b["at_once"])
            lab.block((px - 7, py - 7, px + 7, py + 7))
        for b in sorted((b for b in bursts if b["secs"] > d["timeout_s"]), key=lambda b: -b["secs"]):
            px, py = x(b["tokens"]), y(b["secs"])
            s1, s2 = f"{b['at_once']} at once:", f"{_secs(b['secs'])} s"
            cands = [(px + 10, py + dy, "start", "middle") for dy in (0, -6, 6)]
            cands += [(px - 10, py + dy, "end", "middle") for dy in (0, -6, 6)]
            if not lab.place(front, cands, f"{s1} {s2}", "t"):
                h = text_box(0, 0, [s1, s2], "t", "start", "top")[3]
                cands = [(px + sx * 10, py + dy, a, "top") for sx, a in ((1, "start"), (-1, "end"))
                         for dy in (-4 - h, 4)]
                lab.place(front, cands, [s1, s2], "t")

    worst = pts[-1]
    if worst["secs"] > d["timeout_s"]:
        px, py = x(worst["tokens"]), y(worst["secs"])
        lab.place(front, [(px - 9, py, "end", "middle")], f"measured {_secs(worst['secs'])} s", "t")
    lab.place(front, [(x0 + 4, ly - 4, "start", "bottom"), (x1 - 4, ly - 4, "end", "bottom")], "limit", "t-muted")
    return bottom


def render(d, width):
    narrow = width < 540
    svg = Svg(ID, width, None, "Seconds per decision request by input tokens, by threads and questions", _desc(d))
    bursts = _bursts(d)
    items = [("dotline", "c-focus", "chosen setting"), ("dotline", "c-ctl", "other settings")]
    items += [("burst", n, f"{n} sent at once") for n in sorted({b["at_once"] for b in bursts})]
    items += [("none", None, "dots: measured"), ("none", None, "line: linear fit, estimates from it under each title")]
    lh = _legend(svg, items, 0, 0, width)
    left = labels_width(tick_labels([0, 100, 200, 300, 400]) + [f"{YMAX} s"]) + 8
    top = lh + 16
    ph = 150
    bottom = top
    if narrow:
        for i, s in enumerate(ORDER):
            bottom = _panel(svg, d, s, left, width - RIGHT, top, ph, True, True, i == len(ORDER) - 1, bursts)
            top = bottom + 24
    else:
        gap = 32
        pw = (width - left - gap - RIGHT) / 2
        for r in range(2):
            for c in range(2):
                s = ORDER[r * 2 + c]
                x0 = left + c * (pw + gap)
                b = _panel(svg, d, s, x0, x0 + pw, top, ph, c == 0, r == 1, r == 1, bursts)
                bottom = max(bottom, b)
            top = bottom + 22
    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    out = []
    for q in ("two questions", "four questions"):
        sets = [s for s in ORDER if _questions(d, s) == q]
        by = {s: {p["tokens"]: p["secs"] for p in d["points"] if p["setting"] == s} for s in sets}
        tokens = sorted(set().union(*by.values()))
        rows = [[f"{t:,}"] + [_secs(by[s][t]) if t in by[s] else "–" for s in sets] for t in tokens]
        heads = ["Input tokens"] + [", ".join(d["settings"][s].split(", ")[:2]) + " (s)" for s in sets]
        out.append(table_html(heads, rows, f"Measured seconds per request with {q}, by input tokens, on {_hardware(d)}"))
    rows = []
    for s in ORDER:
        f, o = d["fits"][s], d["fits"][s][ON]
        rows.append([_name(d, s) + (" (chosen)" if s == d["chosen"] else ""), f"{f['s_per_1000_tokens']:.2f}",
                     f"{f['intercept_s']:.1f}".replace("-", "−"), f"{f['worst_residual_s']:.1f}",
                     o["median"], o["mean"], o["p90"], o["max"], o["over_300"]])
    out.append(table_html(
        ["Setting", "s per 1,000 tokens", "Intercept (s)", "Largest gap between a point and the line (s)",
         "Median (s)", "Mean (s)", "p90 (s)", "Max (s)", f"Over {d['timeout_s']} s"],
        rows, f"Linear fit per setting, and times estimated from it over the {N_FIT} confirmation requests"))
    rows = [[b["at_once"], f"{b['tokens']:,}", _secs(b["secs"]), _secs(b["alone_s"])] for b in _bursts(d)]
    out.append(table_html(["Requests at once", "Input tokens", "Seconds", "Seconds alone"], rows,
                          f"Measured requests sent at once with {_name(d, d['chosen'])}, against the {d['timeout_s']} s limit"))
    return "".join(out)
