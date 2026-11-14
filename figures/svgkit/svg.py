"""SVG document and element helpers that enforce the figure contract of figures/README.md."""
from . import text as _t

_ORDER = [
    "id", "class", "viewBox", "role", "aria-labelledby", "d", "x", "y", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "width", "height", "rx", "dy", "text-anchor", "transform",
    "data-layer", "data-tip", "tabindex",
]
_RANK = {k: i for i, k in enumerate(_ORDER)}
_FORBIDDEN_PREFIX = ("fill", "stroke", "font", "style", "opacity", "color", "href", "xlink", "on")


def num(v):
    """At most two decimals, no trailing zeros, no negative zero."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pts(points):
    return " ".join(f"{num(x)},{num(y)}" for x, y in points)


def _esc(s, quote=False):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace('"', "&quot;") if quote else s


class El:
    def __init__(self, tag, attrs=None, text=None):
        self.tag, self.content, self.attrs, self.children = tag, text, {}, []
        self.box = None
        for k, v in (attrs or {}).items():
            if v is not None:
                self.set(k, v)

    def set(self, key, value):
        if key.startswith(_FORBIDDEN_PREFIX) and key != "role":
            raise ValueError(f"attribute {key!r} is not allowed; use a class from fig.css")
        self.attrs[key] = value
        return self

    def add(self, el):
        self.children.append(el)
        return el

    def _attr_str(self):
        out = []
        for k in sorted(self.attrs, key=lambda k: (_RANK.get(k, len(_RANK)), k)):
            v = self.attrs[k]
            v = num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)
            out.append(f' {k}="{_esc(v, True)}"')
        return "".join(out)

    def _render(self, lines):
        a = self._attr_str()
        if self.content is not None and not self.children:
            lines.append(f"<{self.tag}{a}>{_esc(self.content)}</{self.tag}>")
        elif not self.children:
            lines.append(f"<{self.tag}{a}/>")
        else:
            lines.append(f"<{self.tag}{a}>" + (_esc(self.content) if self.content else ""))
            for c in self.children:
                c._render(lines)
            lines.append(f"</{self.tag}>")

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


class Group(El):
    """A container; every drawing helper adds to it and returns the new element."""

    def g(self, cls=None, **attrs):
        return self.add(Group("g", {"class": cls, **_dash(attrs)}))

    def layer(self, name, on=False):
        """One view of a figure with a toggle; the default view is drawn with on=True."""
        return self.add(Group("g", {"class": "is-on" if on else None, "data-layer": name}))

    def rect(self, x, y, w, h, cls, rx=None):
        return self.add(El("rect", {"class": cls, "x": x, "y": y, "width": max(w, 0), "height": max(h, 0), "rx": rx}))

    def bar(self, x, y, w, h, cls, end="top", r=4):
        """A bar of box (x, y, w, h) rounded by r at its data end (top, bottom, left, right), square at the baseline."""
        r = max(0.0, min(r, w / 2 if end in ("top", "bottom") else h / 2, h if end in ("top", "bottom") else w))
        x1, y1 = x + w, y + h
        if r == 0:
            return self.rect(x, y, w, h, cls)
        a = f"A{num(r)} {num(r)} 0 0 1 "
        if end == "top":
            d = f"M{num(x)} {num(y1)}V{num(y + r)}{a}{num(x + r)} {num(y)}H{num(x1 - r)}{a}{num(x1)} {num(y + r)}V{num(y1)}Z"
        elif end == "bottom":
            d = f"M{num(x1)} {num(y)}V{num(y1 - r)}{a}{num(x1 - r)} {num(y1)}H{num(x + r)}{a}{num(x)} {num(y1 - r)}V{num(y)}Z"
        elif end == "right":
            d = f"M{num(x)} {num(y)}H{num(x1 - r)}{a}{num(x1)} {num(y + r)}V{num(y1 - r)}{a}{num(x1 - r)} {num(y1)}H{num(x)}Z"
        elif end == "left":
            d = f"M{num(x1)} {num(y1)}H{num(x + r)}{a}{num(x)} {num(y1 - r)}V{num(y + r)}{a}{num(x + r)} {num(y)}H{num(x1)}Z"
        else:
            raise ValueError(f"bar end must be top, bottom, left or right: {end!r}")
        return self.path(d, cls)

    def line(self, x1, y1, x2, y2, cls):
        return self.add(El("line", {"class": cls, "x1": x1, "y1": y1, "x2": x2, "y2": y2}))

    def path(self, d, cls):
        return self.add(El("path", {"class": cls, "d": d}))

    def polyline(self, points, cls, close=False):
        d = "M" + "L".join(f"{num(x)} {num(y)}" for x, y in points) + ("Z" if close else "")
        return self.path(d, cls)

    def circle(self, cx, cy, r, cls, ring=True):
        """A marker; ring=True adds the 2 px surface ring."""
        return self.add(El("circle", {"class": f"{cls} ring" if ring else cls, "cx": cx, "cy": cy, "r": r}))

    def text(self, x, y, s, cls="t", anchor="start", baseline="alphabetic"):
        """Text at (x, y); s may be a list of lines. baseline: alphabetic, middle, top or bottom."""
        lines = [s] if isinstance(s, str) else list(s)
        size = _t.style(cls)[0]
        dy = _t.baseline_dy(baseline, size)
        el = El("text", {"class": cls, "x": x, "y": y + dy, "text-anchor": None if anchor == "start" else anchor})
        if len(lines) == 1:
            el.content = lines[0]
        else:
            for i, ln in enumerate(lines):
                el.add(El("tspan", {"x": x, "dy": 0 if i == 0 else _t.LINE * size}, ln))
        el.box = _t.text_box(x, y, lines, cls, anchor, baseline)
        return self.add(el)

    def tip(self, text, hit=None, min_size=24):
        """A focusable group with data-tip and a child <title>; draw the marks into it.

        hit=(x, y, w, h) adds a transparent target grown to at least min_size on each side.
        Adjacent targets that tile an area (histogram columns) pass min_size=0 so they do not overlap.
        """
        g = self.add(Group("g", {"data-tip": text, "tabindex": "0"}))
        g.add(El("title", None, text))
        if hit is not None:
            x, y, w, h = hit
            if w < min_size:
                x, w = x - (min_size - w) / 2, min_size
            if h < min_size:
                y, h = y - (min_size - h) / 2, min_size
            g.rect(x, y, w, h, "hit")
        return g


def _dash(attrs):
    return {k.replace("_", "-"): v for k, v in attrs.items()}


class Svg(Group):
    """A figure document. The narrow variant (width < 540) prefixes its ids with '<id>-n'
    so both variants can sit on one page."""

    def __init__(self, fig_id, width, height, title, desc):
        super().__init__("svg")
        self.fig_id, self.width, self.height = fig_id, width, height
        self.base = fig_id if width >= 540 else f"{fig_id}-n"
        self.title, self.desc = title, desc

    def uid(self, name):
        return f"{self.base}-{name}"

    def render(self):
        w, h = self.width, self.height
        if not h:
            raise ValueError(f"{self.fig_id}: height not set")
        for el in self.walk():
            i = el.attrs.get("id")
            if i is not None and not str(i).startswith(self.fig_id):
                raise ValueError(f"id {i!r} does not start with {self.fig_id!r}")
        self._check_text(self, False)
        root = El("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {num(w)} {num(h)}",
            "role": "img",
            "aria-labelledby": f"{self.uid('t')} {self.uid('d')}",
        })
        root.add(El("title", {"id": self.uid("t")}, self.title))
        root.add(El("desc", {"id": self.uid("d")}, self.desc))
        root.children.extend(self.children)
        lines = []
        root._render(lines)
        return "\n".join(lines) + "\n"

    def _check_text(self, el, moved):
        moved = moved or "transform" in el.attrs
        if el.box and not moved:
            x0, y0, x1, y1 = el.box
            if x0 < -0.5 or y0 < -0.5 or x1 > self.width + 0.5 or y1 > self.height + 0.5:
                raise ValueError(f"{self.fig_id}@{self.width}: text {el.content or ''!r} outside the viewBox: {tuple(round(v) for v in el.box)}")
        for c in el.children:
            self._check_text(c, moved)
