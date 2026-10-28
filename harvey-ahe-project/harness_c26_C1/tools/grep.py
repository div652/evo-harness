"""Regex search over sandbox files with explicit pagination metadata."""

from __future__ import annotations

import re
from typing import Any

from tools._common import WorkspaceHandle, is_under, resolve_search_path, run_tool

DEFAULT_PAGE_SIZE = 250
MAX_PAGE_SIZE = 500
_OUTPUT_MODES = {"files_with_matches", "count", "content"}


def grep(
    pattern: str,
    agent_state: Any,
    path: str | None = None,
    glob: str | None = None,
    output_mode: str = "files_with_matches",
    offset: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
) -> str:
    return run_tool(
        agent_state,
        lambda handle: _grep(
            handle,
            pattern,
            path,
            glob,
            output_mode,
            offset,
            limit,
        ),
    )


def _grep(
    handle: WorkspaceHandle,
    pattern_str: str,
    search_path: str | None,
    file_glob: str | None,
    output_mode: str,
    offset: int,
    limit: int,
) -> str:
    if not pattern_str:
        return "Error: pattern is required"
    if output_mode not in _OUTPUT_MODES:
        return "Error: output_mode must be content, files_with_matches, or count"
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        return "Error: offset must be a non-negative integer"
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
        or limit > MAX_PAGE_SIZE
    ):
        return f"Error: limit must be an integer from 1 to {MAX_PAGE_SIZE}"

    sb_path = resolve_search_path(handle, search_path)
    if not handle.exists(sb_path):
        return f"Error: path does not exist: {search_path}"
    try:
        regex = re.compile(pattern_str)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"

    host_root = handle.to_host(sb_path)
    root_resolved = host_root.resolve(strict=False)
    file_paths = sorted(
        (
            file_path
            for file_path in host_root.glob(file_glob or "**/*")
            if file_path.is_file() and is_under(file_path, root_resolved)
        ),
        key=lambda file_path: str(file_path.relative_to(host_root)),
    )

    results: list[str] = []
    for file_path in file_paths:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        matches = list(regex.finditer(text))
        if not matches:
            continue
        relative = str(file_path.relative_to(host_root))
        if output_mode == "files_with_matches":
            results.append(relative)
        elif output_mode == "count":
            results.append(f"{relative}: {len(matches)}")
        else:
            for number, line in enumerate(text.split("\n"), start=1):
                if regex.search(line):
                    results.append(f"{relative}:{number}: {line}")

    if not results:
        return f"No matches for '{pattern_str}'\nSearch status: COMPLETE"

    total = len(results)
    page = results[offset : offset + limit]
    end = offset + len(page)
    partial = end < total
    status = "PARTIAL" if partial else "COMPLETE"
    shown = f"{offset + 1}-{end}" if page else "none"
    next_offset = str(end) if partial else "none"
    lines = [
        f"Search status: {status}",
        f"total_results: {total}",
        f"showing: {shown}",
        f"next_offset: {next_offset}",
    ]
    if partial:
        lines.append(
            "WARNING: This is only one page, not a complete result set. "
            "Use next_offset or narrow/partition the search before drawing conclusions."
        )
    elif not page:
        lines.append("No results on this page; offset is at or beyond total_results.")
    lines.extend(page)
    return "\n".join(lines)
