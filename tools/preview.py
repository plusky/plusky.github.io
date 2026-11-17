"""Write .preview/light.html and .preview/dark.html showing every built figure wide and narrow.

    python3 -I tools/preview.py [--fig-dir content/posts/<post>/fig ...]

.preview/index.html links both. The pages inline tokens.css, fig.css and the SVGs, use the site
fonts from static/fonts when present, and carry a small tooltip script for data-tip.
"""
import argparse
import html
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / ".preview"

FONTS = [("Plain Sans", "plain-sans.woff2"), ("JetBrains Mono", "jetbrains-mono.woff2")]

PAGE_CSS = """
body { margin: 0; padding: 24px 16px; background: var(--bg); color: var(--ink); font-family: var(--font-ui); }
h2 { font-size: 15px; font-weight: 600; margin: 40px 0 12px; }
h3 { font-size: 12px; font-weight: 400; color: var(--ink-3); margin: 16px 0 6px; }
.fig { margin: 0; }
.w720 { width: 720px; } .w360 { width: 360px; }
table { border-collapse: collapse; font-size: 13px; margin-top: 12px; font-variant-numeric: tabular-nums; }
caption { text-align: left; color: var(--ink-2); padding-bottom: 6px; }
th, td { border-bottom: 1px solid var(--rule); padding: 2px 12px 2px 0; text-align: left; }
#tip { position: fixed; pointer-events: none; display: none; background: var(--plate); color: var(--ink);
  border: 1px solid var(--axis); border-radius: 4px; padding: 4px 8px; font-size: 13px; max-width: 280px; }
"""

SCRIPT = """
(function () {
  var tip = document.getElementById("tip"), cur = null;
  function show(el, x, y) {
    cur = el;
    tip.textContent = el.getAttribute("data-tip");
    tip.style.display = "block";
    var w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(x + 12, window.innerWidth - w - 8) + "px";
    tip.style.top = (y - h - 12 < 0 ? y + 16 : y - h - 12) + "px";
  }
  function hide() { cur = null; tip.style.display = "none"; }
  document.addEventListener("pointermove", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (el) show(el, e.clientX, e.clientY); else if (cur) hide();
  });
  document.addEventListener("focusin", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (!el) return hide();
    var r = el.getBoundingClientRect();
    show(el, r.left + r.width / 2, r.top);
  });
  document.addEventListener("focusout", hide);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });
})();
"""


def font_faces():
    out = []
    for family, name in FONTS:
        path = ROOT / "static/fonts" / name
        if path.exists():
            out.append(f'@font-face {{ font-family: "{family}"; src: url("{path.as_uri()}") format("woff2"); '
                       "font-weight: 400 700; }")
    return "\n".join(out)


def figures(fig_dir):
    blocks = []
    for wide in sorted(fig_dir.glob("*.svg")):
        if wide.name.endswith(".narrow.svg"):
            continue
        fig_id = wide.name[:-4]
        narrow = fig_dir / f"{fig_id}.narrow.svg"
        table = fig_dir / f"{fig_id}.table.html"
        svg_w = wide.read_text(encoding="utf-8")
        svg_n = narrow.read_text(encoding="utf-8") if narrow.exists() else svg_w
        blocks.append(
            f"<section><h2>{html.escape(fig_id)}</h2>"
            f'<h3>720</h3><figure class="fig w720">{svg_w}</figure>'
            f'<h3>360{"" if narrow.exists() else " (wide file)"}</h3><figure class="fig w360">{svg_n}</figure>'
            + (table.read_text(encoding="utf-8") if table.exists() else "")
            + "</section>"
        )
    return "\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fig-dir", action="append", help="default: the fig folder of every post")
    ap.add_argument("--out-dir", default=str(OUT), help="where light.html and dark.html go")
    args = ap.parse_args()
    out = pathlib.Path(args.out_dir).resolve()
    css = "\n".join((ROOT / "assets/css" / n).read_text(encoding="utf-8") for n in ("tokens.css", "fig.css"))
    fig_dirs = args.fig_dir or sorted(p.relative_to(ROOT) for p in ROOT.glob("content/posts/*/fig"))
    body = "\n".join(figures((ROOT / d).resolve()) for d in fig_dirs)
    out.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        page = (f'<!doctype html>\n<html lang="en" data-theme="{theme}">\n<head><meta charset="utf-8">'
                f"<title>Figures, {theme}</title>\n<style>\n{font_faces()}\n{css}\n{PAGE_CSS}</style></head>\n"
                f'<body>\n{body}\n<div id="tip" role="tooltip"></div>\n<script>{SCRIPT}</script>\n</body></html>\n')
        (out / f"{theme}.html").write_text(page, encoding="utf-8")
    (out / "index.html").write_text(
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Figures</title></head>\n'
        '<body><p><a href="light.html">light</a> · <a href="dark.html">dark</a></p></body></html>\n',
        encoding="utf-8")
    print(out / "light.html")
    print(out / "dark.html")


if __name__ == "__main__":
    main()
