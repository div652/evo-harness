"""Build the strict-feedback dataset: one review per r2/r3 training run.

For every run of the stage harness's r2 and r3 training campaigns, find the
FIRST end-of-stage review that gives strict feedback (a flag naming a concrete
problem with evidence and implying a corrective action), chosen by an
annotator model from the run's reviews in order. For that review, record:
where it is (trace event, tool-call step, model call), the exact model request
that received it (copied, gzipped, with its sha256), the model's original next
response, and whether the agent eventually followed the feedback (annotator
model, next two stages). Runs whose first error the reviewer flagged
(feedback-uptake case labels) also get that review's location, request copy
and original next step, so the same replays can run on that review too.

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-replay/build_dataset.py [--workers 6] [--limit N]
Writes analysis/feedback-replay/dataset/items.jsonl (+ requests/*.json.gz).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "feedback-uptake"))
from build_reviews import LAB_TASKS, parse_review, result_text  # noqa: E402

ROUNDS = [("r2", "campaign-artifacts/harvey-lab-campaign-30-cao-stage-r2-train80"),
          ("r3", "campaign-artifacts/harvey-lab-campaign-31-cao-stage-r3-train80")]
OUT = HERE / "dataset"
URL = "http://127.0.0.1:4141/v1/chat/completions"
MODEL = os.environ.get("ANNOTATE_MODEL", "claude-opus-5-5")
LOCK = threading.Lock()

SELECT_SYSTEM = """You read the end-of-stage reviews an independent reviewer gave an AI agent during one run, in order. The agent works on a legal document-search task (matters = client engagements, folders NNNN-NNNNN).

A review gives STRICT feedback if at least one of its flags (or its recommendation) both
 (a) names a concrete problem in what the agent just did, with specific evidence: a matter, document, tool call, command, filter or exact cause; and
 (b) clearly implies a corrective action the agent should take next (e.g. open matter X, rerun the scan without filter Y, remove matter Z, page through the truncated output).
Stock or general warnings ("many matters may be missed", "coverage may be incomplete") without specific evidence and a clear action do NOT count.

Return the FIRST review in the list that gives strict feedback. Reply with JSON only:
{"review_idx": <its [n] index, or null if none qualifies>, "strict_item": "<the strict flag/recommendation, quoted or tightly paraphrased, <=50 words>", "implied_action": "<the corrective action, <=25 words>"}"""

FOLLOW_SYSTEM = """You judge whether an AI agent followed one specific piece of reviewer feedback. The agent works on a legal document-search task in declared stages. You see the reviewer's feedback item, the implied corrective action, and what the agent did in its next two stages (goals, tool calls, summaries).

Judge from the material only. "followed": "yes" if the agent's next two stages actually carried out the implied action; "partly" if it did part of it or a weaker version; "no" if it did not (mentioning it without doing it counts as no).
Reply with JSON only: {"followed": "yes"|"partly"|"no", "how": "reopened_same_stage"|"next_stage"|"second_stage"|"none", "note": "<=40 words"}"""


def chat(system: str, user: str) -> dict:
    body = json.dumps({"model": MODEL, "max_tokens": 1200, "temperature": 0, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {os.environ['CAO_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + f" …(+{len(text) - n})"


def trace_calls(trace: Path) -> list[dict]:
    """Ordered tool calls: {idx, id, name, input, result, result_idx, step} (step = 1-based call number, as in timeline.py)."""
    calls, steps = {}, []
    for line in open(trace):
        e = json.loads(line)
        if e.get("event_type") != "message" or isinstance(e.get("message"), str):
            continue
        for c in e["message"].get("content", []):
            if c.get("type") == "tool_use":
                st = {"idx": e["index"], "id": c["id"], "name": c["name"], "input": c["input"], "result": None, "result_idx": None, "step": len(steps) + 1}
                calls[c["id"]] = st
                steps.append(st)
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                calls[c["tool_use_id"]]["result"] = result_text(c.get("content"))
                calls[c["tool_use_id"]]["result_idx"] = e["index"]
    return steps


def find_model_call(model_calls: Path, call_id: str) -> Path | None:
    """The model call whose request's last input item is the output of `call_id` (the call that received it)."""
    dirs = sorted(model_calls.glob("call-*"), key=lambda p: int(p.name.split("-")[1]))
    emit = None
    for d in dirs:  # responses are small: find the call that emitted the tool call
        rp = d / "response.json"
        if rp.exists() and call_id in rp.read_text():
            emit = d
            break
    candidates = [dirs[dirs.index(emit) + 1]] if emit and dirs.index(emit) + 1 < len(dirs) else []
    candidates += dirs  # fallback: full scan
    for d in candidates:
        rq = d / "request.json"
        if not rq.exists():
            continue
        last = json.load(open(rq))["kwargs"]["input"][-1]
        if last.get("type") == "function_call_output" and last.get("call_id") == call_id:
            return d
    return None


