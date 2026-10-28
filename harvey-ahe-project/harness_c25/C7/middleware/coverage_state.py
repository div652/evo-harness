"""Keep unresolved coverage and candidate-ledger state salient across turns."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from harvey_ahe.workspace import handle_for
from nexau.archs.main_sub.execution.hooks import HookResult, Middleware
from nexau.core.messages import Message, Role, TextBlock

_STATE_KEY = "harvey_coverage_state_v1"
_READ_BUDGET_KEY = "harvey_read_turn_chars_v1"
_MARKER = "[Coverage-state reminder]"
_MAX_DISPLAY = 6
_LARGE_READ_BATCH_CHARS = 100_000
_LEDGER_PATHS = (
    "/workspace/candidate-ledger.md",
    # Relative write calls go to output. Inspect this fallback so an accidental
    # scratch-path mistake does not disable the audit; the skill tells the agent
    # to move future ledger updates outside the graded output directory.
    "/workspace/output/candidate-ledger.md",
)
_OPEN_ROW_MARKERS = ("unresolved", "unknown", "pending", "tbd", "unread")
_READ_HEADER = re.compile(
    r"\[read_result\]\n"
    r"source: (?P<source>[^\n]+)\n"
    r"status: (?P<status>[^\n]+)\n"
    r"lines: (?P<start>\d+)-(?P<end>\d+) of (?P<total>\d+) \(end exclusive\)"
)
_PAGE_HEADERS = {
    "glob": re.compile(
        r"Glob page: shown=(?P<shown>\d+) total=(?P<total>\d+) "
        r"offset=(?P<start>\d+) limit=\d+ truncated=(?:true|false) "
        r"next_offset=(?:\d+|none)"
    ),
    "grep": re.compile(
        r"Grep page: shown=(?P<shown>\d+) total=(?P<total>\d+) "
        r"offset=(?P<start>\d+) limit=\d+ truncated=(?:true|false) "
        r"next_offset=(?:\d+|none)"
    ),
}


class CoverageStateMiddleware(Middleware):
    """Track coverage intervals exposed by read, glob, and grep tool metadata.

    The middleware does not block calls or decide legal relevance. It maintains
    trial-local interval state and places one replaceable framework reminder at
    the end of the active history while coverage gaps remain.
    """

    def after_tool(self, hook_input: Any) -> HookResult:
        try:
            text = _result_text(hook_input.tool_output)
            if text is None or hook_input.tool_name not in {"read", "glob", "grep"}:
                return HookResult.no_changes()
            state = _load_state(hook_input.agent_state)
            if hook_input.tool_name == "read":
                _record_read(state, text)
            else:
                _record_page(state, hook_input.tool_name, hook_input.tool_input, text)
                if _is_broad_discovery(hook_input.tool_input, text):
                    dossier = state["dossier"]
                    dossier["discovery_revision"] = int(
                        dossier.get("discovery_revision", 0)
                    ) + 1
            hook_input.agent_state.set_global_value(_STATE_KEY, state)
        except Exception:
            # Middleware failures must never turn a recoverable legal task into an
            # agent error. The original tool result remains authoritative.
            return HookResult.no_changes()
        return HookResult.no_changes()

    def before_model(self, hook_input: Any) -> HookResult:
        try:
            messages, removed = _without_old_reminder(hook_input.messages)
            state = _load_state(hook_input.agent_state)
            ledger = _inspect_ledger(hook_input.agent_state)
            _reconcile_ledger_revision(state, ledger)
            hook_input.agent_state.set_global_value(_STATE_KEY, state)
            prior_read_chars = _read_budget_used(hook_input.agent_state)
            # The read tool consumes this trial-local counter while executing all
            # calls from one assistant response. Reset only at the next model turn.
            hook_input.agent_state.set_global_value(_READ_BUDGET_KEY, 0)
            reminder = _build_reminder(state, prior_read_chars, ledger)
            if reminder is None:
                if removed:
                    return HookResult.with_modifications(messages=messages)
                return HookResult.no_changes()
            messages.append(
                Message(role=Role.FRAMEWORK, content=[TextBlock(text=reminder)])
            )
            return HookResult.with_modifications(messages=messages)
        except Exception:
            return HookResult.no_changes()


def _read_budget_used(agent_state: Any) -> int:
    value = agent_state.get_global_value(_READ_BUDGET_KEY, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _result_text(tool_output: Any) -> str | None:
    if isinstance(tool_output, dict):
        value = tool_output.get("result")
        return value if isinstance(value, str) else None
    return tool_output if isinstance(tool_output, str) else None


def _load_state(agent_state: Any) -> dict[str, dict[str, Any]]:
    value = agent_state.get_global_value(_STATE_KEY, None)
    if not isinstance(value, dict):
        return {"reads": {}, "queries": {}, "dossier": {}}
    reads = value.get("reads")
    queries = value.get("queries")
    dossier = value.get("dossier")
    return {
        "reads": reads if isinstance(reads, dict) else {},
        "queries": queries if isinstance(queries, dict) else {},
        "dossier": dossier if isinstance(dossier, dict) else {},
    }


def _record_read(state: dict[str, dict[str, Any]], text: str) -> None:
    match = _READ_HEADER.search(text)
    if match is None or match.group("status") != "ok":
        return
    source = match.group("source")
    start = int(match.group("start"))
    end = int(match.group("end"))
    total = int(match.group("total"))
    reads = state["reads"]
    record = reads.get(source)
    intervals = record.get("intervals", []) if isinstance(record, dict) else []
    if not isinstance(record, dict) or record.get("total") != total:
        intervals = []
    merged = _merge_intervals(intervals, start, end)
    if _is_complete(merged, total):
        reads.pop(source, None)
    else:
        reads[source] = {"total": total, "intervals": merged}


def _record_page(
    state: dict[str, dict[str, Any]],
    tool_name: str,
    tool_input: dict[str, Any],
    text: str,
) -> None:
    match = _PAGE_HEADERS[tool_name].search(text)
    if match is None:
        return
    start = int(match.group("start"))
    shown = int(match.group("shown"))
    total = int(match.group("total"))
    key, label = _query_identity(tool_name, tool_input)
    queries = state["queries"]
    record = queries.get(key)
    intervals = record.get("intervals", []) if isinstance(record, dict) else []
    if not isinstance(record, dict) or record.get("total") != total:
        intervals = []
    merged = _merge_intervals(intervals, start, start + shown)
    if _is_complete(merged, total):
        queries.pop(key, None)
    else:
        queries[key] = {"label": label, "total": total, "intervals": merged}


def _is_broad_discovery(tool_input: Any, text: str) -> bool:
    """True only for a successful search rooted at the corpus/matter boundary."""
    if not isinstance(tool_input, dict):
        return False
    matched = False
    for pattern in _PAGE_HEADERS.values():
        page = pattern.search(text)
        if page is not None and int(page.group("total")) > 0:
            matched = True
            break
    if not matched:
        return False
    raw_path = tool_input.get("path")
    if raw_path is None or not isinstance(raw_path, str):
        return True
    path = raw_path.strip().strip("/")
    if path.startswith("workspace/"):
        path = path.removeprefix("workspace/")
    parts = [part for part in path.split("/") if part and part != "."]
    return parts in (["documents"], ["documents", "matters"], ["matters"])


def _inspect_ledger(agent_state: Any) -> dict[str, Any]:
    """Return a bounded audit of the agent-authored markdown candidate ledger."""
    handle = handle_for(agent_state)
    for path in _LEDGER_PATHS:
        if not handle.exists(path):
            continue
        raw = handle.read_file(path)
        data = raw if isinstance(raw, bytes) else str(raw).encode("utf-8", "replace")
        text = data.decode("utf-8", "replace")
        rows = _candidate_rows(text)
        open_labels = [label for label, cells in rows if _row_is_open(cells)]
        return {
            "exists": True,
            "path": path,
            "fingerprint": hashlib.sha256(data).hexdigest(),
            "row_count": len(rows),
            "open_labels": open_labels,
        }
    return {
        "exists": False,
        "path": None,
        "fingerprint": None,
        "row_count": 0,
        "open_labels": [],
    }


def _candidate_rows(text: str) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    candidate_index: int | None = None
    expected_columns = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            candidate_index = None
            expected_columns = 0
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        lowered = [cell.casefold() for cell in cells]
        if candidate_index is None:
            for index, value in enumerate(lowered):
                if value in {"candidate", "matter", "candidate / matter"}:
                    candidate_index = index
                    expected_columns = len(cells)
                    break
            continue
        if len(cells) != expected_columns or all(
            re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
        ):
            continue
        label = cells[candidate_index].strip()
        if not label or label.casefold() in {"candidate", "matter"}:
            continue
        rows.append((label, cells))
    return rows


def _row_is_open(cells: list[str]) -> bool:
    for cell in cells:
        normalized = cell.casefold().strip(" `*_:")
        for marker in _OPEN_ROW_MARKERS:
            if not re.search(rf"\b{re.escape(marker)}\b", normalized):
                continue
            if marker == "unread" and re.search(r"\b(?:no|none)\s+unread\b", normalized):
                continue
            return True
    return False


def _reconcile_ledger_revision(
    state: dict[str, dict[str, Any]], ledger: dict[str, Any]
) -> None:
    if not ledger.get("exists"):
        return
    dossier = state["dossier"]
    fingerprint = ledger.get("fingerprint")
    if fingerprint != dossier.get("ledger_fingerprint"):
        dossier["ledger_fingerprint"] = fingerprint
        dossier["ledger_revision"] = int(dossier.get("discovery_revision", 0))


def _query_identity(tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
    arguments = {
        key: value
        for key, value in tool_input.items()
        if key not in {"offset", "limit"}
    }
    key = f"{tool_name}:" + json.dumps(
        arguments, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    if tool_name == "glob":
        label = (
            f"glob pattern={arguments.get('pattern')!r} "
            f"path={arguments.get('path', 'documents')!r} "
            f"type={arguments.get('entry_type', 'files')!r}"
        )
    else:
        label = (
            f"grep pattern={arguments.get('pattern')!r} "
            f"path={arguments.get('path', 'documents')!r}"
        )
    return key, label


def _merge_intervals(
    existing: Any, start: int, end: int
) -> list[list[int]]:
    intervals: list[tuple[int, int]] = []
    if isinstance(existing, list):
        for item in existing:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], int)
                and isinstance(item[1], int)
            ):
                intervals.append((item[0], item[1]))
    intervals.append((start, end))
    intervals.sort()
    merged: list[list[int]] = []
    for left, right in intervals:
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return merged


def _is_complete(intervals: list[list[int]], total: int) -> bool:
    return total == 0 or (
        bool(intervals) and intervals[0][0] == 0 and intervals[0][1] >= total
    )


def _without_old_reminder(messages: list[Message]) -> tuple[list[Message], bool]:
    retained: list[Message] = []
    removed = False
    for message in messages:
        is_ours = message.role == Role.FRAMEWORK and any(
            isinstance(block, TextBlock) and block.text.startswith(_MARKER)
            for block in message.content
        )
        if is_ours:
            removed = True
        else:
            retained.append(message)
    return retained, removed


def _build_reminder(
    state: dict[str, dict[str, Any]],
    prior_read_chars: int = 0,
    ledger: dict[str, Any] | None = None,
) -> str | None:
    reads = state.get("reads", {})
    queries = state.get("queries", {})
    dossier = state.get("dossier", {})
    ledger = ledger or {
        "exists": False,
        "row_count": 0,
        "open_labels": [],
        "path": None,
    }
    discovery_revision = int(dossier.get("discovery_revision", 0))
    ledger_revision = int(dossier.get("ledger_revision", 0))
    stale_passes = max(0, discovery_revision - ledger_revision)
    ledger_missing = discovery_revision > 0 and not ledger.get("exists")
    open_labels = ledger.get("open_labels", [])
    ledger_open = isinstance(open_labels, list) and bool(open_labels)
    ledger_unparseable = bool(ledger.get("exists")) and not ledger.get("row_count")
    large_batch = prior_read_chars >= _LARGE_READ_BATCH_CHARS
    if not any(
        (
            reads,
            queries,
            large_batch,
            ledger_missing,
            ledger_open,
            ledger_unparseable,
            stale_passes,
        )
    ):
        return None
    lines = [_MARKER]
    if ledger_missing:
        lines.append(
            "A corpus-boundary search has returned results, but no candidate ledger is "
            "present. Before another broad search or drafting, create "
            "`/workspace/candidate-ledger.md` and add one row for each legally plausible "
            "matter cluster already surfaced. Incidental hits need not become candidates."
        )
    elif ledger_unparseable:
        lines.append(
            f"The ledger at {ledger.get('path')} has no parseable markdown candidate rows. "
            "Use a pipe table with a `candidate` or `matter` header and one separate row per "
            "plausible candidate; do not hide candidates in narrative or aggregate rows."
        )
    else:
        if stale_passes:
            lines.append(
                f"{stale_passes} new broad discovery result page(s) arrived since the "
                "candidate ledger content last changed. Reconcile each legally plausible "
                "new cluster into its own row before another broad search or drafting."
            )
        if ledger_open:
            shown = [str(value) for value in open_labels[:_MAX_DISPLAY]]
            lines.append(
                f"Candidate ledger audit: {len(open_labels)} row(s) still contain an explicit "
                f"open marker (unresolved/unknown/pending/TBD/unread): {', '.join(shown)}. "
                "Resolve each with candidate-local authoritative evidence or keep researching; "
                "absence of review is not an exclusion."
            )
            if len(open_labels) > _MAX_DISPLAY:
                lines.append(
                    f"- plus {len(open_labels) - _MAX_DISPLAY} additional open ledger row(s)"
                )
    if large_batch:
        lines.append(
            "The previous assistant turn reached the bounded read-output budget. Do not "
            "repeat or fan out the deferred reads now. First compress the returned facts "
            "into the source-bound candidate ledger, decide which exact qualifier remains "
            "unresolved, and use the next batch only for those source/range gaps. Complete "
            "discovery does not require whole-document ingestion."
        )
    if reads or queries:
        lines.extend(
            [
                (
                    f"Tool metadata still shows {len(queries)} incompletely paged discovery "
                    f"set(s) and {len(reads)} partially read document(s). These are coverage "
                    "warnings, not proof that every remainder is relevant or must be read."
                ),
                (
                    "For a corpus-wide, negative, comparative, or superlative conclusion, "
                    "disposition every surfaced candidate in the scratch ledger and carry "
                    "each included candidate's requested proof paths into the deliverable. "
                    "Continue only a missing range that can change an inclusion, exclusion, "
                    "ranking, or requested fact. Otherwise record the source-grounded reason "
                    "the remainder cannot affect the decision and move to reconciliation, "
                    "drafting, verification, and finish."
                ),
            ]
        )
    if queries:
        lines.append("Open discovery coverage:")
        for record in list(queries.values())[:_MAX_DISPLAY]:
            lines.append(
                f"- {_shorten(str(record.get('label', 'query')))}; "
                f"covered {_format_intervals(record.get('intervals'))} "
                f"of 0-{record.get('total', '?')}"
            )
        if len(queries) > _MAX_DISPLAY:
            lines.append(f"- plus {len(queries) - _MAX_DISPLAY} more discovery set(s)")
    if reads:
        lines.append("Open document coverage:")
        for source, record in list(reads.items())[:_MAX_DISPLAY]:
            lines.append(
                f"- {_shorten(source)}; covered "
                f"{_format_intervals(record.get('intervals'))} "
                f"of 0-{record.get('total', '?')} lines"
            )
        if len(reads) > _MAX_DISPLAY:
            lines.append(f"- plus {len(reads) - _MAX_DISPLAY} more document(s)")
    return "\n".join(lines)


def _format_intervals(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(
        f"{item[0]}-{item[1]}"
        for item in value
        if isinstance(item, (list, tuple)) and len(item) == 2
    )


def _shorten(value: str, maximum: int = 160) -> str:
    if len(value) <= maximum:
        return value
    keep = (maximum - 3) // 2
    return value[:keep] + "..." + value[-keep:]
