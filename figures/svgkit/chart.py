"""Chart parts: axes, legend, label placement, dot swarm and flow diagram."""
import math

from .scale import tick_labels
from .svg import num
from .text import CAP, LINE, measure, style, text_box, wrap


def labels_width(labels, cls="t-muted"):
    return max((measure(s, cls) for s in labels), default=0)


def axis_x(g, scale, ticks, y, labels=None, grid_to=None, title=None, cls="t-muted", line=True):
    """Tick labels below y, a baseline hairline and, with grid_to, vertical gridlines up to that y.

    Labels that would touch their neighbour are thinned to every second one.
    Returns the y of the bottom of the lowest text, for sizing the figure.
    """
    labels = labels or tick_labels(ticks)
    xs = [scale(t) for t in ticks]
    if grid_to is not None:
        for x in xs:
            g.line(x, grid_to, x, y, "grid")
    if line:
        lo, hi = sorted((scale.r0, scale.r1))
        g.line(lo, y, hi, y, "axis")
    keep = 1
    while keep < len(xs) and any(
        xs[i + keep] - xs[i] < (measure(labels[i], cls) + measure(labels[i + keep], cls)) / 2 + 8
        for i in range(0, len(xs) - keep, keep)
    ):
        keep += 1
    bottom = y
    for i in range(0, len(xs), keep):
        bottom = g.text(xs[i], y + 6, labels[i], cls, "middle", "top").box[3]
    if title:
        size = style(cls)[0]
        bottom = g.text(max(scale.r0, scale.r1), y + 6 + CAP * size + 8, title, cls, "end", "top").box[3]
    return bottom


def axis_y(g, scale, ticks, x, labels=None, grid_to=None, title=None, cls="t-muted"):
    """Tick labels right-aligned left of x and, with grid_to, horizontal gridlines from x to that x.

    title goes above the top tick, left-aligned with the widest label.
    """
    labels = labels or tick_labels(ticks)
    for t, s in zip(ticks, labels):
        y = scale(t)
        if grid_to is not None:
            g.line(x, y, grid_to, y, "grid")
        g.text(x - 6, y, s, cls, "end", "middle")
    if title:
        top = min(scale(t) for t in ticks)
        g.text(x - 6 - labels_width(labels, cls), top - 14, title, cls, "start", "bottom")


def band_labels(g, band, x, cls="t", anchor="end", width=None):
    """Category names centred on their bands (vertical band axis), wrapped to width if given."""
    for k in band.keys:
        lines = wrap(str(k), width, cls) if width else [str(k)]
        size = style(cls)[0]
        y = band.center(k) - (len(lines) - 1) * LINE * size / 2
        g.text(x, y, lines, cls, anchor, "middle")


def legend(g, items, x, y, width, kind="rect", cls="t"):
    """Swatch and name per series, wrapping into rows within width. Returns the height used.

    items: [(series_class, name)]; kind: rect, line or dot.
    """
    size = style(cls)[0]
    row_h = size + 8
    cx, cy = x, y
    for series, name in items:
        w = 16 + 6 + measure(name, cls)
        if cx > x and cx + w > x + width:
            cx, cy = x, cy + row_h
        mid = cy + row_h / 2
        if kind == "line":
            g.line(cx, mid, cx + 16, mid, series)
        elif kind == "dot":
            g.circle(cx + 8, mid, 5, series, ring=False)
        else:
            g.rect(cx + 3, mid - 5, 10, 10, series, rx=2)
        g.text(cx + 22, mid, name, cls, "start", "middle")
        cx += w + 18
    return cy + row_h - y


class Labeler:
    """Greedy collision-free placement of text boxes within bounds (x0, y0, x1, y1)."""

    def __init__(self, bounds, pad=3):
        self.bounds, self.pad, self.boxes = bounds, pad, []

    def block(self, box):
        self.boxes.append(box)

    def free(self, box):
        p = self.pad
        bx0, by0, bx1, by1 = self.bounds
        if box[0] < bx0 or box[1] < by0 or box[2] > bx1 or box[3] > by1:
            return False
        return all(box[2] + p <= b[0] or b[2] + p <= box[0] or box[3] + p <= b[1] or b[3] + p <= box[1] for b in self.boxes)

    def place(self, g, candidates, s, cls="t"):
        """Draw s at the first free candidate (x, y, anchor, baseline); returns it, or None if all collide.

        With g=None nothing is drawn, which lets a layout try a placement before fixing its sizes.
        """
        for x, y, anchor, baseline in candidates:
            box = text_box(x, y, s, cls, anchor, baseline)
            if self.free(box):
                self.block(box)
                if g is not None:
                    g.text(x, y, s, cls, anchor, baseline)
                return x, y, anchor, baseline, box
        return None


