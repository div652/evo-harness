"""Stage protocol tools: declare a stage and its goal, then close it for review.

The stage guard middleware enforces the pairing (no work outside an open
stage, no second start while one is open, no finish while one is open).
`stage_end` runs an independent critic (a different model) over the stage's
tool calls and returns its review together with the failure patterns seen at
this stage in past training runs, and asks the agent to reopen the stage or
move on.
"""

from __future__ import annotations

from typing import Any

from tools._stage_common import (
    CRITIC_MODEL,
    FIT_MODEL,
    ENTITY_NAME,
    SNO_ENABLED,
    SNO_STAGES,
    NEW_STAGE,
    STAGE_NAMES,
    chat,
    load_state,
    parse_json,
    reference,
    save_state,
    short,
)

_MAX_LOG_CHARS = 40000


def stage_start(
    stage: str,
    goal: str,
    agent_state: Any,
    new_stage_name: str | None = None,
) -> str | dict[str, str]:
    try:
        state = load_state(agent_state)
        if state.get("open"):
            # The middleware blocks this first; kept as a second line of defence.
            return {"status": "error", "error": f"Stage '{state['open']['label']}' is still open. Call stage_end first."}
        if stage != NEW_STAGE and reference(stage) is None:
            return {
                "status": "error",
                "error": f"Unknown stage '{stage}'. Use one of: {', '.join(STAGE_NAMES)}, or '{NEW_STAGE}' with new_stage_name.",
            }
        if stage == NEW_STAGE and not (new_stage_name or "").strip():
            return {"status": "error", "error": f"stage='{NEW_STAGE}' needs new_stage_name (a short descriptive name)."}
        if not (goal or "").strip():
            return {"status": "error", "error": "Give a concrete goal for this stage."}
        label = stage if stage != NEW_STAGE else f"new: {new_stage_name.strip()}"
        attempt = 1 + sum(1 for h in state["history"] if h["label"] == label)
        state["open"] = {"stage": stage, "label": label, "goal": goal.strip(), "attempt": attempt, "calls": []}
        save_state(agent_state, state)
        ref = reference(stage)
        purpose = ref["purpose"] if ref else "A stage you defined yourself."
        again = f" (attempt {attempt}: you are reopening this stage)" if attempt > 1 else ""
        lines = [f"Stage started: {label}{again}.", f"Purpose: {purpose}", f"Your goal: {goal.strip()}"]
        for other in (ref or {}).get("often_confused_with", {}):
            alt = reference(other)
            if alt:
                lines.append(
                    f"Check the label: runs often declared this stage while doing other work. If you are going to "
                    f"{alt['purpose'][0].lower() + alt['purpose'][1:]} that is the stage \"{other}\": close this "
                    "stage and start that one."
                )
        if ref and ref.get("policy"):
            # Lessons whose errors became rare after earlier guidance (policy layer).
            lines.append("Policy for this stage (lessons that removed past failures; keep following them):")
            lines.extend(f"- {p}" for p in ref["policy"])
        if ref:
            # Shown at the start as well as in the end-of-stage review, so the
            # agent can avoid a failure that would end the run before stage_end
            # (e.g. an uncapped scan that overflows the context).
            lines.append("Watch out: failures seen at this stage in past runs:")
            lines.extend(f"- {p}" for p in ref["failure_patterns"])
            if ref.get("passing_runs"):
                lines.append(f"What successful runs did here: {ref['passing_runs']}")
        lines.append(
            "Every tool call from now on belongs to this stage. When you believe the goal is "
            "reached (or you cannot get further), call stage_end alone in its own turn."
        )
        return "\n".join(lines)
    except Exception as exc:
        return {"status": "error", "error": f"Error: {type(exc).__name__}: {exc}"}


def stage_end(
    goal_reached: bool,
    summary: str,
    agent_state: Any,
) -> str | dict[str, str]:
    try:
        state = load_state(agent_state)
        current = state.get("open")
        if not current:
            return {"status": "error", "error": "No stage is open. Call stage_start first."}
        ref = reference(current["stage"])
        # The stage the calls actually belong to, when it differs from the declared one:
        # the review then also covers that stage's failures (mislabelled stages otherwise
        # get the wrong checklist).
        effective = _effective_stage(current)
        eff_ref = reference(effective) if effective else None
        # Only at stages where the training annotations placed
        # surfaced-not-opened errors (rule A8); None means "not shown".
        show_unopened = SNO_ENABLED and (current["stage"] in SNO_STAGES or effective in SNO_STAGES)
        unopened = _surfaced_not_opened(state) if show_unopened else None
        earlier = [h for h in state["history"] if h["label"] == current["label"]]
        critique = _critic(state, current, ref, bool(goal_reached), summary or "", unopened, effective, eff_ref, earlier)
        state["history"].append(
            {
                "stage": current["stage"],
                "label": current["label"],
                "goal": current["goal"],
                "attempt": current["attempt"],
                "goal_reached": bool(goal_reached),
                "n_calls": len(current["calls"]),
                "summary": short(summary or "", 600),
                "effective_stage": effective,
                "critic": critique,
            }
        )
        state["open"] = None
        save_state(agent_state, state)
        return _review_text(current, ref, bool(goal_reached), critique, unopened, effective, eff_ref)
    except Exception as exc:
        return {"status": "error", "error": f"Error: {type(exc).__name__}: {exc}"}


