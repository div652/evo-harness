"""Judge whether the agent's next step commits to the reviewer's feedback.

For each dataset item and arm, an annotator model sees the feedback (the
strict item and implied action, or the first-error flag) and the agent's next
step only: its tool call(s) with arguments (usually a stage_start and its
goal) or message. It is not told which arm produced the step. The arms are:
  original  the step the model actually took in the recorded run
  <variant> a replayed step from replays/<target>/<variant>/

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-replay/judge.py --target first_strict --arm original
  python3 analysis/feedback-replay/judge.py --target first_strict --arm wrapped
Writes analysis/feedback-replay/judgments/<target>/<arm>.jsonl (resumable).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
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

SYSTEM = """You judge one step of an AI agent. The agent works on a legal document-search task in declared stages (matters = client engagements, folders NNNN-NNNNN). It just closed a stage and received an independent reviewer's feedback. You see the feedback and the agent's very next step (usually a stage_start with a goal, sometimes other tool calls or a message).

Decide whether that next step COMMITS to acting on the given feedback item:
- "yes": the step clearly sets out to do the corrective action (e.g. its stage goal states it, or the tool call performs it);
- "partly": it addresses part of it, a weaker version, or mentions it as one aim among others without clearly committing;
- "no": it does not address it (moving on to other work, or only restating its own plan).
Judge only what the step itself says or does.

Reply with JSON only: {"commits": "yes"|"partly"|"no", "move": "reopen_same_stage"|"new_stage"|"other_stage"|"tool_call"|"finish"|"message", "note": "<=30 words"}"""


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
    lines = []
    for n in nxt:
        if n["type"] == "function_call":
            lines.append(f"TOOL CALL {n.get('name')}: {short(n.get('arguments'), 1500)}")
        else:
            lines.append(f"MESSAGE: {short(n.get('text', ''), 1500)}")
    return "\n".join(lines) or "(no tool call and no message)"


def material(item: dict, target: str, nxt: list[dict]) -> str:
    spec = json.load(open(LAB_TASKS / item["task"] / "task.json"))
    if target == "first_strict":
        fb = (f"Feedback item: {item['selection'].get('strict_item')}\nImplied corrective action: {item['selection'].get('implied_action')}")
        review, label = item["review_text"], item["stage_label"]
    else:
        fe = item["first_error_flag"]
        fb = f"Feedback item: {fe.get('flag_quote')}"
        review, label = fe["review_text"], fe["stage_label"]
    return (f"## TASK REQUEST\n{short(spec['instructions'], 1500)}\n\n## STAGE JUST CLOSED\n{label}\n\n## FEEDBACK ITEM TO CHECK\n{fb}\n\n"
            f"## FULL REVIEW THE AGENT RECEIVED\n{short(review, 4000)}\n\n## THE AGENT'S NEXT STEP\n{step_text(nxt)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["first_strict", "first_error"], required=True)
    ap.add_argument("--arm", required=True, help="original, or a replay variant name")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    items = {i["id"]: i for i in map(json.loads, open(HERE / "dataset" / "items.jsonl"))}
    jobs = []
    if args.arm == "original":
        for i in items.values():
            src = i if args.target == "first_strict" else i.get("first_error_flag") or {}
            if src.get("original_next") is not None and (args.target == "first_error" or i.get("has_strict")):
                jobs.append((i["id"], 0, src["original_next"]))
    else:
        for f in sorted((HERE / "replays" / args.target / args.arm).glob("*.json")):
            r = json.load(open(f))
            jobs.append((r["id"], r["sample"], r["next"]))
    out_dir = HERE / "judgments" / args.target
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.arm}.jsonl"
    done = {(r["id"], r["sample"]) for r in map(json.loads, open(out_path))} if out_path.exists() else set()
    jobs = [j for j in jobs if (j[0], j[1]) not in done]
    print(f"jobs {len(jobs)} -> {out_path}", flush=True)

    def work(job: tuple) -> None:
        iid, k, nxt = job
        for attempt in range(3):
            try:
                label = chat(material(items[iid], args.target, nxt))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"FAILED {iid}: {exc}", flush=True)
                    return
                time.sleep(20)
        row = {"id": iid, "sample": k, "arm": args.arm, "target": args.target, **label}
        with LOCK:
            with open(out_path, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, jobs))
    print("done", flush=True)


if __name__ == "__main__":
    main()
