"""Jobs right on the screen set per approach, ranked, with the right answers per class beside each bar."""
import math

from svgkit import Svg, measure, table_html

ID = "models"
NARROW = True
POST = "failure-class-data"
DATA = "results/screens-table.json"

ALWAYS = "always product"
RULE = "elephant-1 with the environment question"
CLASSES = (("product", "product"), ("test", "test"), ("infra", "infra"))
BAR = 18


def _classes(r, sep=" · "):
    return sep.join(f"{label} {r[key][0]}/{r[key][1]}" for key, label in CLASSES)


def _split(d):
    """The fixed answer, the size of the set, and the other approaches ranked by jobs right."""
    always = next(r for r in d["rows"] if r["approach"] == ALWAYS)
    jobs = always["right"][1]
    rows = sorted((r for r in d["rows"] if r is not always), key=lambda r: (-r["right"][0], r["right"][1] < jobs))
    return always, jobs, rows


def render(d, width):
    narrow = width < 540
    always, jobs, rows = _split(d)
    assert any(r["approach"] == RULE for r in rows)
    svg = Svg(ID, width, None,
              f"Jobs right of {jobs} on the screen set per approach, with the right answers per class",
              f"The best approaches get {rows[0]['right'][0]} of the {jobs} screen jobs right, against "
              f"{always['right'][0]} for always answering product; part of the set comes from an internal "
              "instance, counted only.")
    x1 = width - 40 if narrow else (width - max(measure(_classes(r), "t-muted") for r in rows) - 24
                                    - measure(f"{jobs} of {jobs}", "t"))
    marks, front = svg.g(), svg.g()
    y, bands = 0, []
    for r in rows:
        right, of = r["right"]
        cls = "t-strong" if r["approach"] == RULE else "t"
        y = svg.text(0, y, r["approach"], cls, "start", "top").box[3] + 4
        w = x1 * right / jobs
        bands.append(y)
        tip = f"{r['approach']}: {right} of {of} right; {_classes(r, ', ').replace('/', ' of ')}"
        marks.tip(tip, hit=(0, y, w, BAR)).bar(0, y, w, BAR, "c-focus" if r["approach"] == RULE else "c-ctl", "right")
        front.text(w + 6, y + BAR / 2, str(right) if of == jobs else f"{right} of {of}", cls, "start", "middle")
        if narrow:
            y = svg.text(0, y + BAR + 5, _classes(r), "t-muted", "start", "top").box[3] + 14
        else:
            svg.text(width, y + BAR / 2, _classes(r), "t-muted", "end", "middle")
            y += BAR + 14
    bottom = y - 14

    # The fixed answer as a reference mark on every bar.
    rx = x1 * always["right"][0] / jobs
    ref = svg.tip(f"{ALWAYS}: {always['right'][0]} of {jobs} right", hit=(rx - 1, bands[0], 2, bottom - bands[0]))
    for b in bands:
        ref.line(rx, b - 3, rx, b + BAR + 3, "ref")
    y = svg.text(rx, bottom + 8, f"{ALWAYS}, {always['right'][0]}", "t", "start", "top").box[3]
    svg.height = math.ceil(y + 4)
    return svg


def table(d):
    always, jobs, rows = _split(d)
    body = [(r["approach"], *r["right"], *(f"{r[key][0]} of {r[key][1]}" for key, _ in CLASSES))
            for r in [*rows, always]]
    return table_html(["Approach", "Right", "Jobs", "Product", "Test", "Infrastructure"], body,
                      f"Jobs right on the screen set of {jobs} per approach, by failure class. Part of the set comes "
                      "from an internal instance and is reported as counts only.")
