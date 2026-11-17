#!/usr/bin/env python3
"""Check that every number in a post is a known fact.

Usage: check_facts.py content/posts/<post>/index.md...
       check_facts.py --self-test

A number passes when it equals the value of a fact in data/facts.json or in a
data/facts-<name>.json beside it, when the text around it matches one of that
fact's forms, or when it is listed in
data/facts_allow.txt ("<token>  # <reason>"). Years, ordinals, "#814", dotted
versions such as 1.2.3 and ISO dates pass without an entry; number words are
not numbers here.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "data" / "facts.json"
ALLOW = ROOT / "data" / "facts_allow.txt"

# Thousands separators: a comma, a no-break, narrow no-break or thin space, or a plain space when
# every later group has exactly three digits and no digit follows.
NUM = (
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\d{1,3}(?:[\u00a0\u202f\u2009]\d{3})+(?:\.\d+)?"
    r"|\d{1,3}(?: \d{3})+(?! ?\d)(?:\.\d+)?"
    r"|\d+(?:\.\d+)?"
)
TOKEN = re.compile(
    rf"(?<![\w.,#/:-])(?P<a>{NUM})(?:\s+of\s+(?P<b>{NUM}))?(?P<pct>\s?%|\s+per\s?cent\b)?(?![\w%]|\.\d|,\d)",
    re.I,
)
SKIP = [
    re.compile(r"(?<![\w.])\d+(?:\.\d+){2,}(?![\w.]\d)"),  # dotted versions
    re.compile(r"(?<![\w.])\d{4}-\d{2}-\d{2}(?!\d)"),  # ISO dates
]


def blank(text, start, end):
    return text[:start] + re.sub(r"[^\n]", " ", text[start:end]) + text[end:]


def blank_all(text, rx, flags=0, keep=None):
    """Replace every match of rx by spaces, except the span of group `keep` if it matched."""
    for m in reversed(list(re.finditer(rx, text, flags))):
        if keep and m.group(keep) is not None:
            text = blank(text, m.end(keep), m.end())
            text = blank(text, m.start(), m.start(keep))
        else:
            text = blank(text, m.start(), m.end())
    return text


def prose(text):
    """Blank everything that is not prose, keeping offsets and line numbers."""
    fm = re.match(r"(---|\+\+\+)[ \t]*\n.*?^\1[ \t]*$", text, re.S | re.M)
    if fm:
        text = blank(text, 0, fm.end())
    text = blank_all(text, r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]*\1[ \t]*$|\Z)", re.S | re.M)
    text = blank_all(text, r"<!--.*?-->", re.S)
    text = blank_all(
        text,
        r"\{\{[<%]\s*/?\s*(?:fig\b(?:[^>%]|[>%](?!\}\}))*?\bcaption\s*=\s*(?P<q>[\"`])(?P<cap>.*?)(?P=q)"
        r"(?:[^>%]|[>%](?!\}\}))*?|(?:[^>%]|[>%](?!\}\}))*?)[>%]\}\}",
        re.S,
        keep="cap",
    )
    text = blank_all(text, r"(`+).+?\1", re.S)
    text = blank_all(text, r"\[\^[^\]\s]+\]")
    text = blank_all(text, r"\{#[^}\s]*\}")
    text = blank_all(text, r"^[ \t]*\[[^\]]+\]:[ \t]*\S+.*$", re.M)
    text = blank_all(text, r"\]\([^)\s]*(?:\s+\"[^\"]*\")?\)")
    text = blank_all(text, r"<[A-Za-z/!][^>]*>")
    text = blank_all(text, r"\b(?:https?|ftp)://[^\s)>\]]+|\bwww\.[^\s)>\]]+|\S+@\S+\.\w+")
    for rx in SKIP:
        text = blank_all(text, rx)
    return text


def as_number(s):
    return float(re.sub(r"[,\s]", "", s))


def form_regex(form):
    return re.compile(r"\s+".join(map(re.escape, form.split())).replace("%", r"(?:\s?%|\s+per\s?cent)"), re.I)


class Facts:
    def __init__(self, facts, allow):
        self.values, self.pct_values, self.forms = set(), set(), []
        for key, fact in facts.items():
            v = fact.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self.values.add(float(v))
            elif isinstance(v, str) and re.fullmatch(rf"\s*(?:{NUM})\s*%?\s*", v):
                (self.pct_values if "%" in v else self.values).add(as_number(v.strip(" %")))
            self.forms += [form_regex(f) for f in fact.get("forms", []) if f.strip()]
        self.allow = allow

    def known(self, m, text):
        a, b, pct = m.group("a"), m.group("b"), m.group("pct")
        tok = m.group(0)
        if tok in self.allow or tok.replace(" ", "") in self.allow:
            return True
        lo, hi = max(0, m.start() - 200), m.end() + 200
        window = text[lo:hi]
        for rx in self.forms:
            for f in rx.finditer(window):
                if f.start() + lo <= m.start() and f.end() + lo >= m.end():
                    return True
        if b is not None:
            return as_number(a) in self.values and as_number(b) in self.values
        if pct:
            return as_number(a) in self.pct_values
        if a in self.allow:
            return True
        n = as_number(a)
        if n in self.values:
            return True
        return re.fullmatch(r"(19|20)\d\d", a) is not None


def unknown_numbers(text, facts):
    """Return [(line, token, context)] for numbers in prose that no fact covers."""
    clean = prose(text)
    out = []
    for m in TOKEN.finditer(clean):
        if facts.known(m, clean):
            continue
        line = clean.count("\n", 0, m.start()) + 1
        ctx = " ".join(clean[max(0, m.start() - 40):m.end() + 40].split())
        out.append((line, " ".join(m.group(0).split()), ctx))
    return out


def load_allow(path):
    allow, errors = set(), []
    if not path.is_file():
        print(f"check_facts: {path.relative_to(ROOT)} not found, no extra numbers allowed", file=sys.stderr)
        return allow, errors
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or re.match(r"\s*#(\s|$)", line):
            continue
        m = re.match(r"\s*(\S+)\s+#\s*\S", line)
        if m:
            allow.add(m.group(1))
        else:
            errors.append(f"{path.relative_to(ROOT)}:{n}: expected '<token>  # <reason>'")
    return allow, errors


def svg_descs(post):
    """Yield (svg path, line, desc text) for the figures of a post bundle."""
    for svg in sorted((post.parent / "fig").glob("*.svg")):
        raw = svg.read_text(encoding="utf-8")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            print(f"{svg}: cannot parse ({e}); run tools/check_svg.py", file=sys.stderr)
            continue
        for el in root:
            if el.tag.rsplit("}", 1)[-1] == "desc":
                pos = raw.find("<desc")
                yield svg, raw.count("\n", 0, max(pos, 0)) + 1, "".join(el.itertext())


def run(paths):
    if not FACTS.is_file():
        print(f"check_facts: {FACTS.relative_to(ROOT)} not found; it lists the numbers a post may quote", file=sys.stderr)
        return 2
    facts_json = {}
    for path in sorted(FACTS.parent.glob("facts*.json")):
        try:
            part = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"check_facts: {path.relative_to(ROOT)}: {e}", file=sys.stderr)
            return 2
        if again := sorted(facts_json.keys() & part.keys()):
            print(f"check_facts: {path.relative_to(ROOT)}: keys of another facts file: {', '.join(again)}", file=sys.stderr)
            return 2
        facts_json.update(part)
    allow, errors = load_allow(ALLOW)
    for e in errors:
        print(e)
    facts = Facts(facts_json, allow)
    if not paths:
        print("check_facts: no posts given, nothing to check")
        return 1 if errors else 0
    found = len(errors)
    for p in map(Path, paths):
        if not p.is_file():
            print(f"check_facts: {p} does not exist", file=sys.stderr)
            found += 1
            continue
        for line, tok, ctx in unknown_numbers(p.read_text(encoding="utf-8"), facts):
            print(f"{p}:{line}: unknown number {tok!r} in \"...{ctx}...\"")
            found += 1
        for svg, line, desc in svg_descs(p):
            for _, tok, ctx in unknown_numbers(desc, facts):
                print(f"{svg}:{line}: unknown number {tok!r} in <desc> \"...{ctx}...\"")
                found += 1
    if found:
        print(f"check_facts: {found} problem(s); add the fact to data/facts.json, or the token with a reason to data/facts_allow.txt", file=sys.stderr)
        return 1
    print(f"check_facts: {len(paths)} post(s) OK")
    return 0


SAMPLE = """---
title: "28 things"
date: 2026-11-14
---
# Results {#r-2026}

