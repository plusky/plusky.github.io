#!/usr/bin/env python3
"""Check figure SVGs and their table files against figures/README.md.

Usage: check_svg.py PATH...      (directories are searched recursively)
       check_svg.py --self-test
"""

import re
import sys
import xml.parsers.expat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIG_CSS = ROOT / "assets" / "css" / "fig.css"

EXTRA_CLASSES = {"is-on"}
FORBIDDEN_TAGS = {"style", "script", "foreignObject"}
FORBIDDEN_ATTRS = {
    "fill", "stroke", "color", "stop-color", "flood-color", "lighting-color",
    "font", "font-family", "font-size", "font-weight", "font-style", "style",
}
ROOT_FORBIDDEN = {"width", "height", "style"}


class Node:
    __slots__ = ("tag", "attrs", "line", "children", "parent")

    def __init__(self, tag, attrs, line, parent):
        self.tag, self.attrs, self.line, self.parent = tag, attrs, line, parent
        self.children = []


def local(name):
    return name.rsplit(":", 1)[-1]


def parse(text):
    """Return (root Node, None) or (None, (line, message))."""
    parser = xml.parsers.expat.ParserCreate()
    stack, holder, problems = [], [], []

    def start(tag, attrs):
        node = Node(local(tag), attrs, parser.CurrentLineNumber, stack[-1] if stack else None)
        if stack:
            stack[-1].children.append(node)
        else:
            holder.append(node)
        stack.append(node)

    def end(_tag):
        stack.pop()

    def doctype(*_args):
        problems.append((parser.CurrentLineNumber, "DOCTYPE is not allowed"))

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = doctype
    try:
        parser.Parse(text, True)
    except xml.parsers.expat.ExpatError as e:
        return None, (e.lineno, f"not well-formed XML: {xml.parsers.expat.ErrorString(e.code)}")
    if problems:
        return None, problems[0]
    return holder[0], None


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def css_classes(css_text):
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    classes = set()
    for selector in re.findall(r"([^{}]+)\{", css_text):
        classes.update(re.findall(r"\.(-?[A-Za-z_][\w-]*)", selector))
    return classes


def figure_id(name):
    stem = name[:-4] if name.endswith(".svg") else name
    return stem[:-7] if stem.endswith(".narrow") else stem


