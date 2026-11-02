"""Build the harness's stage reference from the training-run error catalog.

Inputs (training runs only):
- `annotations/*.json`: per run, its stages and the errors placed at each
  stage (`first_error`, `other_errors`: stage, kind, why);
- `taxonomy.md`: stage definitions;
- `logs/<task>_T<k>.txt`: tool calls, for the tools used in each stage.

Catalogs are given oldest round first; the last one is the latest round.
For each declarable stage, error kinds placed at that stage are split into:
- active failures: kinds seen in >= MIN_RUNS runs of the latest round
  (no cap; more than SPLIT_WARN kinds prints a hint that the stage may need
  splitting by sub-activity);
- policy: kinds that were common (>= MIN_RUNS in one earlier round, or pooled
  over the earlier rounds) and have
  dropped to <= POLICY_RATIO of that peak (or <= 1 run) in the latest round.
  The guidance worked, so the lesson is kept as a short positive rule shown
  when the stage starts, instead of being dropped (no ping-pong);
- dropped: kinds that were never common.
A kind that had dropped in an earlier round and is common again in the
latest one is printed as a REGRESSION and kept active.
An LLM writes one generic sentence per active kind and one rule per policy
kind, from that stage's own error descriptions and passing-run notes. The
output is regenerated from the catalogs each time, never appended.

Writes `stage_reference.json`, the "## Stage protocol" list in the harness
system prompt, and the stage enum of the `stage_start` tool schema.

Usage (repo root, CAO gateway running, CAO_API_KEY exported):
  python3 harvey-ahe-project/scripts/stage/build_stage_reference.py \
      --catalog harvey-ahe-project/analysis/stages-train harvey-ahe-project/analysis/stages-train-c29 \
                harvey-ahe-project/analysis/stages-train-c30 \
      --taxonomy harvey-ahe-project/analysis/stages-train-c30/taxonomy.md \
      --harness harvey-ahe-project/harness_stage_r3
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import urllib.request
from pathlib import Path

MIN_RUNS = 2
POLICY_RATIO = 0.25
SPLIT_WARN = 5
STEER_MIN = 5          # specific critic flags ignored at a stage in the latest round
STEER_MAX_ENDORSED = 0.25  # gate only if review-endorsed <= this share of specific-ignored
MIN_RELABELS = 5  # declared-vs-actual confusions shown for a stage
DECLARED = re.compile(r"declared:\s*([^;.(]+?)(?:\s*\(|[;.]|$)")
EXAMPLES = 2
NOT_DECLARABLE = {"Finish the run"}
MODEL = os.environ.get("STAGE_BUILD_MODEL", "claude-sonnet-5-5")
URL = os.environ.get("STAGE_BUILD_URL", "http://127.0.0.1:4141/v1/chat/completions")
CALL = re.compile(r"\[(\d+)\] CALL (\w+)")
NO_FAILURES = "No recurring failures (seen in two or more runs) were recorded at this stage in the latest training round."

SYSTEM = (
    "You write guidance for one stage of an AI agent's work, from annotated training runs of that agent. "
    "Use ONLY the material given. Write generically: no matter numbers, client or party names, legal topics "
    "(claim, deal, document or practice types specific to a task) or request wording from any task; describe "
    "behaviour that would apply to any request. Do not mention other stages' failures. Reply with JSON only."
)


def chat(user: str) -> dict:
    body = json.dumps({"model": MODEL, "max_tokens": 1500, "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}).encode()
    request = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {os.environ.get('CAO_API_KEY', '')}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        text = json.load(response)["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def definitions(taxonomy: Path) -> dict[str, str]:
    section = taxonomy.read_text().split("## Stages", 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in line.split("|")[1:-1]] for line in section.splitlines() if line.startswith("| ")]
    return {r[0]: r[1] for r in rows[1:] if len(r) > 1 and not r[0].startswith("---")}


def collect(catalogs: list[Path]):
    errors = collections.defaultdict(lambda: collections.defaultdict(list))  # stage -> kind -> [(round, why)]
    notes = collections.defaultdict(list)  # stage -> passing-run stage notes
    tools = collections.defaultdict(collections.Counter)  # stage -> tool counts in passing runs
    confused = collections.defaultdict(collections.Counter)  # declared stage -> actual stage counts
    critic = collections.defaultdict(collections.Counter)  # stage -> critic outcomes in the latest round
    paths = [(i, c, p) for i, c in enumerate(catalogs) for p in sorted((c / "annotations").glob("*.json"))]
    for rnd, catalog, path in paths:
        task = json.loads(path.read_text())
        for run in task["runs"]:
            for stage in run["stages"]:
                m = DECLARED.match(stage.get("note", ""))
                if m and m.group(1).strip() != stage["stage"]:
                    confused[m.group(1).strip()][stage["stage"]] += 1
            for error in ([run["first_error"]] if run.get("first_error") else []) + (run.get("other_errors") or []):
                if error["kind"].startswith("NEW: "):
                    continue
                errors[error["stage"]][error["kind"]].append((rnd, error["why"]))
                if rnd == len(catalogs) - 1 and error.get("critic"):
                    specific = "specific flag" in (error.get("critic_note") or "")
                    critic[error["stage"]][error["critic"] + ("/specific" if specific else "")] += 1
            if not run["all_pass"]:
                continue
            log = (catalog / "logs" / f"{task['task']}_T{run['trial']}.txt").read_text().splitlines()
            calls = [(int(m.group(1)), m.group(2)) for m in map(CALL.match, log) if m]
            for stage in run["stages"]:
                notes[stage["stage"]].append(re.sub(r"^declared: [^;.]*[;.]\s*", "", stage.get("note", "")))
                tools[stage["stage"]].update(t for n, t in calls if stage["start"] <= n <= stage["end"])
    return errors, notes, tools, confused, critic


def classify(kinds: dict[str, list[tuple[int, str]]], rounds: int) -> tuple[list, list, list]:
    """Split a stage's error kinds into active, policy and regression lists."""
    active, policy, regressions = [], [], []
    last = rounds - 1
    for kind, items in kinds.items():
        per = collections.Counter(r for r, _ in items)
        latest = per[last]
        earlier = [per[r] for r in range(last)]
        peak = max(earlier, default=0)
        dropped_before = any(per[r] <= max(1, POLICY_RATIO * max(earlier[:r] or [0])) and max(earlier[:r] or [0]) >= MIN_RUNS
                             for r in range(1, last))
        if latest >= MIN_RUNS:
            active.append((kind, items, latest))
            if dropped_before:
                regressions.append(kind)
        elif (peak >= MIN_RUNS or sum(earlier) >= MIN_RUNS) and latest <= max(1, POLICY_RATIO * peak):
            # "Was common": >= MIN_RUNS in one earlier round, or pooled over the earlier rounds.
            policy.append((kind, items, max(peak, sum(earlier))))
    active.sort(key=lambda t: -t[2])
    policy.sort(key=lambda t: -t[2])
    return active, policy, regressions


