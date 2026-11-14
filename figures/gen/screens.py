"""Every screened comparison as a dot: net jobs gained against its control, one row per idea family."""
import math

from svgkit import Labeler, Linear, Svg, axis_x, beeswarm, measure, num, table_html, text_box, wrap
from svgkit.text import LINE

ID = "screens"
NARROW = True

DRAWN = ("A", "B", "AB")
SCREEN_NAME = {"A": "half A", "B": "half B", "AB": "both halves (A+B)", "M": "12 hard jobs (other)", "-": "no screen run"}
RULE_ONE, RULE_BOTH = 3, 5

# (label, screen, net): wide text, narrow text
CALLOUTS = {
    ("TF-IDF baseline", "A", 9): ("TF-IDF baseline: had learnt to recognise tickets", "TF-IDF: leakage"),
    ("few-shot examples", "A", 5): ("few-shot examples, one run: +5 on half A, −1 on half B", "few-shot, one run: A +5, B −1"),
    ("contrast pairs in the first prompt", "AB", -12): ("contrast pairs on A+B: −12", "contrast pairs: −12"),
    ("Gemma-26B-A4B, production wording", "AB", 15): ("Gemma-26B-A4B: +15 on 68 of 71, 3 timed out, not counted",
                                                      "Gemma 26B: +15, 3 timed out"),
}


def _count(tries, shown):
    return f"{tries} tries" if shown in (tries, 0) else f"{tries} tries, {shown} drawn"


def _signed(v):
    return f"{v:+d}".replace("-", "−") if v else "0"


def _drawn(r):
    return r["screen"] in DRAWN and r["net"] is not None and r["n"] != 0


def _families(d):
    tries = {f: sum(r["family"] == f for r in d["rows"]) for f in d["families"]}
    return sorted(d["families"], key=lambda f: (-tries[f], d["families"].index(f))), tries


def _classes(r):
    c = r["class_delta"]
    return ", ".join(f"{k} {_signed(c[k])}" for k in ("product", "test", "infra")) if c else ""


def _why(r):
    """The kind of reason logged for a row: class rule, coverage, time, or the leakage check."""
    s = r["reason"] or ""
    return s.split(":")[0] if ":" in s else ("leakage check" if "leakage" in s else "")


def _verdict(d, r):
    return "passed" if r["verdict"] == "pass" else r["verdict"].replace("drop", "dropped")


def _verdict_full(d, r):
    return _verdict(d, r) + (f" ({r['reason']})" if r["reason"] else "")


def _reruns(d):
    """Each pair of a_then_b as (its half-A pass, its half-B runs), from the rows' pair ids alone."""
    by = {}
    for r in d["rows"]:
        if r["pair"] is not None:
            by.setdefault(r["pair"], []).append(r)
    out = []
    for pid, rs in sorted(by.items()):
        a = [r for r in rs if r["screen"] == "A"]
        bs = [r for r in rs if r["screen"] == "B"]
        if len(a) != 1 or a[0]["verdict"] != "pass" or not bs or len(a) + len(bs) != len(rs):
            raise ValueError(f"{ID}: pair {pid} is not one pass on half A with its runs on half B")
        out.append((a[0], bs))
    return out


def _tip(d, r):
    parts = [r["label"], SCREEN_NAME[r["screen"]], f"{r['n']} jobs", f"net {_signed(r['net'])}", _verdict_full(d, r)]
    if r["class_delta"]:
        parts.append(_classes(r))
    if r["control"]:
        parts.append(f"against {r['control']}")
    return " · ".join(parts)


def _noise(d):
    n = d["noise"]
    return (f"In one repeat of the last turn alone, at temperature {n['temperature']}, on the {n['jobs']} jobs of "
            f"half A, {n['answers_changed']} answers changed and {n['right_wrong_switched']} of them switched "
            f"between right and wrong.")


def _marker(g, screen, cx, cy, fill, r):
    if screen == "A":
        g.circle(cx, cy, r, f"c-{fill}")
    elif screen == "B":
        g.circle(cx, cy, r + 1, "bg", ring=False)
        g.circle(cx, cy, r, f"s-{fill}", ring=False)
    else:
        s = r + 1.5
        d = f"M{num(cx)} {num(cy - s)}L{num(cx + s)} {num(cy)}L{num(cx)} {num(cy + s)}L{num(cx - s)} {num(cy)}Z"
        g.path(d, f"c-{fill} ring")


