"""Build the harness's stage reference from the training-run error catalog.

Inputs (training runs only):
- `annotations/*.json`: per run, its stages and the errors placed at each
  stage (`first_error`, `other_errors`: stage, kind, why);
- `taxonomy.md`: stage definitions;
- `logs/<task>_T<k>.txt`: tool calls, for the tools used in each stage.

For each declarable stage it keeps only the most common error kinds placed
at that stage (at most TOP_KINDS, each seen in at least MIN_RUNS runs), and
an LLM writes one generic sentence per kind from that stage's own error
descriptions. The output is regenerated from the whole catalog each time, so
it never grows by appending: after each evolution round, add the new
annotated training runs to the catalog and rebuild.

Writes `stage_reference.json`, the "## Stage protocol" list in the harness
system prompt, and the stage enum of the `stage_start` tool schema.

Usage (repo root, CAO gateway running, CAO_API_KEY exported):
  python3 harvey-ahe-project/scripts/stage/build_stage_reference.py \
      --catalog harvey-ahe-project/analysis/stages-train harvey-ahe-project/analysis/stages-train-c29 \
      --taxonomy harvey-ahe-project/analysis/stages-train-c29/taxonomy.md \
      --harness harvey-ahe-project/harness_stage_r2
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import urllib.request
from pathlib import Path

TOP_KINDS = 4
MIN_RUNS = 2
MIN_RELABELS = 5  # declared-vs-actual confusions shown for a stage
DECLARED = re.compile(r"declared:\s*([^;.(]+?)(?:\s*\(|[;.]|$)")
EXAMPLES = 2
NOT_DECLARABLE = {"Finish the run"}
MODEL = os.environ.get("STAGE_BUILD_MODEL", "claude-sonnet-5-5")
URL = os.environ.get("STAGE_BUILD_URL", "http://127.0.0.1:4141/v1/chat/completions")
CALL = re.compile(r"\[(\d+)\] CALL (\w+)")
NO_FAILURES = "No recurring failures (seen in two or more runs) were recorded at this stage in the training runs."

SYSTEM = (
    "You write guidance for one stage of an AI agent's work, from annotated training runs of that agent. "
    "Use ONLY the material given. Write generically: no matter numbers, client or party names, legal topics "
    "or request wording from any task. Do not mention other stages' failures. Reply with JSON only."
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
    errors = collections.defaultdict(lambda: collections.defaultdict(list))  # stage -> kind -> [why]
    notes = collections.defaultdict(list)  # stage -> passing-run stage notes
    tools = collections.defaultdict(collections.Counter)  # stage -> tool counts in passing runs
    confused = collections.defaultdict(collections.Counter)  # declared stage -> actual stage counts
    paths = [(c, p) for c in catalogs for p in sorted((c / "annotations").glob("*.json"))]
    for catalog, path in paths:
        task = json.loads(path.read_text())
        for run in task["runs"]:
            for stage in run["stages"]:
                m = DECLARED.match(stage.get("note", ""))
                if m and m.group(1).strip() != stage["stage"]:
                    confused[m.group(1).strip()][stage["stage"]] += 1
            for error in ([run["first_error"]] if run.get("first_error") else []) + (run.get("other_errors") or []):
                if error["kind"].startswith("NEW: "):
                    continue
                errors[error["stage"]][error["kind"]].append(error["why"])
            if not run["all_pass"]:
                continue
            log = (catalog / "logs" / f"{task['task']}_T{run['trial']}.txt").read_text().splitlines()
            calls = [(int(m.group(1)), m.group(2)) for m in map(CALL.match, log) if m]
            for stage in run["stages"]:
                notes[stage["stage"]].append(re.sub(r"^declared: [^;.]*[;.]\s*", "", stage.get("note", "")))
                tools[stage["stage"]].update(t for n, t in calls if stage["start"] <= n <= stage["end"])
    return errors, notes, tools, confused


def build_stage(name: str, definition: str, kinds: dict[str, list[str]], notes: list[str], tools: collections.Counter,
                confused: collections.Counter) -> dict:
    top = [(k, w) for k, w in sorted(kinds.items(), key=lambda kv: -len(kv[1])) if len(w) >= MIN_RUNS][:TOP_KINDS]
    errors_text = "\n".join(f"KIND {k} ({len(w)} runs):\n" + "\n".join(f"- {x}" for x in w[:25]) for k, w in top) or "(none)"
    notes_text = "\n".join(f"- {n}" for n in notes[:30]) or "(no passing run used this stage)"
    answer = chat(
        f"STAGE: {name}\nDEFINITION (from the annotation taxonomy): {definition}\n\n"
        f"ERRORS PLACED AT THIS STAGE IN FAILING RUNS, most common kinds only:\n{errors_text}\n\n"
        f"WHAT PASSING RUNS DID IN THIS STAGE (annotator notes):\n{notes_text}\n\n"
        "Return JSON with keys:\n"
        '"purpose": one sentence, what the stage is for (no failure information);\n'
        '"when_to_use": one sentence, when to use it, from the passing-run notes (or "" if none);\n'
        f'"failure_patterns": one generic sentence per KIND above, in the same order ({len(top)} items);\n'
        '"passing_runs": one or two sentences on what passing runs did differently with respect to those '
        'failures, only if the notes show it, else "";\n'
        f'"examples": up to {EXAMPLES} short generic descriptions of what passing runs did inside this stage.'
    )
    return {
        "purpose": answer["purpose"],
        "when_to_use": answer.get("when_to_use") or "",
        "typical_tools": ", ".join(t for t, _ in tools.most_common(4)),
        "examples_from_successful_runs": answer.get("examples") or [],
        "expected_activity": definition,
        "failure_patterns": answer["failure_patterns"] if top else [NO_FAILURES],
        "failure_kinds": {k: len(w) for k, w in top},
        # A contrast only exists for failures recorded at this stage (rule A8).
        "passing_runs": (answer.get("passing_runs") or "No pass/fail contrast was recorded.") if top else "",
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
    errors, notes, tools, confused = collect(args.catalog)
    stages = {name: build_stage(name, d, errors.get(name, {}), notes.get(name, []), tools.get(name, collections.Counter()),
                                confused.get(name, collections.Counter()))
              for name, d in defs.items() if name not in NOT_DECLARABLE}
    sno = dict(old.get("surfaced_not_opened") or {})  # entity, entity_regex, max: per-benchmark settings
    sno["show_at_stages"] = [n for n, s in stages.items() if "surfaced-not-opened" in s["failure_kinds"]]
    sno["_why"] = ("Run fact for the critic: entities that appeared in the agent's search results but were never "
                   "opened. Shown only at the stages whose most common errors include 'surfaced-not-opened' "
                   "in the training catalog; disabled if no stage has it.")
    sno["enabled"] = bool(sno["show_at_stages"]) and bool(sno.get("entity_regex"))
    reference = {
        "_source": (f"Generated by scripts/stage/build_stage_reference.py from {', '.join(map(str, args.catalog))} (training runs only). "
                    f"Per stage: the {TOP_KINDS} most common error kinds placed at that stage (each in >= {MIN_RUNS} runs). "
                    "Regenerated, never appended, after each round."),
        "surfaced_not_opened": sno,
        "stages": stages,
    }
    out.write_text(json.dumps(reference, indent=2, ensure_ascii=False) + "\n")
    write_prompt(args.harness / "systemprompt.md", stages)
    write_enum(args.harness / "tool_descriptions" / "stage_start.tool.yaml", list(stages))
    for name, s in stages.items():
        print(f"{name}: {s['failure_kinds'] or 'no recurring failures'}")
    print("surfaced-not-opened shown at:", sno["show_at_stages"])


if __name__ == "__main__":
    main()