def build_stage(name: str, definition: str, kinds: dict[str, list], notes: list[str], tools: collections.Counter,
                confused: collections.Counter, rounds: int) -> dict:
    active, policy, regressions = classify(kinds, rounds)
    def whys(items, prefer_latest):
        chosen = [w for r, w in items if r == rounds - 1] if prefer_latest else []
        return (chosen or [w for _, w in items])[:25]
    active_text = "\n".join(f"KIND {k} ({n} runs in the latest round):\n" + "\n".join(f"- {x}" for x in whys(i, True))
                            for k, i, n in active) or "(none)"
    policy_text = "\n".join(f"KIND {k} (peak {n} runs, now rare):\n" + "\n".join(f"- {x}" for x in whys(i, False))
                            for k, i, n in policy) or "(none)"
    notes_text = "\n".join(f"- {n}" for n in notes[:30]) or "(no passing run used this stage)"
    answer = chat(
        f"STAGE: {name}\nDEFINITION (from the annotation taxonomy): {definition}\n\n"
        f"CURRENT ERRORS PLACED AT THIS STAGE (latest round):\n{active_text}\n\n"
        f"ERRORS THAT WERE COMMON HERE BEFORE AND ARE NOW RARE (the guidance worked):\n{policy_text}\n\n"
        f"WHAT PASSING RUNS DID IN THIS STAGE (annotator notes):\n{notes_text}\n\n"
        "Return JSON with keys:\n"
        '"purpose": one sentence, what the stage is for (no failure information);\n'
        '"when_to_use": one sentence, when to use it, from the passing-run notes (or "" if none);\n'
        f'"failure_patterns": one generic sentence per CURRENT KIND, in the same order ({len(active)} items);\n'
        f'"policy": one short imperative rule per NOW-RARE KIND, saying what to keep doing so it stays rare, '
        f'in the same order ({len(policy)} items);\n'
        '"passing_runs": one or two sentences on what passing runs did differently with respect to the CURRENT '
        'failures, only if the notes show it, else "";\n'
        f'"examples": up to {EXAMPLES} short generic descriptions of what passing runs did inside this stage.'
    )
    if len(active) > SPLIT_WARN:
        print(f"  SPLIT HINT: {name} has {len(active)} recurring error kinds; check whether they belong to different sub-activities")
    for kind in regressions:
        print(f"  REGRESSION: {name}: '{kind}' had become rare and is common again")
    return {
        "purpose": answer["purpose"],
        "when_to_use": answer.get("when_to_use") or "",
        "typical_tools": ", ".join(t for t, _ in tools.most_common(4)),
        "examples_from_successful_runs": answer.get("examples") or [],
        "expected_activity": definition,
        "policy": answer.get("policy") or [],
        "policy_kinds": {k: n for k, _, n in policy},
        "failure_patterns": answer["failure_patterns"] if active else [NO_FAILURES],
        "failure_kinds": {k: n for k, _, n in active},
        # A contrast only exists for failures recorded at this stage (rule A8).
        "passing_runs": (answer.get("passing_runs") or "No pass/fail contrast was recorded.") if active else "",
        # Stages the agent declared this one for while actually doing other work (annotated relabels).
        "often_confused_with": {s: n for s, n in confused.most_common(2) if n >= MIN_RELABELS},
    }


