"""Jobs with the class right: the posted comments against the rule, by class and by where the label came from."""
import math

from svgkit import Linear, Svg, legend, table_html, wrap

ID = "confirm"
NARROW = True

BAR = 16  # thickness of one bar of a pair
GAP = 2
PAD = 4  # band around a pair, showing how many jobs the row has
PAIR = 2 * BAR + GAP
CLASSES = [("product", "Product bug"), ("test", "Test issue"), ("infra", "Infrastructure")]
POSTED, RULE = "Posted comments", "Rule"
REVIEWED = "Bug reference from a reviewer"


def _detail(per_class):
    parts = [f"{name.lower()} {per_class[k][0]} of {per_class[k][1]}"
             for k, name in CLASSES if k in per_class and per_class[k][1]]
    return f" ({', '.join(parts)})" if parts else ""


def _blocks(d, layer):
    """Rows per block: (name, jobs, [(cls, series, value, tip)], strong)."""
    o3, src = d["o3"], d["by_label_source"]
    ctl, rule = o3["control"], o3["rule"]
    n = o3["jobs"]

    def pair(name, jobs, a, b, tip_a="", tip_b="", what="right", names=("", ""), tip_name=None):
        tn = tip_name or name
        return (name, jobs, [
            ("c-ctl", names[0], a, f"{tn}: posted comments {what} on {a} of {jobs}{tip_a}"),
            ("c-focus", names[1], b, f"{tn}: rule {what} on {b} of {jobs}{tip_b}"),
        ])

    rows = [pair("All jobs", n, ctl["right"], rule["right"], names=("posted comments", "rule")) + (True,)]
    if layer == "all":
        head = f"The {n} jobs, by class of the label"
        sub = "Every label here was set by a model, most with hindsight."
        rows += [pair(name, ctl["by_class"][k]["jobs"], ctl["by_class"][k]["right"],
                      rule["by_class"][k]["right"]) + (False,) for k, name in CLASSES]
    else:
        head = f"The {n} jobs, by where the label came from"
        sub = (f"Every label here was set by a model. Label given by a pass that used hindsight: "
               f"{src['hindsight_total']}; without hindsight: {src['no_hindsight']['jobs']}.")
        for key, name in [("hindsight_rerun_passed", "Label resting on a passing rerun"),
                          ("hindsight_other", "Other hindsight label"),
                          ("no_hindsight", "Label made without hindsight")]:
            s = src[key]
            rows.append(pair(name, s["jobs"], s["posted_right"], s["rule_right"],
                             _detail(s["posted"]), _detail(s["rule"])) + (False,))
    ps, rr, rv = src["person_set"], d["rerun_passed_with_decision"], d["reviewed_by_person"]
    rp = ps["production_replay"]["right"]
    gold = "Gold jobs: label set by a person"
    # This set has no posted comments; the grey bar is a replay of production and is named at the mark.
    person = (gold, ps["jobs"], [
        ("c-ctl-soft", "replay of production", rp,
         f"{gold}: a replay of production right on {rp} of {ps['jobs']}{_detail(ps['production_replay'])}"),
        ("c-focus", "", ps["rule"]["right"],
         f"{gold}: rule right on {ps['rule']['right']} of {ps['jobs']}{_detail(ps['rule'])}"),
    ], False)
    bugs = f" (all product bugs, {rv['tickets']} bugs in all)"
    reviewed = pair(REVIEWED, rv["jobs"], rv["posted_right"], rv["rule_right"], bugs, bugs) + (False,)
    rerun = pair("Passed on a rerun: said infrastructure", rr["jobs"], rr["posted_infra"], rr["rule_infra"],
                 f"; both said it on {rr['both_infra']}", f"; both said it on {rr['both_infra']}",
                 what="said infrastructure", tip_name="Passed on a rerun") + (False,)
    return [
        ((head, sub), rows),
        (("Three checks that do not depend on those labels",
          f"The {rv['jobs']} are among the {n}; the {ps['jobs']} are not, and the {rr['jobs']} only in part."),
         [person, rerun, reviewed]),
    ]


def _draw(g, d, layer, narrow, width, top):
    blocks = _blocks(d, layer)
    items = [("c-ctl", POSTED), ("c-focus", RULE)]
    y = top + legend(g, items, 0, top, width) + 14

    label_w = 0 if narrow else 196
    x0 = label_w + (0 if narrow else 16)
    count_room = 30
    x = Linear((0, d["o3"]["jobs"]), (x0, width - count_room))

    for bi, ((title, sub), rows) in enumerate(blocks):
        if bi:
            y += 12
            g.line(0, y, width, y, "grid")
            y += 16
        y = g.text(0, y, wrap(title, width, "t-strong"), "t-strong", "start", "top").box[3] + 4
        y = g.text(0, y, wrap(sub, width, "t-muted"), "t-muted", "start", "top").box[3] + 14
        axis_top = y
        for name, jobs, bars, strong in rows:
            jobs_s = f"{jobs} jobs"
            if narrow:
                cls = "t-strong" if strong else "t"
                lab = g.text(0, y, name, cls, "start", "top")
                g.text(lab.box[2] + 6, y, jobs_s, "t-muted", "start", "top")
                y = lab.box[3] + 6
                band_y = y
            else:
                lines = wrap(name, label_w, "t-strong" if strong else "t")
                cls = "t-strong" if strong else "t"
                h = (len(lines) * 13 * 1.3) + 14
                band_y = y
                ty = band_y + (PAIR + 2 * PAD) / 2 - h / 2 + 2
                lab = g.text(0, ty, lines, cls, "start", "top")
                g.text(0, lab.box[3] + 3, jobs_s, "t-muted", "start", "top")
            g.rect(x0, band_y, x(jobs) - x0, PAIR + 2 * PAD, "band", rx=2)
            by = band_y + PAD
            for i, (cls_bar, series, v, tip) in enumerate(bars):
                # 24 px targets that meet in the middle of the gap rather than covering the other bar
                hy = by + BAR + GAP / 2 - 24 if i == 0 else by - GAP / 2
                t = g.tip(tip, hit=(x0, hy, max(x(v) - x0, 24), 24), min_size=0)
                t.bar(x0, by, x(v) - x0, BAR, cls_bar, "right")
                t.text(x(v) + 5, by + BAR / 2, f"{series} {v}" if series else str(v),
                       "t-strong" if cls_bar == "c-focus" else "t", "start", "middle")
                by += BAR + GAP
            y = band_y + PAIR + 2 * PAD + (16 if narrow else 14)
            if strong and len(rows) > 1:
                g.line(x0 - (0 if narrow else 8), y - 7, width, y - 7, "grid")
        g.line(x0, axis_top - 4, x0, y - (16 if narrow else 14) + 4, "axis")
        y -= 16 if narrow else 14
    return y


