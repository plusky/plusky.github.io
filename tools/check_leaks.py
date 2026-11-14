#!/usr/bin/env python3
"""Scan text files for data that must not be published.

usage: python3 tools/check_leaks.py [--deny FILE] PATH...

Exits 1 and lists every hit. Without --deny, ~/.config/plusky-site/denylist.txt is read if it exists
(one literal string per line, matched case-insensitively). find_leaks(text) can be imported.
"""

import argparse
import pathlib
import re
import sys

# Patterns are assembled from pieces so that this file does not flag itself.
_LOW, _HIGH = 23 * 10**6, 26 * 10**6 - 1
_NUMBER = re.compile(r"(?<![\d.,'_])\d{1,3}(?:[,'_   ]\d{3})+(?![\d]|[.,]\d)|(?<![\d.,'_])\d{8}(?![\d]|[.,]\d)")
_DOT = r"\."
_HOSTS = [
    ("internal host", re.compile(r"(?<![a-z0-9-])suse" + _DOT + r"de(?![a-z0-9-])", re.I)),
    ("internal host", re.compile(_DOT + "suse" + _DOT + r"cz(?![a-z0-9-])", re.I)),
    ("internal host", re.compile(r"qam" + _DOT + "suse", re.I)),
    ("openqa host", re.compile(r"(?<![a-z0-9-])open" + r"qa" + _DOT + r"(?!opensuse" + _DOT + r"org(?![a-z0-9.-]))"
                               r"[a-z0-9-]+(?:" + _DOT + r"[a-z0-9-]+)*" + _DOT + r"[a-z]{2,}(?![a-z0-9-])", re.I)),
]
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+" + "@" + r"[A-Za-z0-9-]+(?:" + _DOT + r"[A-Za-z0-9-]+)*" + _DOT + r"[A-Za-z]{2,}")
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_PRIVATE_IP = re.compile(
    r"(?<![\d.])(?:"
    + r"10" + _DOT + _OCTET + _DOT + _OCTET + _DOT + _OCTET
    + r"|172" + _DOT + r"(?:1[6-9]|2\d|3[01])" + _DOT + _OCTET + _DOT + _OCTET
    + r"|192" + _DOT + r"168" + _DOT + _OCTET + _DOT + _OCTET
    + r")(?![\d]|\.\d)"
)
_LITERALS = [
    ("openQA data path", "/var/lib/" + "open" + "qa"),
    ("private link", "cl" + "aude.ai/" + "artifact"),
]
DEFAULT_DENY = pathlib.Path.home() / ".config" / "plusky-site" / "denylist.txt"


def load_deny(path: pathlib.Path | None) -> list[str]:
    path = path or DEFAULT_DENY
    if not path.exists():
        return []
    return [s.strip() for s in path.read_text().splitlines() if s.strip() and not s.startswith("#")]


def find_leaks(text: str, deny: list[str] | None = None) -> list[tuple[int, str, str]]:
    """(line number, kind, matched text) for every hit in text."""
    deny = load_deny(None) if deny is None else deny
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in _NUMBER.finditer(line):
            value = int(re.sub(r"\D", "", m.group(0)))
            if _LOW <= value <= _HIGH:
                hits.append((n, "internal job id range", m.group(0)))
        for kind, rx in _HOSTS:
            hits += [(n, kind, m.group(0)) for m in rx.finditer(line)]
        hits += [(n, "e-mail address", m.group(0)) for m in _EMAIL.finditer(line)]
        hits += [(n, "private IP address", m.group(0)) for m in _PRIVATE_IP.finditer(line)]
        low = line.lower()
        for kind, s in _LITERALS:
            if s in low:
                hits.append((n, kind, s))
        for s in deny:
            if s.lower() in low:
                hits.append((n, "deny list", s))
    return hits


def files(paths: list[str]):
    for p in map(pathlib.Path, paths):
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and ".git" not in f.parts:
                    yield f
        elif p.is_file():
            yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="List data that must not be published.")
    parser.add_argument("--deny", type=pathlib.Path, help="deny list, one literal string per line")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    deny = load_deny(args.deny)
    if args.deny and not args.deny.exists():
        parser.error(f"deny list {args.deny} not found")
    found = 0
    for f in files(args.paths):
        raw = f.read_bytes()
        if b"\0" in raw[:8192]:
            continue
        for n, kind, text in find_leaks(raw.decode("utf-8", "replace"), deny):
            print(f"{f}:{n}: {kind}: {text}")
            found += 1
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
