"""Enforce the stage protocol and record each stage's tool calls.

Rules (deterministic, via wrap_tool_call, which can refuse a call without
running it):
- stage_start while a stage is open -> refused (close it with stage_end first);
- stage_end with no open stage -> refused;
- any work tool (bash, read, write, edit, glob, grep) with no open stage -> refused;
- finish while a stage is open -> refused;
- a turn that mixes stage_start/stage_end with other calls -> every call of that
  turn is refused (stage calls must be alone in their turn, so the order is
  unambiguous).
There is deliberately no loop breaker: a run that keeps getting refused is
left to show that behaviour.

A model reply with no tool call would end the run; instead the agent is told
to continue (force_continue).

Every work call made inside a stage is recorded (tool, arguments, start of
the result) for the critic in `stage_end`. When the benchmark's reference file
enables it, entity identifiers (here matter numbers) shown by searches, and
those whose documents were opened or folder listed, are tracked for the
"surfaced but not opened" fact given to the critic at the stages where that
error occurred in training. A different
model checks whether each search-like call fits the open stage; a mismatch
adds a note to the result (never a refusal).
"""

from __future__ import annotations

import json
import threading
from typing import Any

from nexau.archs.main_sub.execution.hooks import HookResult, Middleware
from nexau.core.messages import Message, Role, TextBlock

from middleware.stage_common import (
    FIT_MODEL,
    ENTITY,
    SNO_ENABLED,
    SNO_MAX,
    NEW_STAGE,
    STAGE_TOOLS,
    chat,
    load_state,
    parse_json,
    reference,
    result_text,
    save_state,
    short,
)

_LOCK = threading.Lock()
_WORK_TOOLS = {"bash", "read", "write", "edit", "glob", "grep"}
_FIT_CHECKED = {"bash", "grep", "glob"}
_WRITING_STAGES = {"Write the response", "Check or revise the response", "Calculate figures for the answer"}
_MARKER = "[Stage protocol]"


def _refuse(message: str) -> dict[str, str]:
    return {"status": "error", "error": f"{_MARKER} {message}"}


