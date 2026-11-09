"""Parse every end-of-stage review in the stage harness's training runs.

One row per review (`stage_end` result) with: the review's parts (reviewer
verdict, flags, concerns, recommendation, unopened-matter list, new-stage
suggestion), the agent's own claim, what the agent did next (reopen the same
stage, start another, finish), and whether the matters the reviewer named
were opened afterwards. Run-level fields come from the training annotations
(first error, reviewer outcome) and the judge's scores.

Training runs only (campaigns 30 and 31: stage harness r2 and r3).

Usage (from harvey-ahe-project/): python3 analysis/feedback-uptake/build_reviews.py
Writes analysis/feedback-uptake/data/reviews.jsonl and runs.jsonl.
"""

from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path

ROUNDS = [
    ("r2", "analysis/stages-train-c30", "campaign-artifacts/harvey-lab-campaign-30-cao-stage-r2-train80"),
    ("r3", "analysis/stages-train-c31", "campaign-artifacts/harvey-lab-campaign-31-cao-stage-r3-train80"),
]
LAB_TASKS = Path(os.path.expanduser("~/harvey-labs/tasks/firm-knowledge/tasks"))
OUT = Path("analysis/feedback-uptake/data")
MATTER = re.compile(r"\b\d{4}-\d{5}\b")
OPENING_TOOLS = {"read", "glob", "bash"}  # the harness's own definition of "opened or listed"
WORD = re.compile(r"[a-z][a-z\-]{3,}")
STOP = set("""this that with from have were they them then than into only also each your will what when which their there
these those about after before should would could other more most such does done must make made over under while where
stage agent matter matters file files document documents check confirm search list""".split())


def result_text(content) -> str:
    raw = content if isinstance(content, str) else json.dumps(content)
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            for key in ("result", "error"):
                if isinstance(value.get(key), str):
                    return value[key]
    except Exception:
        pass
    return raw


def parse_review(text: str) -> dict:
    row: dict = {"review_chars": len(text)}
    m = re.match(r"\[Stage review: (.*), attempt (\d+)\]", text)
    row["label"], row["attempt"] = (m.group(1), int(m.group(2))) if m else (None, None)
    m = re.search(r"You reported: goal reached = (\w+)", text)
    row["agent_claim"] = m.group(1) if m else None
    m = re.search(r"Independent reviewer: goal reached = (\w+)", text)
    row["verdict"] = m.group(1) if m else ("unavailable" if "unavailable" in text else None)

    def line(prefix: str) -> str:
        m = re.search(rf"^{re.escape(prefix)}(.*)$", text, re.M)
        return m.group(1).strip() if m else ""

    flags = line("Reviewer flags:")
    row["flags"] = [f.strip() for f in flags.split("; ") if f.strip()] if flags else []
    row["concerns"] = line("Reviewer concerns:")
    row["recommendation"] = line("Reviewer recommendation:")
    row["new_stage_suggested"] = "Reviewer suggests a new step:" in text
    row["stuck_note"] = "This stage has been opened" in text
    row["label_note"] = text.startswith("[Stage review") and "Label: these calls looked like" in text
    unopened = line("Matters that appeared in your search results but none of whose documents you have opened or listed:")
    row["unopened"] = MATTER.findall(unopened)
    row["unopened_truncated"] = unopened.endswith("….") or unopened.endswith("…")
    common = text.split("Common failures at this stage in past runs:", 1)
    row["common_failures_chars"] = len(common[1]) if len(common) > 1 else 0
    return row


def load_scores(attempt: Path) -> dict | None:
    """The latest grading's judge scores (grading/grading-N/scores_judge-1.json)."""
    paths = sorted(attempt.glob("grading/grading-*/scores_judge-1.json"), key=lambda p: int(p.parent.name.split("-")[1]))
    return json.load(open(paths[-1])) if paths else None


