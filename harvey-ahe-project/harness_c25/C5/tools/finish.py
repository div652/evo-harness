"""Stop tool: end the run once the listed deliverables exist."""

from __future__ import annotations

import posixpath
from typing import Any

from tools._common import (
    OUTPUT_PATH,
    WORKSPACE_PATH,
    WorkspaceHandle,
    error_text,
    handle_for,
)

MAX_REJECTIONS = 2
REJECTIONS_KEY = "harvey_finish_rejections"
COVERAGE_REJECTION_KEY = "harvey_coverage_finish_rejection"
COVERAGE_STATE_KEY = "harvey_coverage_state_v2"
MAX_COVERAGE_DISPLAY = 6


def finish(
    summary: str,
    agent_state: Any,
    deliverables: list[str] | None = None,
) -> str | dict[str, str]:
    """Latch completion after capped deliverable and candidate-coverage checks.

    NexAU ends the run when a stop tool succeeds, so every rejection and error
    is returned with ``status: error`` to keep the agent running.
    """
    try:
        handle = handle_for(agent_state)
        missing = _missing_deliverables(handle, deliverables or [])
        rejections = int(agent_state.get_global_value(REJECTIONS_KEY, 0))
        if missing and rejections < MAX_REJECTIONS:
            agent_state.set_global_value(REJECTIONS_KEY, rejections + 1)
            return {
                "status": "error",
                "error": (
                    "Not finished: the following file(s) you listed do not "
                    f"exist in the output directory: {', '.join(missing)}. "
                    "Create them (generate binary formats with a script run "
                    "through bash) or correct the paths, then call finish again."
                ),
            }

        coverage_warning = _unresolved_coverage_summary(agent_state)
        coverage_rejected = bool(
            agent_state.get_global_value(COVERAGE_REJECTION_KEY, False)
        )
        if coverage_warning and not coverage_rejected:
            # Candidate grouping is deliberately heuristic, so this gate fires only
            # once. The agent may resolve real gaps, record why hits are incidental,
            # and retry; a false positive can never create an endless stop loop.
            agent_state.set_global_value(COVERAGE_REJECTION_KEY, True)
            return {
                "status": "error",
                "error": (
                    "Not finished: corpus-wide discovery still has candidate-closure "
                    "gaps. Reconcile these items against the scratch ledger and final "
                    "answer before retrying finish:\n"
                    f"{coverage_warning}"
                ),
            }

        handle.mark_finished(summary)
        return "Finished."
    except Exception as exc:
        return {"status": "error", "error": error_text(exc)}


def _missing_deliverables(handle: WorkspaceHandle, paths: Any) -> list[str]:
    if not isinstance(paths, list):
        return [repr(paths)]
    missing: list[str] = []
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            missing.append(repr(path))
        elif not _deliverable_exists(handle, path):
            missing.append(path)
    return missing


def _deliverable_exists(handle: WorkspaceHandle, path_str: str) -> bool:
    """Accept bare, ``output/``-prefixed, and absolute output paths."""
    if path_str.startswith("/"):
        candidates = [path_str]
    else:
        candidates = [f"{OUTPUT_PATH}/{path_str}", f"{WORKSPACE_PATH}/{path_str}"]
    for candidate in candidates:
        normalized = posixpath.normpath(candidate)
        if normalized.startswith(OUTPUT_PATH + "/") and handle.exists(normalized):
            return True
    return False


def _unresolved_coverage_summary(agent_state: Any) -> str | None:
    """Format only the bounded state needed for the one-shot finish check."""

    state = agent_state.get_global_value(COVERAGE_STATE_KEY, None)
    if not isinstance(state, dict) or not state.get("corpus_mode"):
        return None
    candidates = state.get("candidates")
    deferred = state.get("deferred")
    candidates = candidates if isinstance(candidates, dict) else {}
    deferred = deferred if isinstance(deferred, dict) else {}
    if not candidates and not deferred:
        return None

    lines: list[str] = []
    if candidates:
        lines.append(
            f"{len(candidates)} matter cluster(s) surfaced by semantic discovery have "
            "no subsequent source read."
        )
        for matter, record in list(candidates.items())[:MAX_COVERAGE_DISPLAY]:
            paths = record.get("paths", []) if isinstance(record, dict) else []
            sample = paths[0] if isinstance(paths, list) and paths else "path unavailable"
            lines.append(f"- {matter}: {_shorten(str(sample))}")
        if len(candidates) > MAX_COVERAGE_DISPLAY:
            lines.append(
                f"- plus {len(candidates) - MAX_COVERAGE_DISPLAY} more cluster(s)"
            )
    if deferred:
        lines.append(f"{len(deferred)} exact read(s) were deferred with zero text:")
        for source in list(deferred)[:MAX_COVERAGE_DISPLAY]:
            lines.append(f"- {_shorten(str(source))}")
        if len(deferred) > MAX_COVERAGE_DISPLAY:
            lines.append(
                f"- plus {len(deferred) - MAX_COVERAGE_DISPLAY} more deferred source(s)"
            )
    return "\n".join(lines)


def _shorten(value: str, maximum: int = 220) -> str:
    if len(value) <= maximum:
        return value
    keep = (maximum - 3) // 2
    return value[:keep] + "..." + value[-keep:]
