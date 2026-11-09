"""Aggregate the feedback-uptake data into markdown tables.

Inputs (analysis/feedback-uptake/data/): reviews.jsonl, runs.jsonl,
case_labels.jsonl (first-error cases), flag_labels.jsonl (sampled reviews).
Writes analysis/feedback-uptake/data/tables.md.

Usage (from harvey-ahe-project/): python3 analysis/feedback-uptake/analyze.py
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

DATA = Path("analysis/feedback-uptake/data")
NOT_OPENED = {"surfaced-not-opened", "listed-document-not-opened", "mistyped-path"}
JUDGEMENT = {"over-inclusion", "under-inclusion", "misstated-facts", "missing-detail", "missing-identifier",
             "hedged-answer", "incomplete-population", "miscount"}


def load(name: str) -> list[dict]:
    path = DATA / name
    return [json.loads(l) for l in open(path)] if path.exists() else []


def pct(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "–"


def dist(rows: list[dict], key: str, order: list | None = None) -> list[str]:
    c = collections.Counter(str(r.get(key)) for r in rows)
    keys = order or [k for k, _ in c.most_common()]
    return [f"| {k} | {pct(c[k], len(rows))} |" for k in keys if c[k]]


def family(kind: str) -> str:
    return "not opened" if kind in NOT_OPENED else "judgement" if kind in JUDGEMENT else "search/scan"


def main() -> None:
    R, U, C, F = load("reviews.jsonl"), load("runs.jsonl"), load("case_labels.jsonl"), load("flag_labels.jsonl")
    sample_path = DATA / "flag_sample.json"
    if sample_path.exists():  # only the current stratified sample
        keep = {tuple(k) for k in json.loads(sample_path.read_text())}
        F = [r for r in F if (r["round"], r["task"], r["trial"], r["review_idx"]) in keep]
    out: list[str] = ["# Feedback uptake: tables", ""]
    failing = [u for u in U if not u["all_pass"]]
    out += [f"Training runs r2+r3: {len(U)}; failing: {len(failing)}; reviews parsed: {len(R)}.", ""]

    # --- first-error cases (LLM labels)
    out += ["## A. First-error cases where the reviewer flagged the error (LLM-labelled)", "",
            f"Cases labelled: {len(C)}.", ""]
    for key, title in [("flag_correct", "Was the reviewer right?"), ("names_needed_item", "Did the flag name the needed item?"),
                       ("flag_part", "Where in the review"), ("advice_shape", "Shape of the ask"),
                       ("timing", "Timing vs the agent's decision"), ("agent_next", "Agent's next step"),
                       ("next_goal_addresses_flag", "Next goal addresses the flag"), ("eventual_action", "Ever acted on it"),
                       ("agent_disputed", "Agent argued against it"), ("summary_overclaims", "Agent's summary overclaimed"),
                       ("why_not_followed", "Why not followed"), ("would_fix_if_followed", "Would following it fix the first error"),
                       ("would_pass_if_followed", "Would the run then pass")]:
        out += [f"### {title} (`{key}`)", "", "| Value | Cases |", "|---|---|", *dist(C, key), ""]
    # splits
    out += ["### Splits", "", "| Group | n | flag right | named item | acted fully | acted partly | never acted | would pass if followed |", "|---|---|---|---|---|---|---|---|"]

    def split(name: str, rows: list[dict]) -> None:
        n = len(rows)
        if not n:
            return
        f = lambda k, v: sum(1 for r in rows if r.get(k) == v)  # noqa: E731
        out.append(f"| {name} | {n} | {f('flag_correct', 'yes') / n:.0%} | {f('names_needed_item', True) / n:.0%} | "
                   f"{f('eventual_action', 'full') / n:.0%} | {f('eventual_action', 'partial') / n:.0%} | {f('eventual_action', 'none') / n:.0%} | "
                   f"{f('would_pass_if_followed', 'likely') / n:.0%} |")
    split("all", C)
    for ft in ("specific", "generic"):
        split(f"annotation: {ft} flag", [r for r in C if r.get("flag_type") == ft])
    for cr in ("flagged-ignored", "flagged-fixed-partly"):
        split(f"annotation: {cr}", [r for r in C if r["critic"] == cr])
    for fam in ("not opened", "judgement", "search/scan"):
        split(f"error family: {fam}", [r for r in C if family(r["kind"]) == fam])
    for t in ("before_decision", "after_decision"):
        split(f"timing: {t}", [r for r in C if r.get("timing") == t])
    for s in ("one_action", "several_actions", "vague"):
        split(f"ask: {s}", [r for r in C if r.get("advice_shape") == s])
    for rnd in ("r2", "r3"):
        split(f"round {rnd}", [r for r in C if r["round"] == rnd])
    out.append("")
    # headroom
    head = [r for r in C if r.get("flag_correct") == "yes" and r.get("would_fix_if_followed") == "yes" and r.get("would_pass_if_followed") == "likely"]
    out += ["### Headroom", "",
            f"Cases where the flag was right, following it would fix the first error, and the run would likely pass: **{len(head)}** "
            f"of {len(C)} labelled cases ({len(head) / max(len(C), 1):.0%}); {len(head) / len(U):.1%} of all {len(U)} r2+r3 runs "
            f"(all-pass was {sum(u['all_pass'] for u in U) / len(U):.1%}).", ""]
    hc = collections.Counter(r["why_not_followed"] for r in head)
    out += ["| Why not followed (headroom cases) | n |", "|---|---|", *[f"| {k} | {v} |" for k, v in hc.most_common()], ""]

    # --- flag-level sample
    flags = [dict(fl, **{k: r[k] for k in ("label", "verdict", "run_all_pass", "n_flags", "review_chars", "next_action", "agent_claim")})
             for r in F for fl in r.get("flags", [])]
    out += ["## B. Flag-level uptake in a random sample of reviews (LLM-labelled; half from passing, half from failing runs)", "",
            f"Reviews: {len(F)}; flags: {len(flags)}.", "",
            "| Group | flags | acted yes | partly | no | already planned |", "|---|---|---|---|---|---|"]

    def frow(name: str, rows: list[dict]) -> None:
        n = len(rows)
        if not n:
            return
        g = lambda v: sum(1 for r in rows if r.get("acted_on") == v)  # noqa: E731
        out.append(f"| {name} | {n} | {g('yes') / n:.0%} | {g('partly') / n:.0%} | {g('no') / n:.0%} | "
                   f"{sum(1 for r in rows if r.get('agent_already_planned')) / n:.0%} |")
    frow("all", flags)
    for v in (True, False):
        frow(f"specific={v}", [f for f in flags if f.get("specific") is v])
    for v in (True, False):
        frow(f"concrete action={v}", [f for f in flags if f.get("concrete_action") is v])
    frow("specific + concrete, not already planned", [f for f in flags if f.get("specific") and f.get("concrete_action") and not f.get("agent_already_planned")])
    for p in (1, 2, 3):
        frow(f"position {p} in the flag list", [f for f in flags if f.get("n") == p])
    frow("position 4+", [f for f in flags if (f.get("n") or 0) >= 4])
    for lo, hi in ((1, 2), (2, 4), (4, 99)):
        frow(f"review has {lo}-{hi - 1} flags", [f for f in flags if lo <= f["n_flags"] < hi])
    for v in ("partly", "no"):
        frow(f"reviewer verdict {v}", [f for f in flags if f["verdict"] == v])
    for v in (True, False):
        frow(f"run passed={v}", [f for f in flags if f["run_all_pass"] is v])
    for a in ("reopen", "new", "other"):
        frow(f"agent's next move: {a}", [f for f in flags if f["next_action"] == a])
    group = lambda label: "agent-defined (new) stages" if label.startswith("new:") else label  # noqa: E731
    stages = collections.Counter(group(f["label"]) for f in flags)
    for s, n in stages.most_common():
        if n >= 15:
            frow(f"stage: {s}", [f for f in flags if group(f["label"]) == s])
    out.append("")
    hw = collections.Counter(f.get("how") for f in flags if f.get("acted_on") in ("yes", "partly"))
    out += ["| How acted-on flags were acted on | n |", "|---|---|", *[f"| {k} | {v} |" for k, v in hw.most_common()], ""]
    out += ["| Recommendation followed (review level) | reviews |", "|---|---|", *dist(F, "recommendation_followed", ["yes", "partly", "no"]), ""]
    out += ["| Next goal driven by the review | reviews |", "|---|---|", *dist(F, "next_goal_driven_by_review", ["yes", "partly", "no"]), ""]

    # --- script-level: named unopened needed matters
    out += ["## C. Script measures over all reviews", ""]
    named = [r for r in R if r["named_unopened"]]
    out += [f"Reviews naming at least one matter the agent had not opened or listed: {len(named)}; one of them opened in the next stage: "
            f"{pct(sum(bool(r['named_unopened_opened_next_stage']) for r in named), len(named))}; at any later point: "
            f"{pct(sum(bool(r['named_unopened_opened_later']) for r in named), len(named))}.", ""]
    # times a needed matter is named before it is opened
    per = collections.defaultdict(list)  # (run, matter) -> list of (review_no, opened_next, opened_later)
    for r in R:
        for m in r["named_unopened_needed"]:
            per[(r["round"], r["task"], r["trial"], m)].append((r["review_no"], m in r["named_unopened_opened_next_stage"], m in r["named_unopened_opened_later"]))
    times = collections.Counter()
    never = 0
    for key, rows in per.items():
        rows.sort()
        if not rows[0][2]:
            never += 1
            continue
        k = next((i + 1 for i, row in enumerate(rows) if row[1]), None)
        times[k if k is not None else "opened without a prompt in the next stage"] += 1
    out += [f"Needed matters named by a review while unopened: {len(per)}. Never opened afterwards: {never}.", "",
            "| Reviews naming it before the agent opened it in the following stage | needed matters |", "|---|---|",
            *[f"| {k} | {v} |" for k, v in sorted(times.items(), key=lambda kv: (isinstance(kv[0], str), kv[0]))], ""]
    (DATA / "tables.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
