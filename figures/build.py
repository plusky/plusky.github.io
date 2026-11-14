"""Build the figures of the post.

    python3 -I figures/build.py [--only ID] [--data-dir data/fig] [--out content/posts/failure-class/fig]

A generator is a module figures/gen/<name>.py with:

    ID = "chars-per-token"          # figure id; its data is <data-dir>/<ID>.json, or {} if there is none
    NARROW = True                   # also draw a 360-wide variant
    def render(data, width): ...    # -> svgkit.Svg, called with width 720 and, if NARROW, 360
    def table(data): ...            # -> HTML string, svgkit.table_html(...) or svgkit.list_html(...)

A diagram is a generator without a data file; render and table get an empty dict. Modules whose name
starts with an underscore are shared helpers, not generators.

It writes <out>/<ID>.svg, <ID>.narrow.svg and <ID>.table.html. Every class an SVG uses must be defined in
assets/css/fig.css.
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))


def known_classes():
    css = (ROOT / "assets/css/fig.css").read_text(encoding="utf-8")
    return set(re.findall(r"\.([a-z][a-z0-9-]*)", re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)))


def check_classes(name, svg, allowed):
    used = {c for attr in re.findall(r' class="([^"]*)"', svg) for c in attr.split()}
    unknown = sorted(used - allowed)
    if unknown:
        raise SystemExit(f"{name}: classes not in fig.css: {', '.join(unknown)}")


def load(path):
    spec = importlib.util.spec_from_file_location(f"gen_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, text):
    path.write_bytes(text.encode("utf-8"))
    print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def main():
    ap = argparse.ArgumentParser(description="Build the figures of the post.")
    ap.add_argument("--only", metavar="ID")
    ap.add_argument("--data-dir", default="data/fig")
    ap.add_argument("--out", default="content/posts/failure-class/fig")
    args = ap.parse_args()
    data_dir = (ROOT / args.data_dir).resolve()
    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    allowed = known_classes()

    for path in sorted((HERE / "gen").glob("[!_]*.py")):
        mod = load(path)
        if args.only and mod.ID != args.only:
            continue
        src = data_dir / f"{mod.ID}.json"
        data = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
        variants = [(720, f"{mod.ID}.svg")] + ([(360, f"{mod.ID}.narrow.svg")] if mod.NARROW else [])
        for width, name in variants:
            svg = mod.render(data, width).render()
            check_classes(name, svg, allowed)
            write(out / name, svg)
        if not mod.NARROW:
            (out / f"{mod.ID}.narrow.svg").unlink(missing_ok=True)
        write(out / f"{mod.ID}.table.html", mod.table(data))


if __name__ == "__main__":
    main()
