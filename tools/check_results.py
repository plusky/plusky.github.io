#!/usr/bin/env python3
"""Check the result files under data/.

usage: python3 tools/check_results.py [--self-test] [DATA_DIR]

data/results/<id>.json    one table per experiment: counts, rates, timings
data/jobs/<set>.json      one row per job of a set that is entirely public: the job number and fixed codes
data/fig, data/facts.json no number of a million or more and no run of 7 digits, so no job number

Exits 1 and lists every problem, by place and never by value. check_result(), check_jobs() and
check_numbers() can be imported.
"""

import datetime
import json
import math
import pathlib
import re
import sys

SCOPES = {"o3", "mixed", "internal-aggregate", "bench", "public-record"}
REPOS = {"os-autoinst-scripts", "openQA"}
MILLION = 10**6
JOB_LIMIT = 10**7  # job numbers of the public instance are below this
EXAMPLE = "comment-example.json"  # the one posted comment the article shows, with its job

_CLASS = frozenset({"product", "test", "infra"})
# Column order and the values each column may hold. "job" is the job number, bool is yes or no.
SETS = {
    "confirmation": {
        "job": "job",
        "label": _CLASS,
        "label_source": frozenset({"hindsight", "no-hindsight"}),
        "posted": _CLASS,
        "rule_three": _CLASS,
        "rule_two": _CLASS,
        "shares_test_and_build": bool,
    },
    "gold": {
        "job": "job",
        "label": _CLASS,
        "iq2m": _CLASS | {None},
        "q8": _CLASS | {None},
        "decision_label": _CLASS,
        "decision_rule": _CLASS,
        "doubtful": bool,
        "ticket": range(1, 28),
    },
    "reruns": {
        "job": "job",
        "label": _CLASS | {"unclear"},
        "posted": _CLASS,
        "first_failure": bool,
        "group": frozenset({"passed-later-same-build", "rerun-not-passed", "not-rerun", "not-first-failure"}),
        "restart": frozenset({"yes", "no", "missing"}),
        "bisect": frozenset({"yes", "no-model", "no-same-module-rule", "no-streak-rule", "missing"}),
        "rerun_started_by": frozenset({"unknown", "mass-restart", "retry-setting", "new-run", "hook", None}),
    },
}

