#!/usr/bin/env python3
"""Check the links of the built site.

Usage: check_links.py --internal public   every local href/src/#fragment resolves,
                                          and nothing is loaded from another host
       check_links.py --external public   outbound links answer (slow, local only)
       check_links.py --self-test
"""

import argparse
import html.parser
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "links.json"
CACHE_DAYS = 14
HOST_GAP = 3.0
USER_AGENT = "Mozilla/5.0 (compatible; site-link-check/1.0)"
SITE_HOSTS = {"plusky.github.io"}

# <link rel> values that name a page rather than load a resource.
LINK_RELS = {
    "alternate", "author", "bookmark", "canonical", "external", "help", "license", "me",
    "next", "nofollow", "noopener", "noreferrer", "pingback", "prev", "search", "tag", "webmention",
}
CSS_URL = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)|@import\s+(['"])(.*?)\3""", re.I)
SKIP_SCHEMES = ("mailto:", "tel:", "data:", "javascript:")


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.refs = []  # (line, url, kind) with kind "link" or "load"
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = dict(attrs)
        for key in ("id", "name") if tag == "a" else ("id",):
            if a.get(key):
                self.ids.add(a[key])
        for key, value in attrs:
            if value is None:
                continue
            if key == "href" or key == "xlink:href":
                if tag in ("a", "area"):
                    kind = "link"
                elif tag == "link":
                    rels = set((a.get("rel") or "").lower().split())
                    kind = "link" if rels and rels <= LINK_RELS else "load"
                else:
                    kind = "load"
                self.refs.append((line, value.strip(), kind))
            elif key in ("src", "poster") or (key == "data" and tag == "object"):
                self.refs.append((line, value.strip(), "load"))
            elif key in ("srcset", "imagesrcset"):
                for part in value.split(","):
                    if part.strip():
                        self.refs.append((line, part.split()[0], "load"))
            elif key == "style":
                self.refs += [(line, u, "load") for u in css_urls(value)]
        if tag == "style":
            self.in_style = True

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            line = self.getpos()[0]
            self.refs += [(line, u, "load") for u in css_urls(data)]


def css_urls(text):
    return [m.group(2) if m.group(2) is not None else m.group(4) for m in CSS_URL.finditer(text)]


def is_external(url):
    s = urlsplit(url)
    return bool(s.netloc) and s.netloc.lower() not in SITE_HOSTS


def local_path(public, base_file, url):
    """Map a same-site URL to (file path, fragment)."""
    url, frag = urldefrag(url)
    s = urlsplit(url)
    path = unquote(s.path)
    if not path:
        return base_file, frag
    target = public / path.lstrip("/") if path.startswith("/") else base_file.parent / path
    if target.is_dir() or path.endswith("/"):
        target = target / "index.html"
    return target, frag


def scan(public):
    pages, css = {}, {}
    for f in sorted(public.rglob("*")):
        if f.suffix in (".html", ".htm"):
            p = Page()
            p.feed(f.read_text(encoding="utf-8", errors="replace"))
            p.close()
            pages[f.resolve()] = p
        elif f.suffix == ".css":
            text = f.read_text(encoding="utf-8", errors="replace")
            css[f.resolve()] = [(text.count("\n", 0, m.start()) + 1, m.group(2) if m.group(2) is not None else m.group(4))
                                for m in CSS_URL.finditer(text)]
    return pages, css


def check_internal(public):
    public = public.resolve()
    pages, css = scan(public)
    problems = []

    def check(src, line, url, kind):
        if not url or url.lower().startswith(SKIP_SCHEMES):
            return
        if is_external(url):
            if kind == "load":
                problems.append(f"{src.relative_to(public)}:{line}: loads from another host: {url}")
            return
        if urlsplit(url).scheme not in ("", "http", "https"):
            return
        target, frag = local_path(public, src, url)
        try:
            target = target.resolve()
            target.relative_to(public)
        except ValueError:
            problems.append(f"{src.relative_to(public)}:{line}: points outside the site: {url}")
            return
        if not target.is_file():
            problems.append(f"{src.relative_to(public)}:{line}: missing target: {url}")
        elif frag and frag != "top" and target in pages and unquote(frag) not in pages[target].ids:
            problems.append(f"{src.relative_to(public)}:{line}: no id \"{unquote(frag)}\" in {target.relative_to(public)}: {url}")

    for f, page in pages.items():
        for line, url, kind in page.refs:
            check(f, line, url, kind)
    for f, refs in css.items():
        for line, url in refs:
            check(f, line, url, "load")
    for p in problems:
        print(p)
    if problems:
        print(f"check_links: {len(problems)} problem(s) in {len(pages)} page(s)", file=sys.stderr)
        return 1
    print(f"check_links: {len(pages)} page(s) and {len(css)} stylesheet(s) OK")
    return 0


def outbound(public):
    pages, _ = scan(public.resolve())
    found = defaultdict(list)
    for f, page in pages.items():
        for line, url, kind in page.refs:
            if kind == "link" and urlsplit(url).scheme in ("http", "https") and is_external(url):
                found[urldefrag(url)[0]].append(f"{f.relative_to(public.resolve())}:{line}")
    return found


def request(url, method):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if method == "GET":
                r.read(1024)
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except (urllib.error.URLError, OSError) as e:
        return None, str(getattr(e, "reason", e))


def check_external(public):
    if os.environ.get("CI"):
        print("check_links: --external is not run in CI", file=sys.stderr)
        return 2
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    now = time.time()
    links = outbound(public)
    todo = [u for u in links if not (cache.get(u, {}).get("ok") and now - cache[u]["checked"] < CACHE_DAYS * 86400)]
    print(f"check_links: {len(links)} outbound link(s), {len(todo)} to check")
    last = {}

    def polite(url, method):
        host = urlsplit(url).netloc.lower()
        wait = last.get(host, 0) + HOST_GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            return request(url, method)
        finally:
            last[host] = time.monotonic()

    by_host = defaultdict(list)
    for u in todo:
        by_host[urlsplit(u).netloc.lower()].append(u)
    # Interleave hosts so the per-host gap rarely has to be waited out.
    order, queues = [], list(by_host.values())
    while any(queues):
        order += [q.pop(0) for q in queues if q]
    unjudged = []
    for url in order:
        status, reason = polite(url, "HEAD")
        if status is None or status >= 400:
            status, reason = polite(url, "GET")
        ok = status is not None and status < 400
        if status == 429:
            unjudged.append(url)
            continue
        cache[url] = {"ok": ok, "status": status, "checked": now}
        if not ok:
            print(f"  {status or 'error'} {reason}: {url}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for u in unjudged:
        print(f"rate limited, not judged: {u}")
    broken = [u for u in links if u in cache and not cache[u]["ok"]]
    for u in broken:
        print(f"broken: {u}  (from {', '.join(links[u][:3])})")
    if broken:
        print(f"check_links: {len(broken)} broken outbound link(s)", file=sys.stderr)
        return 1
    print("check_links: outbound links OK")
    return 0


def self_test():
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        pub = Path(tmp) / "public"
        (pub / "posts" / "a").mkdir(parents=True)
        (pub / "css").mkdir()
        (pub / "index.html").write_text(
            '<link rel="stylesheet" href="/css/s.css"><link rel="canonical" href="https://plusky.github.io/">'
            '<link rel="me" href="https://github.com/x">'
            '<a href="posts/a/">a</a><a href="/posts/a/#sec">s</a><a href="https://example.org/x">x</a>'
            '<a href="mailto:x">m</a><svg><use href="#i1"/></svg><p id="i1"></p>', encoding="utf-8")
        (pub / "posts" / "a" / "index.html").write_text(
            '<h2 id="sec">S</h2><img src="../../css/../img.png" srcset="/img.png 2x"><a href="#sec">x</a>', encoding="utf-8")
        (pub / "img.png").write_bytes(b"")
        (pub / "css" / "s.css").write_text("body{background:url('../img.png')}", encoding="utf-8")
        out = capture(check_internal, pub)
        if out[0] != 0:
            failed += 1
            print(f"FAIL good site: {out[1]}")
        bad = {
            "index.html": '<a href="/nope/">x</a>\n<a href="/posts/a/#missing">y</a>\n'
                          '<script src="https://cdn.example/x.js"></script>\n<img src="//cdn.example/i.png">\n'
                          '<link rel="stylesheet" href="https://fonts.example/c.css">\n<div style="background:url(https://x.example/b.png)"></div>\n'
                          '<a href="#gone">z</a>\n<a href="../../etc/passwd">p</a>',
        }
        (pub / "index.html").write_text(bad["index.html"], encoding="utf-8")
        (pub / "css" / "s.css").write_text("@import 'https://fonts.example/f.css';\na{background:url(missing.png)}", encoding="utf-8")
        rc, text = capture(check_internal, pub)
        want = ["index.html:1: missing target", "index.html:2: no id \"missing\"", "index.html:3: loads from another host",
                "index.html:4: loads from another host", "index.html:5: loads from another host",
                "index.html:6: loads from another host", "index.html:7: no id \"gone\"", "index.html:8: points outside",
                "css/s.css:1: loads from another host", "css/s.css:2: missing target"]
        missing = [w for w in want if w not in text]
        if rc != 1 or missing:
            failed += 1
            print(f"FAIL bad site: rc={rc}, not reported: {missing}\n{text}")
        links = outbound(pub)
        if list(links) != []:
            failed += 1
            print(f"FAIL outbound: {list(links)}")
        (pub / "posts" / "a" / "index.html").write_text('<a href="https://example.org/p#x">x</a><a href="https://example.org/p">y</a>', encoding="utf-8")
        if list(outbound(pub)) != ["https://example.org/p"]:
            failed += 1
            print(f"FAIL outbound dedup: {list(outbound(pub))}")
    print(f"check_links self-test: {4 - failed}/4 passed")
    return 1 if failed else 0


def capture(fn, *args):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = fn(*args)
    return rc, buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description="Check the links of the built site.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--internal", metavar="DIR", type=Path)
    g.add_argument("--external", metavar="DIR", type=Path)
    g.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    public = args.internal or args.external
    if not public.is_dir() or not any(public.rglob("*.html")):
        print(f"check_links: {public} has no built pages; run 'make build' first", file=sys.stderr)
        return 2
    return check_internal(public) if args.internal else check_external(public)


if __name__ == "__main__":
    sys.exit(main())