_DIRS = [(1, 0, "start", "middle"), (-1, 0, "end", "middle"), (0, -1, "middle", "bottom"), (0, 1, "middle", "top"),
         (0.7, -0.7, "start", "bottom"), (-0.7, -0.7, "end", "bottom"), (0.7, 0.7, "start", "top"), (-0.7, 0.7, "end", "top")]


def label_point(g, labeler, px, py, s, cls="t", r=4, rings=(6, 18, 34)):
    """Label a marker at (px, py) beside it, or farther out with a leader line when the near spots are taken."""
    for k, dist in enumerate(rings):
        cands = [(px + dx * (r + dist), py + dy * (r + dist), a, b) for dx, dy, a, b in _DIRS]
        for cand in cands:
            got = labeler.place(g, [cand], s, cls)
            if got:
                if k:
                    _leader(g, px, py, r, got[4])
                return got
    return None


def _leader(g, px, py, r, box):
    """A hairline from the marker edge to the nearest point of the label box."""
    qx = min(max(px, box[0] - 2), box[2] + 2)
    qy = min(max(py, box[1] - 2), box[3] + 2)
    d = math.hypot(qx - px, qy - py)
    if d > r + 2:
        g.line(px + (qx - px) * (r + 2) / d, py + (qy - py) * (r + 2) / d, qx, qy, "leader")


def spread(targets, sizes, lo, hi, gap=2):
    """Positions near targets for items of the given sizes along one axis, without overlap, within [lo, hi]."""
    order = sorted(range(len(targets)), key=lambda i: (targets[i], i))
    clusters = []  # [start, total_size, members]
    for i in order:
        clusters.append([targets[i] - sizes[i] / 2, sizes[i], [i]])
        while True:
            c = clusters[-1]
            c[0] = sum(targets[j] for j in c[2]) / len(c[2]) - (c[1] + gap * (len(c[2]) - 1)) / 2
            c[0] = min(max(c[0], lo), hi - c[1] - gap * (len(c[2]) - 1))
            if len(clusters) > 1:
                p = clusters[-2]
                if p[0] + p[1] + gap * len(p[2]) > c[0]:
                    clusters[-2:] = [[p[0], p[1] + c[1], p[2] + c[2]]]
                    continue
            break
    out = [0.0] * len(targets)
    for start, _, members in clusters:
        pos = start
        for j in members:
            out[j] = pos + sizes[j] / 2
            pos += sizes[j] + gap
    return out


def end_labels(g, items, x, lo, hi, cls="t"):
    """Labels at the right end of lines: items [(y, text)]; a leader joins a label moved off its line end."""
    size = style(cls)[0]
    ys = spread([y for y, _ in items], [size + 2] * len(items), lo, hi)
    for (y, s), ly in zip(items, ys):
        tx = x + 6
        if abs(ly - y) > 1:
            g.line(x + 2, y, x + 10, ly, "leader")
            tx = x + 14
        g.text(tx, ly, s, cls, "start", "middle")


def beeswarm(values, scale, r, gap=1, one_sided=False):
    """Deterministic dot swarm: returns (x, offset) per value in input order, offsets centred on 0."""
    d = 2 * r + gap
    placed = []
    out = [None] * len(values)
    for i in sorted(range(len(values)), key=lambda i: (values[i], i)):
        x = scale(values[i])
        near = [(px, po) for px, po in placed if abs(px - x) < d]
        cands = [0.0]
        for px, po in near:
            dy = math.sqrt(max(d * d - (px - x) ** 2, 0))
            cands += [po + dy, po - dy]
        cands = sorted({round(c, 6) for c in cands if not one_sided or c >= 0}, key=lambda c: (abs(c), -c))
        for c in cands:
            if all((px - x) ** 2 + (po - c) ** 2 >= d * d - 1e-6 for px, po in near):
                break
        placed.append((x, c))
        out[i] = (x, c)
    return out