Of all failures, 28 of 71 were product bugs, which is 39%. That held in 2025.
We looked at 1,204 jobs over 3 weeks[^1] and 12.5 hours.
See `run 99 times` and https://example.org/a/42 and [PR](https://x.example/7).
Fixed in #814, version 1.2.3, on the 2nd try, with Python 3.13 and x86_64.

```
77 lines of code
```

{{< fig id="f2" caption="Share was 40% here" alt="5 bars" >}}
{{< note n="5" >}}
<span data-x="66">ok</span> but 17 of 20 and 6% and 1 of 3 are wrong.

[^1]: Over 10 days.
"""

SAMPLE_FACTS = {
    "product": {"value": 28, "forms": ["28 of 71", "39%"], "what": "", "scope": ""},
    "jobs": {"value": 1204, "forms": [], "what": "", "scope": ""},
    "share": {"value": "40%", "forms": [], "what": "", "scope": ""},
    "hours": {"value": 12.5, "forms": ["3 weeks"], "what": "", "scope": ""},
    "one": {"value": 1, "forms": [], "what": "", "scope": ""},
}


def self_test():
    failed = 0
    facts = Facts(SAMPLE_FACTS, {"3.13", "10"})
    got = [(ln, tok) for ln, tok, _ in unknown_numbers(SAMPLE, facts)]
    want = [(18, "17 of 20"), (18, "6%"), (18, "1 of 3")]
    if got != want:
        failed += 1
        print(f"FAIL sample: expected {want}, got {got}")
    cases = [
        ("percent needs percent value", "It was 28% then.", ["28%"]),
        ("decimal", "Took 4.5 s.", ["4.5"]),
        ("sentence end", "We saw 1204.", []),
        ("negative context", "a-1 b/2 c:3", []),
        ("percent word", "about 39 percent", []),
        ("unknown form part", "28 of 70", ["28 of 70"]),
        ("no-break space group", "We looked at 1\u00a0204 jobs.", []),
        ("narrow no-break space group", "We looked at 1\u202f204 jobs.", []),
        ("thin space group", "We looked at 1\u2009204 jobs.", []),
        ("plain space group", "We looked at 1 204 jobs.", []),
        ("plain space groups", "In 12 345 678 runs.", ["12 345 678"]),
        ("no-break space, short group", "Saw 1\u00a020 runs.", ["20"]),
        ("plain space, digits follow", "Saw 1 204 5 runs.", ["204", "5"]),
        ("plain space, long group", "Saw 7 3048 runs.", ["7", "3048"]),
    ]
    for label, text, want in cases:
        got = [tok for _, tok, _ in unknown_numbers(text, facts)]
        if got != want:
            failed += 1
            print(f"FAIL {label}: expected {want}, got {got}")
    total = len(cases) + 1
    print(f"check_facts self-test: {total - failed}/{total} passed")
    return 1 if failed else 0


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    if any(a.startswith("-") for a in argv):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
