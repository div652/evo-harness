import json, re, sys
from pathlib import Path

BASE = Path("/home/agarwaldi/AHE_Harvey_cao/harvey-ahe-project/analysis/stages-train")
tasks = sys.argv[1:] or sorted(f.stem for f in (BASE / "annotations").glob("*.json"))
idx = {(r["task"], r["trial"]): r for r in json.load(open(BASE / "runs_index.json"))}

# taxonomy sections
tax = (BASE / "taxonomy.md").read_text()
def section(title):
    m = re.search(r"^## " + re.escape(title) + r".*?\n(.*?)(?=^## |\Z)", tax, re.S | re.M)
    rows = []
    for line in m.group(1).splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            rows.append(cells[0])
    return set(rows[1:])
STAGES, TAGS, HS, KINDS = section("Stages"), section("Tags"), section("Hindsight values"), section("Error kinds")
RUN_ENDED = {t for t in TAGS if t.startswith("run ended: ")}  # e.g. context overflow, text reply without finish
print(len(STAGES), "stages", len(TAGS), "tags", len(HS), "hindsight", len(KINDS), "kinds")

HINDSIGHT_WORDS = re.compile(r"\b(target|decoy|correct|wrong|rubric|criteri\w*|needed matter)\b", re.I)
MATTER = re.compile(r"\b\d{4}-\d{5}\b")
TASK_WORDS = re.compile(r"\b(antitrust|second request|clearance|HSR|FTC|DIP|debtor|bankrupt\w*|reorganization|plan of|LPAC|LPA|advisory committee|waterfall|deal-by-deal|American|fund|IRB|informed consent|clinical|Solara|Crestline|Penterra|Thornwick|Solstice|Ridgeline|Pellegrino)\b", re.I)
errs = []
def bad(msg): errs.append(msg)