def flow(g, columns, links, x, y, w, h, direction="lr", node=12, gap=2, label_width=None):
    """A sankey-like flow through stages.

    columns: [[{"id", "label", "cls"}], ...] in drawing order; links: [{"source", "target", "value", "cls"?}].
    A ribbon takes its link's "cls", else the colour of its source node, else of its target when the
    source is a neutral c-ctl node, so a split into classes is coloured by class on both sides.
    The box (x, y, w, h) holds nodes and ribbons; labels go outside it on the first and last stage
    and beside the nodes in between. direction "lr" runs left to right, "tb" top to bottom.
    Returns {id: (x, y, w, h)} of the node rectangles.
    """
    tb = direction == "tb"
    inflow, outflow = {}, {}
    for ln in links:
        outflow[ln["source"]] = outflow.get(ln["source"], 0) + ln["value"]
        inflow[ln["target"]] = inflow.get(ln["target"], 0) + ln["value"]
    val = {n["id"]: max(inflow.get(n["id"], 0), outflow.get(n["id"], 0)) for col in columns for n in col}
    across, along = (h, w) if tb else (w, h)
    k = max(sum(val[n["id"]] for n in col) / max(along - gap * (len(col) - 1), 1) for col in columns)
    step = (across - node) / max(len(columns) - 1, 1)
    pos, order, nodes, col_of = {}, {}, {}, {}
    for ci, col in enumerate(columns):
        c0 = step * ci
        a = 0.0
        for ri, n in enumerate(col):
            length = val[n["id"]] / k
            pos[n["id"]] = (c0, a, length)
            order[n["id"]] = (ci, ri)
            col_of[n["id"]] = n
            a += length + gap
    # Ribbons leave each node in the order of their targets and enter in the order of their sources.
    idx = range(len(links))
    s_at, t_at = {}, {}
    off = {i: 0.0 for i in pos}
    for i in sorted(idx, key=lambda i: (order[links[i]["source"]], order[links[i]["target"]])):
        src = links[i]["source"]
        s_at[i] = pos[src][1] + off[src]
        off[src] += links[i]["value"] / k
    off = {i: 0.0 for i in pos}
    for i in sorted(idx, key=lambda i: (order[links[i]["target"]], order[links[i]["source"]])):
        tgt = links[i]["target"]
        t_at[i] = pos[tgt][1] + off[tgt]
        off[tgt] += links[i]["value"] / k
    ribbons = g.g()
    for i, ln in enumerate(links):
        s, t = ln["source"], ln["target"]
        thick = ln["value"] / k
        c_s, c_t = pos[s][0] + node, pos[t][0]
        cm = (c_s + c_t) / 2
        a0, b0 = s_at[i], t_at[i]
        P = [(c_s, a0), (cm, a0), (cm, b0), (c_t, b0),
             (c_t, b0 + thick), (cm, b0 + thick), (cm, a0 + thick), (c_s, a0 + thick)]
        P = [f"{num(x + b)} {num(y + a)}" if tb else f"{num(x + a)} {num(y + b)}" for a, b in P]
        d = f"M{P[0]}C{P[1]} {P[2]} {P[3]}L{P[4]}C{P[5]} {P[6]} {P[7]}Z"
        cls = ln.get("cls") or _ribbon_cls(col_of[s].get("cls", "c-ctl"), col_of[t].get("cls", "c-ctl"))
        text = f"{col_of[s]['label']} → {col_of[t]['label']}: {ln['value']:,}"
        ribbons.tip(text).path(d, f"{cls} flow")
    nodes_g = g.g()
    last = len(columns) - 1
    for nid, (c0, a, length) in pos.items():
        n = col_of[nid]
        bx, by, bw, bh = (x + a, y + c0, length, node) if tb else (x + c0, y + a, node, length)
        nodes[nid] = (bx, by, bw, bh)
        nodes_g.tip(f"{n['label']}: {val[nid]:,}", hit=(bx, by, bw, bh)).rect(bx, by, bw, bh, n.get("cls", "c-ctl"))
    for nid, (bx, by, bw, bh) in nodes.items():
        ci = order[nid][0]
        n = col_of[nid]
        lw = label_width or (bw if tb else 120)
        lines = wrap(n["label"], max(lw, 40))
        size = style("t")[0]
        if tb:
            if ci == 0:
                ly, base = by - 6 - (len(lines) - 1) * LINE * size, "bottom"
            else:
                ly, base = by + bh + 6, "top"
            box = text_box(bx, ly, lines, "t", "start", base)
            if 0 < ci < last:
                g.rect(box[0] - 2, box[1] - 2, box[2] - box[0] + 4, box[3] - box[1] + 4, "bg", rx=2)
            g.text(bx, ly, lines, "t", "start", base)
        else:
            ly = by + bh / 2 - (len(lines) - 1) * LINE * size / 2
            if ci == 0:
                g.text(bx - 6, ly, lines, "t", "end", "middle")
            else:
                box = text_box(bx + bw + 6, ly, lines, "t", "start", "middle")
                if ci < last:
                    g.rect(box[0] - 2, box[1] - 2, box[2] - box[0] + 4, box[3] - box[1] + 4, "bg", rx=2)
                g.text(bx + bw + 6, ly, lines, "t", "start", "middle")
    return nodes


def _ribbon_cls(src, tgt):
    return tgt if src.startswith("c-ctl") else src
