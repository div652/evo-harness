"""Keep unresolved discovery candidates and paged reads salient across turns."""

from __future__ import annotations

import json
import re
from typing import Any

from nexau.archs.main_sub.execution.hooks import HookResult, Middleware
from nexau.core.messages import Message, Role, TextBlock

_STATE_KEY = "harvey_coverage_state_v2"
_READ_BUDGET_KEY = "harvey_read_turn_chars_v1"
_MARKER = "[Coverage-state reminder]"
_MAX_DISPLAY = 6
_MAX_PATH_SAMPLES = 3
_LARGE_READ_BATCH_CHARS = 100_000
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
_GENERIC_GLOB_TOKENS = {
    "doc",
    "docx",
    "eml",
    "file",
    "files",
    "html",
    "jpeg",
    "jpg",
    "json",
    "md",
    "pdf",
    "png",
    "ppt",
    "pptx",
    "rtf",
    "text",
    "txt",
    "xls",
    "xlsx",
    "xml",
}


class CoverageStateMiddleware(Middleware):
    """Track intervals plus corpus search-hit clusters with no source follow-up.

    This middleware never decides legal relevance. It records deterministic tool
    metadata in trial-local storage and places one replaceable reminder at the end
    of active history. Candidate tracking starts only after the agent performs the
    protocol's direct matter-directory census.
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
            hook_input.agent_state.set_global_value(_STATE_KEY, state)
        except Exception:
            # A reminder failure must not turn a recoverable legal task into an
            # agent error. The original tool result remains authoritative.
            return HookResult.no_changes()
        return HookResult.no_changes()

    def before_model(self, hook_input: Any) -> HookResult:
        try:
            messages, removed = _without_old_reminder(hook_input.messages)
            state = _load_state(hook_input.agent_state)
            prior_read_chars = _read_budget_used(hook_input.agent_state)
            # The read tool consumes this trial-local counter across all reads from
            # one assistant response. Reset it only for the next model turn.
            hook_input.agent_state.set_global_value(_READ_BUDGET_KEY, 0)
            reminder = _build_reminder(state, prior_read_chars)
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


def unresolved_coverage_summary(agent_state: Any, maximum: int = _MAX_DISPLAY) -> str | None:
    """Return a bounded finish warning for zero-follow-up hits and deferred reads."""

    state = _load_state(agent_state)
    if not state.get("corpus_mode"):
        return None
    candidates = state.get("candidates", {})
    deferred = state.get("deferred", {})
    if not candidates and not deferred:
        return None
    lines: list[str] = []
    if candidates:
        lines.append(
            f"{len(candidates)} matter cluster(s) surfaced by semantic discovery have "
            "no subsequent source read or explicit machine-visible resolution."
        )
        for matter, record in list(candidates.items())[:maximum]:
            samples = record.get("paths", []) if isinstance(record, dict) else []
            sample = samples[0] if isinstance(samples, list) and samples else "path unavailable"
            lines.append(f"- {matter}: {_shorten(str(sample), 220)}")
        if len(candidates) > maximum:
            lines.append(f"- plus {len(candidates) - maximum} more cluster(s)")
    if deferred:
        lines.append(f"{len(deferred)} read(s) returned no text because they were deferred:")
        for source in list(deferred)[:maximum]:
            lines.append(f"- {_shorten(source, 220)}")
        if len(deferred) > maximum:
            lines.append(f"- plus {len(deferred) - maximum} more deferred source(s)")
    return "\n".join(lines)


def _read_budget_used(agent_state: Any) -> int:
    value = agent_state.get_global_value(_READ_BUDGET_KEY, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _result_text(tool_output: Any) -> str | None:
    if isinstance(tool_output, dict):
        value = tool_output.get("result")
        return value if isinstance(value, str) else None
    return tool_output if isinstance(tool_output, str) else None


def _load_state(agent_state: Any) -> dict[str, Any]:
    value = agent_state.get_global_value(_STATE_KEY, None)
    if not isinstance(value, dict):
        return _empty_state()
    state = _empty_state()
    for key in ("reads", "queries", "candidates", "deferred"):
        item = value.get(key)
        if isinstance(item, dict):
            state[key] = item
    read_matters = value.get("read_matters")
    if isinstance(read_matters, list):
        state["read_matters"] = [item for item in read_matters if isinstance(item, str)]
    state["corpus_mode"] = bool(value.get("corpus_mode"))
    return state


def _empty_state() -> dict[str, Any]:
    return {
        "reads": {},
        "queries": {},
        "candidates": {},
        "deferred": {},
        "read_matters": [],
        "corpus_mode": False,
    }


def _record_read(state: dict[str, Any], text: str) -> None:
    match = _READ_HEADER.search(text)
    if match is None:
        return
    source = match.group("source")
    status = match.group("status")
    start = int(match.group("start"))
    end = int(match.group("end"))
    total = int(match.group("total"))

    if status == "deferred":
        state["deferred"][source] = {"next_offset": start}
        return
    if status != "ok":
        return

    # Any successful progress on the exact path discharges a prior zero-text
    # deferral. A source read in a surfaced matter also closes the narrower
    # "search hit with zero follow-up" warning for that matter cluster.
    if end > start:
        state["deferred"].pop(source, None)
        matter = _matter_from_source(source)
        if matter is not None:
            read_matters = state["read_matters"]
            if matter not in read_matters:
                read_matters.append(matter)
            state["candidates"].pop(matter, None)

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
    state: dict[str, Any],
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

    if _is_matter_census(tool_name, tool_input):
        state["corpus_mode"] = True
    if not state.get("corpus_mode"):
        return
    if not _is_corpus_root(tool_input.get("path")):
        return
    if not _is_semantic_candidate_query(tool_name, tool_input):
        return
    _record_candidate_hits(state, tool_name, tool_input, text)


def _is_matter_census(tool_name: str, tool_input: dict[str, Any]) -> bool:
    return (
        tool_name == "glob"
        and tool_input.get("pattern") == "*"
        and tool_input.get("entry_type", "files") == "directories"
        and _is_corpus_root(tool_input.get("path"))
    )


def _is_corpus_root(path: Any) -> bool:
    if path is None or path == "":
        return True
    if not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/").rstrip("/").lower()
    return normalized in {"documents", "documents/matters"} or normalized.endswith(
        "/documents/matters"
    ) or normalized.endswith("/documents")


def _is_semantic_candidate_query(tool_name: str, tool_input: dict[str, Any]) -> bool:
    if tool_name == "grep":
        return bool(str(tool_input.get("pattern", "")).strip())
    if tool_input.get("entry_type", "files") == "directories":
        return False
    pattern = str(tool_input.get("pattern", "")).lower()
    tokens = [token for token in re.findall(r"[a-z0-9]+", pattern) if token not in _GENERIC_GLOB_TOKENS]
    return bool(tokens)


def _record_candidate_hits(
    state: dict[str, Any],
    tool_name: str,
    tool_input: dict[str, Any],
    text: str,
) -> None:
    lines = text.splitlines()[1:]
    read_matters = set(state.get("read_matters", []))
    for line in lines:
        path = _path_from_result_line(tool_name, tool_input, line)
        matter = _matter_from_relative_path(path, tool_input.get("path"))
        if matter is None or matter in read_matters:
            continue
        candidates = state["candidates"]
        record = candidates.get(matter)
        if not isinstance(record, dict):
            record = {"paths": [], "hit_count": 0}
            candidates[matter] = record
        record["hit_count"] = int(record.get("hit_count", 0)) + 1
        paths = record.get("paths")
        if not isinstance(paths, list):
            paths = []
            record["paths"] = paths
        if path not in paths and len(paths) < _MAX_PATH_SAMPLES:
            paths.append(path)


def _path_from_result_line(
    tool_name: str, tool_input: dict[str, Any], line: str
) -> str:
    if tool_name == "glob":
        return line.strip()
    mode = tool_input.get("output_mode", "files_with_matches")
    if mode == "count":
        match = re.match(r"^(.*): \d+$", line)
        return match.group(1) if match else line.strip()
    if mode == "content":
        match = re.match(r"^(.*):\d+: ", line)
        return match.group(1) if match else line.strip()
    return line.strip()


def _matter_from_relative_path(path: str, search_path: Any) -> str | None:
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.startswith("workspace/documents/"):
        normalized = normalized[len("workspace/documents/") :]
    elif normalized.startswith("documents/"):
        normalized = normalized[len("documents/") :]
    parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]
    if not parts:
        return None
    search = str(search_path or "").replace("\\", "/").rstrip("/").lower()
    if (not search or search.endswith("/documents") or search == "documents") and parts[0].lower() == "matters":
        parts = parts[1:]
    if len(parts) < 2:
        return None
    return parts[0]


def _matter_from_source(source: str) -> str | None:
    marker = "/documents/"
    normalized = source.replace("\\", "/")
    if marker not in normalized:
        return None
    relative = normalized.split(marker, 1)[1]
    parts = [part for part in relative.split("/") if part]
    if parts and parts[0].lower() == "matters":
        parts = parts[1:]
    return parts[0] if len(parts) >= 2 else None


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


def _merge_intervals(existing: Any, start: int, end: int) -> list[list[int]]:
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


def _build_reminder(state: dict[str, Any], prior_read_chars: int = 0) -> str | None:
    reads = state.get("reads", {})
    queries = state.get("queries", {})
    candidates = state.get("candidates", {})
    deferred = state.get("deferred", {})
    large_batch = prior_read_chars >= _LARGE_READ_BATCH_CHARS
    if not reads and not queries and not candidates and not deferred and not large_batch:
        return None

    lines = [_MARKER]
    if candidates:
        lines.append(
            f"Semantic discovery surfaced {len(candidates)} matter cluster(s) with zero "
            "subsequent source reads. Do not replace this candidate queue with a new broad "
            "search or a hand-picked subset. Add every cluster to the scratch ledger, then "
            "read a primary or status source for each plausible cluster or record a "
            "source-grounded exclusion."
        )
        for matter, record in list(candidates.items())[:_MAX_DISPLAY]:
            samples = record.get("paths", []) if isinstance(record, dict) else []
            sample = samples[0] if isinstance(samples, list) and samples else "path unavailable"
            lines.append(f"- unresolved hit cluster {matter}: {_shorten(str(sample))}")
        if len(candidates) > _MAX_DISPLAY:
            lines.append(f"- plus {len(candidates) - _MAX_DISPLAY} more hit cluster(s)")

    if deferred:
        lines.append(
            f"{len(deferred)} exact source read(s) were deferred with zero text. They remain "
            "unresolved until retried in a later turn; do not classify from the filename."
        )
        for source in list(deferred)[:_MAX_DISPLAY]:
            lines.append(f"- deferred: {_shorten(source)}")
        if len(deferred) > _MAX_DISPLAY:
            lines.append(f"- plus {len(deferred) - _MAX_DISPLAY} more deferred source(s)")

    if large_batch:
        lines.append(
            "The previous assistant turn reached the bounded read-output budget. First "
            "compress returned facts into the source-bound ledger; use the next batch only "
            "for an unresolved candidate, qualifier, or exact deferred source."
        )

    if reads or queries:
        lines.append(
            f"Tool metadata also shows {len(queries)} incompletely paged discovery set(s) "
            f"and {len(reads)} partially read document(s). Continue only ranges that can "
            "change a candidate disposition or requested fact; otherwise record why not."
        )
    if queries:
        lines.append("Open discovery coverage:")
        for record in list(queries.values())[:_MAX_DISPLAY]:
            lines.append(
                f"- {_shorten(str(record.get('label', 'query')))}; covered "
                f"{_format_intervals(record.get('intervals'))} of 0-{record.get('total', '?')}"
            )
        if len(queries) > _MAX_DISPLAY:
            lines.append(f"- plus {len(queries) - _MAX_DISPLAY} more discovery set(s)")
    if reads:
        lines.append("Open document coverage:")
        for source, record in list(reads.items())[:_MAX_DISPLAY]:
            lines.append(
                f"- {_shorten(source)}; covered {_format_intervals(record.get('intervals'))} "
                f"of 0-{record.get('total', '?')} lines"
            )
        if len(reads) > _MAX_DISPLAY:
            lines.append(f"- plus {len(reads) - _MAX_DISPLAY} more document(s)")

    lines.append(
        "The internal candidate ledger is not the user-facing answer set. For a singular "
        "latest, earliest, largest, or selected-matter request, reconcile all candidates "
        "internally but report only the selected answer unless comparison was requested."
    )
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
