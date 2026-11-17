"""Who reads the comments: the reviewed share of jobs with an LLM comment, and those jobs per job group."""
import math

from svgkit import Svg, legend, measure, table_html, text_box, wrap
from svgkit.text import DESCENT

ID = "readers"
NARROW = True
POST = "failure-class-data"

BAR = 20
METER = 14
GAP = 10  # between ranked bars


def _pct(v):
    s = f"{v * 100:.1f}".rstrip("0").rstrip(".")
    return f"{s}%"


def _end_label(g):
    return f"{g['jobs_with_llm_comment']:,} · {g['reviewed_jobs']:,} reviewed"


def _tip(g):
    return (f"{g['group']}: {g['jobs_with_llm_comment']:,} jobs with an LLM comment, "
            f"{g['reviewed_jobs']:,} reviewed by a person")


def _headline(svg, y, width, big, line):
    """A big share and its sentence beside it, wrapped to the room left; returns the bottom."""
    bw = measure(big, "t-big")
    big_box = svg.text(0, y, big, "t-big", "start", "top").box
    # The sentence shares the big number's baseline.
    base = big_box[3] - DESCENT * 22
    lines = wrap(line, width - bw - 12, "t-strong")
    box = svg.text(bw + 12, base, lines, "t-strong", "start", "alphabetic").box
    return max(box[3], big_box[3])


def render(d, width):
    narrow = width < 540
    n, rev = d["jobs_with_llm_comment"], d["reviewed_jobs"]
    dev_pct = f"{round(d['development_share'] * 100)}%"
    svg = Svg(ID, width, None,
              f"Jobs with an LLM comment in {d['window_days']} days, reviewed share and jobs per job group",
              f"In {d['window_days']} days the four job groups shown had {n:,} jobs with an LLM comment; "
              f"{rev:,} ({_pct(d['reviewed_share'])}) were later reviewed by a person, and "
              f"{d['development_jobs']:,} ({dev_pct}) were in the Development group, which is almost never "
              f"reviewed ({d['development_reviewed_jobs']:,} of {d['development_jobs']:,}).")

    # Part one: the meter of reviewed against all jobs with a comment.
    y = _headline(svg, 0, width,
                  _pct(d["reviewed_share"]),
                  f"of {n:,} jobs with an LLM comment in the four groups shown, over "
                  f"{d['window_days']} days, were later reviewed by a person") + 12
    w_rev = width * rev / n
    rest = n - rev
    # The two hit areas tile the meter at the gap so neither overlaps the other or leaves the viewBox.
    hy, hh = y - (24 - METER) / 2, 24
    svg.tip(f"Reviewed by a person: {rev:,} of {n:,} jobs ({_pct(d['reviewed_share'])})",
            hit=(0, hy, w_rev + 1, hh), min_size=0
            ).bar(0, y, w_rev, METER, "c-ctl", "right")
    svg.tip(f"Not reviewed: {rest:,} of {n:,} jobs ({_pct(1 - d['reviewed_share'])})",
            hit=(w_rev + 1, hy, width - w_rev - 1, hh), min_size=0
            ).bar(w_rev + 2, y, width - w_rev - 2, METER, "c-ctl-soft", "right")
    y += METER + 6
    svg.text(0, y, f"{rev:,} reviewed", "t-muted", "start", "top")
    svg.text(width, y, f"{rest:,} not reviewed", "t-muted", "end", "top")
    y = text_box(0, y, "0", "t-muted", "start", "top")[3] + (32 if narrow else 36)

    # Part two: jobs with a comment per job group, ranked.
    y = _headline(svg, y, width, dev_pct,
                  f"were in the Development group, which is almost never reviewed "
                  f"({d['development_reviewed_jobs']:,} of {d['development_jobs']:,})") + 12
    # The helper insets its swatch by 3; shift it so the swatch meets the shared left edge.
    y += legend(svg, [("c-focus", "Development group"), ("c-ctl", "Groups people review")], -3, y, width + 3) + 10

    groups = sorted(d["groups"], key=lambda g: -g["jobs_with_llm_comment"])
    top = max(g["jobs_with_llm_comment"] for g in groups)
    label_room = max(measure(_end_label(g)) for g in groups) + 8
    if narrow:
        x0 = 0
    else:
        x0 = max(measure(g["group"]) for g in groups) + 12
    span = width - x0 - label_room
    for g in groups:
        cls = "c-focus" if g["development"] else "c-ctl"
        if narrow:
            y = svg.text(0, y, g["group"], "t", "start", "top").box[3] + 5
        w = span * g["jobs_with_llm_comment"] / top
        svg.tip(_tip(g), hit=(x0, y, max(w, 24), BAR)).bar(x0, y, w, BAR, cls, "right")
        if not narrow:
            svg.text(x0 - 8, y + BAR / 2, g["group"], "t", "end", "middle")
        svg.text(x0 + w + 6, y + BAR / 2, _end_label(g), "t", "start", "middle")
        y += BAR + (14 if narrow else GAP)

    svg.height = math.ceil(y - GAP + 4)
    return svg


def table(d):
    groups = sorted(d["groups"], key=lambda g: -g["jobs_with_llm_comment"])
    rows = [(g["group"], f"{g['jobs_with_llm_comment']:,}", f"{g['reviewed_jobs']:,}",
             "yes" if g["development"] else "no") for g in groups]
    n, rev = d["jobs_with_llm_comment"], d["reviewed_jobs"]
    rows.append(("All four groups", f"{n:,}", f"{rev:,}", ""))
    s7 = d["seven_groups"]
    rest = n - rev
    caption = (f"Jobs with an LLM comment in the four groups counted first, over {d['window_days']} days "
               f"({d['jobs_per_day']:,} a day): {rev:,} of {n:,} ({_pct(d['reviewed_share'])}) later reviewed "
               f"by a person, {rest:,} ({_pct(1 - d['reviewed_share'])}) not; {d['development_jobs']:,} "
               f"({round(d['development_share'] * 100)}%) in the Development group. With the three groups read "
               f"later, all seven groups had {s7['jobs_with_llm_comment']:,} such jobs, {s7['reviewed_jobs']:,} "
               f"({_pct(s7['reviewed_share'])}) reviewed, {round(s7['development_share'] * 100)}% in Development")
    return table_html(["Job group", "Jobs with an LLM comment", "Reviewed by a person", "Development group"],
                      rows, caption)
