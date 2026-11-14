"""Strip plot of the probability given to "the test environment failed", one row per hindsight label."""
import math

from svgkit import Labeler, Linear, Svg, axis_x, beeswarm, measure, table_html, text_box, wrap

ID = "env"
NARROW = True

R = 4
CLASSES = [("product", "product bug", "c-product"), ("test", "test issue", "c-test"), ("infra", "infrastructure", "c-infra")]


def _bin(v):
    # Values carry 5 decimals; integer arithmetic keeps 0.3 in the bin that starts at 0.3 and 0.29966 below it.
    return min(int(round(v * 100000)) // 10000, 9)


def _bin_name(i):
    return f"{i / 10:.1f}–{(i + 1) / 10:.1f}"


def _desc(d):
    t, a = d["threshold"], d["confirmation"]["above_by_label"]
    return (f"On {d['confirmation']['jobs']} jobs the threshold was not read from, {a['infra'][0]} of {a['infra'][1]} "
            f"infrastructure jobs get {t} or more for “the test environment failed”, against "
            f"{a['product'][0]} of {a['product'][1]} product bugs and {a['test'][0]} of {a['test'][1]} test issues; "
            f"the threshold was chosen after seeing other jobs.")


def render(d, width):
    narrow = width < 540
    t = d["threshold"]
    conf = d["confirmation"]
    above = conf["above_by_label"]
    svg = Svg(ID, width, None,
              f"Probability given to “the test environment failed” for {conf['jobs']} jobs, by hindsight label",
              _desc(d))
    back, marks, front = svg.g(), svg.g(), svg.g()

    head = "at or above " + f"{t}"
    if narrow:
        left, right = 12, width - 12
    else:
        name_w = max(measure(n, "t-strong") for _, n, _ in CLASSES) + 18
        count_w = max([measure(head, "t-muted")] + [measure(f"{above[k][0]} of {above[k][1]}", "t-strong") for k, _, _ in CLASSES])
        left, right = name_w + 14, width - count_w - 20
    x = Linear((0, 1), (left, right))
    xt = x(t)

    # Threshold label above the plot, beside its line, wrapped if the line sits too far right.
    label = f"threshold {t}, chosen after seeing other jobs"
    lines = [label]
    if measure(label, "t-strong") > (width if narrow else right) - xt - 8:
        lines = [f"threshold {t},", "chosen after seeing other jobs"]
    lab_box = text_box(xt + 6, 0, lines, "t-strong", "start", "top")
    front.text(xt + 6, 0, lines, "t-strong", "start", "top")
    top = lab_box[3] + 8

    rows = []
    y = top
    for key, name, cls in CLASSES:
        vals = [p["env"] for p in conf["points"] if p["label"] == key]
        pos = beeswarm(vals, x, R, gap=1)
        reach = max(abs(o) for _, o in pos) + R + 2
        lab_h = 22 if narrow else 0
        h = lab_h + max(2 * reach + 16, 36)
        rows.append((key, name, cls, vals, pos, y, lab_h, h))
        y += h
    base = y

    back.rect(xt, top, right - xt, base - top, "band")
    for _, _, _, _, _, ry, _, _ in rows[1:]:
        back.line(0 if narrow else left - 8, ry, width, ry, "grid")
    bottom = axis_x(back, x, x.ticks(5 if narrow else 10), base,
                    title="probability given to “the test environment failed”")
    # Under the marks so the dot at exactly the threshold stays whole.
    back.line(xt, lab_box[1], xt, base, "ref")

    for key, name, cls, vals, pos, ry, lab_h, h in rows:
        mid = ry + lab_h + (h - lab_h) / 2
        count = f"{above[key][0]} of {above[key][1]}"
        if narrow:
            ly = ry + 12
            front.circle(left + 5, ly, 5, cls, ring=False)
            front.text(left + 16, ly, name, "t-strong", "start", "middle")
            front.text(right, ly, f"{count} {head}", "t", "end", "middle")
        else:
            front.circle(8, mid, 5, cls, ring=False)
            front.text(19, mid, name, "t-strong", "start", "middle")
            front.text(width, mid - 8, count, "t-strong", "end", "middle")
            front.text(width, mid + 9, head, "t-muted", "end", "middle")
        by_bin = {}
        for v, (px, off) in zip(vals, pos):
            by_bin.setdefault(_bin(v), []).append((px, off))
        for b in sorted(by_bin):
            dots = by_bin[b]
            n = len(dots)
            tip = f"{name}, {_bin_name(b)}: {n} job{'s' if n != 1 else ''}"
            g = marks.tip(tip, hit=(x(b / 10), ry + lab_h, x((b + 1) / 10) - x(b / 10), h - lab_h), min_size=0)
            for px, off in dots:
                g.circle(px, mid + off, R, cls)

    ro = d["read_off"]
    note = (f"The threshold was read from {ro['jobs']} other jobs, internal ones included; on those, "
            f"{ro['infra'][0]} of {ro['infra'][1]} infrastructure jobs and {ro['others'][0]} of {ro['others'][1]} "
            f"others were at or above {t}.")
    nl = wrap(note, width - 4, "t-muted")
    nb = text_box(0, bottom + 14, nl, "t-muted", "start", "top")
    front.text(0, bottom + 14, nl, "t-muted", "start", "top")

    svg.height = math.ceil(nb[3] + 4)
    return svg


def table(d):
    t = d["threshold"]
    conf, ro = d["confirmation"], d["read_off"]
    a = conf["above_by_label"]
    rows = [(name, f"{conf['jobs']} jobs the threshold was not read from", a[k][0], a[k][1] - a[k][0], a[k][1])
            for k, name, _ in CLASSES]
    rd = f"{ro['jobs']} jobs the threshold was read from, internal jobs included"
    rows.append(("infrastructure", rd, ro["infra"][0], ro["infra"][1] - ro["infra"][0], ro["infra"][1]))
    rows.append(("product bug or test issue", rd, ro["others"][0], ro["others"][1] - ro["others"][0], ro["others"][1]))
    first = table_html(
        ["Hindsight label", "Jobs", f"At or above {t}", f"Below {t}", "Total"], rows,
        f"Jobs whose probability for “the test environment failed” is at or above the threshold {t}, "
        f"which was chosen after seeing the {ro['jobs']} jobs in the last two rows")
    counts = {k: [0] * 10 for k, _, _ in CLASSES}
    for p in conf["points"]:
        counts[p["label"]][_bin(p["env"])] += 1
    bins = [(_bin_name(i), *(counts[k][i] for k, _, _ in CLASSES)) for i in range(10)]
    second = table_html(
        ["Probability", *(name for _, name, _ in CLASSES)], bins,
        f"Jobs per probability bin on the {conf['jobs']} jobs the threshold was not read from "
        f"(each bin includes its lower bound)")
    return first + second