def next_outputs(model_call: Path) -> list[dict]:
    """The model's recorded next step: its tool calls and any message text."""
    resp = json.load(open(model_call / "response.json"))["response"]
    out = []
    for o in resp.get("output", []):
        if o["type"] == "function_call":
            out.append({"type": "function_call", "name": o.get("name"), "arguments": o.get("arguments")})
        elif o["type"] == "message":
            out.append({"type": "message", "text": " ".join(c.get("text", "") for c in o.get("content", []) if isinstance(c, dict))})
    return out


def next_stages_text(steps: list[dict], after_step: int) -> str:
    out, seen = [], 0
    for s in steps[after_step:]:
        if s["name"] == "stage_start":
            seen += 1
            if seen > 2:
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


def build_one(rnd: str, unit_res: Path, first_error_flags: dict) -> dict | None:
    res = json.load(open(unit_res))
    task, trial = res["task_id"].split("/")[-1], res["trial"]
    attempt = unit_res.parent
    unit = attempt.parent.name
    runtime = Path(str(attempt).replace("/units/", "/runtime/")) / "model_calls"
    steps = trace_calls(attempt / "trace.jsonl")
    reviews = [s for s in steps if s["name"] == "stage_end" and s["result"] and s["result"].startswith("[Stage review")]
    listing = []
    for s in reviews:
        r = parse_review(s["result"])
        listing.append(f"### Review [{s['result_idx']}] of stage '{r['label']}' (attempt {r['attempt']}), verdict {r['verdict']}\n"
                       f"Flags: {' | '.join(r['flags']) or '(none)'}\nConcerns: {short(r['concerns'], 500)}\nRecommendation: {short(r['recommendation'], 600)}")
    spec = json.load(open(LAB_TASKS / task / "task.json"))
    sel = chat(SELECT_SYSTEM, f"## TASK REQUEST\n{spec['instructions']}\n\n## REVIEWS IN ORDER\n" + "\n\n".join(listing))
    item = {"id": f"{rnd}-{task}-T{trial}", "round": rnd, "task": task, "trial": trial, "run_all_pass": bool(res["dual"]["all_pass"]),
            "unit": unit, "attempt_dir": str(attempt), "n_reviews": len(reviews), "selection": sel}
    fe = first_error_flags.get((rnd, task, trial))
    if fe:
        item["first_error_flag"] = dict(fe)
        fe_rev = next((s for s in reviews if s["result_idx"] == fe.get("review_idx")), None)
        fe_mc = find_model_call(runtime, fe_rev["id"]) if fe_rev else None
        if fe_rev and fe_mc:
            raw = (fe_mc / "request.json").read_bytes()
            OUT.joinpath("requests").mkdir(parents=True, exist_ok=True)
            copy = OUT / "requests" / f"{rnd}-{task}-T{trial}.first-error.request.json.gz"
            copy.write_bytes(gzip.compress(raw))
            item["first_error_flag"].update({
                "stage_end_idx": fe_rev["idx"], "timeline_step": fe_rev["step"], "stage_label": parse_review(fe_rev["result"])["label"],
                "review_no": reviews.index(fe_rev) + 1, "review_text": fe_rev["result"], "model_call": fe_mc.name,
                "model_call_dir": str(fe_mc), "request_sha256": hashlib.sha256(raw).hexdigest(),
                "request_copy": str(copy.relative_to(HERE)), "original_next": next_outputs(fe_mc)})
    if sel.get("review_idx") is None:
        item["has_strict"] = False
        return item
    rev = next((s for s in reviews if s["result_idx"] == sel["review_idx"]), None)
    if rev is None:
        item["has_strict"] = False
        item["error"] = "selected index is not a review"
        return item
    item["has_strict"] = True
    r = parse_review(rev["result"])
    mc = find_model_call(runtime, rev["id"])
    item.update({"review_idx": rev["result_idx"], "stage_end_idx": rev["idx"], "stage_end_call_id": rev["id"],
                 "timeline_step": rev["step"], "stage_label": r["label"], "stage_attempt": r["attempt"], "verdict": r["verdict"],
                 "review_no": reviews.index(rev) + 1, "review_text": rev["result"], "is_first_error_flag": bool(fe and fe.get("review_idx") == rev["result_idx"])})
    if mc is None:
        item["error"] = "model call not found"
        return item
    req_raw = (mc / "request.json").read_bytes()
    OUT.joinpath("requests").mkdir(parents=True, exist_ok=True)
    req_copy = OUT / "requests" / f"{item['id']}.request.json.gz"
    req_copy.write_bytes(gzip.compress(req_raw))
    nxt = next_outputs(mc)
    item.update({"model_call": mc.name, "model_call_dir": str(mc), "request_sha256": hashlib.sha256(req_raw).hexdigest(),
                 "request_copy": str(req_copy.relative_to(HERE)), "original_next": nxt})
    follow = chat(FOLLOW_SYSTEM, f"## FEEDBACK ITEM (review [{rev['result_idx']}] of stage '{r['label']}')\n{sel.get('strict_item')}\n"
                                 f"Implied action: {sel.get('implied_action')}\n\n## FULL REVIEW\n{short(rev['result'], 4000)}\n\n"
                                 f"## WHAT THE AGENT DID NEXT\n{next_stages_text(steps, rev['step'])}")
    item["original_followed"] = follow
    return item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = HERE.parent / "feedback-uptake" / "data" / "case_labels.jsonl"
    first_error_flags = {}
    for row in map(json.loads, open(cases)):
        first_error_flags[(row["round"], row["task"], row["trial"])] = {
            "review_idx": row.get("flag_review_idx"), "kind": row["kind"], "critic": row["critic"], "flag_quote": row.get("flag_quote")}
    units = []
    for rnd, camp in ROUNDS:
        latest = {}
        for res in Path(camp).glob("evaluations/C0-train/units/*/attempt-*/result.json"):
            r = json.load(open(res))
            key = (r["task_id"], r["trial"])
            if key not in latest or str(res) > str(latest[key]):
                latest[key] = res
        units += [(rnd, p) for p in sorted(latest.values())]
    out_path = OUT / "items.jsonl"
    done = {json.loads(l)["unit"] for l in open(out_path)} if out_path.exists() else set()
    todo = [(rnd, p) for rnd, p in units if p.parent.parent.name not in done][: args.limit]
    print(f"runs {len(units)}, done {len(done)}, to do {len(todo)}", flush=True)

    def work(job: tuple) -> None:
        rnd, p = job
        for attempt in range(3):
            try:
                item = build_one(rnd, p, first_error_flags)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"FAILED {p}: {exc}", flush=True)
                    return
                time.sleep(20)
        if item is None:
            return
        with LOCK:
            with open(out_path, "a") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"ok {item['id']} strict={item.get('has_strict')} step={item.get('timeline_step')} call={item.get('model_call')} "
              f"followed={item.get('original_followed', {}).get('followed')} {item.get('error', '')}", flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, todo))


if __name__ == "__main__":
    main()
