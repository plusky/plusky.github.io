"""What Gemma at Q8 answered for each label a person set, per kind of failure, with the production quantisation below."""
import math

from svgkit import Svg, legend, measure, table_html, wrap

ID = "confusion"
NARROW = True

CLASSES = ("product", "test", "infra")
CLS = {"product": "c-product", "test": "c-test", "infra": "c-infra"}
NAME = {"product": "product bug", "test": "test issue", "infra": "infrastructure"}
LAYERS = [("all", None), ("script", "script failure"), ("needle", "needle failure"), ("serial", "serial console")]
KIND_NAME = {None: "all jobs", "script failure": "failed in a script", "needle failure": "needle mismatch",
             "serial console": "serial console", "other": "other"}
# key, short name for tips and table, block title, rows drawn (label indices), bar thickness
BLOCKS = [
    ("gold_q8", "Gemma at Q8", "Gemma at Q8, labels set by people", (0, 1), 24),
    ("gold_iq2m", "IQ2_M", "IQ2_M, the quantisation in production, on the same jobs", (0, 1), 20),
    ("silver_posted", "Silver, posted", "Silver jobs labelled infrastructure afterwards, against the class "
     "posted in production", (2,), 20),
]
GAP = 2
HIT = 24


def _matrix(d, key, kind):
    s = d[key]
    if kind is None:
        return s["label_by_answer"]
    k = s["by_kind"].get(kind)
    return k["label_by_answer"] if k else None


def _jobs(n):
    return f"{n} job" if n == 1 else f"{n} jobs"


def _note(key, label, row):
    n = sum(row)
    if key == "gold_q8" and label == "test":
        return f"{row[0]} of {n} called product bug, {row[1] or 'none a'} test issue"
    if key == "gold_q8" and label == "product":
        return f"{row[0]} of {n} called product bug"
    if key == "gold_iq2m" and label == "test":
        return f"{row[1]} of {n} called test issue"
    return None


def _bar(g, x, y, w, h, row, label, short, kind):
    n = sum(row)
    parts = [(c, v) for c, v in zip(CLASSES, row) if v]
    avail = w - GAP * (len(parts) - 1)
    segs, cx = [], x
    for i, (c, v) in enumerate(parts):
        sw = avail * v / n
        segs.append((c, v, cx, sw, i == len(parts) - 1))
        cx += sw + GAP
    verb = "posted" if short.startswith("Silver") else "answered"
    # Narrow parts get grown hit targets kept inside the bar; draw them last so a wide neighbour does not cover them.
    for c, v, sx, sw, last in sorted(segs, key=lambda s: s[3] < HIT):
        tip = (f"{short}, {KIND_NAME[kind]}: labelled {NAME[label]}, {verb} {NAME[c]}: "
               f"{v} of {_jobs(n)} ({round(100 * v / n)}%)")
        hit = None
        if sw < HIT:
            hit = (min(max(sx + sw / 2 - HIT / 2, x), x + w - HIT), y + h / 2 - HIT / 2, HIT, HIT)
        t = g.tip(tip, hit=hit)
        if last:
            t.bar(sx, y, sw, h, CLS[c], end="right")
        else:
            t.rect(sx, y, sw, h, CLS[c])
        s = str(v)
        if h >= 20 and measure(s, "t-on") + 12 <= sw:
            t.text(sx + 6, y + h / 2, s, "t-on", "start", "middle")


def render(d, width):
    narrow = width < 540
    svg = Svg(ID, width, None,
              "What Gemma at Q8 answered against the label a person set, by kind of failure",
              "Of the jobs a person labelled test issue, Gemma at Q8 called 39 product bugs and 6 test issues; "
              "the IQ2_M quantisation in production called 15 test issues.")

    y = 0
    head = svg.g()
    head.text(0, y, "Answered", "t-muted", "start", "top")
    lx = 0 if narrow else measure("Answered", "t-muted") + 14
    ly = y + 16 if narrow else y - 6
    lh = legend(head, [(CLS[c], NAME[c]) for c in CLASSES], lx, ly, width - lx)
    y = ly + lh + 16

    label_w = 0 if narrow else max(measure(NAME[c], "t-strong") for c in NAME) + 16
    bar_x, bar_w = label_w, width - label_w

    # Block and row positions are shared by every layer so switching does not move anything.
    rows_at = []
    for bi, (key, short, title, rows, h) in enumerate(BLOCKS):
        if bi:
            y += 10
        if key == "silver_posted":
            head.text(0, y, "No job a person labelled is infrastructure.", "t-muted", "start", "top")
            y += 12 + 8
        lines = wrap(title, width, "t-strong")
        head.text(0, y, lines, "t-strong", "start", "top")
        y += 13 + 18 * (len(lines) - 1) + 12
        ys = []
        for li in rows:
            if narrow:
                y += 16 + 6
            ys.append(y)
            y += max(h, 34) if not narrow else h
            if _note(key, CLASSES[li], [1, 1, 1]):
                y += 6 + 13
            y += 12
        rows_at.append(ys)

    for name, kind in LAYERS:
        layer = svg.layer(name, on=name == "all")
        for (key, short, title, rows, h), ys in zip(BLOCKS, rows_at):
            m = _matrix(d, key, kind)
            if m is None:
                note = f"The silver set has no {KIND_NAME[kind]} split."
                layer.text(0, ys[0] - (16 + 6 if narrow else 0), note, "t-muted", "start", "top")
                continue
            for li, by in zip(rows, ys):
                label, row = CLASSES[li], m[li]
                n = sum(row)
                lbl_y = by + (max(h, 34) if not narrow else h) / 2
                if narrow:
                    layer.text(0, by - 6, NAME[label], "t-strong", "start", "bottom")
                    layer.text(width, by - 6, _jobs(n), "t-muted", "end", "bottom")
                else:
                    layer.text(0, lbl_y - 8, NAME[label], "t-strong", "start", "middle")
                    layer.text(0, lbl_y + 9, _jobs(n), "t-muted", "start", "middle")
                bar_y = by if narrow else lbl_y - h / 2
                if n:
                    _bar(layer, bar_x, bar_y, bar_w, h, row, label, short, kind)
                note = _note(key, label, row) if n else None
                if note:
                    note_y = (by + h if narrow else by + max(h, 34)) + 6
                    layer.text(bar_x, note_y, note, "t", "start", "top")

    svg.height = math.ceil(y - 12)
    return svg


def table(d):
    out = []
    for key, short, title, rows, h in BLOCKS:
        for kind in [None] + d["kinds"]:
            m = _matrix(d, key, kind)
            if m is None:
                continue
            for li in rows:
                row = m[li]
                out.append((short, KIND_NAME[kind], NAME[CLASSES[li]], *row, sum(row)))
    return table_html(
        ["Answers", "Failure kind", "Label", "Answered product bug", "Answered test issue",
         "Answered infrastructure", "Jobs"],
        out,
        "What the model answered for each label, by kind of failure. Gemma at Q8 and IQ2_M: the gold jobs, "
        "labels set by people, the model run again on them at 8-bit (Q8) and at the IQ2_M quantisation that "
        "runs in production; no gold job is labelled infrastructure. Silver, posted: silver jobs labelled "
        "infrastructure afterwards, against the class posted in production; the silver set has no "
        "serial-console split.")