def _legend(g, x, y, width, r):
    """Colour for the verdict, shape for the screen; wraps within width. Returns the bottom y."""
    groups = [("verdict", [("sq", "focus", "passed its rule"), ("sq", "ctl", "dropped")]),
              ("screen", [("A", "ctl", "half A"), ("B", "ctl", "half B"), ("AB", "ctl", "both halves (A+B)")])]
    row_h = 21

    def gw(head, items):
        return measure(head, "t-muted") + 10 + sum(16 + measure(n, "t") + 16 for _, _, n in items) - 16

    cx, cy = x, y
    for head, items in groups:
        if cx > x and cx + gw(head, items) > x + width:
            cx, cy = x, cy + row_h
        mid = cy + row_h / 2
        cx = g.text(cx, mid, head, "t-muted", "start", "middle").box[2] + 10
        for shape, fill, name in items:
            if shape == "sq":
                g.rect(cx + 1, mid - 5, 10, 10, f"c-{fill}", rx=2)
            else:
                _marker(g, shape, cx + 6, mid, fill, r)
            cx = g.text(cx + 16, mid, name, "t", "start", "middle").box[2] + 16
        cx += 20
    return cy + row_h


_DIRS = [(1, 0, "start", "middle"), (-1, 0, "end", "middle"), (0, -1, "middle", "bottom"), (0, 1, "middle", "top"),
         (0.7, -0.7, "start", "bottom"), (-0.7, -0.7, "end", "bottom"), (0.7, 0.7, "start", "top"), (-0.7, 0.7, "end", "top"),
         (0.2, -1, "start", "bottom"), (-0.2, -1, "end", "bottom"), (0.2, 1, "start", "top"), (-0.2, 1, "end", "top")]


