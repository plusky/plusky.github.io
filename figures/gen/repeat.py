"""The same prompt run twice: jobs that kept their class, per job set."""
import math

from svgkit import Svg, legend, measure, table_html, wrap

ID = "repeat"
NARROW = True

BAR = 20
GAP = 2
HIT = 24

# (index into data["sets"], name, note, full name for hover and table, starts a separate group)
SHOWN = [
    (2, "Gold jobs", "run again a day later", "Gold jobs, run again a day later", False),
    (3, "Test issues among them", None, "Test issues among those gold jobs", False),
    (4, "Another 16 gold jobs (8 shared)", "run again four days later",
     "Another 16 gold jobs (8 shared), run again four days later", False),
    (1, "Product bugs, internal instance", "internal counts",
     "Product bugs from an internal instance (internal counts)", True),
]

CONTEXT = {
    0: "Gold jobs and internal product bugs together",
    5: "Verdict only, asked again on the same stored answers to the first two questions",
}


def _bar(g, x0, y, w, d, name):
    same, jobs = d["same"], d["jobs"]
    changed = jobs - same
    kw = w * same / jobs
    if changed:
        kw = max(kw - GAP / 2, 0)
    cx, cw = x0 + kw + GAP, x0 + w - (x0 + kw + GAP)
    # A thin last segment gets a hit target that grows leftwards, so it stays inside the bar's extent.
    hx = min(cx, x0 + w - HIT) if changed else x0 + w
    g.tip(f"{name}: {same} of {jobs} kept the class", hit=(x0, y, min(kw, hx - x0), BAR)).bar(
        x0, y, kw, BAR, "c-ctl", "right", r=0 if changed else 4)
    if changed:
        g.tip(f"{name}: {changed} of {jobs} changed", hit=(hx, y, x0 + w - hx, BAR)).bar(
            cx, y, cw, BAR, "c-focus", "right")


def _count(d):
    return f"{d['same']} of {d['jobs']} kept"


def render(d, width):
    narrow = width < 540
    sets = d["sets"]
    o3, test, again, internal = (sets[i] for i, *_ in SHOWN)
    svg = Svg(ID, width, None,
              "Jobs that kept their class when the same prompt ran twice",
              f"The same prompt run twice kept the class on {o3['same']} of {o3['jobs']} gold jobs, "
              f"{test['same']} of {test['jobs']} test issues among them and {again['same']} of {again['jobs']} "
              f"gold jobs run again four days later, half of them from that set, against "
              f"{internal['same']} of {internal['jobs']} product bugs "
              f"from an internal instance.")
    y = legend(svg, [("c-ctl", "kept its class"), ("c-focus", "changed")], 0, 0, width) + 14
    bars = svg.g()
    if narrow:
        for i, name, note, full, sep in SHOWN:
            d_ = sets[i]
            if sep:
                svg.line(0, y - 4, width, y - 4, "grid")
                y += 8
            cnt = "t" if sep else "t-strong"
            svg.text(width, y, _count(d_), cnt, "end", "top")
            room = width - measure(_count(d_), cnt) - 12
            for s in wrap(name, room, "t-strong"):
                y = svg.text(0, y, s, "t-strong", "start", "top").box[3] + 2
            if note:
                for s in wrap(note, width, "t-muted"):
                    y = svg.text(0, y, s, "t-muted", "start", "top").box[3] + 2
            y += 4
            _bar(bars, 0, y, width, d_, full)
            y += BAR + 16
        bottom = y - 16
    else:
        lab_w = max(max(measure(n, "t-strong") for _, n, *_ in SHOWN),
                    max(measure(n, "t-muted") for _, _, n, *_ in SHOWN if n)) + 16
        cnt_w = max(measure(_count(sets[i]), "t-strong") for i, *_ in SHOWN) + 12
        x0, w = lab_w, width - lab_w - cnt_w
        for i, name, note, full, sep in SHOWN:
            d_ = sets[i]
            if sep:
                svg.line(0, y - 8, width, y - 8, "grid")
                y += 6
            mid = y + BAR / 2
            if note:
                svg.text(lab_w - 16, mid - 8, name, "t-strong", "end", "middle")
                svg.text(lab_w - 16, mid + 9, note, "t-muted", "end", "middle")
            else:
                svg.text(lab_w - 16, mid, name, "t-strong", "end", "middle")
            _bar(bars, x0, y, w, d_, full)
            svg.text(x0 + w + 8, mid, _count(d_), "t" if sep else "t-strong", "start", "middle")
            y += BAR + 22
        bottom = y - 22 + (BAR / 2 + 9 + 8 if SHOWN[-1][2] else BAR)
    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    rows = [(full, d["sets"][i]["jobs"], d["sets"][i]["same"], d["sets"][i]["jobs"] - d["sets"][i]["same"])
            for i, _, _, full, _ in SHOWN]
    rows += [(f"{name} (mixed counts; context, not drawn)", d["sets"][i]["jobs"], d["sets"][i]["same"],
              d["sets"][i]["jobs"] - d["sets"][i]["same"]) for i, name in CONTEXT.items()]
    return table_html(["Job set", "Jobs", "Kept its class", "Changed"], rows,
                      f"Jobs that kept their class when the same prompt ran twice ({d['model']})")
