"""Render a stage-harness trace as a markdown timeline.

Every tool call is shown in order with its arguments, a short view of its
result, and all harness feedback in full: the stage_start notes, the
stage_end review (critic + failure patterns), refusals, stage-fit notes and
forced-continue messages.

Usage: python3 timeline.py <attempt dir> [title] > out.md
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

ARG_LIMIT = 1500
RESULT_LIMIT = 300


def text_of(content) -> str:
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def result_body(raw: str) -> str:
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            for key in ("result", "error"):
                if isinstance(value.get(key), str):
                    return value[key]
        return raw
    except Exception:
        return raw


def fence(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text.rstrip()}\n```"


def short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f" …[+{len(text) - limit} chars]"


def main() -> None:
    attempt = Path(sys.argv[1])
    title = sys.argv[2] if len(sys.argv) > 2 else attempt.parent.name
    events = [json.loads(l) for l in open(attempt / "trace.jsonl")]
    calls: dict[str, dict] = {}
    order: list[tuple[str, object]] = []
    for e in events:
        if e.get("event_type") != "message" or isinstance(e["message"], str):
            continue
        m = e["message"]
        for c in m.get("content", []):
            t = c.get("type")
            if t == "tool_use":
                calls[c["id"]] = {"idx": e["index"], "name": c["name"], "input": c["input"]}
                order.append(("call", c["id"]))
            elif t == "tool_result":
                order.append(("result", (c.get("tool_use_id"), text_of(c.get("content")))))
            elif t == "text" and str(e["index"]) not in ("0",):
                order.append(("text", (e["index"], m.get("role"), c.get("text", ""))))
    out = [f"# {title}", ""]
    scores = sorted(glob.glob(str(attempt / "grading/*/scores_judge-1.json")))
    pending: dict[str, str] = {}
    step = 0
    for kind, payload in order:
        if kind == "text":
            idx, role, text = payload
            if role == "user" and str(idx) == "1":
                out += ["## Request", "", "> " + text.replace("\n", "\n> "), ""]
            elif "[Stage protocol]" in text:
                out += [f"**Harness message [{idx}] (forced continue):**", "", fence(text), ""]
            elif text.strip():
                out += [f"*Model text [{idx}]:* {short(text.strip(), 600)}", ""]
            continue
        if kind == "call":
            info = calls[payload]
            step += 1
            name, args = info["name"], info["input"]
            if name == "stage_start":
                label = args.get("stage") if args.get("stage") != "new" else f"new: {args.get('new_stage_name')}"
                out += ["---", "", f"## ▶ {step}. stage_start: {label}  `[{info['idx']}]`", "", f"**Goal (agent):** {args.get('goal', '')}", ""]
            elif name == "stage_end":
                out += [f"### ■ {step}. stage_end  `[{info['idx']}]`", "", f"**Agent says goal reached:** {args.get('goal_reached')}", "", f"**Agent summary:** {args.get('summary', '')}", ""]
            else:
                shown = {k: v for k, v in args.items()}
                if name == "write" and isinstance(shown.get("content"), str):
                    shown["content"] = short(shown["content"], 700)
                if name == "edit":
                    for k in ("old_string", "new_string"):
                        if isinstance(shown.get(k), str):
                            shown[k] = short(shown[k], 300)
                if name == "bash" and isinstance(shown.get("command"), str):
                    body = short(shown.pop("command"), ARG_LIMIT)
                    extra = f" {json.dumps(shown, ensure_ascii=False)}" if shown else ""
                    out += [f"**{step}. `bash`**{extra}  `[{info['idx']}]`", "", fence(body, "bash"), ""]
                else:
                    out += [f"**{step}. `{name}`** `{short(json.dumps(shown, ensure_ascii=False), ARG_LIMIT)}`  `[{info['idx']}]`", ""]
            continue
        call_id, raw = payload
        info = calls.get(call_id, {"name": "?", "idx": "?"})
        body = result_body(raw)
        name = info["name"]
        if name == "stage_start":
            out += ["**Harness (stage_start result):**", "", fence(body), ""]
        elif name == "stage_end":
            out += ["**Harness review (critic + failure patterns):**", "", fence(body), ""]
        else:
            note = ""
            if "[Stage protocol]" in body:
                cut = body.find("[Stage protocol]")
                note, body = body[cut:], body[:cut]
            refused = note and "Stage check:" not in note
            if refused:
                out += [f"→ **Refused by harness:** `{note.strip()}`", ""]
            else:
                out += [f"→ result ({len(raw)} chars):", "", fence(short(body.strip(), RESULT_LIMIT)), ""]
                if note:
                    out += [f"→ **Harness stage-fit note:** {note.strip()}", ""]
    if scores:
        s = json.load(open(scores[-1]))
        out += ["---", "", f"## Judge: {s['n_passed']}/{s['n_criteria']} (all_pass = {s['all_pass']})", ""]
        for c in s["criteria_results"]:
            out.append(f"- **{c['id']} [{c['verdict']}]** {c.get('title', '')}: {c.get('reasoning', '')}")
    print("\n".join(out))


if __name__ == "__main__":
    main()