def write_prompt(prompt: Path, stages: dict) -> None:
    text = prompt.read_text()
    start, end = text.index("## Stage protocol"), text.index("These are a menu, not a fixed sequence")
    lines = ["## Stage protocol", "", "Work in declared stages. A stage is a stretch of work with one purpose and a",
             "concrete goal. The stages seen in this kind of task, with when to use them,",
             "the tools typically used in them, and examples of what successful runs did in", "them:", ""]
    for i, (name, s) in enumerate(stages.items(), 1):
        lines.append(f"{i}. **{name}**: {s['purpose']}")
        if s["when_to_use"]:
            lines.append(f"   - When: {s['when_to_use']}")
        if s["typical_tools"]:
            lines.append(f"   - Typical tools: {s['typical_tools']}.")
        lines += [f"   - Example: {e}" for e in s["examples_from_successful_runs"]]
        for other in s.get("often_confused_with", {}):
            lines.append(f"   - Not for: {stages[other]['purpose'][0].lower() + stages[other]['purpose'][1:]} "
                         f"That is **{other}** (runs often mislabelled it as this stage).")
    prompt.write_text(text[:start] + "\n".join(lines) + "\n\n" + text[end:])


def write_enum(tool_yaml: Path, names: list[str]) -> None:
    text = tool_yaml.read_text()
    enum = "      enum:\n" + "".join(f"      - {n}\n" for n in names) + "      - new\n"
    tool_yaml.write_text(re.sub(r"      enum:\n(?:      - .*\n)+", enum, text, count=1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, nargs="+", required=True,
                        help="one or more catalog folders (one per round); the first one's taxonomy.md is used unless --taxonomy")
    parser.add_argument("--taxonomy", type=Path)
    parser.add_argument("--harness", type=Path, required=True)
    args = parser.parse_args()
    out = args.harness / "middleware" / "stage_reference.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    defs = definitions(args.taxonomy or args.catalog[0] / "taxonomy.md")
    errors, notes, tools, confused, critic = collect(args.catalog)
    stages = {name: build_stage(name, d, errors.get(name, {}), notes.get(name, []), tools.get(name, collections.Counter()),
                                confused.get(name, collections.Counter()), len(args.catalog))
              for name, d in defs.items() if name not in NOT_DECLARABLE}
    # Steering gate: a stage whose specific critic flags were often ignored, while its reviews rarely
    # pushed toward the error, must resolve those flags before the run moves on to another stage.
    for name, st in stages.items():
        c = critic.get(name, collections.Counter())
        ignored, endorsed = c["flagged-ignored/specific"], c["review-endorsed"] + c["review-endorsed/specific"]
        st["steering_gate"] = ignored >= STEER_MIN and endorsed <= STEER_MAX_ENDORSED * ignored
        st["steering_evidence"] = {"specific_flags_ignored": ignored, "review_endorsed": endorsed}
        if st["steering_gate"]:
            print(f"  STEERING GATE: {name} (specific flags ignored {ignored}, review-endorsed {endorsed})")
    sno = dict(old.get("surfaced_not_opened") or {})  # entity, entity_regex, max: per-benchmark settings
    sno["show_at_stages"] = [n for n, s in stages.items() if "surfaced-not-opened" in s["failure_kinds"]]
    sno["_why"] = ("Run fact for the critic: entities that appeared in the agent's search results but were never "
                   "opened. Shown only at the stages whose most common errors include 'surfaced-not-opened' "
                   "in the training catalog; disabled if no stage has it.")
    sno["enabled"] = bool(sno["show_at_stages"]) and bool(sno.get("entity_regex"))
    reference = {
        "_source": (f"Generated by scripts/stage/build_stage_reference.py from {', '.join(map(str, args.catalog))} (training runs only). "
                    f"Per stage: active failures = kinds in >= {MIN_RUNS} runs of the latest round; policy = kinds that "
                    f"were common earlier and fell to <= {POLICY_RATIO:.0%} of their peak. Regenerated, never appended."),
        "surfaced_not_opened": sno,
        "stages": stages,
    }
    out.write_text(json.dumps(reference, indent=2, ensure_ascii=False) + "\n")
    write_prompt(args.harness / "systemprompt.md", stages)
    write_enum(args.harness / "tool_descriptions" / "stage_start.tool.yaml", list(stages))
    for name, s in stages.items():
        print(f"{name}: active {s['failure_kinds'] or '-'} | policy {s['policy_kinds'] or '-'}")
    print("surfaced-not-opened shown at:", sno["show_at_stages"])


if __name__ == "__main__":
    main()
