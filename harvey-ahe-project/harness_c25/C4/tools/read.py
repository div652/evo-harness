"""Read a sandbox file; office documents and PDFs are parsed in the sandbox."""

from __future__ import annotations

import shlex
from pathlib import PurePosixPath
from typing import Any

from tools._common import WorkspaceHandle, resolve_read_path, run_tool

PARSED_EXTENSIONS = ("docx", "pdf", "pptx", "xlsx")
PARSE_TIMEOUT_SECONDS = 120
MAX_LINES_PER_RESULT = 800
MAX_CHARS_PER_RESULT = 40_000
MAX_READ_CHARS_PER_TURN = 120_000
MIN_USEFUL_RESULT_CHARS = 2_000
_READ_BUDGET_KEY = "harvey_read_turn_chars_v1"


def read(
    file_path: str,
    agent_state: Any,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    def operation(handle: WorkspaceHandle) -> str:
        used = _budget_used(agent_state)
        remaining = max(0, MAX_READ_CHARS_PER_TURN - used)
        result = _read(handle, file_path, offset, limit, remaining)
        agent_state.set_global_value(_READ_BUDGET_KEY, used + len(result))
        return result

    return run_tool(agent_state, operation)


def _budget_used(agent_state: Any) -> int:
    value = agent_state.get_global_value(_READ_BUDGET_KEY, 0)
    return value if isinstance(value, int) and value >= 0 else 0


def _read(
    handle: WorkspaceHandle,
    file_path: str,
    offset: int | None,
    limit: int | None,
    remaining_chars: int | None = None,
) -> str:
    if not file_path:
        return "Error: file_path is required"
    if offset is not None and offset < 0:
        return "Error: offset must be zero or greater"
    if limit is not None and limit < 1:
        return "Error: limit must be greater than zero"
    sb_path = resolve_read_path(handle, file_path)
    if not handle.exists(sb_path):
        return f"Error: file not found: {file_path}"
    start = offset or 0
    if remaining_chars is not None and remaining_chars < MIN_USEFUL_RESULT_CHARS:
        return _deferred_result(sb_path, start)
    content = _read_and_parse(handle, sb_path)
    char_cap = MAX_CHARS_PER_RESULT
    if remaining_chars is not None:
        char_cap = min(char_cap, remaining_chars)
    return _format_result(
        sb_path,
        content,
        offset,
        limit,
        max_lines=MAX_LINES_PER_RESULT,
        max_chars=char_cap,
    )


def _deferred_result(sb_path: str, start: int) -> str:
    return (
        "[read_result]\n"
        f"source: {sb_path}\n"
        "status: deferred\n"
        f"lines: {start}-{start} of 0 (end exclusive)\n"
        "complete: false\n"
        f"next_offset: {start}\n"
        "limited_by: aggregate_turn_character_budget\n"
        "[/read_result]\n"
        "Read deferred because this assistant turn has already returned the safe "
        "aggregate amount of document text. Do not retry in the same batch. First "
        "synthesize the evidence already returned into the candidate ledger; on the "
        "next turn, request only the source and range needed to resolve a specific gap."
    )


def _format_result(
    sb_path: str,
    content: str,
    offset: int | None,
    limit: int | None,
    *,
    max_lines: int | None = None,
    max_chars: int | None = None,
) -> str:
    """Bind content to its source and expose every imposed line-window limit."""
    lines = content.split("\n")
    total_lines = len(lines)
    start = min(offset or 0, total_lines)
    requested_end = start + limit if limit is not None else total_lines
    end = min(requested_end, total_lines)
    limit_reasons: list[str] = []
    if max_lines is not None and end > start + max_lines:
        end = start + max_lines
        limit_reasons.append("per_result_line_cap")

    failed = content.startswith("Error:")
    if not failed and max_chars is not None:
        char_end = _end_for_character_cap(lines, start, end, max_chars)
        if char_end < end:
            end = char_end
            limit_reasons.append("per_result_or_turn_character_cap")

    # A single unusually long parsed line cannot be split with line-based offsets
    # without silently losing provenance. Return a typed error and let the agent use
    # a targeted sandbox extraction rather than injecting the giant line.
    oversized_line = not failed and start < total_lines and end == start
    if oversized_line:
        header = (
            "[read_result]\n"
            f"source: {sb_path}\n"
            "status: error\n"
            f"lines: {start}-{start} of {total_lines} (end exclusive)\n"
            "complete: false\n"
            f"next_offset: {start}\n"
            "limited_by: oversized_single_line\n"
            "[/read_result]"
        )
        return (
            f"{header}\nError: parsed line {start} exceeds the safe result size. "
            "Use bash with a targeted parser/search for the needed field; do not "
            "request the same broad read again."
        )

    truncated = end < total_lines
    page = "\n".join(lines[start:end])
    next_offset = str(end) if truncated and not failed else "none"
    if failed:
        status = "error"
        complete = False
        limited_by = "parser_or_read_error"
    else:
        status = "ok"
        complete = not truncated
        limited_by = ",".join(limit_reasons) if limit_reasons else "none"
    header = (
        "[read_result]\n"
        f"source: {sb_path}\n"
        f"status: {status}\n"
        f"lines: {start}-{end} of {total_lines} (end exclusive)\n"
        f"complete: {str(complete).lower()}\n"
        f"next_offset: {next_offset}\n"
        f"limited_by: {limited_by}\n"
        "[/read_result]"
    )
    return f"{header}\n{page}"


def _end_for_character_cap(
    lines: list[str], start: int, end: int, max_chars: int
) -> int:
    used = 0
    cursor = start
    while cursor < end:
        addition = len(lines[cursor]) + (1 if cursor > start else 0)
        if used + addition > max_chars:
            break
        used += addition
        cursor += 1
    return cursor


def _read_and_parse(handle: WorkspaceHandle, sb_path: str) -> str:
    ext = PurePosixPath(sb_path).suffix.lower()[1:]
    if ext in PARSED_EXTENSIONS:
        return _parse_in_sandbox(handle, ext, sb_path)
    try:
        return handle.read_file(sb_path).decode("utf-8", errors="replace")
    except IsADirectoryError:
        return f"Error: {sb_path} is a directory, not a file"
    except OSError as exc:
        return f"Error: failed to read {sb_path}: {type(exc).__name__}: {exc}"


def _parse_in_sandbox(handle: WorkspaceHandle, ext: str, sb_path: str) -> str:
    result = handle.exec(
        f"parse-doc {ext} {shlex.quote(sb_path)}",
        timeout=PARSE_TIMEOUT_SECONDS,
    )
    if result.timed_out:
        return f"Error: parser timed out on {sb_path} ({ext})"
    if result.returncode != 0:
        err = (result.stderr or "").strip().splitlines()
        tail = err[-1] if err else f"exit {result.returncode}"
        return f"Error: failed to parse {sb_path} ({ext}): {tail}"
    return result.stdout
