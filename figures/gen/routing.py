"""Diagram: the three turns of a job before and after nginx routed them by job id."""
from gen._diagram import arrow, check, lines
from svgkit import Svg, list_html

ID = "routing"
NARROW = True
POST = "failure-class-data"

TITLE = "Why turns two and three lost their cache"
DESC = ("The three turns of one job reuse most of their prompt from the server's cache, but the load balancer "
        "sent them to different servers.")
LENS = [96, 108, 120]
CACHED = 0.95
BAR = 18
PITCH = 48
SERVERS = "ABC"


def _panel(g, pw, after, where):
    head = [("After", "t-strong"), ("hash $http_x_openqa_job consistent;", "t-mono"),
            ("on 503 the request passes to the next server", "t-muted")] if after else \
        [("Before", "t-strong"), ("least_conn;", "t-mono"), ("ties go round robin", "t-muted")]
    lines(g, 0, 14, head, pw, where)
    sx, sw = pw - 40, 40
    nx, nw = 176, 46
    g.text(0, 78, "turn", "t-muted")
    g.text(sx + sw / 2, 78, "server", "t-muted", anchor="middle")
    r0 = 92
    rows = [r0 + i * PITCH for i in range(3)]
    g.rect(nx, r0 - 6, nw, rows[-1] + BAR + 6 - (r0 - 6), "box", rx=6)
    g.text(nx + nw / 2, (r0 + rows[-1] + BAR) / 2 + 4.5, "nginx", "t-strong", anchor="middle")
    check("nginx", "t-strong", nw - 8, where)
    for i, (y, n) in enumerate(zip(rows, LENS)):
        g.text(0, y + 13.5, str(i + 1), "t-strong")
        x0 = 18
        if after and i:
            c = n * CACHED
            g.rect(x0, y, c - 1, BAR, "c-ctl-soft")
            g.bar(x0 + c + 1, y, n - c - 1, BAR, "c-focus", end="right")
            status = "95% from the cache"
        else:
            g.bar(x0, y, n, BAR, "c-focus", end="right")
            status = "all read fresh" if i == 0 else f"all read fresh on {SERVERS[i]}"
        g.text(x0, y + BAR + 15, status, "t-muted")
        check(status, "t-muted", nx - x0 - 6, where)
        arrow(g, [(x0 + n + 6, y + BAR / 2), (nx, y + BAR / 2)])
        g.rect(sx, y - 5, sw, BAR + 10, "box", rx=6)
        g.text(sx + sw / 2, y + 13.5, SERVERS[i], "t-strong", anchor="middle")
        if not after:
            arrow(g, [(nx + nw, y + BAR / 2), (sx, y + BAR / 2)])
        else:
            ty = rows[0] + BAR / 2 + (i - 1) * 8
            arrow(g, [(nx + nw, y + BAR / 2), (sx, ty)])
    return rows[-1] + BAR + 18


def _legend(g, x, y):
    g.rect(x, y - 10, 12, 12, "c-focus")
    g.text(x + 18, y, "tokens read fresh", "t")
    x2 = x + 18 + 130
    g.rect(x2, y - 10, 12, 12, "c-ctl-soft")
    g.text(x2 + 18, y, "tokens taken from the cache", "t")


def render(data, width):
    s = Svg(ID, width, 0, TITLE, DESC)
    if width >= 540:
        h = _panel(s.g(transform="translate(0 0)"), 340, False, "routing before")
        _panel(s.g(transform="translate(380 0)"), 340, True, "routing after")
        s.line(360, 0, 360, h, "grid")
        _legend(s, 0, h + 24)
        s.height = h + 30
        return s
    _legend(s, 0, 14)
    h = _panel(s.g(transform="translate(0 32)"), 360, False, "routing-n before")
    s.line(0, 32 + h + 12, 360, 32 + h + 12, "grid")
    y2 = 32 + h + 30
    s.height = y2 + _panel(s.g(transform=f"translate(0 {y2})"), 360, True, "routing-n after")
    return s


ITEMS = [
    ("Each job asks three questions in one chat. Turn 2 and turn 3 repeat the whole earlier conversation, so most "
    "of their prompt is already in the cache of the server that answered turn 1."),
    ("Before: nginx with least_conn, where ties fall back to round robin.", [
        "Turn 1 goes to server A and is read fresh.",
        "Turn 2 goes to server B, which has no cached prompt and reads everything fresh.",
        "Turn 3 goes to server C, which also reads everything fresh.",
    ]),
    (("After: nginx with hash $http_x_openqa_job consistent, keyed on the job id the script sends in the "
     "X-Openqa-Job header."), [
        "All three turns go to server A.",
        "Turns 2 and 3 take 95% of their prompt tokens from the cache.",
        "If the server answers 503, the request passes to the next server.",
    ]),
]


def table(data):
    return list_html(ITEMS)
