"""Keep unresolved paged discovery and document reads salient across turns."""

from __future__ import annotations

import json
import re
from typing import Any

from nexau.archs.main_sub.execution.hooks import HookResult, Middleware
from nexau.core.messages import Message, Role, TextBlock

_STATE_KEY = "harvey_coverage_state_v1"
_MARKER = "[Coverage-state reminder]"
_MAX_DISPLAY = 6
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
            reminder = _build_reminder(state)
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


def _result_text(tool_output: Any) -> str | None:
    if isinstance(tool_output, dict):
        value = tool_output.get("result")
        return value if isinstance(value, str) else None
    return tool_output if isinstance(tool_output, str) else None


def _load_state(agent_state: Any) -> dict[str, dict[str, Any]]:
    value = agent_state.get_global_value(_STATE_KEY, None)
    if not isinstance(value, dict):
        return {"reads": {}, "queries": {}}
    reads = value.get("reads")
    queries = value.get("queries")
    return {
        "reads": reads if isinstance(reads, dict) else {},
        "queries": queries if isinstance(queries, dict) else {},
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


def _build_reminder(state: dict[str, dict[str, Any]]) -> str | None:
    reads = state.get("reads", {})
    queries = state.get("queries", {})
    if not reads and not queries:
        return None
    lines = [
        _MARKER,
        (
            f"Tool metadata still shows {len(queries)} incompletely paged discovery "
            f"set(s) and {len(reads)} partially read document(s). These are coverage "
            "warnings, not proof that every remainder is relevant."
        ),
        (
            "Before a corpus-wide, negative, comparative, or superlative conclusion—and "
            "before drafting or finishing—continue relevant missing ranges (or narrow the "
            "search), disposition every surfaced candidate in the scratch ledger, and "
            "carry each included candidate's requested proof paths into the deliverable. "
            "A candidate used to include, exclude, or rank must not rest on an unread "
            "range. If a remainder truly cannot affect the decision, record the "
            "source-grounded reason in the ledger rather than silently dropping it."
        ),
    ]
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
