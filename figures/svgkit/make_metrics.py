"""Write metrics.json: advance widths of Source Sans 3 at weights 400 and 600.

    python3 figures/svgkit/make_metrics.py [path/to/SourceSans3[wght].ttf]

Needs fontTools. The default font path is .cache/fonts/SourceSans3-VF.ttf.
"""
import json
import pathlib
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CHARS = (
    [chr(c) for c in range(0x20, 0x7F)]
    + [chr(c) for c in range(0xA0, 0x100)]
    + list("−×±≤≥≈→←↑↓…·%")
)


def tnum_map(font):
    """Glyph substitutions of the 'tnum' feature; figures in fig.css are tabular."""
    out = {}
    gsub = font["GSUB"].table
    for rec in gsub.FeatureList.FeatureRecord:
        if rec.FeatureTag != "tnum":
            continue
        for li in rec.Feature.LookupListIndex:
            for st in gsub.LookupList.Lookup[li].SubTable:
                st = getattr(st, "ExtSubTable", st)
                out.update(getattr(st, "mapping", {}) or {})
    return out


def widths(path, wght):
    font = instantiateVariableFont(TTFont(path), {"wght": wght})
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    tnum = tnum_map(font)
    adv = {}
    for ch in CHARS:
        glyph = cmap.get(ord(ch))
        if glyph is None:
            continue
        if ch.isdigit():
            glyph = tnum.get(glyph, glyph)
        adv[ch] = hmtx[glyph][0]
    return font, adv


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ROOT / ".cache/fonts/SourceSans3-VF.ttf"
    font, regular = widths(path, 400)
    _, semibold = widths(path, 600)
    os2 = font["OS/2"]
    data = {
        "font": "Source Sans 3",
        "units_per_em": font["head"].unitsPerEm,
        "cap_height": os2.sCapHeight,
        "x_height": os2.sxHeight,
        "figures": "tabular",
        "400": regular,
        "600": semibold,
    }
    (HERE / "metrics.json").write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8"
    )
    missing = [c for c in CHARS if c not in regular]
    print(f"{len(regular)} glyphs, missing: {''.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
