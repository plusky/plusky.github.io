"""Thinking on against off: tokens generated per turn, seconds per job and jobs with the right class."""
import math

from svgkit import Linear, Svg, axis_x, beeswarm, labels_width, legend, measure, nice_ticks, table_html, wrap

ID = "thinking"
NARROW = True
POST = "failure-class-data"

BAR = 20
ROW_GAP = 6
R = 4
ON, OFF = "c-focus", "c-ctl"


def _pct(v):
    return f"{round(v * 100)}%"


def _num(v):
    return f"{v:,.0f}"


def _panels(d):
    on, off = d["on"], d["off"]
    return [
        {
            "title": "Tokens generated per turn",
            "max": on["generated_per_turn"],
            "rows": [(ON, "on", on["generated_per_turn"], _num(on["generated_per_turn"])),
                     (OFF, "off", off["generated_per_turn"], _num(off["generated_per_turn"]))],
            "tip": lambda s, v: f"Thinking {s}: {_num(v)} tokens generated per turn",
        },
        {
            "title": "Median seconds per job",
            "note": f"thinking off: {_pct(d['time_saved_share'])} less time, all {d['jobs']} jobs together",
            "max": max(j["on"] for j in d["per_job_s"]),
            "rows": [(ON, "on", on["median_s"], f"{_num(on['median_s'])} s"),
                     (OFF, "off", off["median_s"], f"{_num(off['median_s'])} s")],
            "tip": lambda s, v: f"Thinking {s}: median {_num(v)} s per job",
            "strip": True,
        },
        {
            "title": f"Jobs with the right class, of {d['jobs']}",
            "note": f"thinking off: {on['class_right'] - off['class_right']} fewer right",
            "max": d["jobs"],
            "rows": [(ON, "on", on["class_right"], f"{on['class_right']} of {d['jobs']}"),
                     (OFF, "off", off["class_right"], f"{off['class_right']} of {d['jobs']}")],
            "tip": lambda s, v: f"Thinking {s}: {v} of {d['jobs']} jobs with the right class",
            "track": True,
        },
    ]


def render(d, width):
    narrow = width < 540
    share = d["thinking_share_of_generation"]
    svg = Svg(ID, width, None,
              "Thinking on against off: tokens generated, seconds per job and jobs with the right class",
              f"On {d['hardware']}, thinking was {_pct(share)} of the tokens the model generated; turning it off "
              f"cut the median job from {_num(d['on']['median_s'])} to {_num(d['off']['median_s'])} seconds "
              f"and the time for all {d['jobs']} jobs by {_pct(d['time_saved_share'])}, but dropped the jobs "
              f"with the right class from {d['on']['class_right']} to {d['off']['class_right']}.")
    panels = _panels(d)
    for p in panels:
        ticks = nice_ticks(0, p["max"], 5)
        p["ticks"] = [t for t in ticks if t <= p["max"]] if p.get("track") else ticks
        p["dmax"] = p["max"] if p.get("track") else ticks[-1]

    left = labels_width(["on", "off"], "t") + 10
    # The plot ends where every value label right of its bar (or track) still fits.
    right = width - 4
    for p in panels:
        for _, _, v, s in p["rows"]:
            end = p["dmax"] if p.get("track") else v
            need = 6 + measure(s, "t") + 2
            right = min(right, left + (width - need - left) * p["dmax"] / end)
        right = min(right, width - measure(f"{p['ticks'][-1]:,}", "t-muted") / 2 - 2)

    y = legend(svg, [(ON, "thinking on"), (OFF, "thinking off")], 0, 0, width) + 14
    for p in panels:
        x = Linear((0, p["dmax"]), (left, right))
        g = svg.g()
        back = g.g()
        lines = wrap(p["title"], width - 4, "t-strong")
        top = g.text(0, y, lines, "t-strong", "start", "top").box[3] + 8
        if p.get("note"):
            top = g.text(0, top - 4, wrap(p["note"], width - 4), "t", "start", "top").box[3] + 8
        if p is panels[0]:
            top += 18
        for i, (cls, name, v, label) in enumerate(p["rows"]):
            by = top + i * (BAR + ROW_GAP)
            g.text(left - 10, by + BAR / 2, name, "t", "end", "middle")
            if p.get("track"):
                g.rect(left, by, right - left, BAR, "band", rx=4)
            t = g.tip(p["tip"](name, v), hit=(left, by, max(x(v) - left, 1), BAR))
            if p is panels[0] and name == "on":
                # The thinking-on bar splits into thinking and the visible answer.
                xt = x(v * share)
                t.rect(left, by, xt - 1 - left, BAR, ON)
                # A wash of the on hue, outlined inside its box, so the whole bar reads as thinking on.
                t.bar(xt + 2, by + 1, x(v) - xt - 3, BAR - 2, "wash-focus s-focus", "right", r=3)
                g.text(left, by - 4, f"thinking {_pct(share)}", "t", "start", "bottom")
                g.text(x(v), by - 4, "visible answer", "t-muted", "end", "bottom")
            else:
                t.bar(left, by, x(v) - left, BAR, cls, "right")
            lx = (right if p.get("track") else x(v)) + 6
            g.text(lx, by + BAR / 2, label, "t", "start", "middle")
        base = top + 2 * BAR + ROW_GAP + 6
        if p.get("strip"):
            base = _strip(g, d, x, left, base + 6)
        y = axis_x(back, x, p["ticks"], base, grid_to=top - 2 if not p.get("track") else None,
                   title="seconds" if p.get("strip") else None) + 26
    svg.height = math.ceil(y - 26 + 4)
    return svg