def _effective_stage(current: dict[str, Any]) -> str | None:
    """Ask the fit model which listed stage the stage's calls belong to; None if it is the declared one."""
    if current["stage"] == NEW_STAGE or not current["calls"]:
        return None
    menu = "\n".join(f"- {name}: {reference(name)['purpose']}" for name in STAGE_NAMES)
    calls = "\n".join(f"- {c['tool']} {short(c['args'], 300)}" for c in current["calls"][:40])
    system = ("You classify a stretch of an agent's tool calls into one stage from a fixed list. Judge only from "
              "what the calls do. Reply with JSON only: {\"stage\": \"<exact name from the list>\"}.")
    try:
        answer = parse_json(chat(FIT_MODEL, system, f"STAGES:\n{menu}\n\nCALLS:\n{calls}", max_tokens=80)) or {}
    except Exception:
        return None
    name = answer.get("stage")
    return name if name in STAGE_NAMES and name != current["stage"] else None


def _surfaced_not_opened(state: dict[str, Any]) -> list[str]:
    opened = set(state.get("opened", []))
    return [m for m in state.get("surfaced", {}) if m not in opened]


def _critic(
    state: dict[str, Any],
    current: dict[str, Any],
    ref: dict[str, Any] | None,
    goal_reached: bool,
    summary: str,
    unopened: list[str] | None,
    effective: str | None = None,
    eff_ref: dict[str, Any] | None = None,
    earlier: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    log_lines: list[str] = []
    for call in current["calls"]:
        log_lines.append(f"- {call['tool']} {call['args']}\n  -> {call['result']}")
    log = "\n".join(log_lines)
    if len(log) > _MAX_LOG_CHARS:
        log = "[earlier calls omitted]\n" + log[-_MAX_LOG_CHARS:]
    patterns = "\n".join(f"- {p}" for p in (ref or {}).get("failure_patterns", [])) or "- (none known: this is a stage the agent defined itself)"
    policy = "\n".join(f"- {p}" for p in (ref or {}).get("policy", []))
    if eff_ref:
        patterns += f"\n(The calls look like '{effective}' work; that stage's patterns apply too:)\n" + "\n".join(
            f"- {p}" for p in eff_ref.get("failure_patterns", []))
        if eff_ref.get("policy"):
            policy += "\n" + "\n".join(f"- {p}" for p in eff_ref["policy"])
    stuck = ""
    if current["attempt"] >= 3:
        tried = "; ".join(f"attempt {h['attempt']}: {short(h['goal'], 200)}" for h in (earlier or []))
        stuck = (
            f"THE AGENT HAS OPENED THIS STAGE {current['attempt']} TIMES ({tried}). Recommend a different approach "
            "from the earlier attempts. If a step that is not among the listed stages would help, propose it as a new "
            "stage in \"new_stage\" with a short name and goal.\n\n"
        )
    system = (
        "You review one stage of an AI agent's work on a legal document-search task. The agent "
        "searches a shared document store and writes a response. You do NOT know the right answer; "
        "judge only from the request, the stage goal and the stage's tool calls and results shown. "
        "Use the known failure patterns of this stage as your checklist, but list a failure in "
        "applicable_failures ONLY if you can point to the specific call, result, matter or document in "
        "this stage's log that shows it; name that evidence. Do not repeat a pattern as a generic "
        "warning. Your recommendation must not itself lead into a known failure pattern of the stage it "
        "points to (those patterns are listed for every stage). Do not invent facts. "
        "Reply with JSON only: {\"goal_reached\": \"yes\"|\"partly\"|\"no\", "
        "\"applicable_failures\": [short strings, each naming its evidence], \"concerns\": \"<=120 words\", "
        "\"recommendation\": \"<=80 words, concrete next actions\", "
        "\"new_stage\": {\"name\": \"...\", \"goal\": \"...\"} or null}."
    )
    others = "\n".join(
        f"- {name}: " + " ".join(r["failure_patterns"])
        for name in STAGE_NAMES
        if name != current["stage"] and (r := reference(name)) and r.get("failure_kinds")
    )
    user = (
        f"REQUEST (task given to the agent):\n{short(state.get('request', ''), 6000)}\n\n"
        f"STAGE: {current['label']} (attempt {current['attempt']})\n"
        f"STAGE PURPOSE: {(ref or {}).get('purpose', 'defined by the agent')}\n"
        f"AGENT'S GOAL: {current['goal']}\n"
        f"AGENT'S SELF-ASSESSMENT: goal_reached={goal_reached}; summary: {short(summary, 3000)}\n\n"
        f"KNOWN FAILURE PATTERNS AT THIS STAGE (from past runs):\n{patterns}\n\n"
        + (f"STAGE POLICY (rules that removed past failures; check they still hold):\n{policy}\n\n" if policy else "")
        + stuck
        + f"KNOWN FAILURE PATTERNS OF OTHER STAGES (your recommendation must not lead into these):\n{others}\n\n"
        + (
            f"{ENTITY_NAME.upper()}S THAT APPEARED IN SEARCH RESULTS SO FAR BUT HAVE NO DOCUMENT OPENED OR FOLDER LISTED: "
            f"{', '.join(unopened[:60]) or 'none'}\n\n"
            if unopened is not None
            else ""
        )
        + f"STAGE TOOL CALLS ({len(current['calls'])}):\n{log or '(no tool calls in this stage)'}"
    )
    try:
        text = chat(CRITIC_MODEL, system, user)
        parsed = parse_json(text)
        if parsed is None:
            return {"available": True, "raw": short(text, 1500)}
        parsed["available"] = True
        return parsed
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {short(str(exc), 200)}"}


def _review_text(
    current: dict[str, Any],
    ref: dict[str, Any] | None,
    goal_reached: bool,
    critique: dict[str, Any],
    unopened: list[str] | None,
    effective: str | None = None,
    eff_ref: dict[str, Any] | None = None,
) -> str:
    lines = [f"[Stage review: {current['label']}, attempt {current['attempt']}]"]
    lines.append(f"You reported: goal reached = {'yes' if goal_reached else 'no'}.")
    if critique.get("available"):
        if "raw" in critique:
            lines.append(f"Independent reviewer: {critique['raw']}")
        else:
            lines.append(f"Independent reviewer: goal reached = {critique.get('goal_reached', '?')}.")
            if critique.get("applicable_failures"):
                lines.append("Reviewer flags: " + "; ".join(str(x) for x in critique["applicable_failures"]))
            if critique.get("concerns"):
                lines.append(f"Reviewer concerns: {critique['concerns']}")
            if critique.get("recommendation"):
                lines.append(f"Reviewer recommendation: {critique['recommendation']}")
    else:
        lines.append("Independent reviewer: unavailable for this stage.")
    if effective:
        lines.append(
            f"Label: these calls looked like '{effective}' work, so they were also reviewed against that stage's "
            f"failures. Declare '{effective}' for this kind of work."
        )
    new_stage = critique.get("new_stage") if critique.get("available") else None
    if isinstance(new_stage, dict) and new_stage.get("name"):
        lines.append(
            f"Reviewer suggests a new step: '{new_stage['name']}' ({new_stage.get('goal', '')}). You can start it with "
            f"stage_start(stage=\"new\", new_stage_name=\"{new_stage['name']}\", goal=...)."
        )
    elif current["attempt"] >= 3:
        lines.append(
            f"This stage has been opened {current['attempt']} times. If repeating it is not getting further, try a "
            "different approach; you may define a new stage (stage=\"new\", new_stage_name=...) if none of the listed "
            "stages fits it."
        )
    if unopened:
        lines.append(
            f"{ENTITY_NAME.capitalize()}s that appeared in your search results but none of whose documents you have opened "
            f"or listed: {', '.join(unopened[:40])}{' …' if len(unopened) > 40 else ''}."
        )
    if ref:
        lines.append("Common failures at this stage in past runs:")
        lines.extend(f"- {p}" for p in ref["failure_patterns"])
        if eff_ref:
            lines.append(f"Common failures at '{effective}':")
            lines.extend(f"- {p}" for p in eff_ref["failure_patterns"])
        if ref.get("passing_runs"):
            lines.append(f"What successful runs did: {ref['passing_runs']}")
    if goal_reached:
        lines.append(
            "Reconsider before moving on. If the goal was not fully reached, or any failure above applies, "
            f"reopen this stage now: call stage_start with stage=\"{current['stage']}\""
            + (f" and new_stage_name=\"{current['label'][5:]}\"" if current["stage"] == "new" else "")
            + " and a goal that says what you will fix. Otherwise call stage_start for the next stage you need."
        )
    else:
        lines.append(
            "You said the goal was not reached. Reopen this stage: call stage_start with "
            f"stage=\"{current['stage']}\""
            + (f" and new_stage_name=\"{current['label'][5:]}\"" if current["stage"] == "new" else "")
            + " and a sharper goal that follows the recommendation above, or start a different stage if that is what is needed."
        )
    return "\n".join(lines)