def words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def trace_steps(trace: Path) -> list[dict]:
    """Ordered tool calls with their results: {idx, name, input, result}."""
    calls: dict[str, dict] = {}
    steps: list[dict] = []
    for line_ in open(trace):
        e = json.loads(line_)
        if e.get("event_type") != "message" or isinstance(e.get("message"), str):
            continue
        for c in e["message"].get("content", []):
            if c.get("type") == "tool_use":
                step = {"idx": e["index"], "name": c["name"], "input": c["input"], "result": None, "result_idx": None}
                calls[c["id"]] = step
                steps.append(step)
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                step = calls[c["tool_use_id"]]
                step["result"] = result_text(c.get("content"))
                step["result_idx"] = e["index"]
    return steps


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reviews, runs = [], []
    for rnd, catalog, campaign in ROUNDS:
        units = {}
        for res in glob.glob(f"{campaign}/evaluations/C0-train/units/*/attempt-*/result.json"):
            r = json.load(open(res))
            key = (r["task_id"].split("/")[-1], r["trial"])
            # keep the latest attempt
            if key not in units or res > units[key]:
                units[key] = res
        for ann_path in sorted(glob.glob(f"{catalog}/annotations/*.json")):
            ann = json.load(open(ann_path))
            task = ann["task"]
            spec = json.load(open(LAB_TASKS / task / "task.json"))
            needed = sorted({m for c in spec["criteria"] for m in MATTER.findall(c["title"])})
            for run in ann["runs"]:
                res = units.get((task, run["trial"]))
                if res is None:
                    continue
                attempt = Path(res).parent
                scores = load_scores(attempt)
                failed_matters = sorted({m for c in (scores or {}).get("criteria_results", []) if c["verdict"] != "pass" for m in MATTER.findall(c.get("title", ""))})
                fe = run.get("first_error") or {}
                note = (fe.get("critic_note") or "").lower()
                run_row = {
                    "round": rnd, "task": task, "trial": run["trial"], "all_pass": run["all_pass"],
                    "attempt_dir": str(attempt), "needed": needed, "failed_matters": failed_matters,
                    "first_error": {k: fe.get(k) for k in ("kind", "stage", "start", "end", "critic", "critic_note", "why")} if fe else None,
                    "flag_type": "specific" if "specific flag" in note else "generic" if "generic flag" in note else None,
                }
                steps = trace_steps(attempt / "trace.jsonl")
                opened: set[str] = set()
                review_rows = []
                for i, step in enumerate(steps):
                    if step["name"] in OPENING_TOOLS:
                        opened |= set(MATTER.findall(json.dumps(step["input"])))
                    if step["name"] != "stage_end" or not step["result"] or not step["result"].startswith("[Stage review"):
                        continue
                    row = parse_review(step["result"])
                    named_text = " ".join(row["flags"]) + " " + row["concerns"] + " " + row["recommendation"]
                    named = set(MATTER.findall(named_text))
                    named_flags = set(MATTER.findall(" ".join(row["flags"])))
                    named_rec = set(MATTER.findall(row["recommendation"]))
                    later_opened: set[str] = set()
                    nxt = None
                    for later in steps[i + 1:]:
                        if later["name"] in OPENING_TOOLS:
                            later_opened |= set(MATTER.findall(json.dumps(later["input"])))
                        if nxt is None and later["name"] in ("stage_start", "finish"):
                            nxt = later
                    next_stage_opened: set[str] = set()
                    if nxt is not None and nxt["name"] == "stage_start":
                        j = steps.index(nxt)
                        for later in steps[j + 1:]:
                            if later["name"] == "stage_end":
                                break
                            if later["name"] in OPENING_TOOLS:
                                next_stage_opened |= set(MATTER.findall(json.dumps(later["input"])))
                    if nxt is None:
                        action, next_label, next_goal = "none", None, ""
                    elif nxt["name"] == "finish":
                        action, next_label, next_goal = "finish", None, ""
                    else:
                        a = nxt["input"]
                        next_label = a.get("stage") if a.get("stage") != "new" else f"new: {a.get('new_stage_name')}"
                        next_goal = a.get("goal", "")
                        action = "reopen" if next_label == row["label"] else ("new" if a.get("stage") == "new" else "other")
                    rec_words = words(row["recommendation"])
                    goal_words = words(next_goal)
                    named_unopened = named - opened
                    row.update({
                        "round": rnd, "task": task, "trial": run["trial"], "run_all_pass": run["all_pass"],
                        "call_idx": step["idx"], "review_idx": step["result_idx"],
                        "summary": step["input"].get("summary", ""),
                        "n_flags": len(row["flags"]),
                        "named": sorted(named), "named_in_flags": sorted(named_flags), "named_in_rec": sorted(named_rec),
                        "named_unopened": sorted(named_unopened),
                        "named_unopened_needed": sorted(named_unopened & set(needed)),
                        "named_unopened_opened_next_stage": sorted(named_unopened & next_stage_opened),
                        "named_unopened_opened_later": sorted(named_unopened & later_opened),
                        "unopened_needed": sorted(set(row["unopened"]) & set(needed)),
                        "unopened_needed_opened_later": sorted(set(row["unopened"]) & set(needed) & later_opened),
                        "next_action": action, "next_label": next_label, "next_goal": next_goal,
                        "goal_rec_overlap": round(len(rec_words & goal_words) / len(rec_words), 3) if rec_words else None,
                        "next_goal_names_named": sorted(named & set(MATTER.findall(next_goal))),
                    })
                    review_rows.append(row)
                for k, row in enumerate(review_rows):
                    row["review_no"] = k + 1
                    row["n_reviews"] = len(review_rows)
                reviews += review_rows
                run_row["n_reviews"] = len(review_rows)
                runs.append(run_row)
    with open(OUT / "reviews.jsonl", "w") as f:
        for row in reviews:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(OUT / "runs.jsonl", "w") as f:
        for row in runs:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"runs {len(runs)}, reviews {len(reviews)}")


if __name__ == "__main__":
    main()
