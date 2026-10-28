# REJECTED (user, 2026-10-28): a general output cap is a harness improvement outside the
# hypothesis under test (stage-level grouping, error stats, feedback and steering). Not used.
"""Cap very large shell and grep results; save the full output in the sandbox.

Evidence (training runs only): context overflow is the first error of 15
base-harness runs and of 35 stage-harness runs (campaign 29); 32 of those 35
ended inside "Scan document text with an extraction script" or "Search file
contents for request keywords", each on a single bash/grep result of
millions of characters (median 7M), before any response was written. Passing
runs also print large outputs (median largest 381K, 90th percentile 1.8M
characters), so the cap is set well above the typical passing-run result.

A bash or grep result longer than CAP_CHARS is replaced by its first
HEAD_CHARS and last TAIL_CHARS characters plus a note. The full output is
written to /workspace/tool_outputs/<n>.txt in the trial sandbox, where the
agent can page it with read (offset/limit) or search it with grep.
"""

from __future__ import annotations

from typing import Any

from harvey_ahe.workspace import handle_for
from nexau.archs.main_sub.execution.hooks import Middleware

CAP_CHARS = 1_000_000
HEAD_CHARS = 150_000
TAIL_CHARS = 50_000
SAVE_DIR = "/workspace/tool_outputs"
COUNTER_KEY = "harvey_output_cap_count"
CAPPED_TOOLS = {"bash", "grep"}


class OutputCapMiddleware(Middleware):
    def wrap_tool_call(self, params: Any, call_next: Any) -> Any:
        result = call_next(params)
        if params.tool_name not in CAPPED_TOOLS:
            return result
        try:
            key, text = _text_field(result)
            if text is None or len(text) <= CAP_CHARS:
                return result
            count = int(params.agent_state.get_global_value(COUNTER_KEY, 0)) + 1
            params.agent_state.set_global_value(COUNTER_KEY, count)
            path = f"{SAVE_DIR}/{params.tool_name}-{count}.txt"
            saved = True
            try:
                handle = handle_for(params.agent_state)
                handle.exec(f"mkdir -p {SAVE_DIR}")
                handle.write_file(path, text)
            except Exception:
                saved = False
            note = (
                f"\n\n[Output capped by the harness: {len(text):,} characters, of which the first "
                f"{HEAD_CHARS:,} and the last {TAIL_CHARS:,} are shown. "
                + (f"The full output is saved at {path}; page it with read (offset/limit) or search it with grep. "
                   if saved else "The full output could not be saved. ")
                + "Narrow the command or cap what it prints so the needed lines fit.]\n\n"
            )
            capped = text[:HEAD_CHARS] + note + text[-TAIL_CHARS:]
            if key is None:
                return capped
            updated = dict(result)
            updated[key] = capped
            return updated
        except Exception:
            return result


def _text_field(result: Any) -> tuple[str | None, str | None]:
    if isinstance(result, str):
        return None, result
    if isinstance(result, dict):
        for key in ("result", "content", "output"):
            if isinstance(result.get(key), str):
                return key, result[key]
    return None, None