def _clear(boxes, px, py, qx, qy, r):
    """True when the leader from the dot at (px, py) to (qx, qy) passes no other blocked box."""
    d = math.hypot(qx - px, qy - py)
    others = [b for b in boxes if not (b[0] <= px <= b[2] and b[1] <= py <= b[3])]
    for k in range(int(d // 2) + 1):
        t = k * 2 / d if d else 0
        if t * d < r:
            continue
        x, y = px + (qx - px) * t, py + (qy - py) * t
        if any(b[0] - 1 <= x <= b[2] + 1 and b[1] - 1 <= y <= b[3] + 1 for b in others):
            return False
    return True


def _callout(g, lab, px, py, s, r):
    """Label a dot at the nearest free spot, wrapping if that helps, on a surface plate with a leader when moved off."""
    variants = [[s], wrap(s, 170, "t"), wrap(s, 120, "t"), wrap(s, 80, "t")]
    for dist in range(4, 240, 6):
        for dx, dy, a, b in _DIRS:
            for lines in variants:
                tx, ty = px + dx * (r + dist), py + dy * (r + dist)
                if b == "middle":
                    ty -= (len(lines) - 1) * LINE * 13 / 2
                x0, y0, x1, y1 = text_box(tx, ty, lines, "t", a, b)
                plate = (x0 - 3, y0 - 2, x1 + 3, y1 + 2)
                if not lab.free(plate):
                    continue
                qx, qy = min(max(px, plate[0]), plate[2]), min(max(py, plate[1]), plate[3])
                dd = math.hypot(qx - px, qy - py)
                if dist > 4 and not _clear(lab.boxes, px, py, qx, qy, r + 1):
                    continue
                lab.block(plate)
                if dist > 4:
                    g.line(px + (qx - px) * (r + 1) / dd, py + (qy - py) * (r + 1) / dd, qx, qy, "leader")
                g.rect(plate[0], plate[1], plate[2] - plate[0], plate[3] - plate[1], "bg", rx=2)
                g.text(tx, ty, lines, "t", a, b)
                return True
    return False


def _cell(cx, cy, others, half=12):
    """The part of a 24 px square around the dot that is nearer to it than to any other dot."""
    poly = [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
    for ox, oy in others:
        if abs(ox - cx) >= 2 * half or abs(oy - cy) >= 2 * half or (ox, oy) == (cx, cy):
            continue
        nx, ny = ox - cx, oy - cy
        c = (ox * ox + oy * oy - cx * cx - cy * cy) / 2
        side = [p[0] * nx + p[1] * ny <= c for p in poly]
        out = []
        for i, p in enumerate(poly):
            j = (i + 1) % len(poly)
            q = poly[j]
            if side[i]:
                out.append(p)
            if side[i] != side[j]:
                t = (c - p[0] * nx - p[1] * ny) / ((q[0] - p[0]) * nx + (q[1] - p[1]) * ny)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        poly = out
    return "M" + "L".join(f"{num(x)} {num(y)}" for x, y in poly) + "Z"


def render(d, width):
    narrow = width < 540
    rows = d["rows"]
    drawn = [r for r in rows if _drawn(r)]
    reruns = _reruns(d)
    ab, oh = d["a_then_b"], d["on_the_halves"]
    if ((len(reruns), sum(any(b["verdict"] == "pass" for b in bs) for _, bs in reruns), len(drawn),
         sum(r["verdict"] == "pass" for r in drawn))
            != (ab["pairs"], ab["pairs_passed_on_b"], oh["comparisons"], oh["passed"])):
        raise ValueError(f"{ID}: rows disagree with a_then_b or on_the_halves")
    fams, tries = _families(d)
    dot_r = 4
    gap = 1

    right = width - 6
    if narrow:
        left = 6
    else:
        left = max(measure(f, "t") for f in fams) + 16
    x = Linear((-13, 16), (left, right))

    svg = Svg(ID, width, None,
              "Net jobs gained against the control for every screened idea, by idea family",
              f"Of the {ab['pairs']} comparisons that passed on half A and were then run on half B against the same "
              f"control in a later run, {ab['pairs_failed_on_b']} failed there, and {oh['passed']} of the "
              f"{oh['comparisons']} comparisons on the two halves passed their rule.")
    back, links, dots, front = svg.g(), svg.g(), svg.g(), svg.g()

    y = _legend(front, 0, 0, width, dot_r) + 10
    notes = [(f"{ab['pairs_failed_on_b']} of the {ab['pairs']} comparisons that passed on half A failed when run "
              f"on half B against the same control in a later run.", "t-strong"),
             (f"A line joins each such pass to its half-B run. {oh['passed']} of the {oh['comparisons']} "
              f"comparisons drawn passed their rule.", "t")]
    for s, cls in notes:
        y = front.text(0, y, wrap(s, width - 6, cls), cls, "start", "top").box[3] + 6
    y += 8

    # Header: the one-half rule label on top so it can run across the both-halves line, which starts below it.
    one = "+3: rule for one half" if not narrow else "+3: one-half rule"
    both = "+5: rule for both halves" if not narrow else "+5: both-halves rule"
    row = 18
    b_one = front.text(x(RULE_ONE) + 5, y, one, "t-strong", "start", "top").box
    b_both = front.text(x(RULE_BOTH) + 5, y + row, both, "t-strong", "start", "top").box
    plot_top = b_both[3] + 8

    # Rows: swarm each family, size the row to its swarm.
    layout = []
    yy = plot_top
    for f in fams:
        pts = [r for r in rows if r["family"] == f and _drawn(r)]
        sw = beeswarm([r["net"] for r in pts], x, dot_r + 1, gap)
        ext = max((abs(o) for _, o in sw), default=0) + dot_r + 3
        label_h = 22 if narrow else 0
        h = max(2 * ext + 12, 40 if not narrow else 30) + label_h
        if any((r["label"], r["screen"], r["net"]) in CALLOUTS for r in pts):
            h += 32 if narrow else 24
        layout.append((f, pts, sw, yy, h, label_h))
        yy += h
    plot_bottom = yy

    for row_ in layout:
        back.line(0 if narrow else left, row_[3], right, row_[3], "grid")
    back.line(x(0), plot_top, x(0), plot_bottom, "axis")
    back.line(x(RULE_ONE), b_one[1] - 1, x(RULE_ONE), plot_bottom, "ref")
    back.line(x(RULE_BOTH), b_both[1] - 1, x(RULE_BOTH), plot_bottom, "ref")
    bottom = axis_x(back, x, [-10, -5, 0, 5, 10, 15], plot_bottom, title="net jobs gained against the control")

    lab = Labeler((0 if narrow else left, plot_top + 2, width - 1, plot_bottom - 2))
    for v in (RULE_ONE, RULE_BOTH):
        lab.block((x(v) - 1, plot_top, x(v) + 1, plot_bottom))
    placed = []
    for f, pts, sw, top, h, label_h in layout:
        cy0 = top + label_h + (h - label_h) / 2
        if narrow:
            b = front.text(left, top + 6, f, "t-strong", "start", "top").box
            b2 = front.text(b[2] + 6, top + 6, _count(tries[f], len(pts)), "t-muted", "start", "top").box
            links.rect(b[0] - 3, b[1] - 1, b2[2] - b[0] + 6, b2[3] - b[1] + 2, "bg", rx=2)
            lab.block(b)
            lab.block(b2)
        else:
            front.text(left - 12, cy0 - 7, f, "t", "end", "middle")
            front.text(left - 12, cy0 + 8, _count(tries[f], len(pts)), "t-muted", "end", "middle")
        if not pts:
            s = "no net count" if narrow else f"{tries[f]} tries with no net count"
            nb = front.text(x(-12), cy0, s, "t-muted", "start", "middle").box
            lab.block(nb)
        order = sorted(range(len(pts)), key=lambda i: (pts[i]["verdict"] == "pass", i))
        centres = [(cx, cy0 + off) for cx, off in sw]
        at = {id(r): c for r, c in zip(pts, centres)}
        for a, bs in reruns:
            if id(a) in at:
                for b in bs:
                    (ax, ay), (bx, by) = at[id(a)], at[id(b)]
                    links.line(ax, ay, bx, by, "leader")
        for i in order:
            r = pts[i]
            cx, cy = centres[i]
            fill = "focus" if r["verdict"] == "pass" else "ctl"
            g = dots.tip(_tip(d, r))
            g.path(_cell(cx, cy, centres), "hit")
            _marker(g, r["screen"], cx, cy, fill, dot_r)
            lab.block((cx - dot_r - 1, cy - dot_r - 1, cx + dot_r + 1, cy + dot_r + 1))
            key = (r["label"], r["screen"], r["net"])
            if key in CALLOUTS:
                placed.append((cx, cy, CALLOUTS[key][1 if narrow else 0], top + label_h, top + h))
    x0, _, x1, _ = lab.bounds
    for cx, cy, s, y0, y1 in placed:
        lab.bounds = (x0, y0 + 2, x1, y1 - 2)
        if not _callout(front, lab, cx, cy, s, dot_r + 1):
            raise ValueError(f"{ID}@{width}: no room for the label {s!r}")

    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    fams, tries = _families(d)
    rows = sorted(d["rows"], key=lambda r: (fams.index(r["family"]), r["time"]))
    out = []
    for r in rows:
        out.append((
            r["label"], r["family"], SCREEN_NAME[r["screen"]] + ("" if _drawn(r) else ", not drawn"),
            r["n"] if r["n"] is not None else "–",
            _signed(r["net"]) if r["net"] is not None else "–",
            _classes(r) or "–", _verdict_full(d, r), r["control"] or "–", r["time"].replace("T", " "),
        ))
    rules = {x["screen"]: x["rule"] for x in d["rules"]}
    other = sum(r["screen"] == "M" for r in d["rows"])
    no_net = sum(r["net"] is None for r in d["rows"])
    empty = sum(r["n"] == 0 for r in d["rows"])
    why = {}
    for r in d["rows"]:
        if _drawn(r) and r["verdict"] != "pass" and _why(r):
            why[_why(r)] = why.get(_why(r), 0) + 1
    whys = f"{sum(why.values())} were dropped: " + ", ".join(
        f"{v} by the {k}" if k == "class rule" else f"{v} for {k}" for k, v in why.items())
    leak = [r for r in d["rows"] if _drawn(r) and r["verdict"] == "pass" and r["reason"]]
    logged_cov = [r for r in d["rows"] if r["verdict"] == "drop (coverage)"]
    if logged_cov != [r for r in logged_cov if not _drawn(r)]:
        raise ValueError(f"{ID}: a row logged as dropped for coverage is drawn")
    caption = (f"All {len(d['rows'])} logged comparisons, by idea family. Rule for one half (A, {d['jobs']['A']} jobs; "
               f"B, {d['jobs']['B']} jobs): {rules['A']}. Rule for both halves: {rules['AB']}. "
               f"The {other} comparisons on the 12-hard-jobs screen are folded into “other” and not drawn, since their "
               f"net counts right answers over three wordings ({rules['M']}); {no_net} rows have no net count and "
               f"{empty} compared no jobs, and these are not drawn either. Of the drawn rows whose net met their "
               f"rule's number, {whys}; {len(leak)} pass was later overturned by a leakage check. "
               f"The reason is given with the verdict. The {why.get('coverage', 0)} dropped for coverage were "
               f"logged as dropped, with the jobs that timed out as the reason; the {len(logged_cov)} "
               f"{'row' if len(logged_cov) == 1 else 'rows'} logged as “dropped (coverage)” had no screen run and "
               f"no net count, so {'it is' if len(logged_cov) == 1 else 'they are'} not drawn.")
    caption += " " + _noise(d)
    return table_html(["Idea", "Family", "Screen", "Jobs", "Net", "Change per class", "Verdict", "Control", "Logged"],
                      out, caption)
