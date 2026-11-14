"""Histogram of characters per token over the measured prompts, with the assumed and proposed ratios."""
import math

from svgkit import Labeler, Linear, Svg, axis_x, labels_width, nice_ticks, table_html, text_box, tick_labels, wrap

ID = "chars-per-token"
NARROW = True

ROW = 20  # height of one row of reference-line labels
TAIL = 3.1  # bins from here on are drawn as one bar, set apart from the axis
GAP = 14  # space between the axis end and the tail bar


def _ratio(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else f"{v:.1f}"


def _split(d):
    body = [b for b in d["bins"] if b["lo"] < TAIL - 1e-9]
    tail = [b for b in d["bins"] if b["lo"] >= TAIL - 1e-9]
    return body, {"lo": tail[0]["lo"], "hi": tail[-1]["hi"], "n": sum(b["n"] for b in tail), "bins": len(tail)}


def _prompts(n):
    return f"{n} prompt" if n == 1 else f"{n} prompts"


def _below(d, v):
    """Prompts below v, counted from the bins; v must be a bin edge."""
    if not any(abs(b["hi"] - v) < 1e-9 for b in d["bins"]):
        raise ValueError(f"{ID}: {v} is not a bin edge")
    return sum(b["n"] for b in d["bins"] if b["hi"] <= v + 1e-9)


def _overlaps(a, b, p=3):
    return not (a[2] + p <= b[0] or b[2] + p <= a[0] or a[3] + p <= b[1] or b[3] + p <= a[1])


def render(d, width):
    narrow = width < 540
    body, tail = _split(d)
    bw = d["bin_width"]
    lo, hi = body[0]["lo"], body[-1]["hi"]
    yticks = nice_ticks(0, max(b["n"] for b in body + [tail]), 4 if narrow else 5)
    ylabels = tick_labels(yticks)
    left = labels_width(ylabels) + 8
    right = width - 4
    # The tail bar is as wide as one bin and sits GAP beyond the axis end.
    unit = (right - left - GAP) / (hi - lo + bw)
    x = Linear((lo, hi), (left, left + unit * (hi - lo)))
    tail_x0 = x(hi) + GAP
    assumed = x(d["assumed"])

    svg = Svg(ID, width, None,
              f"Characters per token in {d['n']} measured prompts",
              f"Real prompts hold a median of {d['median']:.2f} characters per token, fewer than the "
              f"{_ratio(d['assumed'])} the script assumed, so prompts cut by character count still overflowed.")
    back, bars, front = svg.g(), svg.g(), svg.g()

    # Labels sit in rows above the plot beside their line. A line runs down from its own label,
    # so a label may sit above another line's label but never across a line below that line's top.
    refs = [
        (d["assumed"], f"assumed {_ratio(d['assumed'])}", "t-strong"),
        (d["median"], f"median {d['median']:.2f}", "t-strong"),
        (d["proposed"], f"proposed {_ratio(d['proposed'])}", "t"),
    ]
    labels = [text_box(0, 0, "prompts", "t-muted", "start", "top")]
    front.text(0, 0, "prompts", "t-muted", "start", "top")
    lines, tops = [], {}
    for v, s, cls in refs:
        lx = x(v)
        for r in range(4):
            for dx, a in ((5, "start"), (-5, "end")):
                box = text_box(lx + dx, r * ROW, s, cls, a, "top")
                stem = (lx - 1, box[1], lx + 1, 1e6)
                if (box[0] >= 0 and box[2] <= width
                        and not any(_overlaps(box, o) for o in labels + lines)
                        and not any(_overlaps(stem, o, 0) for o in labels)):
                    break
            else:
                continue
            break
        else:
            raise ValueError(f"{ID}@{width}: no room for the label {s!r}")
        front.text(lx + dx, r * ROW, s, cls, a, "top")
        labels.append(box)
        lines.append(stem)
        tops[v] = box[1]

    plot_top = max(b[3] for b in labels) + 10
    plot_h = 190 if narrow else 230
    base = plot_top + plot_h
    y = Linear((0, yticks[-1]), (base, plot_top))

    for t, s in zip(yticks, ylabels):
        back.line(left, y(t), right, y(t), "grid")
        back.text(left - 6, y(t), s, "t-muted", "end", "middle")
    xticks = x.ticks(4 if narrow else 8)
    bottom = axis_x(back, x, xticks, base, title="characters per token")
    title_box = back.children[-1].box  # axis_x draws its title last
    back.line(tail_x0, base, right, base, "axis")
    for v, _, _ in refs:
        front.line(x(v), max(0, tops[v] - 1), x(v), base, "ref")

    plot_lab = Labeler((left, plot_top, right, base))
    for v, _, _ in refs:
        plot_lab.block((x(v) - 1, plot_top, x(v) + 1, base))
    cols = [(b, x(b["lo"]), x(b["hi"]), f"{b['lo']:.2f}–{b['hi']:.2f} characters per token: {_prompts(b['n'])}")
            for b in body]
    cols.append((tail, tail_x0, tail_x0 + unit * bw,
                 f"{tail['lo']:.2f} and more ({tail['lo']:.2f}–{tail['hi']:.2f}, {tail['bins']} bins drawn as one bar): "
                 f"{_prompts(tail['n'])}"))
    for b, x0, x1, tip in cols:
        # Columns tile the plot, so their hit areas are the full column and must not grow into a neighbour.
        g = bars.tip(tip, hit=(x0, plot_top, x1 - x0, plot_h), min_size=0)
        if b["n"]:
            g.bar(x0 + 1, y(b["n"]), x1 - x0 - 2, base - y(b["n"]), "c-focus", "top")
            plot_lab.block((x0, y(b["n"]), x1, base))

    tail_label = f"{_ratio(tail['lo'])} and more"
    if not plot_lab.place(front, [(tail_x0 + unit * bw, y(tail["n"]) - 6, "end", "bottom")], tail_label, "t-muted"):
        raise ValueError(f"{ID}@{width}: no room for the tail label")

    note = f"{round(d['share_below_assumed'] * 100)}% of prompts are below {_ratio(d['assumed'])}"
    if not narrow:
        # Beside the assumed line on the side it counts, above the bars just below 2.5.
        room = assumed - 8 - (x(d["median"]) + 4)
        while not plot_lab.place(front, [(assumed - 8, plot_top + 10, "end", "top")],
                                 wrap(note, room, "t-strong"), "t-strong"):
            room -= 10
            if room < 40:
                raise ValueError(f"{ID}@{width}: the note collides with the bars")
    else:
        # No room between the lines at this width: a bracket under the axis spans everything below 2.5.
        by = max(text_box(x(t), base + 6, s, "t-muted", "middle", "top")[3]
                 for t, s in zip(xticks, tick_labels(xticks))) + 6
        front.line(x(lo), by, assumed, by, "leader")
        front.line(x(lo), by - 4, x(lo), by, "leader")
        front.line(assumed, by - 4, assumed, by, "leader")
        nb = front.text(x(lo), by + 6, wrap(note, assumed - x(lo), "t-strong"), "t-strong", "start", "top").box
        if _overlaps(nb, title_box) or _overlaps((x(lo), by - 4, assumed, by), title_box):
            raise ValueError(f"{ID}@{width}: the note collides with the axis title")
        bottom = max(bottom, nb[3])

    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    _, tail = _split(d)
    rows = [(f"{b['lo']:.2f}–{b['hi']:.2f}", b["n"]) for b in d["bins"]]
    total = sum(b["n"] for b in d["bins"])
    if total != d["n"]:
        raise ValueError(f"{ID}: the bins hold {total} prompts, not {d['n']}")
    rows.append(("All prompts", total))
    caption = (f"Characters per token in {d['n']} prompts, in bins of {d['bin_width']}: median {d['median']:.2f}, "
               f"{round(d['share_below_assumed'] * 100)}% below the assumed {_ratio(d['assumed'])} "
               f"({_below(d, d['assumed'])} prompts), {_prompts(_below(d, d['proposed']))} below the proposed "
               f"{_ratio(d['proposed'])}. The figure draws the {tail['bins']} bins from {tail['lo']:.2f} to "
               f"{tail['hi']:.2f} as one bar of {tail['n']} prompts, labelled {_ratio(tail['lo'])} and more.")
    return table_html(["Characters per token", "Prompts"], rows, caption)
