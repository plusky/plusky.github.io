"""What became of the commented first failures, and how many of the passing reruns each retry rule would catch."""
import math

from svgkit import Linear, Svg, axis_x, flow, legend, measure, nice_ticks, table_html, text_box, wrap

ID = "reruns"
NARROW = True

GROUPS = [  # data key, name, colour
    ("passed_later_same_build", "Passed on a rerun", "c-focus"),
    ("rerun_not_passed", "Rerun, failed again", "c-ctl"),
    ("not_rerun", "Never rerun", "c-ctl-soft"),
]
RULES = ["The hook as it was (its investigation retries)", "Restart: YES", "Restart: YES or BISECT: YES", "Every first failure"]
BAR = 14
LABEL_BAND = 26


def _flow_parts(d, narrow=False):
    names = {"all": "Commented jobs", "first": "First failures", "rest": "Not a first failure"}
    values = {"all": d["silver_jobs"], "first": d["first_failures"], "rest": d["not_first_failures"]}
    for key, name, _ in GROUPS:
        names[key], values[key] = name, d["groups"][key]["jobs"]
    label = {k: f"{names[k]} {values[k]}" for k in names}
    if narrow:
        # Keeps the bottom row of labels to two lines in the thin column.
        label["rerun_not_passed"] = f"Failed again {values['rerun_not_passed']}"
    columns = [
        [{"id": "all", "label": label["all"], "cls": "c-ctl"}],
        [{"id": "first", "label": label["first"], "cls": "c-ctl"},
         {"id": "rest", "label": label["rest"], "cls": "c-ctl-soft"}],
        [{"id": key, "label": label[key], "cls": cls} for key, _, cls in GROUPS],
    ]
    links = [{"source": "all", "target": "first", "value": values["first"]},
             {"source": "all", "target": "rest", "value": values["rest"]}]
    links += [{"source": "first", "target": key, "value": values[key]} for key, _, _ in GROUPS]
    return columns, links, names, label


def _short_tips(g, names, label):
    """The flow labels carry their counts; the tips name the nodes and give the count once."""
    for el in g.walk():
        tip = el.attrs.get("data-tip")
        if tip is None:
            continue
        for k in sorted(label, key=lambda k: -len(label[k])):
            tip = tip.replace(label[k], names[k])
        el.attrs["data-tip"] = tip
        el.children[0].content = tip


def _relabel(g, nodes, label, narrow):
    """Middle-stage labels go above their nodes on clear surface, without a chip; the focus outcome is set strong."""
    middle = ["first", "rest"] if narrow else ["first"]
    for el in list(g.children):
        if el.tag == "rect" and el.attrs.get("class") == "bg":
            g.children.remove(el)
        elif el.tag != "text":
            continue
        elif el.content in [label[k] for k in middle]:
            g.children.remove(el)
        elif (el.content or " ".join(c.content for c in el.children)) == label["passed_later_same_build"]:
            el.attrs["class"] = "t-strong"
    if narrow:
        # The incoming ribbons stop short of the middle row, leaving a clear band for its labels.
        x0, top = nodes["first"][0], nodes["first"][1]
        x1 = nodes["rest"][0] + nodes["rest"][2]
        g.children.insert(1, g.rect(x0, top - LABEL_BAND, x1 - x0, LABEL_BAND, "bg"))
        g.children.pop()
    for k in middle:
        bx, by = nodes[k][:2]
        g.text(bx, by - 6, label[k], "t", "start", "bottom")


def _rules(d):
    return [(name, r["retries"], r["covers"]) for name, r in zip(RULES, d["retry_rules"])]


