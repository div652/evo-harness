"""Write a round-by-round markdown report of an RRSI campaign.

Reads only the campaign's own records (algorithm/rounds, checkpoints,
evaluations, costs) and never changes them.

Usage: python3 rrsi_rounds_report.py CAMPAIGN_DIR OUTPUT_MD
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

IST = timedelta(hours=5, minutes=30)


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ist(timestamp: float) -> str:
    return (datetime.fromtimestamp(timestamp, UTC) + IST).strftime("%Y-%m-%d %H:%M IST")


def metrics(campaign: Path, label: str) -> dict:
    result = load(campaign / "evaluations" / f"{label}-train" / "adapter_result.json")
    if not result:
        return {}
    m = result["summary"]["metrics"]
    return {
        "allpass": m.get("mean_dual_all_pass_rate"),
        "pooled": m.get("pooled_criterion_pass_rate"),
    }


def cost(campaign: Path, label: str) -> float | None:
    data = load(campaign / "costs" / f"{label}-train.json")
    return data.get("mean_cost_per_trial") if data else None


def fmt(value: float | None, spec: str = ".3f") -> str:
    return "–" if value is None else format(value, spec)


def candidate_record(round_dir: Path, variant: str) -> dict | None:
    """The last successful submission of a variant (after any repairs)."""

    found = sorted(
        glob.glob(str(round_dir / variant / "propose-*" / "attempt-*" / "candidate.json")),
        key=lambda p: (int(p.split("propose-")[1].split("/")[0]), p),
    )
    return load(Path(found[-1])) if found else None


def critic_verdicts(round_dir: Path, variant: str) -> list[str]:
    verdicts = []
    for path in sorted(glob.glob(str(round_dir / variant / "critic-*" / "attempt-*" / "verdict.json"))):
        verdict = load(Path(path)) or {}
        verdicts.append(verdict.get("verdict", "?"))
    return verdicts


def edits_text(record: dict | None) -> str:
    if not record:
        return "–"
    parts = []
    for edit in record.get("edits") or []:
        hypothesis = " ".join(str(edit.get("hypothesis", "")).split())
        if len(hypothesis) > 160:
            hypothesis = hypothesis[:157] + "..."
        parts.append(f"**{edit.get('component')}**: {hypothesis}")
    return "<br>".join(parts) or "–"


def main(campaign: Path, output: Path) -> None:
    calibration = load(campaign / "algorithm" / "calibration.json") or {}
    frontier = load(campaign / "algorithm" / "reports" / "frontier.json") or {}
    lines: list[str] = []
    add = lines.append
    add(f"# RRSI campaign rounds: {campaign.name}")
    add("")
    add(f"Updated {ist(datetime.now(UTC).timestamp())}. Generated from the campaign's "
        "records by `scripts/rrsi_rounds_report.py`; S is the pooled criterion pass "
        "rate on the 80 training tasks x 3 trials (RRSI's objective); all-pass is "
        "reported, not optimized; cost is catalog units per trial (evaluated agent "
        "only).")
    add("")
    base = metrics(campaign, "C0")
    add(f"- Noise band delta: **{fmt(calibration.get('delta'), '.4f')}** "
        f"(bootstrap, z = {calibration.get('z', '–')})")
    weights = calibration.get("weights") or {}
    if weights:
        add("- Selection weights: " + ", ".join(
            f"{k} {v:.4g}" for k, v in weights.items()))
    add(f"- Baseline C0: S {fmt(base.get('pooled'))}, all-pass "
        f"{fmt(base.get('allpass'))}, cost {fmt(cost(campaign, 'C0'), '.2f')}")
    path = frontier.get("accepted_path") or ["C0"]
    add(f"- Accepted path: {' -> '.join(path)}; current incumbent **{path[-1]}**")
    final = load(campaign / "final" / "final_test.json")
    if final:
        add("- Final test: " + ", ".join(
            f"{k} criterion {v['metrics'].get('pooled_criterion_pass_rate', 0):.3f} / "
            f"all-pass {v['metrics'].get('mean_dual_all_pass_rate', 0):.3f}"
            for k, v in final["test_summaries"].items()))
    add("")

    add("## Summary")
    add("")
    add("| Round | Edit budget | Stalled | Incumbent before | Winner | Incumbent S after |")
    add("|---|---|---|---|---|---|")
    round_dirs = sorted((campaign / "algorithm" / "rounds").glob("r*"))
    for round_dir in round_dirs:
        directives = load(round_dir / "directives.json") or {}
        decisions = load(round_dir / "decisions.json")
        t = int(round_dir.name[1:])
        if decisions:
            winner = decisions.get("winner") or "none"
            after = next((d["S"] for d in decisions["decisions"]
                          if d["checkpoint"] == decisions.get("winner")),
                         decisions.get("S_incumbent"))
            add(f"| {t} | {directives.get('b_t', '–')} | "
                f"{'yes' if directives.get('sigma_t') else 'no'} | "
                f"{decisions['incumbent']} ({decisions['S_incumbent']:.3f}) | "
                f"{winner} | {after:.3f} |")
        else:
            add(f"| {t} | {directives.get('b_t', '–')} | "
                f"{'yes' if directives.get('sigma_t') else 'no'} | "
                f"{directives.get('incumbent', '–')} | in progress | – |")
    add("")

    add("## Rounds")
    for round_dir in reversed(round_dirs):
        t = int(round_dir.name[1:])
        directives = load(round_dir / "directives.json") or {}
        decisions = load(round_dir / "decisions.json")
        started = os.path.getmtime(round_dir / "directives.json") if (round_dir / "directives.json").exists() else os.path.getmtime(round_dir)
        add("")
        add(f"### Round {t}" + ("" if decisions else " (in progress)"))
        add("")
        explore = directives.get("explore") or {}
        prune = [p["component"] for p in directives.get("prune_set") or []]
        add(f"Incumbent {directives.get('incumbent', '–')} "
            f"(S {fmt(directives.get('S_incumbent'))}); edit budget "
            f"{directives.get('b_t', '–')}; stalled: "
            f"{'yes' if directives.get('sigma_t') else 'no'}; untried components: "
            f"{', '.join(explore.get('untried') or []) or 'none'}; prune: "
            f"{', '.join(prune) or 'none'}.")
        if decisions:
            add(f"Decided {ist(os.path.getmtime(round_dir / 'decisions.json'))}; "
                f"winner: **{decisions.get('winner') or 'none (incumbent kept)'}**.")
        else:
            add(f"Started around {ist(started)}.")
        add("")
        add("| Variant | Checkpoint | Edits | Critic | S (dS) | All-pass | Cost (dC) | Decision |")
        add("|---|---|---|---|---|---|---|---|")
        rows = {d["variant"]: d for d in (decisions or {}).get("decisions", [])}
        variants = sorted({p.name for p in round_dir.iterdir() if p.is_dir() and len(p.name) == 1})
        for variant in variants:
            record = candidate_record(round_dir, variant)
            label = (rows.get(variant) or {}).get("checkpoint") or (record or {}).get("checkpoint")
            m = metrics(campaign, label) if label else {}
            critic = ", ".join(critic_verdicts(round_dir, variant)) or "–"
            row = rows.get(variant)
            if row and row.get("S") is not None:
                score = f"{row['S']:.3f} ({row['delta_S']:+.3f})"
                spend = f"{fmt(row.get('C'), '.2f')} ({row['delta_C']:+.0%})"
                verdict = ("**accepted**" if label == decisions.get("winner")
                           else "admissible, lost" if row["admissible"] else "rejected")
                reason = row["reason"].split(":", 1)[0]
                decision = f"{verdict}: {reason}"
            elif row:
                score, spend, decision = "–", "–", f"dropped: {row['reason'][:80]}"
            else:
                score = fmt(m.get("pooled"))
                spend = fmt(cost(campaign, label), ".2f") if label else "–"
                decision = "evaluating" if label and not m else ("drafting" if not record else "pending")
            add(f"| {variant} | {label or '–'} | {edits_text(record)} | {critic} | "
                f"{score} | {fmt(m.get('allpass'))} | {spend} | {decision} |")
    add("")
    temporary = output.with_suffix(".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, output)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
