"""LLM-annotate each failing run whose first error the reviewer flagged.

For every r2/r3 training run whose first error has reviewer outcome
`flagged-ignored` or `flagged-fixed-partly`, an annotator model reads the task,
the rubric verdicts, the training annotation, the agent's stages, every review
and what the agent did after it, and returns a JSON judgement: which review
flagged the error, whether the flag was right, its timing and shape, what the
agent did, and why the advice was not followed.

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-uptake/annotate_cases.py [--limit N] [--workers 6]
Writes analysis/feedback-uptake/data/case_labels.jsonl (resumable).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_reviews import LAB_TASKS, load_scores, trace_steps  # noqa: E402

DATA = Path("analysis/feedback-uptake/data")
URL = os.environ.get("ANNOTATE_URL", "http://127.0.0.1:4141/v1/chat/completions")
MODEL = os.environ.get("ANNOTATE_MODEL", "claude-opus-5-5")
LOCK = threading.Lock()

SYSTEM = """You analyse one failing run of an AI agent on a legal document-search task, to understand why the agent did not act on an independent reviewer's feedback.

Setting. The agent searches a firm's document store (matters = client engagements, folders named NNNN-NNNNN) and writes an answer file. A hidden rubric names the matters/documents the answer must state; a run passes only if every criterion passes. The harness makes the agent work in declared stages; when a stage ends, an independent reviewer model reads that stage's tool calls and returns a verdict (yes/partly/no), flags (specific problems), concerns and a recommendation. The review also lists matters that appeared in the agent's search results but were never opened, and the stage's common past failures. The agent then decides to reopen the stage or move on.

A human annotator already identified the run's FIRST ERROR (the earliest step after which the run could no longer pass) and judged that the reviewer flagged it. Your job: examine the reviews and the agent's subsequent behaviour and answer the questions. Judge only from the material given. Do not invent facts. Quote briefly.

