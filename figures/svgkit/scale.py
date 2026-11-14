"""Scales and tick values."""
import math


def nice_ticks(lo, hi, n=5):
    """Ticks at 1, 2, 2.5 or 5 times a power of ten that cover [lo, hi] in about n steps."""
    if hi < lo:
        lo, hi = hi, lo
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= raw * (1 - 1e-9):
            break
    step = m * mag
    digits = max(0, -math.floor(math.log10(step) + 1e-9) + (1 if m == 2.5 else 0))
    start = math.floor(lo / step + 1e-9)
    end = math.ceil(hi / step - 1e-9)
    return [round(i * step, digits) for i in range(start, end + 1)]


def tick_labels(ticks, suffix=""):
    """Labels with one shared number of decimals and a true minus sign."""
    dec = 0
    for t in ticks:
        s = repr(float(t))
        if "e" not in s and "." in s:
            dec = max(dec, len(s.split(".")[1].rstrip("0")))
    return [f"{t:,.{dec}f}".replace("-", "−") + suffix for t in ticks]


class Linear:
    def __init__(self, domain, range_):
        (self.d0, self.d1), (self.r0, self.r1) = domain, range_

    def __call__(self, v):
        if self.d1 == self.d0:
            return (self.r0 + self.r1) / 2
        return self.r0 + (v - self.d0) * (self.r1 - self.r0) / (self.d1 - self.d0)

    def ticks(self, n=5):
        eps = abs(self.d1 - self.d0) * 1e-9
        lo, hi = min(self.d0, self.d1), max(self.d0, self.d1)
        return [t for t in nice_ticks(lo, hi, n) if lo - eps <= t <= hi + eps]


class Band:
    """Equal bands for categories along [start, end]; inner and outer padding as fractions of a step."""

    def __init__(self, keys, start, end, inner=0.3, outer=0.15):
        self.keys = list(keys)
        self.start, self.end = start, end
        n = len(self.keys)
        self.step = (end - start) / max(n - inner + 2 * outer, 1e-9)
        self.bw = self.step * (1 - inner)
        self._first = start + self.step * outer

    def __call__(self, key):
        return self._first + self.keys.index(key) * self.step

    def center(self, key):
        return self(key) + self.bw / 2

    def slot(self, key, cap=24):
        """(position, thickness) of a bar centred in the band, thickness capped at 24 px."""
        t = min(cap, self.bw)
        return self.center(key) - t / 2, t
