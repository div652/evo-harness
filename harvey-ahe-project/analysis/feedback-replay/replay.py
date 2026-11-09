"""Replay one model step with the reviewer's feedback changed.

For each dataset item, take the exact recorded model request that received
the review (its last input item is the `stage_end` tool output), apply a
variant to the review text, resend it to the same model (gpt-5.6-luna via
CAO), and save the model's next step. Nothing is executed: only the one
response that follows the review is generated.

Variants (add new ones to VARIANTS):
  control  the review unchanged (measures the model's own variability)
  wrapped  the whole review wrapped in [VERIFIER FEEDBACK] ... [\\VERIFIER FEEDBACK]

Targets:
  first_strict  the run's first strict-feedback review (every item with has_strict)
  first_error   the review that flagged the run's first error (items with first_error_flag.request_copy)

Both arms add reasoning {"summary": "auto"} (the recorded requests predate the
summary fix); --no-summaries sends the request without it.

Usage (from harvey-ahe-project/, CAO running, CAO_API_KEY exported):
  python3 analysis/feedback-replay/replay.py --target first_strict --variant wrapped [--samples 1] [--workers 6]
Writes analysis/feedback-replay/replays/<target>/<variant>/<id>.s<k>.json
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
URL = os.environ.get("REPLAY_URL", "http://127.0.0.1:4141/v1/responses")


def wrap(text: str) -> str:
    return "[VERIFIER FEEDBACK]\n" + text + "\n[\\VERIFIER FEEDBACK]"


VARIANTS = {
    "control": lambda text: text,
    "wrapped": wrap,
}


def load_request(item: dict, target: str) -> tuple[dict, str]:
    src = item if target == "first_strict" else item["first_error_flag"]
    raw = gzip.decompress((HERE / src["request_copy"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != src["request_sha256"]:
        raise ValueError(f"{item['id']}: request copy does not match its recorded sha256")
    return json.loads(raw)["kwargs"], src["review_text"]


def apply_variant(kwargs: dict, review: str, variant: str) -> dict:
    kwargs = json.loads(json.dumps(kwargs))
    last = kwargs["input"][-1]
    if last.get("type") != "function_call_output":
        raise ValueError("last input item is not the stage_end output")
    if variant == "control":
        return kwargs  # byte-identical tool output
    payload = json.loads(last["output"])
    if payload.get("result") != review:
        raise ValueError("recorded tool output does not hold the review text")
    payload["result"] = VARIANTS[variant](review)
    last["output"] = json.dumps(payload, indent=2, ensure_ascii=False)
    return kwargs


def send(kwargs: dict, summaries: bool) -> dict:
    body = {k: v for k, v in kwargs.items() if k != "extra_body"}
    body.update(kwargs.get("extra_body") or {})
    body["stream"] = False
    if summaries:
        body["reasoning"] = {**(body.get("reasoning") or {}), "summary": "auto"}
    data = json.dumps(body).encode()
    for attempt in range(6):
        req = urllib.request.Request(URL, data=data, headers={
            "Authorization": f"Bearer {os.environ['CAO_API_KEY']}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(30 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(30 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def summarize_output(resp: dict) -> dict:
    out = {"model": resp.get("model"), "usage": resp.get("usage"), "next": [], "reasoning_summary": []}
    for o in resp.get("output", []):
        if o.get("type") == "function_call":
            out["next"].append({"type": "function_call", "name": o.get("name"), "arguments": o.get("arguments")})
        elif o.get("type") == "message":
            out["next"].append({"type": "message", "text": " ".join(c.get("text", "") for c in o.get("content", []) if isinstance(c, dict))})
        elif o.get("type") == "reasoning":
            out["reasoning_summary"] += [s.get("text", "") for s in o.get("summary") or []]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["first_strict", "first_error"], required=True)
    ap.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-summaries", action="store_true")
    args = ap.parse_args()
    items = [json.loads(l) for l in open(HERE / "dataset" / "items.jsonl")]
    if args.target == "first_strict":
        items = [i for i in items if i.get("has_strict") and i.get("request_copy")]
    else:
        items = [i for i in items if (i.get("first_error_flag") or {}).get("request_copy")]
    out_dir = HERE / "replays" / args.target / args.variant
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(i, k) for i in sorted(items, key=lambda x: x["id"]) for k in range(1, args.samples + 1)
            if not (out_dir / f"{i['id']}.s{k}.json").exists()][: args.limit]
    print(f"items {len(items)}, jobs {len(jobs)} -> {out_dir}", flush=True)

    def work(job: tuple) -> None:
        item, k = job
        try:
            kwargs, review = load_request(item, args.target)
            resp = send(apply_variant(kwargs, review, args.variant), not args.no_summaries)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {item['id']} s{k}: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
            return
        row = {"id": item["id"], "target": args.target, "variant": args.variant, "sample": k,
               "summaries": not args.no_summaries, **summarize_output(resp)}
        (out_dir / f"{item['id']}.s{k}.json").write_text(json.dumps(row, ensure_ascii=False, indent=1))
        names = [n.get("name") or "message" for n in row["next"]]
        print(f"ok {item['id']} s{k} {names}", flush=True)

    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(work, jobs))


if __name__ == "__main__":
    main()