Reply with JSON only, with exactly these keys:
{
 "flag_review_idx": <integer event index [n] of the FIRST review whose feedback addresses the first error; null if none does>,
 "flag_quote": "<the reviewer's words that address it, <=40 words>",
 "flag_part": "flags" | "concerns" | "recommendation" | "unopened_list" | "several",
 "names_needed_item": true | false,          // names the specific matter/document the rubric needed (or the exact wrongly-included one)
 "flag_correct": "yes" | "partly" | "no",    // was the reviewer right about this problem, given the rubric verdicts?
 "advice_shape": "one_action" | "several_actions" | "vague",   // the ask about THIS problem: one concrete action, one among many, or unclear
 "competing_asks": <integer: number of distinct things that review asked the agent to do>,
 "timing": "before_decision" | "after_decision",   // did this feedback arrive before or after the agent's decision that caused the first error (e.g. choosing what to open, or writing the answer)?
 "times_repeated": <integer: number of LATER reviews that raise the same problem again>,
 "agent_next": "reopened_same_stage" | "started_suggested_stage" | "moved_on" | "finished",
 "next_goal_addresses_flag": "yes" | "partly" | "no",
 "eventual_action": "none" | "partial" | "full",   // did the agent ever act on this specific advice, at any later point?
 "agent_disputed": true | false,             // did the agent explicitly argue the flag does not apply (in a summary or goal)?
 "summary_overclaims": true | false,         // did the agent's stage summary claim completeness that the flag contradicts?
 "why_not_followed": "own_plan_continued" | "buried_among_other_asks" | "advice_too_vague" | "advice_arrived_after_decision" | "agent_judged_flag_wrong" | "acted_superficially" | "reviewer_wrong_or_misleading" | "other",
 "would_fix_if_followed": "yes" | "partly" | "no",   // would fully following this advice have fixed the first error?
 "would_pass_if_followed": "likely" | "unlikely",     // would the run then likely all-pass (are all failed criteria explained by this error)?
 "explanation": "<=60 words: what happened between the flag and the end of the run>"
}"""


def chat(user: str) -> str:
    body = json.dumps({"model": MODEL, "max_tokens": 2000, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {os.environ['CAO_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + f" …(+{len(text) - n})"


def case_material(run: dict, reviews: list[dict]) -> str:
    spec = json.load(open(LAB_TASKS / run["task"] / "task.json"))
    attempt = Path(run["attempt_dir"])
    scores = load_scores(attempt) or {"criteria_results": []}
    ann = json.load(open(f"analysis/stages-train-c{'30' if run['round'] == 'r2' else '31'}/annotations/{run['task']}.json"))
    arun = next(r for r in ann["runs"] if r["trial"] == run["trial"])
    out = ["## TASK REQUEST", spec["instructions"], "", "## RUBRIC VERDICTS (judge)"]
    for c in scores["criteria_results"]:
        line = f"- [{c['verdict'].upper()}] {c['title']}"
        if c["verdict"] != "pass":
            line += f" — judge: {short(c.get('reasoning', ''), 300)}"
        out.append(line)
    fe = run["first_error"]
    out += ["", "## HUMAN ANNOTATION", f"First error: {fe['kind']} at stage '{fe['stage']}' (events [{fe['start']}]-[{fe['end']}]).",
            f"Why: {fe['why']}", f"Reviewer outcome: {fe['critic']} — {fe['critic_note']}"]
    for e in arun.get("other_errors") or []:
        out.append(f"Later error: {e['kind']} at '{e['stage']}': {short(e['why'], 250)}")
    out += ["", "## AGENT'S STAGES (annotator notes; [start]-[end] event indices)"]
    for s in arun["stages"]:
        out.append(f"- [{s['start']}]-[{s['end']}] {s['stage']}: {short(s.get('note', ''), 220)}")
    out += ["", "## TOOL CALLS (compact: index, tool, arguments)"]
    for st in trace_steps(attempt / "trace.jsonl"):
        if st["name"] in ("stage_start", "stage_end"):
            continue
        out.append(f"[{st['idx']}] {st['name']} {short(json.dumps(st['input'], ensure_ascii=False), 220)}")
    out += ["", "## EVERY STAGE REVIEW, WITH WHAT THE AGENT DID NEXT"]
    for r in reviews:
        out += [f"### Review at [{r['review_idx']}] of stage '{r['label']}' (attempt {r['attempt']})",
                f"Agent's stage summary: {short(r['summary'], 900)}",
                f"Agent claimed goal reached: {r['agent_claim']}. Reviewer verdict: {r['verdict']}.",
                f"Reviewer flags: {' | '.join(r['flags']) or '(none)'}",
                f"Reviewer concerns: {short(r['concerns'], 700)}",
                f"Reviewer recommendation: {short(r['recommendation'], 700)}"]
        if r["new_stage_suggested"]:
            out.append("(Reviewer also suggested a new stage.)")
        if r["unopened"]:
            out.append(f"Harness list of surfaced-but-unopened matters ({len(r['unopened'])}{'+' if r['unopened_truncated'] else ''}): {', '.join(r['unopened'][:25])}{' …' if len(r['unopened']) > 25 else ''}")
        out.append(f"AGENT NEXT: {r['next_action']} -> {r['next_label'] or ''} | goal: {short(r['next_goal'], 400)}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    runs = [json.loads(l) for l in open(DATA / "runs.jsonl")]
    reviews = [json.loads(l) for l in open(DATA / "reviews.jsonl")]
    by_run: dict = {}
    for r in reviews:
        by_run.setdefault((r["round"], r["task"], r["trial"]), []).append(r)
    cases = [u for u in runs if not u["all_pass"] and u["first_error"]
             and u["first_error"]["critic"] in ("flagged-ignored", "flagged-fixed-partly")]
    out_path = DATA / "case_labels.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path):
            row = json.loads(line)
            done.add((row["round"], row["task"], row["trial"]))
    todo = [u for u in cases if (u["round"], u["task"], u["trial"]) not in done][: args.limit]
    print(f"cases {len(cases)}, done {len(done)}, to do {len(todo)}", flush=True)

    def work(u: dict) -> None:
        key = (u["round"], u["task"], u["trial"])
        material = case_material(u, by_run.get(key, []))
        for attempt in range(3):
            try:
                text = chat(material)
                label = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"FAILED {key}: {exc}", flush=True)
                    return
                time.sleep(20)
        row = {"round": u["round"], "task": u["task"], "trial": u["trial"],
               "critic": u["first_error"]["critic"], "flag_type": u["flag_type"],
               "kind": u["first_error"]["kind"], "stage": u["first_error"]["stage"],
               "material_chars": len(material), **label}
        with LOCK:
            with open(out_path, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"ok {key} {label.get('why_not_followed')}", flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))


if __name__ == "__main__":
    main()
