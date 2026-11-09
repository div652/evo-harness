"""Reviewer-independent judging for the first-error items.

For each step, an annotator model sees the run's FIRST ERROR (from the human
training annotation: kind, stage, why), the review the agent received, and
the agent's next step, and answers two questions:
  review_raises_problem   does the review point the agent at that problem?
  step_commits_to_fix     does the agent's next step set out to fix it?
It is not told which reviewer wrote the review or which arm the step is from.

Arms:
  original        recorded Sonnet review + recorded next step
  control_nosum   recorded Sonnet review + replayed next step (replays/first_error/control_nosum)
  reviewer_sonnet fresh Sonnet review + replayed next step
  reviewer_luna   fresh gpt-5.6-luna (medium) review + replayed next step

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-replay/judge_problem.py --arm reviewer_luna [--workers 24]
  python3 analysis/feedback-replay/judge_problem.py --summarize original control_nosum reviewer_sonnet reviewer_luna
Writes judgments/first_error/problem_<arm>.jsonl and results_reviewer_swap.md.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import os
import random
import re
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
URL = "http://127.0.0.1:4141/v1/chat/completions"
MODEL = os.environ.get("ANNOTATE_MODEL", "claude-opus-5-5")
LAB_TASKS = Path(os.path.expanduser("~/harvey-labs/tasks/firm-knowledge/tasks"))
LOCK = threading.Lock()
SCORE = {"yes": 1.0, "partly": 0.5, "no": 0.0}

SYSTEM = """You judge one moment in an AI agent's run on a legal document-search task (matters = client engagements, folders NNNN-NNNNN). The agent works in declared stages; when a stage ends, a reviewer writes a review, and the agent then takes its next step (usually starting a stage with a goal).

You are told the run's FIRST ERROR: the mistake, identified afterwards by a human annotator, after which the run could no longer pass. Answer two questions from the material only:
1. review_raises_problem: does the review the agent received point it at THIS problem (the specific mistake or its direct cause), so that acting on the review would address it? "yes" = clearly and specifically; "partly" = only generally, or among unrelated points with no clear link; "no" = not at all.
2. step_commits_to_fix: does the agent's next step set out to fix THIS problem? "yes" = its goal or call clearly does; "partly" = it touches it weakly or as one aim among others; "no" = it does not.