def render(d, width):
    narrow = width < 540
    passed = d["groups"]["passed_later_same_build"]["jobs"]
    rules = _rules(d)
    svg = Svg(ID, width, None,
              "Commented jobs by what a rerun did, and the jobs each retry rule retries",
              f"Of {d['silver_jobs']} commented jobs, {passed} passed when simply run again in the same build; "
              f"the hook's investigation retries covered {rules[0][2]} of them, "
              f"while the comment said Restart: YES on {rules[1][2]}.")
    columns, links, names, label = _flow_parts(d, narrow)

    y = 0
    svg.text(0, y, f"What became of the {d['silver_jobs']} commented jobs", "t-strong", "start", "top")
    y += 13 + (12 if narrow else 30)
    fg = svg.g()
    if narrow:
        # The first row is labelled above its node.
        top = y + 13 + 6
        nodes = flow(fg, columns, links, 0, top, width, 270, direction="tb")
    else:
        lw = 120
        nodes = flow(fg, columns, links, lw + 6, y, width - 2 * (lw + 6), 200, label_width=lw)
    _short_tips(fg, names, label)
    _relabel(fg, nodes, label, narrow)
    bottom = max([b[1] + b[3] for b in nodes.values()] + [el.box[3] for el in fg.walk() if el.box])

    y = bottom + 40
    head = wrap(f"What each retry rule retries among the {d['silver_jobs']} commented jobs, "
                f"and how many of the {passed} it covers", width, "t-strong")
    y = svg.text(0, y, head, "t-strong", "start", "top").box[3] + 10
    y += legend(svg, [("c-ctl", "jobs it retries"), ("c-focus", f"of the {passed} it covers")], 0, y, width)
    y += 10

    num_w = measure("188") + 8
    if narrow:
        x0, x1 = 0, width - num_w
    else:
        x0, x1 = 210, width - num_w
    ticks = nice_ticks(0, max(r for _, r, _ in rules), 4)
    x = Linear((0, ticks[-1]), (x0, x1))
    plot_top = y
    rows = []
    for name, retries, covers in rules:
        if narrow:
            name_y = y + 4
            y = text_box(0, name_y, name, "t", "start", "top")[3] + 6
            rows.append((name, retries, covers, y, (0, name_y)))
            y += 2 * BAR + 2 + 14
        else:
            rows.append((name, retries, covers, y + 8, None))
            y += 2 * BAR + 2 + 24
    base = y - 6
    end = axis_x(svg, x, ticks, base, grid_to=plot_top, title="jobs")
    if narrow:
        # The 0 tick sits on the left edge; start it there instead of centring it outside the viewBox.
        for el in svg.walk():
            if el.tag == "text" and el.content == "0" and el.attrs.get("x") == x0:
                el.attrs.pop("text-anchor", None)
                w = el.box[2] - el.box[0]
                el.box = (x0, el.box[1], x0 + w, el.box[3])
    bars = svg.g()
    for i, (name, retries, covers, by, at) in enumerate(rows):
        # The hook against Restart: YES is the comparison the text makes; the wider rules are context.
        key = "t-strong" if i < 2 else "t"
        if narrow:
            svg.text(at[0], at[1], name, key, "start", "top")
        else:
            lines = wrap(name, x0 - 14, key)
            svg.text(x0 - 10, by + BAR + 1 - (len(lines) - 1) * 1.3 * 13 / 2, lines, key, "end", "middle")
        verb = "retried" if i == 0 else "would retry"
        tip = f"{name}: {verb} {retries} jobs, {covers} of them among the {passed} that passed on a rerun"
        g = bars.tip(tip, hit=(x0, by, max(x(retries) - x0, 24), 2 * BAR + 2))
        g.bar(x0, by, x(retries) - x0, BAR, "c-ctl", "right")
        g.bar(x0, by + BAR + 2, x(covers) - x0, BAR, "c-focus", "right")
        g.text(x(retries) + 6, by + BAR / 2, str(retries), "t", "start", "middle")
        g.text(x(covers) + 6, by + BAR + 2 + BAR / 2, str(covers), key, "start", "middle")
    svg.height = math.ceil(end + 4)
    return svg


def table(d):
    passed = d["groups"]["passed_later_same_build"]["jobs"]
    first = d["first_failures"]
    flow_rows = [("Commented jobs", d["silver_jobs"]), ("First failures", first),
                 ("Not a first failure", d["not_first_failures"])]
    flow_rows += [(f"First failures: {name.lower()}", d["groups"][key]["jobs"]) for key, name, _ in GROUPS]
    out = table_html(["Jobs", "Count"], flow_rows,
                     f"What became of {d['silver_jobs']} commented jobs: {passed} of {first} first failures "
                     "passed when run again in the same build")
    out += table_html(["Retry rule", "Jobs it retries", f"Of the {passed} that passed on a rerun, it covers"],
                      _rules(d), f"Jobs each retry rule retries among the {d['silver_jobs']} commented jobs (the hook's are "
                      "actual retries, the others what the rule would have retried) and how many of the "
                      f"{passed} passing reruns each covers")
    return out