def check_svg_text(name, text, classes):
    """Return a list of (line, message) for one SVG file named `name`."""
    root, err = parse(text)
    if err:
        return [err]
    out = []
    fid = figure_id(name)
    if root.tag != "svg":
        out.append((root.line, f"root element is <{root.tag}>, expected <svg>"))
    for attr in ("viewBox", "role", "aria-labelledby"):
        if attr not in root.attrs:
            out.append((root.line, f"root has no {attr}"))
    if root.attrs.get("role", "img") != "img":
        out.append((root.line, 'root role must be "img"'))
    for attr in sorted(ROOT_FORBIDDEN & set(root.attrs)):
        out.append((root.line, f"root must not have {attr}"))

    nodes = list(walk(root))
    by_id = {}
    for n in nodes:
        if "id" in n.attrs:
            if n.attrs["id"] in by_id:
                out.append((n.line, f'duplicate id "{n.attrs["id"]}"'))
            by_id[n.attrs["id"]] = n

    labels = root.attrs.get("aria-labelledby", "").split()
    found = set()
    for ref in labels:
        target = by_id.get(ref)
        if target is None:
            out.append((root.line, f'aria-labelledby names "{ref}", which is no id in the file'))
        elif target.tag not in ("title", "desc"):
            out.append((root.line, f'aria-labelledby "{ref}" is a <{target.tag}>, not <title> or <desc>'))
        else:
            found.add(target.tag)
    if "aria-labelledby" in root.attrs:
        for tag in ("title", "desc"):
            if tag not in found:
                out.append((root.line, f"aria-labelledby does not point at a <{tag}>"))

    layers = []
    for n in nodes:
        if n.tag in FORBIDDEN_TAGS:
            out.append((n.line, f"<{n.tag}> is not allowed"))
        for attr, value in n.attrs.items():
            name_l = local(attr)
            if attr.lower().startswith("on"):
                out.append((n.line, f"event handler attribute {attr} is not allowed"))
            elif name_l == "href" and not value.startswith("#"):
                out.append((n.line, f'{attr}="{value}" must be a same-document "#id"'))
            elif attr in FORBIDDEN_ATTRS:
                out.append((n.line, f'presentation attribute {attr}="{value}" is not allowed, use a class'))
        for token in n.attrs.get("class", "").split():
            if token not in classes and token not in EXTRA_CLASSES:
                out.append((n.line, f'class "{token}" is not defined in assets/css/fig.css'))
        if "id" in n.attrs and not n.attrs["id"].startswith(fid + "-"):
            out.append((n.line, f'id "{n.attrs["id"]}" does not start with "{fid}-"'))
        if "data-tip" in n.attrs:
            if not any(c.tag == "title" for c in n.children):
                out.append((n.line, "element with data-tip has no child <title>"))
            if "tabindex" not in n.attrs:
                out.append((n.line, "element with data-tip has no tabindex"))
        if "data-layer" in n.attrs:
            if n.tag != "g":
                out.append((n.line, f"data-layer on <{n.tag}>, expected <g>"))
            layers.append(n)
    if layers:
        on = [n for n in layers if "is-on" in n.attrs.get("class", "").split()]
        if len(on) != 1:
            out.append((layers[0].line, f"{len(on)} data-layer groups have class is-on, expected exactly 1"))
    return out


TABLE_RULES = [
    (re.compile(r"<\s*script\b", re.I), "script is not allowed"),
    (re.compile(r"(?:https?:)?//[A-Za-z0-9]", re.I), "external URL is not allowed"),
]


def check_table_text(text):
    out = []
    for rx, msg in TABLE_RULES:
        for m in rx.finditer(text):
            out.append((text.count("\n", 0, m.start()) + 1, msg))
    return out


def collect(paths):
    files, missing = [], []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.name.endswith((".svg", ".table.html")))
        elif p.is_file():
            files.append(p)
        else:
            missing.append(p)
    return files, missing


def run(paths):
    if not FIG_CSS.is_file():
        print(f"check_svg: {FIG_CSS.relative_to(ROOT)} not found; it defines the allowed classes", file=sys.stderr)
        return 2
    classes = css_classes(FIG_CSS.read_text(encoding="utf-8"))
    files, missing = collect(paths)
    for p in missing:
        print(f"check_svg: {p} does not exist, skipped", file=sys.stderr)
    findings = 0
    svgs = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        if f.name.endswith(".svg"):
            svgs += 1
            problems = check_svg_text(f.name, text, classes)
        else:
            problems = check_table_text(text)
        for line, msg in problems:
            print(f"{f}:{line}: {msg}")
        findings += len(problems)
    if not files:
        print("check_svg: no SVG or table files found", file=sys.stderr)
    if findings:
        print(f"check_svg: {findings} finding(s) in {len(files)} file(s)", file=sys.stderr)
        return 1
    print(f"check_svg: {svgs} SVG and {len(files) - svgs} table file(s) OK")
    return 0


