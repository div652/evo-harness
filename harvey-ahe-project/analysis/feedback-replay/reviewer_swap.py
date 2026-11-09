"""Swap the stage reviewer's model, then replay the agent's next step.

For each first-error item (the review that flagged the run's first error),
rebuild the reviewer's exact input from the trace with the round's own frozen
harness code (campaign checkpoint C0: the r2 or r3 `tools/stage.py`), ask a
reviewer model for a fresh critique, render the review with the harness's own
`_review_text`, put it in place of the recorded review in the exact recorded
model request (no other change, no reasoning-summary request), and generate the
agent's next step (gpt-5.6-luna via CAO).

Reviewers:
  luna       gpt-5.6-luna, reasoning effort medium (Responses API; 32K output tokens so reasoning is not cut;
             the medium run on 2026-11-09 used 16K)
  luna_high  gpt-5.6-luna, reasoning effort high
  sonnet  claude-sonnet-5-5 through the harness's own call (the original reviewer, fresh sample)

Each item first checks the rebuild: rendering the review with the recorded
critique (parsed back from the recorded review) must reproduce the recorded
review text exactly (`rebuild_exact`).

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-replay/reviewer_swap.py --round r3 --reviewer luna --samples 2 --workers 24
Writes analysis/feedback-replay/replays/first_error/reviewer_<name>/<id>.s<k>.json
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from replay import load_request, send, summarize_output  # noqa: E402

CAMPAIGN = {"r2": "campaign-artifacts/harvey-lab-campaign-30-cao-stage-r2-train80",
            "r3": "campaign-artifacts/harvey-lab-campaign-31-cao-stage-r3-train80"}
RESPONSES_URL = "http://127.0.0.1:4141/v1/responses"
WORK_TOOLS = {"bash", "read", "write", "edit", "glob", "grep"}
MARKER = "[Stage protocol]"


def load_harness(rnd: str):
    harness = (Path(CAMPAIGN[rnd]) / "checkpoints" / "C0" / "harness").resolve()
    sys.path.insert(0, str(harness))
    stage = importlib.import_module("tools.stage")
    common = importlib.import_module("tools._stage_common")
    return stage, common


def make_luna_chat(effort: str):
    def luna_chat(model: str, system: str, user: str, max_tokens: int = 900) -> str:  # noqa: ARG001 (signature of the harness chat)
        return _luna_call(system, user, effort)
    return luna_chat


def _luna_call(system: str, user: str, effort: str) -> str:
    body = json.dumps({"model": "gpt-5.6-luna", "instructions": system, "input": user, "stream": False,
                       "reasoning": {"effort": effort, "summary": "auto"}, "max_output_tokens": 32000}).encode()
    for attempt in range(6):
        req = urllib.request.Request(RESPONSES_URL, data=body, headers={
            "Authorization": f"Bearer {os.environ['CAO_API_KEY']}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                resp = json.load(r)
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == 5 or (isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(30 * (attempt + 1))
    texts = [c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if isinstance(c, dict)]
    return "\n".join(texts)


def stripped_result(raw, common) -> str:
    """The tool result as the guard recorded it: result text, without an appended stage-fit note."""
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:  # noqa: BLE001
        value = raw
    text = common.result_text(value)
    cut = text.find("\n\n" + MARKER + " Stage check:")
    return text[:cut] if cut >= 0 else text


def rebuild(item: dict, stage_mod, common) -> dict:
    """Rebuild the harness state at the flagged stage_end from the trace."""
    fe = item["first_error_flag"]
    events = [json.loads(l) for l in open(Path(item["attempt_dir"]) / "trace.jsonl")]
    request = ""
    calls, order = {}, []
    for e in events:
        if e.get("event_type") != "message" or isinstance(e.get("message"), str):
            continue
        m = e["message"]
        if m.get("role") == "user" and not request:
            texts = [c.get("text", "") for c in m.get("content", []) if c.get("type") == "text"]
            if any(texts):
                request = " ".join(texts).strip()
        for c in m.get("content", []):
            if c.get("type") == "tool_use":
                calls[c["id"]] = {"idx": e["index"], "name": c["name"], "input": c["input"], "raw": None}
                order.append(c["id"])
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                calls[c["tool_use_id"]]["raw"] = c.get("content")
    state = {"request": request, "surfaced": {}, "opened": [], "history": []}
    current = None
    target = None
    for cid in order:
        c = calls[cid]
        name, args = c["name"], c["input"]
        raw = c["raw"]
        if name == "stage_start":
            if raw is None or ("Stage started:" not in str(raw)):
                continue  # refused
            label = args.get("stage") if args.get("stage") != "new" else f"new: {(args.get('new_stage_name') or '').strip()}"
            attempt = 1 + sum(1 for h in state["history"] if h["label"] == label)
            current = {"stage": args.get("stage"), "label": label, "goal": (args.get("goal") or "").strip(), "attempt": attempt, "calls": []}
            continue
        if name == "stage_end":
            if current is None or raw is None or "[Stage review" not in str(raw):
                continue
            if c["idx"] == fe["stage_end_idx"]:
                target = (current, args)
                break
            state["history"].append({"stage": current["stage"], "label": current["label"], "goal": current["goal"],
                                     "attempt": current["attempt"], "goal_reached": bool(args.get("goal_reached"))})
            current = None
            continue
        if name not in WORK_TOOLS or current is None or raw is None:
            continue
        text = stripped_result(raw, common)
        if text.startswith(MARKER):
            continue  # refused by the guard: not recorded
        arg_text = json.dumps(args, ensure_ascii=False)
        current["calls"].append({"tool": name, "args": common.short(arg_text, 400), "result": common.short(text, 700)})
        if common.SNO_ENABLED and common.ENTITY is not None:
            opened = set(state["opened"])
            if name in ("read", "glob", "bash"):
                opened |= set(common.ENTITY.findall(arg_text))
            if name in ("grep", "glob", "bash"):
                shown = set(common.ENTITY.findall(text))
                if 0 < len(shown) <= common.SNO_MAX:
                    for entity in sorted(shown):
                        state["surfaced"].setdefault(entity, current["label"])
            state["opened"] = sorted(opened)
    if target is None:
        raise ValueError("flagged stage_end not found in trace")
    current, end_args = target
    return {"state": state, "current": current, "goal_reached": bool(end_args.get("goal_reached")), "summary": end_args.get("summary") or ""}


def parse_critique(review: str) -> dict:
    """The recorded critique, parsed back from the recorded review text."""
    if "Independent reviewer: unavailable" in review:
        return {"available": False}
    m = re.search(r"^Independent reviewer: goal reached = (.*)\.$", review, re.M)
    if not m:
        raw = re.search(r"^Independent reviewer: (.*)$", review, re.M)
        return {"available": True, "raw": raw.group(1) if raw else ""}
    crit = {"available": True, "goal_reached": m.group(1)}
    for key, prefix in (("applicable_failures", "Reviewer flags: "), ("concerns", "Reviewer concerns: "), ("recommendation", "Reviewer recommendation: ")):
        mm = re.search(rf"^{re.escape(prefix)}(.*)$", review, re.M)
        if mm:
            crit[key] = [mm.group(1)] if key == "applicable_failures" else mm.group(1)
    ns = re.search(r"^Reviewer suggests a new step: '(.*)' \((.*)\)\. You can start it with", review, re.M)
    if ns:
        crit["new_stage"] = {"name": ns.group(1), "goal": ns.group(2)}
    return crit


def review_for(rnd: str, stage_mod, common, rb: dict, critique: dict, effective: str | None) -> str:
    current = rb["current"]
    ref = common.reference(current["stage"])
    if rnd == "r2":
        unopened = stage_mod._surfaced_not_opened(rb["state"]) if common.SNO_ENABLED and current["stage"] in common.SNO_STAGES else None
        return stage_mod._review_text(current, ref, rb["goal_reached"], critique, unopened)
    eff_ref = common.reference(effective) if effective else None
    show = common.SNO_ENABLED and (current["stage"] in common.SNO_STAGES or effective in common.SNO_STAGES)
    unopened = stage_mod._surfaced_not_opened(rb["state"]) if show else None
    return stage_mod._review_text(current, ref, rb["goal_reached"], critique, unopened, effective, eff_ref)


def fresh_critique(rnd: str, stage_mod, common, rb: dict, effective: str | None) -> dict:
    current = rb["current"]
    ref = common.reference(current["stage"])
    if rnd == "r2":
        unopened = stage_mod._surfaced_not_opened(rb["state"]) if common.SNO_ENABLED and current["stage"] in common.SNO_STAGES else None
        return stage_mod._critic(rb["state"], current, ref, rb["goal_reached"], rb["summary"], unopened)
    eff_ref = common.reference(effective) if effective else None
    show = common.SNO_ENABLED and (current["stage"] in common.SNO_STAGES or effective in common.SNO_STAGES)
    unopened = stage_mod._surfaced_not_opened(rb["state"]) if show else None
    earlier = [h for h in rb["state"]["history"] if h["label"] == current["label"]]
    return stage_mod._critic(rb["state"], current, ref, rb["goal_reached"], rb["summary"], unopened, effective, eff_ref, earlier)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", choices=["r2", "r3"], required=True)
    ap.add_argument("--reviewer", choices=["luna", "luna_high", "sonnet"], required=True)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--check-only", action="store_true", help="only verify the rebuild, no model calls")
    args = ap.parse_args()
    stage_mod, common = load_harness(args.round)
    if args.reviewer in ("luna", "luna_high"):
        # the harness critic calls chat(CRITIC_MODEL, system, user)
        stage_mod.chat = make_luna_chat("high" if args.reviewer == "luna_high" else "medium")
    items = [i for i in map(json.loads, open(HERE / "dataset" / "items.jsonl"))
             if i["round"] == args.round and (i.get("first_error_flag") or {}).get("request_copy")]
    out_dir = HERE / "replays" / "first_error" / f"reviewer_{args.reviewer}"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(i, k) for i in sorted(items, key=lambda x: x["id"]) for k in range(1, args.samples + 1)
            if not (out_dir / f"{i['id']}.s{k}.json").exists()][: args.limit]
    print(f"{args.round} items {len(items)}, jobs {len(jobs)} -> {out_dir}", flush=True)

    def work(job: tuple) -> dict | None:
        item, k = job
        fe = item["first_error_flag"]
        try:
            rb = rebuild(item, stage_mod, common)
            eff = re.search(r"^Label: these calls looked like '(.*)' work", fe["review_text"], re.M)
            effective = eff.group(1) if eff and args.round == "r3" else None
            exact = review_for(args.round, stage_mod, common, rb, parse_critique(fe["review_text"]), effective) == fe["review_text"]
            if args.check_only:
                return {"id": item["id"], "rebuild_exact": exact}
            critique = fresh_critique(args.round, stage_mod, common, rb, effective)
            review = review_for(args.round, stage_mod, common, rb, critique, effective)
            kwargs, recorded = load_request(item, "first_error")
            last = kwargs["input"][-1]
            payload = json.loads(last["output"])
            if payload.get("result") != recorded:
                raise ValueError("recorded tool output does not hold the review text")
            payload["result"] = review
            last["output"] = json.dumps(payload, indent=2, ensure_ascii=False)
            resp = send(kwargs, summaries=False)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {item['id']} s{k}: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
            return None
        row = {"id": item["id"], "target": "first_error", "variant": f"reviewer_{args.reviewer}", "sample": k,
               "summaries": False, "rebuild_exact": exact, "critique": critique, "review_text": review, **summarize_output(resp)}
        (out_dir / f"{item['id']}.s{k}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1))
        print(f"ok {item['id']} s{k} exact={exact} verdict={critique.get('goal_reached')} next={[n.get('name') for n in row['next']]}", flush=True)
        return row

    with cf.ThreadPoolExecutor(args.workers) as ex:
        results = [r for r in ex.map(work, jobs) if r]
    if args.check_only:
        print(f"rebuild exact: {sum(r['rebuild_exact'] for r in results)}/{len(results)}", flush=True)
        for r in results:
            if not r["rebuild_exact"]:
                print("  not exact:", r["id"])


if __name__ == "__main__":
    main()