_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
_KEY = re.compile(r"[a-z][a-z0-9_]{0,31}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DIGITS = re.compile(r"\d(?:[   .,'_-]?\d){6,}")  # 7 digits, also when grouped
_ISO_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_RESULT_KEYS = {"id", "scope", "title", "compared", "sample", "date", "columns", "rows", "verdict"}
_RESULT_OPTIONAL = {"pr", "note"}
_JOBS_KEYS = {"set", "scope", "date", "jobs", "columns", "rows"}


def _text(value, limit):
    """Why value is not a short single-line text, or None."""
    if not isinstance(value, str) or len(value.splitlines()) != 1 or len(value) > limit:
        return f"must be one line of 1 to {limit} characters"
    if _digits(value):
        return "holds a run of 7 or more digits"
    return None


def _digits(text):
    return bool(_DIGITS.search(_ISO_DATE.sub(lambda m: "" if _is_date(m.group(0)) else m.group(0), text)))


def _number(value):
    """A table cell: below a million, and written with fewer than 7 digits also when it has decimals."""
    return (type(value) in (int, float) and math.isfinite(value) and (value == 0 or 1e-4 <= abs(value) < MILLION)
            and len(re.sub(r"\D", "", repr(value))) < 7)


def _is_date(value):
    try:
        return isinstance(value, str) and bool(_DATE.fullmatch(value)) and bool(datetime.date.fromisoformat(value))
    except ValueError:
        return False


def _no_repeats(pairs):
    """json.loads keeps the last of two equal keys; the first would stay in the file unchecked."""
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("a key is repeated")
    return dict(pairs)


def parse(raw: bytes):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_no_repeats)


def known(parts):
    """Whether a path below data/, as its parts, is a file the checks cover or a note beside them."""
    if len(parts) == 1:
        return bool(re.fullmatch(r"facts[a-z-]*\.json|facts_allow\.txt", parts[0]))
    return (len(parts) == 2 and parts[0] in ("fig", "results", "jobs")
            and (parts[1].endswith(".json") or parts == ("fig", "SCHEMA.md")))


def check_result(stem, d):
    """Problems of one data/results file, as a list of strings."""
    if not isinstance(d, dict):
        return ["not an object"]
    out = []
    if missing := _RESULT_KEYS - set(d):
        out.append(f"missing keys: {sorted(missing)}")
    if extra := set(d) - _RESULT_KEYS - _RESULT_OPTIONAL:
        out.append(f"unknown keys: {sorted(extra)}")
    if out:
        return out
    if d["id"] != stem or not _SLUG.fullmatch(stem) or _digits(stem):
        out.append("id must equal the file name and be a lower-case slug without a run of 7 digits")
    if not isinstance(d["scope"], str) or d["scope"] not in SCOPES:
        out.append(f"scope must be one of {sorted(SCOPES)}")
    if not _is_date(d["date"]):
        out.append("date must be YYYY-MM-DD")
    for key in ("title", "compared", "sample", "verdict", "note"):
        if key in d and (why := _text(d[key], 400)):
            out.append(f"{key} {why}")
    prs = d.get("pr", [])
    for pr in prs if isinstance(prs, list) else [None]:
        if not (isinstance(pr, dict) and set(pr) == {"repo", "number"} and isinstance(pr["repo"], str)
                and pr["repo"] in REPOS and type(pr["number"]) is int and 0 < pr["number"] < 10**5):
            out.append(f"pr is a list of {{repo, number}} with repo one of {sorted(REPOS)}")
    columns = d["columns"]
    if not (isinstance(columns, list) and columns
            and all(isinstance(c, dict) and {"key", "label"} <= set(c) <= {"key", "label", "align"} for c in columns)):
        return out + ["columns must be a list of {key, label, align?}"]
    keys = [c["key"] for c in columns]
    if not all(isinstance(k, str) and _KEY.fullmatch(k) for k in keys):
        return out + ["a column key is not a lower-case name"]
    for c in columns:
        if why := _text(c["label"], 60):
            out.append(f"a column label {why}")
        if "align" in c and c["align"] not in ("right", "center"):
            out.append("align is right or center")
    if len(set(keys)) != len(keys):
        out.append("column keys repeat")
    rows = d["rows"]
    if not (isinstance(rows, list) and rows):
        return out + ["rows must be a non-empty list"]
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != set(keys):
            out.append(f"row {i}: keys differ from the columns")
            continue
        for key, value in row.items():
            if value is None or _number(value):
                continue
            if isinstance(value, str):
                why = _text(value, 120)
            elif isinstance(value, list) and len(value) == 2 and all(type(x) is int and 0 <= x < MILLION for x in value):
                continue
            else:
                why = "is not null, a number below a million, a short text or a pair [a, b]"
            if why:
                out.append(f"row {i}, {key}: {why}")
    return out


def check_jobs(stem, d):
    """Problems of one data/jobs file, as a list of strings."""
    if not isinstance(d, dict) or set(d) != _JOBS_KEYS:
        return [f"keys must be exactly {sorted(_JOBS_KEYS)}"]
    rules = SETS.get(stem)
    if rules is None or d["set"] != stem:
        return [f"set must equal the file name and be one of {sorted(SETS)}"]
    out = []
    if d["scope"] != "o3":
        out.append("scope must be o3")
    if not _is_date(d["date"]):
        out.append("date must be YYYY-MM-DD")
    if d["columns"] != list(rules):
        return out + [f"columns must be {list(rules)}"]
    rows = d["rows"]
    if not isinstance(rows, list) or type(d["jobs"]) is not int or d["jobs"] != len(rows):
        return out + ["jobs must be the number of rows"]
    previous = 0
    for i, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != len(rules):
            out.append(f"row {i}: wrong number of cells")
            continue
        for (name, rule), value in zip(rules.items(), row):
            if rule == "job":
                ok = type(value) is int and previous < value < JOB_LIMIT
                previous = value if type(value) is int else previous
            elif rule is bool:
                ok = type(value) is bool
            elif isinstance(rule, range):
                ok = type(value) is int and value in rule
            else:
                ok = (value is None or type(value) is str) and value in rule
            if not ok:
                out.append(f"row {i}, {name}: not allowed (job numbers ascend and stay below {JOB_LIMIT})"
                           if rule == "job" else f"row {i}, {name}: not one of the allowed values")
    return out


def check_numbers(obj, where="$"):
    """Places in obj that hold a number of a million or more, or a key or text with a run of 7 digits."""
    if isinstance(obj, dict):
        named = [f"{where}: a key with a run of 7 or more digits" for k in obj if _digits(k)]
        return named + [p for k, v in obj.items() for p in check_numbers(v, f"{where}.{k}")]
    if isinstance(obj, list):
        return [p for i, v in enumerate(obj) for p in check_numbers(v, f"{where}[{i}]")]
    if type(obj) in (int, float) and not (math.isfinite(obj) and abs(obj) < MILLION):
        return [f"{where}: a number of a million or more"]
    if isinstance(obj, str) and _digits(obj):
        return [f"{where}: a run of 7 or more digits"]
    return []


def run(data_dir):
    root = pathlib.Path(data_dir)
    problems = []
    for path in sorted(p for p in root.rglob("*") if not p.is_dir()):
        parts = path.relative_to(root).parts
        if not known(parts):
            problems.append((path, "not a file the checks know; Hugo would read it as data all the same"))
            continue
        if any(_digits(part) for part in parts):
            problems.append((path, "the file name holds a run of 7 or more digits"))
        if path.suffix != ".json":
            continue
        try:
            obj = parse(path.read_bytes())
        except ValueError:
            problems.append((path, "not UTF-8 JSON, or a key is repeated"))
            continue
        if parts == ("fig", EXAMPLE) and isinstance(obj, dict):
            # The example names its job; its text is the posted comment and is left to the leak check.
            if not (type(obj.get("job")) is int and 0 < obj["job"] < JOB_LIMIT):
                problems.append((path, "job must be a job number of the public instance"))
            obj = {k: v for k, v in obj.items() if k not in ("job", "text")}
        check = {"results": check_result, "jobs": check_jobs}.get(parts[0])
        problems += [(path, p) for p in (check(path.stem, obj) if check else check_numbers(obj))]
    for path, problem in problems:
        print(f"{path}: {problem}")
    return 1 if problems else 0


def self_test():
    def result(**change):
        d = {"id": "sample", "scope": "bench", "title": "Sample", "compared": "A against B", "sample": "17 jobs",
             "date": "2026-11-08", "pr": [{"repo": "openQA", "number": 8070}], "verdict": "kept",
             "columns": [{"key": "setting", "label": "Setting"}, {"key": "right", "label": "Right", "align": "right"}],
             "rows": [{"setting": "a", "right": [13, 17]}, {"setting": "b", "right": 0.5}, {"setting": "c", "right": None}]}
        return {**d, **change}

    def jobs(rows=None, **change):
        public = 6 * MILLION
        rows = rows or [[public + 1, "infra", "hindsight", "product", "infra", "infra", False],
                        [public + 2, "test", "no-hindsight", "test", "test", "product", True]]
        d = {"set": "confirmation", "scope": "o3", "date": "2026-11-12", "jobs": len(rows),
             "columns": list(SETS["confirmation"]), "rows": rows}
        return {**d, **change}

    public, internal = 6 * MILLION, 24 * MILLION
    row = [public + 1, "infra", "hindsight", "product", "infra", "infra", False]
    cases = [
        ("result", result(), False),
        ("result: unknown key", result(log="x"), True),
        ("result: id differs from file", result(id="other"), True),
        ("result: unknown scope", result(scope="private"), True),
        ("result: text over two lines", result(verdict="a\nb"), True),
        ("result: digits in a cell", result(rows=[{"setting": "job " + str(public), "right": 1}]), True),
        ("result: large number", result(rows=[{"setting": "a", "right": public}]), True),
        ("result: yes/no cell", result(rows=[{"setting": "a", "right": True}]), True),
        ("result: row keys", result(rows=[{"setting": "a"}]), True),
        ("result: unknown repo", result(pr=[{"repo": "other", "number": 1}]), True),
        ("result: repo that is a list", result(pr=[{"repo": [], "number": 1}]), True),
        ("result: scope that is a list", result(scope=["bench"]), True),
        ("result: digits behind a decimal point", result(rows=[{"setting": "a", "right": 6000.001}]), True),
        ("result: digits as a false date", result(verdict="see 6000-00-01"), True),
        ("result: a real date", result(verdict="read on 2026-11-14"), False),
        ("jobs", jobs(), False),
        ("jobs: internal number", jobs([[internal, *row[1:]]]), True),
        ("jobs: number as text", jobs([[str(public), *row[1:]]]), True),
        ("jobs: not ascending", jobs([row, row]), True),
        ("jobs: unknown code", jobs([[*row[:3], "some text", *row[4:]]]), True),
        ("jobs: extra cell", jobs([[*row, "x"]]), True),
        ("jobs: fraction", jobs([[*row[:6], 0.5]]), True),
        ("jobs: wrong count", jobs(jobs=3), True),
        ("jobs: scope", jobs(scope="mixed"), True),
        ("jobs: extra key", jobs(note="x"), True),
        ("jobs: other columns", jobs(columns=["job", "label"]), True),
    ]
    failed = 0
    for label, obj, want in cases:
        check, stem = (check_result, "sample") if label.startswith("result") else (check_jobs, "confirmation")
        if bool(check(stem, obj)) != want:
            failed += 1
            print(f"FAIL {label}: expected {'problems' if want else 'none'}")
    grouped = f"{str(public)[:1]},{str(public)[1:4]},{str(public)[4:]}"
    numbers = [({"a": [MILLION - 1, 0.5, "12 of 17", "read on 2026-11-14"]}, False), ({"a": [public]}, True),
               ({"a": {"b": str(public)}}, True), ({"a": grouped}, True), ({str(public): 1}, True)]
    for obj, want in numbers:
        if bool(check_numbers(obj)) != want:
            failed += 1
            print(f"FAIL numbers {sorted(obj)}: expected {'problems' if want else 'none'}")
    try:
        parse(b'{"a": 1, "a": 2}')
        repeated_refused = False
    except ValueError:
        repeated_refused = True
    more = [
        ("a repeated key is refused", repeated_refused),
        ("plain JSON loads", parse(b'{"a": 1, "b": 2}') == {"a": 1, "b": 2}),
        ("a carriage return makes a second line", _text("a\rb", 400) is not None),
        ("an impossible date", not _is_date("9999-99-99")),
        ("known files", all(map(known, [("facts.json",), ("facts-data.json",), ("facts_allow.txt",),
                                        ("fig", "x.json"), ("fig", "SCHEMA.md"), ("jobs", "gold.json")]))),
        ("unknown files", not any(map(known, [("jobs.json",), ("other.json",), ("fig", "sub", "x.json"),
                                              ("fig", "x.yaml"), ("results", "x.toml"), ("new", "x.json")]))),
    ]
    for label, ok in more:
        if not ok:
            failed += 1
            print(f"FAIL {label}")
    total = len(cases) + len(numbers) + len(more)
    print(f"check_results self-test: {total - failed}/{total} passed")
    return 1 if failed else 0


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    if len(argv) > 1 or any(a.startswith("-") for a in argv):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return run(argv[0] if argv else "data")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
