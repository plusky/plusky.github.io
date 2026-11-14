"""Helpers shared by the diagram generators (no data file; build.py skips this module)."""
import math

from svgkit import measure

SLACK = 1.12  # the fallback font may be wider than Source Sans 3


def check(text, cls, maxw, where=""):
    w = measure(text, cls) * (1 if cls == "t-mono" else SLACK)
    if w > maxw:
        raise ValueError(f"{where}: {text!r} needs {w:.0f} > {maxw:.0f}")


def lines(g, x, y, items, maxw=None, where="", anchor="start", step=18):
    """items: list of (text, cls); returns the baseline after the last line."""
    for i, (s, cls) in enumerate(items):
        if maxw:
            check(s, cls, maxw, where)
        g.text(x, y + i * step, s, cls, anchor=anchor)
    return y + (len(items) - 1) * step


def head(g, x, y, ang, cls, size=7):
    """Arrowhead with its tip at (x, y), pointing along ang (radians)."""
    bx, by = x - size * math.cos(ang), y - size * math.sin(ang)
    px, py = -math.sin(ang) * size * 0.5, math.cos(ang) * size * 0.5
    g.polyline([(x, y), (bx + px, by + py), (bx - px, by - py)], cls, close=True)


def arrow(g, pts, kind="plain"):
    """A polyline arrow ending at the last point. kind: plain, off, focus."""
    line_cls, head_cls = {"plain": ("arrow", "head"), "off": ("arrow-off", "head-off"), "focus": ("s-focus", "c-focus")}[kind]
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 8 if kind == "focus" else 7
    # stop the shaft inside the head so its square end does not poke out
    sx, sy = x2 - (size - 1) * math.cos(ang), y2 - (size - 1) * math.sin(ang)
    g.polyline(list(pts[:-1]) + [(sx, sy)], line_cls)
    head(g, x2, y2, ang, head_cls, size)
