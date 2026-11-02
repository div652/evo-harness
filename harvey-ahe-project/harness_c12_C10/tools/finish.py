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
VALID_SCOPES = {"narrow", "corpus"}
VALID_CARDINALITY_CHECKS = {"not_applicable", "matches", "mismatch"}
VALID_SEMANTIC_GATE_CHECKS = {"not_applicable", "verified", "mismatch"}
VALID_CUTOFF_TIE_CHECKS = {
    "not_applicable",
    "no_cutoff_tie",
    "all_tied_present",
    "user_tiebreak_applied",
    "mismatch",
}


def finish(
    summary: str,
    deliverables: list[str],
    completion_audit: dict[str, Any],
    agent_state: Any,
) -> str | dict[str, str]:
    """Latch completion after a capped, structured completion audit.

    NexAU ends the run when a stop tool succeeds, so every rejection and error
    is returned with ``status: error`` to keep the agent running.
    """
    try:
        handle = handle_for(agent_state)
        problems = _completion_problems(handle, deliverables, completion_audit)
        rejections = int(agent_state.get_global_value(REJECTIONS_KEY, 0))
        if problems and rejections < MAX_REJECTIONS:
            agent_state.set_global_value(REJECTIONS_KEY, rejections + 1)
            return {
                "status": "error",
                "error": (
                    "Not finished. Resolve these completion-audit failures, "
                    "update the deliverable, and retry: " + "; ".join(problems)
                ),
            }
        handle.mark_finished(summary)
        return "Finished."
    except Exception as exc:
        return {"status": "error", "error": error_text(exc)}


def _completion_problems(
    handle: WorkspaceHandle,
    deliverables: Any,
    audit: Any,
) -> list[str]:
    problems: list[str] = []
    missing = _missing_deliverables(handle, deliverables)
    if missing:
        problems.append(
            "missing or invalid output file(s): " + ", ".join(missing)
        )
    if not isinstance(audit, dict):
        return problems + ["completion_audit must be an object"]

    scope = audit.get("research_scope")
    unresolved = audit.get("unresolved_candidate_count")
    unread = audit.get("unread_high_signal_file_count")
    cardinality = audit.get("answer_cardinality_check")
    semantic_gates = audit.get("semantic_gate_check")
    cutoff_ties = audit.get("cutoff_tie_check")
    late_changes = audit.get("late_changes_verified")

    if scope not in VALID_SCOPES:
        problems.append("research_scope must be 'narrow' or 'corpus'")
    if isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0:
        problems.append("unresolved_candidate_count must be a non-negative integer")
    if isinstance(unread, bool) or not isinstance(unread, int) or unread < 0:
        problems.append("unread_high_signal_file_count must be a non-negative integer")
    if cardinality not in VALID_CARDINALITY_CHECKS:
        problems.append(
            "answer_cardinality_check must be 'not_applicable', 'matches', or 'mismatch'"
        )
    elif cardinality == "mismatch":
        problems.append("affirmatively presented answers do not match the request")
    if semantic_gates not in VALID_SEMANTIC_GATE_CHECKS:
        problems.append(
            "semantic_gate_check must be 'not_applicable', 'verified', or 'mismatch'"
        )
    elif semantic_gates == "mismatch":
        problems.append("one or more inclusions lack a source-backed pass for every gate")
    if cutoff_ties not in VALID_CUTOFF_TIE_CHECKS:
        problems.append(
            "cutoff_tie_check has an invalid value"
        )
    elif cutoff_ties == "mismatch":
        problems.append("a ranking cutoff tie is not fully presented or validly resolved")
    if late_changes is not True:
        problems.append("late_changes_verified must be true after final source recheck")

    if scope == "corpus":
        for artifact in ("/workspace/lead_union.txt", "/workspace/review_state.md"):
            if not handle.exists(artifact):
                problems.append(f"missing corpus reconciliation artifact: {artifact}")
            elif not handle.read_file(artifact).strip():
                problems.append(f"empty corpus reconciliation artifact: {artifact}")
        if isinstance(unresolved, int) and not isinstance(unresolved, bool) and unresolved:
            problems.append(
                f"{unresolved} plausible candidate(s) remain unresolved or undispositioned"
            )
        if isinstance(unread, int) and not isinstance(unread, bool) and unread:
            problems.append(f"{unread} high-signal discovered file(s) remain unread")
        if cardinality == "not_applicable":
            problems.append(
                "corpus set/ranking work requires answer_cardinality_check='matches'"
            )
        if semantic_gates != "verified":
            problems.append(
                "corpus work requires semantic_gate_check='verified' after a source-backed gate-matrix audit"
            )
    return problems


def _missing_deliverables(handle: WorkspaceHandle, paths: Any) -> list[str]:
    if not isinstance(paths, list) or not paths:
        return ["deliverables must be a non-empty list"]
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