def _strip(g, d, x, left, top):
    """Each job's seconds as a dot swarm per setting, under the median bars on the same scale."""
    g.text(0, top, "each job", "t-muted", "start", "top")
    top += 18
    jobs = d["per_job_s"]
    for key, cls, name in (("on", ON, "on"), ("off", OFF, "off")):
        vals = [j[key] for j in jobs]
        pos = beeswarm(vals, x, R, gap=1)
        lo = min(o for _, o in pos)
        hi = max(o for _, o in pos)
        mid = top + R - lo
        g.text(left - 10, mid, name, "t", "end", "middle")
        for k, (j, (px, off)) in enumerate(zip(jobs, pos), 1):
            t = g.tip(f"Job {k}: thinking {name} {_num(j[key])} s", hit=(px - R, mid + off - R, 2 * R, 2 * R))
            t.circle(px, mid + off, R, cls)
        top = mid + hi + R + 8
    return top


def table(d):
    on, off = d["on"], d["off"]
    rows = [
        ("Tokens generated per turn", _num(on["generated_per_turn"]), _num(off["generated_per_turn"])),
        ("Thinking, share of generated tokens", _pct(d["thinking_share_of_generation"]), "–"),
        ("Median seconds per job", _num(on["median_s"]), _num(off["median_s"])),
        ("90th percentile seconds per job", _num(on["p90_s"]), _num(off["p90_s"])),
        ("Total seconds, all jobs", _num(on["total_s"]), _num(off["total_s"])),
        ("Seconds reading the prompt, all jobs", _num(on["prompt_s"]), _num(off["prompt_s"])),
        ("Seconds generating, all jobs", _num(on["generation_s"]), _num(off["generation_s"])),
        (f"Jobs with the right class, of {d['jobs']}", on["class_right"], off["class_right"]),
    ]
    rows += [(f"Job {k}, seconds", _num(j["on"]), _num(j["off"])) for k, j in enumerate(d["per_job_s"], 1)]
    caption = (f"Thinking on against off for {d['jobs']} jobs, {d['model']}, on {d['hardware']}; "
               f"thinking off took {_pct(d['time_saved_share'])} less time in total. Jobs sorted by seconds with thinking on.")
    return table_html(["Measure", "Thinking on", "Thinking off"], rows, caption)
