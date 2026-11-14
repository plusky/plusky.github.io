"""Diagram: from a failed job through one prompt and three model answers to the job comment and its readers."""
from gen._diagram import arrow, check, lines
from svgkit import Svg, list_html

ID = "pipeline"
NARROW = True

TITLE = "From a failed job to a comment"
DESC = "The model gives three answers per job, and only one of them is wired to anything."
P = 12  # inner padding
R = 6

A = [("Test job fails", "t-strong"), ("the job-done hook finds", "t"), ("no known issue and runs", "t"),
     ("openqa-llm-investigate", "t-mono")]
B = [("One prompt", "t-strong"), ("failure analysis of the log", "t"), ("earlier reviews of the module", "t"),
     ("settings diff to last good job", "t"), ("test commits since then", "t")]
C_HEAD = [("llama.cpp server", "t-strong"), ("Gemma 4 E4B, 3 hosts, nginx", "t-muted")]
TURNS = [("Q1", "analysis per module"), ("Q2", "summary, at most 2 sentences"), ("Q3", "verdict, with job statistics")]


def _box(g, x, y, w, h, cls="box"):
    g.rect(x, y, w, h, cls, rx=R)


def _server(g, x, y, w, where):
    _box(g, x, y, w, 112)
    yb = lines(g, x + P, y + 24, C_HEAD, w - 2 * P, where)
    for i, (q, s) in enumerate(TURNS):
        by = yb + 24 + i * 18
        g.text(x + P, by, q, "t-strong")
        check(s, "t", w - 2 * P - 28, where)
        g.text(x + P + 28, by, s, "t")


def _outputs(g, x, y, w, rx, rw, narrow):
    """Comment box at (x, y, w) and its three readers at (rx, rw). Returns the bottom."""
    where = f"{ID} outputs"
    cls_vals = [("Product bug | Test issue |", "t-muted"), ("Infrastructure problem", "t-muted")]
    head_lines = [("Job comment" if narrow else "Comment on the job", "t-strong"), ("ends with three lines:", "t-muted")]
    # readers, top to bottom; each row is aligned with its line in the comment
    people = [("People only", "t-strong"), ("reviewed 2.2% of", "t"), ("commented jobs", "t")] if narrow else \
        [("People only", "t-strong"), ("reviewed 2.2% of commented jobs", "t")]
    bisect = [("openqa-investigate", "t-strong"), ("retry, last good tests", "t"), ("and build, then", "t"),
              ("bisect jobs", "t")] if narrow else \
        [("openqa-investigate", "t-strong"), ("retry, last good tests and build,", "t"),
         ("then openqa-trigger-bisect-jobs", "t")]

    lines(g, x + P, y + 24, head_lines, w - 2 * P, where)
    h1 = 14 + 18 * len(people)
    e1_y = y + 58
    mid1 = e1_y + h1 / 2
    c_y = mid1 - 14  # the mono line and its two value lines centre on the reader
    lines(g, x + P, c_y, [("Classification:", "t-mono")], w - 2 * P, where)
    lines(g, x + P, c_y + 18, cls_vals, w - 2 * P, where, step=16)
    _box(g, rx, e1_y, rw, h1)
    lines(g, rx + P, e1_y + 23, people, rw - 2 * P, where)
    arrow(g, [(x + w, mid1), (rx, mid1)])
    if not narrow:
        g.text((x + w + rx) / 2, mid1 - 7, "read", "t-muted", anchor="middle")

    h2 = 14 + 18 * len(bisect)
    e2_y = e1_y + h1 + 12
    b_y = e2_y + 22
    lines(g, x + P, b_y + 4, [("BISECT: YES | NO", "t-mono")], w - 2 * P, where)
    _box(g, rx, e2_y, rw, h2, "box-focus")
    lines(g, rx + P, e2_y + 23, bisect, rw - 2 * P, where)
    arrow(g, [(x + w, b_y), (rx, b_y)], "focus")
    g.text((x + w + rx) / 2, b_y - 8, "YES", "t-strong", anchor="middle")

    r_y = e2_y + h2 + 24
    lines(g, x + P, r_y + 4, [("Restart: YES | NO", "t-mono")], w - 2 * P, where)
    arrow(g, [(x + w, r_y), (rx - 4, r_y)], "off")
    nc = [("not connected:", "t-strong"), ("nothing acts on it", "t")] if narrow else \
        [("not connected: nothing acts on it", "t")]
    lines(g, rx + 4, r_y + 4, nc, rw, where)
    bottom = r_y + 4 + 18 * (len(nc) - 1) + 16
    _box(g, x, y, w, bottom - y)
    # the comment box is drawn last but belongs behind its text
    g.children.insert(0, g.children.pop())
    return bottom


def _wide():
    s = Svg(ID, 720, 0, TITLE, DESC)
    g = s.g()
    _box(g, 0, 0, 190, 112)
    lines(g, P, 24, A, 190 - 2 * P, "pipeline A")
    arrow(g, [(190, 56), (224, 56)])
    _box(g, 224, 0, 224, 112)
    lines(g, 224 + P, 24, B, 224 - 2 * P, "pipeline B")
    arrow(g, [(448, 56), (482, 56)])
    _server(g, 482, 0, 238, "pipeline C")
    arrow(g, [(601, 112), (601, 138), (150, 138), (150, 160)])
    g.text(378, 131, "the script posts the replies", "t-muted", anchor="middle")
    s.height = _outputs(s.g(), 0, 160, 300, 400, 320, False) + 4
    return s


def _narrow():
    s = Svg(ID, 360, 0, TITLE, DESC)
    g = s.g()
    W = 360
    y = 0
    _box(g, 0, y, W, 94)
    lines(g, P, y + 24, A, W - 2 * P, "pipeline-n A")
    y += 94
    arrow(g, [(W / 2, y), (W / 2, y + 26)])
    y += 26
    _box(g, 0, y, W, 112)
    lines(g, P, y + 24, B, W - 2 * P, "pipeline-n B")
    y += 112
    arrow(g, [(W / 2, y), (W / 2, y + 26)])
    y += 26
    _server(g, 0, y, W, "pipeline-n C")
    y += 112
    arrow(g, [(80, y), (80, y + 34)])
    g.text(92, y + 22, "the script posts the replies", "t-muted")
    y += 34
    s.height = _outputs(s.g(), 0, y, 164, 198, 162, True) + 4
    return s


def render(data, width):
    return _wide() if width >= 540 else _narrow()


ITEMS = [
    "A test job fails on openQA. If no known issue matches, the job-done hook runs openqa-llm-investigate.",
    ("The script builds one prompt from:", [
        "the failure analysis of the job's log, with earlier reviews of runs failing in the same module",
        "the settings difference to the last good job",
        "the test commits since the last good job",
    ]),
    ("It asks a llama.cpp server running Gemma 4 E4B (three hosts behind nginx) three questions in one chat:", [
        "question 1: the analysis, one line per failed module",
        "question 2: a summary of at most two sentences",
        "question 3: the verdict, with the job statistics",
    ]),
    ("The script posts a comment on the job that ends with three lines:", [
        ("Classification: Product bug | Test issue | Infrastructure problem. Only people read it; they reviewed "
        "2.2% of the commented jobs."),
        ("BISECT: YES | NO. On YES the hook starts openqa-investigate (a retry and reruns with the last good tests "
        "and build) and then openqa-trigger-bisect-jobs. This is the only answer wired to anything."),
        "Restart: YES | NO. Not connected: nothing acts on it.",
    ]),
]


def table(data):
    return list_html(ITEMS)