def render(d, width):
    narrow = width < 540
    o3 = d["o3"]
    ps, rr = d["by_label_source"]["person_set"], d["rerun_passed_with_decision"]
    rv = d["reviewed_by_person"]
    svg = Svg(ID, width, None,
              "Jobs with the class right: posted comments against the rule",
              f"On {o3['jobs']} jobs whose labels a model set, most of them "
              f"with hindsight, the rule had the class right on {o3['rule']['right']} against "
              f"{o3['control']['right']} for the posted comments; on three checks that do not depend on those labels "
              f"the lead is gone: {ps['rule']['right']} for the rule against {ps['production_replay']['right']} for a "
              f"replay of production on {ps['jobs']} gold jobs, {rr['rule_infra']} against {rr['posted_infra']} saying "
              f"infrastructure on the {rr['jobs']} that passed on a rerun, and {rv['rule_right']} against "
              f"{rv['posted_right']} on the {rv['jobs']} with a bug reference from a reviewer.")
    bottom = 0
    for name in ("all", "source"):
        layer = svg.layer(name, on=name == "all")
        bottom = max(bottom, _draw(layer, d, name, narrow, width, 0))
    svg.height = math.ceil(bottom + 4)
    return svg


def table(d):
    o3, src = d["o3"], d["by_label_source"]
    ctl, rule = o3["control"], o3["rule"]
    ps, rr, rv = src["person_set"], d["rerun_passed_with_decision"], d["reviewed_by_person"]

    def of(a, b):
        return f"{a} of {b}"

    rows = [(f"All {o3['jobs']} jobs (label set by a model)", o3["jobs"], ctl["right"], rule["right"])]
    for k, name in CLASSES:
        rows.append((f"All jobs: {name.lower()}", ctl["by_class"][k]["jobs"], ctl["by_class"][k]["right"], rule["by_class"][k]["right"]))
    for key, name in [("hindsight_rerun_passed", "Label resting on a passing rerun"),
                      ("hindsight_other", "Other hindsight label"),
                      ("no_hindsight", "Label made without hindsight")]:
        s = src[key]
        rows.append((name, s["jobs"], s["posted_right"], s["rule_right"]))
        for k, cname in CLASSES:
            if s["posted"][k][1]:
                rows.append((f"{name}: {cname.lower()}", s["posted"][k][1], of(*s["posted"][k]), of(*s["rule"][k])))
    rp = ps["production_replay"]
    rows.append((f"Gold jobs: label set by a person (not among the {o3['jobs']}; among the jobs the threshold "
                 f"was chosen on)", ps["jobs"], f"{rp['right']} (replay of production)", ps["rule"]["right"]))
    for k, cname in CLASSES[:2]:
        rows.append((f"Gold jobs: {cname.lower()}", ps["rule"][k][1], f"{of(*rp[k])} (replay)", of(*ps["rule"][k])))
    rows.append((f"Passed on a rerun (only partly among the {o3['jobs']}): said infrastructure", rr["jobs"], rr["posted_infra"],
                 f"{rr['rule_infra']} (both said it: {rr['both_infra']})"))
    rows.append((f"{REVIEWED} (among the {o3['jobs']}; {rv['tickets']} bugs in all, one on "
                 f"{rv['largest_ticket_jobs']} jobs; all product bugs)", rv["jobs"], rv["posted_right"], rv["rule_right"]))
    caption = (f"Jobs with the class right, posted comments against the rule. The rows from the first down to "
               f"those under 'Label made without hindsight' are the {o3['jobs']} public jobs whose reference label a model set; "
               f"a label counts as hindsight when the labelling pass that gave it set the hindsight flag: "
               f"{src['hindsight_total']} jobs, the rows 'Label resting on a passing rerun' and 'Other hindsight label'; "
               f"with 'Label made without hindsight' ({src['no_hindsight']['jobs']}) they split the {o3['jobs']}. "
               f"The last rows are the three checks that do not depend on those labels: a person or a passing rerun "
               f"decided the class. On the {ps['jobs']} gold jobs the comparison is a replay of production, not the "
               f"posted comments. The {rv['jobs']} jobs with a bug reference from a reviewer are among the "
               f"{o3['jobs']} and take their class from it; the hindsight labeller could read those references, "
               f"so their label is not independent of them, and two bugs say nothing about test issues or "
               f"infrastructure.")
    return table_html(["Set", "Jobs", "Posted comments", "Rule"], rows, caption)