for task in tasks:
    J = json.load(open(BASE / f"annotations/{task}.json"))
    md = (BASE / f"annotations/{task}.md").read_text()
    md_runs = re.split(r"^## T(\d)", md, flags=re.M)
    md_by = {int(md_runs[i]): md_runs[i + 1] for i in range(1, len(md_runs), 2)}
    for gen in ("divergence",):
        if MATTER.search(J[gen]) or TASK_WORDS.search(J[gen]): bad(f"{task} {gen} has task content: {J[gen]}")
    for r in J["runs"]:
        k = r["trial"]; tag = f"{task}_T{k}"
        ix = idx[(task, k)]
        for f in ("all_pass", "n_passed", "n_criteria"):
            if r[f] != ix[f]: bad(f"{tag} {f} mismatch")
        # events from log
        calls, allev = [], []
        for line in open(BASE / f"logs/{task}_T{k}.txt"):
            m = re.match(r"^\[(\d+)\] (CALL (\w+))?", line)
            if m:
                allev.append(int(m.group(1)))
                if m.group(2): calls.append((int(m.group(1)), m.group(3)))
        st = r["stages"]
        if st[0]["start"] != min(n for n, _ in calls): bad(f"{tag} first stage does not start at first call")
        for a, b in zip(st, st[1:]):
            if b["start"] != a["end"] + 1: bad(f"{tag} gap/overlap between {a['start']}-{a['end']} and {b['start']}")
        for s in st:
            if s["start"] > s["end"]: bad(f"{tag} empty stage {s}")
            if not any(s["start"] <= n <= s["end"] for n, _ in calls): bad(f"{tag} stage without a call {s['stage']} {s['start']}")
        for n, c in calls:
            hits = [s for s in st if s["start"] <= n <= s["end"]]
            if len(hits) != 1: bad(f"{tag} call [{n}] {c} covered {len(hits)} times")
        fin = [n for n, c in calls if c == "finish"]
        last = st[-1]
        if fin:
            if not (last["start"] <= fin[-1] <= last["end"]) or last["stage"] != "Finish the run" or last["end"] != fin[-1]:
                bad(f"{tag} does not end with finish")
        else:
            if not any(t in RUN_ENDED for t in last["tags"]): bad(f"{tag} no finish and no run-ended tag from {sorted(RUN_ENDED)}")
            if last["end"] != max(allev): bad(f"{tag} last stage does not reach last event")
        for s in st[:-1]:
            if any(t in RUN_ENDED for t in s["tags"]): bad(f"{tag} run-ended tag on a stage that is not last")
        # vocabulary + wording
        for s in st:
            if s["stage"] not in STAGES: bad(f"{tag} unknown stage {s['stage']}")
            for t in s["tags"]:
                if t not in TAGS: bad(f"{tag} unknown tag {t}")
            if s["hindsight"] not in HS: bad(f"{tag} unknown hindsight {s['hindsight']}")
            for txt in [s["stage"], s["note"]] + s["tags"]:
                if HINDSIGHT_WORDS.search(txt): bad(f"{tag} hindsight word in: {txt}")
                if MATTER.search(txt) or TASK_WORDS.search(txt): bad(f"{tag} task content in: {txt}")
        # sequence
        seq = []
        for s in st:
            if not seq or seq[-1] != s["stage"]: seq.append(s["stage"])
        if r["sequence"] != " → ".join(seq): bad(f"{tag} sequence mismatch")
        # errors
        fe = r["first_error"]
        if r["all_pass"]:
            if fe is not None or r["other_errors"] or r["failure_point"]: bad(f"{tag} passing run has error fields")
        else:
            if not fe: bad(f"{tag} failing run lacks first_error")
        for e in ([fe] if fe else []) + r["other_errors"]:
            s = st[e["stage_no"] - 1]
            if (e["stage"], e["start"], e["end"]) != (s["stage"], s["start"], s["end"]): bad(f"{tag} error stage mismatch {e}")
            if e["kind"] not in KINDS: bad(f"{tag} unknown kind {e['kind']}")
            if e["events"]:
                m = re.fullmatch(r"\[(\d+)\]-\[(\d+)\]", e["events"])
                if not m or not (s["start"] <= int(m.group(1)) <= int(m.group(2)) <= s["end"]): bad(f"{tag} bad events {e['events']}")
            for txt in (e["why"],):
                if MATTER.search(txt): bad(f"{tag} matter number in why")
        if r["failure_point"] and (MATTER.search(r["failure_point"]) or TASK_WORDS.search(r["failure_point"])): bad(f"{tag} task content in failure_point")
        # md
        body = md_by.get(k)
        if body is None: bad(f"{tag} missing in md"); continue
        rows = [l for l in body.splitlines() if re.match(r"^\| \d+ \|", l)]
        if len(rows) != len(st): bad(f"{tag} md rows {len(rows)} != stages {len(st)}")
        for i, (l, s) in enumerate(zip(rows, st), 1):
            if f"| {s['stage']} | [{s['start']}]-[{s['end']}] |" not in l: bad(f"{tag} md row {i} mismatch")
            want_fe = fe is not None and fe["stage_no"] == i
            want_le = any(e["stage_no"] == i for e in r["other_errors"])
            if ("⛔ first error" in l) != want_fe: bad(f"{tag} md ⛔ marker row {i}")
            if ("⚠ later error" in l) != want_le: bad(f"{tag} md ⚠ marker row {i}")
        fl = [l for l in body.splitlines() if l.startswith("**First error:**")]
        if len(fl) != 1: bad(f"{tag} md first-error lines: {len(fl)}")
        elif fe:
            exp = f"**First error:** stage {fe['stage_no']} ({fe['stage']}) [{fe['start']}]-[{fe['end']}], {fe['kind']}: {fe['why']}"
            if fl[0] != exp: bad(f"{tag} md First error line mismatch")
        elif "none" not in fl[0]: bad(f"{tag} md First error should be none")
        if f"**Sequence:** {r['sequence']}" not in body: bad(f"{tag} md sequence missing")
        ll = [l for l in body.splitlines() if l.startswith("**Later error:**")]
        exp_ll = [f"**Later error:** stage {e['stage_no']} ({e['stage']}) [{e['start']}]-[{e['end']}], {e['kind']}: {e['why']}" for e in r["other_errors"]]
        if ll != exp_ll: bad(f"{tag} md Later error lines mismatch")
    if "## Task context" not in md: bad(f"{task} md lacks Task context")
    if "NEW:" in md or "NEW:" in json.dumps(J): bad(f"{task} still contains a NEW: name")

nfail = sum(1 for t in tasks for r in json.load(open(BASE / f"annotations/{t}.json"))["runs"] if not r["all_pass"])
nfe = sum(1 for t in tasks for r in json.load(open(BASE / f"annotations/{t}.json"))["runs"] if not r["all_pass"] and r["first_error"])
print(f"{len(tasks)} tasks, {nfail} failing runs, {nfe} with first_error")
print("\n".join(errs) if errs else "ALL CHECKS PASSED")
