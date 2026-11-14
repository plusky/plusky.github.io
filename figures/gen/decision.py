"""Diagram: a chat model writes its answer, a decision model returns a probability per answer."""
from gen._diagram import SLACK, arrow, check, lines
from svgkit import Svg, list_html, wrap

ID = "decision"
NARROW = True

TITLE = "One writes, one weighs"
DESC = ("A chat model writes an answer token by token; a decision model returns a probability for each answer "
        "it was given.")
LX, BX, SCALE = 0, 104, 180  # label column, bar start, px per 1.0
CLASSES = [("product bug", 0.43, "c-product"), ("test issue", 0.35, "c-test"), ("infrastructure", 0.22, "c-infra")]
ENV, THRESHOLD = 0.06, 0.3
RULE = ("Rule used in the article: an environment answer of at least 0.3 means infrastructure, otherwise "
        "whichever of product bug and test issue has the higher probability. Here 0.06 is below 0.3, so: "
        "product bug.")


def _box(g, w, y, text, cls, where):
    g.rect(0, y, w, 30, "box", rx=6)
    check(text, cls, w - 24, where)
    g.text(12, y + 19.5, text, cls)


def _prob_bar(g, y, label, p, cls, where, h=18):
    g.text(LX, y + h / 2 + 4.5, label, "t")
    check(label, "t", BX - LX - 6, where)
    g.bar(BX, y, max(p * SCALE, 2), h, cls, end="right")
    g.text(BX + p * SCALE + 6, y + h / 2 + 4.5, "1.0" if p == 1 else f"{p:.2f}", "t")


def _chat(g, w):
    where = f"{ID} chat@{w}"
    lines(g, 0, 14, [("Chat model writes", "t-strong"), ("Gemma 4 E4B", "t-muted")], w, where)
    _box(g, w, 46, "prompt with the job state", "t", where)
    arrow(g, [(24, 76), (24, 102)])
    g.text(36, 93, "generates token by token", "t-muted")
    tw = round(w * 0.9)
    g.rect(0, 104, tw - 1, 22, "c-ctl-soft")
    g.bar(tw + 1, 104, w - tw - 1, 22, "c-ctl", end="right")
    g.text(0, 143, "thinking, about 90% of the tokens", "t")
    g.text(w, 143, "text", "t", anchor="end")
    check("thinking, about 90% of the tokens    text", "t", w, where)
    _box(g, w, 154, "… Classification: Product bug", "t-mono", where)
    g.text(0, 202, "the class is parsed from the last lines", "t-muted")
    g.text(0, 232, "probability of the answer token", "t-strong")
    _prob_bar(g, 242, "product bug", 1.0, "c-product", where)
    note = [("about 1.0 whatever the answer,", "t-muted"), ("so it says nothing about confidence", "t-muted")]
    return lines(g, 0, 282, note, w, where)


def _decision(g, w):
    where = f"{ID} decision@{w}"
    lines(g, 0, 14, [("Decision model weighs", "t-strong"), ("elephant-1, 9B", "t-muted")], w, where)
    _box(g, w, 46, "job state + question + list of answers", "t", where)
    arrow(g, [(24, 76), (24, 102)])
    g.text(36, 93, "returns one probability per answer", "t-muted")
    for i, (label, p, cls) in enumerate(CLASSES):
        _prob_bar(g, 106 + i * 26, label, p, cls, where)
    g.text(0, 202, "second question, yes or no", "t-muted")
    g.text(0, 232, "did the test environment fail?", "t-strong")
    _prob_bar(g, 242, "yes", ENV, "c-infra", where)
    tx = BX + THRESHOLD * SCALE
    g.line(tx, 236, tx, 266, "ref")
    g.text(tx + 6, 282, "threshold 0.3", "t-muted")
    return 282


def _rule(g, y, w):
    g.line(0, y, w, y, "grid")
    rl = wrap(RULE, w / SLACK, "t")
    lines(g, 0, y + 26, [(ln, "t") for ln in rl], w, f"{ID} rule@{w}")
    return y + 26 + 18 * (len(rl) - 1)


def render(data, width):
    s = Svg(ID, width, 0, TITLE, DESC)
    if width >= 540:
        _chat(s.g(transform="translate(0 0)"), 340)
        _decision(s.g(transform="translate(380 0)"), 340)
        s.line(360, 0, 360, 300, "grid")
        s.height = _rule(s, 318, 720) + 6
        return s
    h = _chat(s.g(transform="translate(0 0)"), 360)
    s.line(0, h + 16, 360, h + 16, "grid")
    y2 = h + 34
    h2 = _decision(s.g(transform=f"translate(0 {y2})"), 360)
    s.height = _rule(s, y2 + h2 + 18, 360) + 6
    return s


ITEMS = [
    ("Chat model, Gemma 4 E4B:", [
        "In: the prompt with the job state.",
        ("Out: a block of thinking tokens, about 90% of what it generates, then text ending with "
        "“Classification: Product bug”."),
        "The class is parsed from the last lines.",
        ("The probability of the answer token after all that thinking is about 1.0 whatever the answer, so it says "
        "nothing about confidence."),
    ]),
    ("Decision model, elephant-1 (9B):", [
        "In: the same job state, a question and a fixed list of answers.",
        "Out: one probability per answer, for example product bug 0.43, test issue 0.35, infrastructure 0.22.",
        "A second yes/no question, “did the test environment fail?”, gets 0.06 against a threshold of 0.3.",
    ]),
    ("Rule used in the article: an environment answer of at least 0.3 means infrastructure, otherwise whichever "
    "of product bug and test issue has the higher probability. Here 0.06 is below 0.3, so the answer is "
    "product bug."),
]


def table(data):
    return list_html(ITEMS)
