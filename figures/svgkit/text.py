"""Text measurement from the Source Sans 3 advance widths in metrics.json."""
import json
import pathlib

_M = json.loads((pathlib.Path(__file__).with_name("metrics.json")).read_text(encoding="utf-8"))
_UPM = _M["units_per_em"]
CAP = _M["cap_height"] / _UPM
DESCENT = 0.25
LINE = 1.3

# size, weight, monospace: mirrors the text classes of fig.css
STYLE = {
    "t": (13, 400, False),
    "t-strong": (13, 600, False),
    "t-muted": (12, 400, False),
    "t-big": (22, 600, False),
    "t-on": (12, 600, False),
    "t-mono": (12, 400, True),
}


def style(cls):
    for c in cls.split():
        if c in STYLE:
            return STYLE[c]
    raise ValueError(f"text needs one of the classes {sorted(STYLE)}: {cls!r}")


def text_width(text, size=13, weight=400):
    table = _M["600"] if weight >= 500 else _M["400"]
    fallback = table["n"]
    return sum(table.get(ch, fallback) for ch in text) * size / _UPM


def measure(text, cls="t"):
    size, weight, mono = style(cls)
    if mono:
        return 0.6 * size * len(text)
    return text_width(text, size, weight)


def baseline_dy(baseline, size):
    """Offset from y to the alphabetic baseline; avoids dominant-baseline, which renderers disagree on."""
    return {"alphabetic": 0, "middle": CAP * size / 2, "top": CAP * size, "bottom": -DESCENT * size}[baseline]


def text_box(x, y, lines, cls="t", anchor="start", baseline="alphabetic"):
    """Bounding box (x0, y0, x1, y1) of text placed as Group.text would place it."""
    if isinstance(lines, str):
        lines = [lines]
    size = style(cls)[0]
    w = max(measure(s, cls) for s in lines)
    x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
    base = y + baseline_dy(baseline, size)
    return (x0, base - CAP * size, x0 + w, base + (len(lines) - 1) * LINE * size + DESCENT * size)


def wrap(text, width, cls="t"):
    """Greedy word wrap to lines no wider than width (a single long word stays whole)."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}" if cur else word
        if cur and measure(trial, cls) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines
