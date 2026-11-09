"""Summarise the replay experiment: does a variant change whether the agent commits to the feedback?

Reads judgments/<target>/<arm>.jsonl and dataset/items.jsonl. Scores each step
yes = 1, partly = 0.5, no = 0, averages over an item's samples, and compares
arms on the same items (paired bootstrap over items).

Usage (from harvey-ahe-project/): python3 analysis/feedback-replay/summarize.py --target first_strict --arms original control wrapped
"""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
SCORE = {"yes": 1.0, "partly": 0.5, "no": 0.0}


def load(target: str, arm: str) -> dict[str, list[dict]]:
    path = HERE / "judgments" / target / f"{arm}.jsonl"
    rows: dict[str, list[dict]] = collections.defaultdict(list)
    for r in map(json.loads, open(path)):
        rows[r["id"]].append(r)
    return rows


def boot(diffs: list[float], n: int = 5000) -> tuple[float, float]:
    rng = random.Random(0)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    args = ap.parse_args()
    items = {i["id"]: i for i in map(json.loads, open(HERE / "dataset" / "items.jsonl"))}
    data = {a: load(args.target, a) for a in args.arms}
    common = sorted(set.intersection(*(set(d) for d in data.values())))
    out = [f"# Replay results: {args.target}", "", f"Items with every arm judged: {len(common)}", "",
           "| Arm | steps | commits yes | partly | no | mean score | moves: reopen / new / other stage |", "|---|---|---|---|---|---|---|"]
    mean = {}
    for a in args.arms:
        rows = [r for i in common for r in data[a][i]]
        c = collections.Counter(r["commits"] for r in rows)
        mv = collections.Counter(r["move"] for r in rows)
        n = len(rows)
        mean[a] = {i: sum(SCORE.get(r["commits"], 0) for r in data[a][i]) / len(data[a][i]) for i in common}
        out.append(f"| {a} | {n} | {c['yes'] / n:.0%} | {c['partly'] / n:.0%} | {c['no'] / n:.0%} | "
                   f"{sum(mean[a].values()) / len(common):.3f} | {mv['reopen_same_stage'] / n:.0%} / {mv['new_stage'] / n:.0%} / {mv['other_stage'] / n:.0%} |")
    out.append("")
    base = "control" if "control" in args.arms else args.arms[0]
    out += ["## Paired differences (mean score per item, 95% bootstrap CI over items)", "", "| Comparison | difference | CI |", "|---|---|---|"]
    for a in args.arms:
        if a == base:
            continue
        diffs = [mean[a][i] - mean[base][i] for i in common]
        lo, hi = boot(diffs)
        out.append(f"| {a} − {base} | {sum(diffs) / len(diffs):+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
    out.append("")
    # splits
    def group_rows(name: str, key) -> None:
        groups = collections.defaultdict(list)
        for i in common:
            groups[key(items[i])].append(i)
        out.extend([f"## By {name}", "", "| Group | items | " + " | ".join(args.arms) + " |", "|---|---|" + "---|" * len(args.arms)])
        for g, ids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(ids) < 8:
                continue
            out.append(f"| {g} | {len(ids)} | " + " | ".join(f"{sum(mean[a][i] for i in ids) / len(ids):.2f}" for a in args.arms) + " |")
        out.append("")
    if args.target == "first_strict":
        group_rows("whether the agent eventually followed it in the recorded run", lambda it: (it.get("original_followed") or {}).get("followed"))
        group_rows("stage", lambda it: "agent-defined (new)" if str(it.get("stage_label", "")).startswith("new:") else it.get("stage_label"))
        group_rows("review number in the run", lambda it: "1st review" if it.get("review_no") == 1 else "2nd-3rd" if it.get("review_no", 0) <= 3 else "4th+")
    else:
        group_rows("reviewer outcome (annotation)", lambda it: it["first_error_flag"].get("critic"))
        group_rows("first error kind", lambda it: it["first_error_flag"].get("kind"))
    group_rows("run outcome", lambda it: "passed" if it["run_all_pass"] else "failed")
    text = "\n".join(out) + "\n"
    (HERE / f"results_{args.target}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
