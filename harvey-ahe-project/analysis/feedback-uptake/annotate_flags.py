"""Flag-level uptake: for a sample of reviews, was each flag acted on next?

Samples reviews (verdict partly/no, at least one flag, not the run's last
review) from r2/r3 training runs, half from passing and half from failing
runs (simple random sample within each half). An annotator model reads the review, the agent's
stage summary, and what the agent did in the next two stages, and labels each
flag: is it specific, does it ask one concrete action, and did the agent act
on it in the next stages.

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-uptake/annotate_flags.py [--n 150] [--workers 4]
Writes analysis/feedback-uptake/data/flag_labels.jsonl (resumable).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import annotate_cases  # noqa: E402
from build_reviews import LAB_TASKS, trace_steps  # noqa: E402

DATA = Path("analysis/feedback-uptake/data")
LOCK = threading.Lock()

SYSTEM = """You analyse whether an AI agent acted on an independent reviewer's feedback. The agent works on a legal document-search task in declared stages (matters = client engagements, folders NNNN-NNNNN). When a stage ends, a reviewer reads its tool calls and returns flags (problems), concerns and a recommendation. You see one such review and what the agent did in the next two stages.

For EACH reviewer flag (numbered as given), decide from the material only:
- "specific": true if it names a concrete item or evidence (a matter number, document, call, exact cause); false for a stock or general warning;
- "concrete_action": true if it implies one clear thing to do (open X, rerun Y with Z); false if vague or only a concern;
- "acted_on": "yes" | "partly" | "no" — did the agent's next two stages actually do what the flag implies (not merely mention it)?
- "how": "reopened_same_stage" | "next_stage" | "second_stage" | "none";
- "agent_already_planned": true if the agent's own stage summary or next goal shows it was going to do this anyway, independently of the flag.
Also judge the review's recommendation as a whole ("recommendation_followed": yes|partly|no) and whether the agent's next goal is driven by the review ("next_goal_driven_by_review": yes|partly|no).

Reply with JSON only:
{"flags": [{"n": 1, "specific": true, "concrete_action": true, "acted_on": "no", "how": "none", "agent_already_planned": false}, ...],
 "recommendation_followed": "...", "next_goal_driven_by_review": "...", "note": "<=40 words"}"""


def short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + f" …(+{len(text) - n})"


def material(review: dict, run: dict) -> str:
    spec = json.load(open(LAB_TASKS / review["task"] / "task.json"))
    steps = trace_steps(Path(run["attempt_dir"]) / "trace.jsonl")
    out = ["## TASK REQUEST", spec["instructions"], "",
           f"## REVIEW at [{review['review_idx']}] of stage '{review['label']}' (attempt {review['attempt']})",
           f"Agent's stage summary: {short(review['summary'], 1200)}",
           f"Agent claimed goal reached: {review['agent_claim']}. Reviewer verdict: {review['verdict']}.", "Reviewer flags:"]
    out += [f"  {i}. {f}" for i, f in enumerate(review["flags"], 1)]
    out += [f"Reviewer concerns: {short(review['concerns'], 900)}", f"Reviewer recommendation: {short(review['recommendation'], 900)}"]
    if review["unopened"]:
        out.append(f"Harness list of surfaced-but-unopened matters: {', '.join(review['unopened'][:25])}{' …' if len(review['unopened']) > 25 else ''}")
    out += ["", "## WHAT THE AGENT DID NEXT (next two stages: goals, calls, summaries)"]
    after = [s for s in steps if s["idx"] > review["call_idx"]]
    stages_seen = 0
    for s in after:
        if s["name"] == "stage_start":
            stages_seen += 1
            if stages_seen > 2:
                break
            a = s["input"]
            label = a.get("stage") if a.get("stage") != "new" else f"new: {a.get('new_stage_name')}"
            out.append(f"[{s['idx']}] STAGE START: {label} | goal: {short(a.get('goal', ''), 500)}")
        elif s["name"] == "stage_end":
            out.append(f"[{s['idx']}] STAGE END | summary: {short(s['input'].get('summary', ''), 700)}")
        elif s["name"] == "finish":
            out.append(f"[{s['idx']}] FINISH")
            break
        else:
            out.append(f"[{s['idx']}] {s['name']} {short(json.dumps(s['input'], ensure_ascii=False), 260)}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    runs = {(u["round"], u["task"], u["trial"]): u for u in (json.loads(l) for l in open(DATA / "runs.jsonl"))}
    reviews = [json.loads(l) for l in open(DATA / "reviews.jsonl")]
    pool = [r for r in reviews if r["verdict"] in ("partly", "no") and r["flags"] and r["review_no"] < r["n_reviews"]]
    rng = random.Random(11)
    sample = []
    for passed in (True, False):
        # simple random sample within passing and within failing runs, so rates are representative
        sub = [r for r in pool if r["run_all_pass"] == passed]
        sample += rng.sample(sub, args.n // 2)
    keys = [[r["round"], r["task"], r["trial"], r["review_idx"]] for r in sample]
    (DATA / "flag_sample.json").write_text(json.dumps(keys))
    out_path = DATA / "flag_labels.jsonl"
    done = set()
    if out_path.exists():
        done = {(r["round"], r["task"], r["trial"], r["review_idx"]) for r in map(json.loads, open(out_path))}
    todo = [r for r in sample if (r["round"], r["task"], r["trial"], r["review_idx"]) not in done]
    print(f"sample {len(sample)}, done {len(done)}, to do {len(todo)}", flush=True)
    annotate_cases.SYSTEM = SYSTEM  # reuse the endpoint helper with this prompt

    def work(r: dict) -> None:
        key = (r["round"], r["task"], r["trial"])
        text_in = material(r, runs[key])
        for attempt in range(3):
            try:
                label = json.loads(re.search(r"\{.*\}", annotate_cases.chat(text_in), re.S).group(0))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"FAILED {key} {r['review_idx']}: {exc}", flush=True)
                    return
                time.sleep(20)
        row = {k: r[k] for k in ("round", "task", "trial", "review_idx", "label", "verdict", "agent_claim", "n_flags",
                                  "review_chars", "run_all_pass", "next_action", "review_no", "n_reviews")}
        row["flag_texts"] = r["flags"]
        row.update(label)
        with LOCK:
            with open(out_path, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"ok {key} [{r['review_idx']}]", flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))


if __name__ == "__main__":
    main()