Reply with JSON only: {"review_raises_problem": "yes"|"partly"|"no", "step_commits_to_fix": "yes"|"partly"|"no", "note": "<=30 words"}"""


def chat(user: str) -> dict:
    body = json.dumps({"model": MODEL, "max_tokens": 600, "temperature": 0, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {os.environ['CAO_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + f" …(+{len(text) - n})"


def step_text(nxt: list[dict]) -> str:
    out = []
    for n in nxt:
        if n["type"] == "function_call":
            out.append(f"TOOL CALL {n.get('name')}: {short(n.get('arguments'), 1500)}")
        else:
            out.append(f"MESSAGE: {short(n.get('text', ''), 1500)}")
    return "\n".join(out) or "(no tool call and no message)"


def first_errors() -> dict:
    runs = HERE.parent / "feedback-uptake" / "data" / "runs.jsonl"
    return {f"{u['round']}-{u['task']}-T{u['trial']}": u["first_error"] for u in map(json.loads, open(runs)) if u.get("first_error")}


def jobs_for(arm: str, items: dict) -> list[tuple]:
    if arm == "original":
        return [(i["id"], 0, i["first_error_flag"]["review_text"], i["first_error_flag"]["original_next"])
                for i in items.values() if (i.get("first_error_flag") or {}).get("request_copy")]
    jobs = []
    for f in sorted((HERE / "replays" / "first_error" / arm).glob("*.json")):
        r = json.load(open(f))
        review = r.get("review_text") or items[r["id"]]["first_error_flag"]["review_text"]
        jobs.append((r["id"], r["sample"], review, r["next"]))
    return jobs


def judge(arm: str, workers: int) -> None:
    items = {i["id"]: i for i in map(json.loads, open(HERE / "dataset" / "items.jsonl"))}
    fes = first_errors()
    out_path = HERE / "judgments" / "first_error" / f"problem_{arm}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["id"], r["sample"]) for r in map(json.loads, open(out_path))} if out_path.exists() else set()
    todo = [j for j in jobs_for(arm, items) if (j[0], j[1]) not in done]
    print(f"{arm}: jobs {len(todo)}", flush=True)

    def work(job: tuple) -> None:
        iid, k, review, nxt = job
        it, fe = items[iid], fes[iid]
        spec = json.load(open(LAB_TASKS / it["task"] / "task.json"))
        material = (f"## TASK REQUEST\n{short(spec['instructions'], 1500)}\n\n## THE RUN'S FIRST ERROR (human annotation)\n"
                    f"Kind: {fe['kind']}, at stage '{fe['stage']}'.\n{fe['why']}\n\n## REVIEW THE AGENT RECEIVED\n{short(review, 5000)}\n\n"
                    f"## THE AGENT'S NEXT STEP\n{step_text(nxt)}")
        for attempt in range(3):
            try:
                label = chat(material)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"FAILED {iid} s{k}: {exc}", flush=True)
                    return
                time.sleep(20)
        with LOCK:
            with open(out_path, "a") as f:
                f.write(json.dumps({"id": iid, "sample": k, "arm": arm, **label}, ensure_ascii=False) + "\n")

    with cf.ThreadPoolExecutor(workers) as ex:
        list(ex.map(work, todo))
    print("done", flush=True)


def summarize(arms: list[str]) -> None:
    data = {}
    for a in arms:
        rows = collections.defaultdict(list)
        for r in map(json.loads, open(HERE / "judgments" / "first_error" / f"problem_{a}.jsonl")):
            rows[r["id"]].append(r)
        data[a] = rows
    common = sorted(set.intersection(*(set(d) for d in data.values())))
    per = {a: {i: (sum(SCORE[r["review_raises_problem"]] for r in data[a][i]) / len(data[a][i]),
                   sum(SCORE[r["step_commits_to_fix"]] for r in data[a][i]) / len(data[a][i])) for i in common} for a in arms}
    out = ["# Reviewer swap on the first-error items", "", f"Items with every arm judged: {len(common)}", "",
           "Scores: yes = 1, partly = 0.5, no = 0, averaged over an item's samples.", "",
           "| Arm | steps | review raises the problem: yes / partly / no | score | next step commits to fixing it: yes / partly / no | score |",
           "|---|---|---|---|---|---|"]
    for a in arms:
        rows = [r for i in common for r in data[a][i]]
        n = len(rows)
        rv = collections.Counter(r["review_raises_problem"] for r in rows)
        st = collections.Counter(r["step_commits_to_fix"] for r in rows)
        out.append(f"| {a} | {n} | {rv['yes'] / n:.0%} / {rv['partly'] / n:.0%} / {rv['no'] / n:.0%} | {sum(v[0] for v in per[a].values()) / len(common):.3f} | "
                   f"{st['yes'] / n:.0%} / {st['partly'] / n:.0%} / {st['no'] / n:.0%} | {sum(v[1] for v in per[a].values()) / len(common):.3f} |")
    out += ["", "## Paired differences (95% bootstrap CI over items)", "", "| Comparison | review score | step score |", "|---|---|---|"]

    def ci(diffs: list[float]) -> str:
        rng = random.Random(0)
        bs = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(5000))
        return f"{sum(diffs) / len(diffs):+.3f} [{bs[125]:+.3f}, {bs[4875]:+.3f}]"
    pairs = [("reviewer_luna", "reviewer_sonnet"), ("reviewer_sonnet", "control_nosum"), ("reviewer_luna", "control_nosum")]
    for a, b in pairs:
        if a in per and b in per:
            out.append(f"| {a} − {b} | {ci([per[a][i][0] - per[b][i][0] for i in common])} | {ci([per[a][i][1] - per[b][i][1] for i in common])} |")
    # commitment given the review raised the problem
    out += ["", "## Next-step commitment when the review did / did not raise the problem", "",
            "| Arm | review raised it (yes) | steps | commit score | review did not (no) | steps | commit score |", "|---|---|---|---|---|---|---|"]
    for a in arms:
        rows = [r for i in common for r in data[a][i]]
        y = [r for r in rows if r["review_raises_problem"] == "yes"]
        nn = [r for r in rows if r["review_raises_problem"] == "no"]
        f = lambda rs: f"{sum(SCORE[r['step_commits_to_fix']] for r in rs) / len(rs):.2f}" if rs else "–"  # noqa: E731
        out.append(f"| {a} | | {len(y)} | {f(y)} | | {len(nn)} | {f(nn)} |")
    text = "\n".join(out) + "\n"
    (HERE / "results_reviewer_swap.md").write_text(text)
    print(text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--summarize", nargs="+")
    args = ap.parse_args()
    if args.summarize:
        summarize(args.summarize)
    else:
        judge(args.arm, args.workers)


if __name__ == "__main__":
    main()