GOOD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 200" role="img" aria-labelledby="f1-t f1-d">
<title id="f1-t">A</title><desc id="f1-d">B</desc>
<g data-layer="a" class="is-on"><rect class="c-test" x="1" y="1" width="2" height="2" data-tip="x" tabindex="0"><title>x</title></rect></g>
<g data-layer="b"><use href="#f1-m"/></g>
<path id="f1-m" class="axis" d="M0 0H1" opacity="0.5"/>
</svg>"""

BAD = [
    ("broken XML", GOOD.replace("</svg>", ""), "not well-formed"),
    ("doctype", '<!DOCTYPE svg [<!ENTITY a "b">]>' + GOOD, "DOCTYPE"),
    ("root width", GOOD.replace('viewBox=', 'width="720" viewBox='), "root must not have width"),
    ("no viewBox", GOOD.replace('viewBox="0 0 720 200" ', ""), "root has no viewBox"),
    ("no desc", GOOD.replace('<desc id="f1-d">B</desc>', ""), 'names "f1-d"'),
    ("label not title", GOOD.replace('"f1-t f1-d"', '"f1-m f1-d"'), "not <title> or <desc>"),
    ("style element", GOOD.replace("<title id", "<style>a{}</style><title id"), "<style> is not allowed"),
    ("script", GOOD.replace("</svg>", "<script>x</script></svg>"), "<script> is not allowed"),
    ("foreignObject", GOOD.replace("</svg>", "<foreignObject/></svg>"), "<foreignObject> is not allowed"),
    ("handler", GOOD.replace('class="axis"', 'class="axis" onclick="x()"'), "event handler"),
    ("external href", GOOD.replace('href="#f1-m"', 'href="https://x.example/a.svg#m"'), "same-document"),
    ("xlink href", GOOD.replace('href="#f1-m"', 'xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="a.svg"'), "same-document"),
    ("fill attr", GOOD.replace('class="axis"', 'class="axis" fill="#f00"'), "presentation attribute fill"),
    ("fill none", GOOD.replace('class="axis"', 'class="axis" fill="none"'), "presentation attribute fill"),
    ("font attr", GOOD.replace('class="axis"', 'class="axis" font-size="12"'), "font-size"),
    ("style attr", GOOD.replace('class="axis"', 'class="axis" style="x"'), "style"),
    ("unknown class", GOOD.replace('class="axis"', 'class="axis red"'), 'class "red"'),
    ("id prefix", GOOD.replace('"f1-m"', '"m"').replace('"#f1-m"', '"#m"'), 'does not start with "f1-"'),
    ("tip no title", GOOD.replace("<title>x</title>", ""), "no child <title>"),
    ("tip no tabindex", GOOD.replace(' tabindex="0"', ""), "no tabindex"),
    ("two layers on", GOOD.replace('<g data-layer="b">', '<g data-layer="b" class="is-on">'), "2 data-layer"),
    ("no layer on", GOOD.replace(' class="is-on"', ""), "0 data-layer"),
]


def self_test():
    classes = css_classes(".fig .c-test { fill: red; }\n/* .red */\n.fig .axis, .fig .grid { x: y; }")
    failed = 0

    def expect(label, problems, needle):
        nonlocal failed
        ok = any(needle in m for _, m in problems) if needle else not problems
        if not ok:
            failed += 1
            print(f"FAIL {label}: expected {needle or 'no finding'!r}, got {problems}")

    expect("good", check_svg_text("f1.svg", GOOD, classes), None)
    expect("good narrow", check_svg_text("f1.narrow.svg", GOOD, classes), None)
    for label, text, needle in BAD:
        expect(label, check_svg_text("f1.svg", text, classes), needle)
    expect("line number", [(ln, m) for ln, m in check_svg_text("f1.svg", BAD[11][1], classes) if ln == 4], "same-document")
    expect("table good", check_table_text("<table><tr><td>1</td></tr></table>"), None)
    expect("table script", check_table_text("<table>\n<script>x</script></table>"), "script")
    expect("table url", check_table_text('<a href="https://x.example/">x</a>'), "external URL")
    expect("table protocol-relative", check_table_text('<img src="//x.example/a.png">'), "external URL")
    if css_classes("/* .red */ .a{} .b .c {}") != {"a", "b", "c"}:
        failed += 1
        print("FAIL css class parsing")
    total = len(BAD) + 9
    print(f"check_svg self-test: {total - failed}/{total} passed")
    return 1 if failed else 0


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    if not argv or any(a.startswith("-") for a in argv):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