class StageGuardMiddleware(Middleware):
    def before_model(self, hook_input: Any) -> HookResult:
        try:
            with _LOCK:
                state = load_state(hook_input.agent_state)
                if not state.get("request"):
                    for message in hook_input.messages:
                        if getattr(message, "role", None) == Role.USER:
                            text = " ".join(
                                getattr(block, "text", "") for block in (message.content or [])
                            ).strip()
                            if text:
                                state["request"] = text
                                save_state(hook_input.agent_state, state)
                                break
        except Exception:
            pass
        return HookResult.no_changes()

    def after_model(self, hook_input: Any) -> HookResult:
        try:
            parsed = hook_input.parsed_response
            calls = list(getattr(parsed, "tool_calls", None) or []) if parsed else []
            if not calls:
                with _LOCK:
                    state = load_state(hook_input.agent_state)
                    open_stage = state.get("open")
                    state["text_replies"] = int(state.get("text_replies", 0)) + 1
                    save_state(hook_input.agent_state, state)
                hint = (
                    f"Stage '{open_stage['label']}' is still open. "
                    if open_stage
                    else ""
                )
                messages = list(hook_input.messages)
                messages.append(
                    Message(
                        role=Role.FRAMEWORK,
                        content=[
                            TextBlock(
                                text=(
                                    f"{_MARKER} You replied without calling a tool, which does not end the task. "
                                    f"{hint}Continue through the stages; write the deliverable to the output "
                                    "directory with the write tool, close the open stage with stage_end, "
                                    "then call finish."
                                )
                            )
                        ],
                    )
                )
                return HookResult.with_modifications(messages=messages, force_continue=True)
            names = [getattr(c, "tool_name", "") for c in calls]
            if any(n in STAGE_TOOLS for n in names) and len(calls) > 1:
                with _LOCK:
                    state = load_state(hook_input.agent_state)
                    state["blocked_ids"] = list(
                        set(state.get("blocked_ids", [])) | {getattr(c, "tool_call_id", "") for c in calls}
                    )
                    save_state(hook_input.agent_state, state)
        except Exception:
            pass
        return HookResult.no_changes()

    def wrap_tool_call(self, params: Any, call_next: Any) -> Any:
        name = params.tool_name
        agent_state = params.agent_state
        try:
            with _LOCK:
                state = load_state(agent_state)
                blocked = state.get("blocked_ids", [])
                if params.tool_call_id in blocked:
                    blocked.remove(params.tool_call_id)
                    save_state(agent_state, state)
                    return _refuse(
                        "stage_start and stage_end must be called alone in their own turn. None of the "
                        "calls in this turn were run; issue the stage call by itself first, then the others."
                    )
                open_stage = state.get("open")
            if name == "stage_start" and open_stage:
                return _refuse(f"Stage '{open_stage['label']}' is still open. Call stage_end first.")
            if name == "stage_end" and not open_stage:
                return _refuse("No stage is open. Call stage_start first.")
            if name == "finish" and open_stage:
                return _refuse(f"Stage '{open_stage['label']}' is still open. Call stage_end before finish.")
            if name in _WORK_TOOLS and not open_stage:
                return _refuse(
                    "No stage is open. Call stage_start (alone in its turn) with the stage you are in and its goal, "
                    "then repeat this call."
                )
        except Exception:
            return call_next(params)

        result = call_next(params)
        if name not in _WORK_TOOLS:
            return result
        try:
            note = self._fit_note(open_stage, name, params.parameters)
            self._record(agent_state, name, params.parameters, result, note)
            if note:
                result = _append(result, note)
        except Exception:
            pass
        return result

    # -- helpers -----------------------------------------------------------

    def _record(self, agent_state: Any, name: str, args: dict[str, Any], result: Any, note: str | None) -> None:
        text = result_text(result)
        arg_text = json.dumps(args, ensure_ascii=False)
        with _LOCK:
            state = load_state(agent_state)
            current = state.get("open")
            if current is not None:
                current["calls"].append(
                    {"tool": name, "args": short(arg_text, 400), "result": short(text, 700)}
                )
                if note:
                    state.setdefault("mismatches", []).append(
                        {"stage": current["label"], "tool": name, "args": short(arg_text, 200)}
                    )
            label = current["label"] if current else "?"
            if SNO_ENABLED and ENTITY is not None:
                opened = set(state.get("opened", []))
                if name in ("read", "glob", "bash"):
                    opened |= set(ENTITY.findall(arg_text))
                if name in ("grep", "glob", "bash"):
                    shown = set(ENTITY.findall(text))
                    # A result showing more entities than this is a full listing, not a hit list.
                    if 0 < len(shown) <= SNO_MAX:
                        surfaced = state.setdefault("surfaced", {})
                        for entity in sorted(shown):
                            surfaced.setdefault(entity, label)
                state["opened"] = sorted(opened)
            save_state(agent_state, state)

    def _fit_note(self, open_stage: dict[str, Any] | None, name: str, args: dict[str, Any]) -> str | None:
        if not open_stage or open_stage["stage"] == NEW_STAGE:
            return None
        ref = reference(open_stage["stage"]) or {}
        if name in ("write", "edit"):
            if open_stage["stage"] not in _WRITING_STAGES and "output" in json.dumps(args):
                return (
                    f"{_MARKER} Stage check: this writes to the output directory while the open stage is "
                    f"'{open_stage['label']}'. If you are now writing or revising the answer, call stage_end and start "
                    "'Write the response' or 'Check or revise the response'."
                )
            return None
        if name not in _FIT_CHECKED:
            return None
        system = (
            "Classify one tool call of an agent searching a legal document store "
            "(documents/matters/NNNN-NNNNN/...). Decide whether the call fits the activity expected "
            "in the agent's declared stage. Store-wide = over all matters; in-matter = inside named "
            "matter folders. Reply with JSON only: {\"fits\": true|false, \"activity\": \"<=12 words\"}."
        )
        user = (
            f"Declared stage: {open_stage['label']}\nExpected activity: {ref.get('expected_activity', '')}\n"
            f"Stage goal: {short(open_stage['goal'], 500)}\nTool: {name}\n"
            f"Arguments: {short(json.dumps(args, ensure_ascii=False), 1500)}"
        )
        try:
            verdict = parse_json(chat(FIT_MODEL, system, user, max_tokens=120)) or {}
        except Exception:
            return None
        if verdict.get("fits") is False:
            return (
                f"{_MARKER} Stage check: this call looks like {verdict.get('activity', 'different work')}, "
                f"which does not match the open stage '{open_stage['label']}' ({ref.get('expected_activity', '')}). "
                "If you have moved on to different work, call stage_end and start the matching stage."
            )
        return None


def _append(result: Any, note: str) -> Any:
    if isinstance(result, str):
        return f"{result}\n\n{note}"
    if isinstance(result, dict):
        updated = dict(result)
        for key in ("result", "error"):
            if isinstance(updated.get(key), str):
                updated[key] = f"{updated[key]}\n\n{note}"
                return updated
        updated["stage_note"] = note
        return updated
    return result
