"""Find sandbox files by glob pattern with explicit pagination metadata."""

from __future__ import annotations

from typing import Any

from tools._common import WorkspaceHandle, is_under, resolve_search_path, run_tool

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def glob(
    pattern: str,
    agent_state: Any,
    path: str | None = None,
    offset: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
) -> str:
    return run_tool(
        agent_state,
        lambda handle: _glob(handle, pattern, path, offset, limit),
    )


def _glob(
    handle: WorkspaceHandle,
    pattern: str,
    search_path: str | None,
    offset: int,
    limit: int,
) -> str:
    if not pattern:
        return "Error: pattern is required"
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
    host_root = handle.to_host(sb_path)
    if not host_root.exists():
        return f"Error: path does not exist: {search_path}"
    root_resolved = host_root.resolve(strict=False)

    matches = sorted(
        str(match.relative_to(host_root))
        for match in host_root.glob(pattern)
        if match.is_file() and is_under(match, root_resolved)
    )
    if not matches:
        return f"No files matching '{pattern}' in {sb_path}\nSearch status: COMPLETE"

    total = len(matches)
    page = matches[offset : offset + limit]
    end = offset + len(page)
    partial = end < total
    status = "PARTIAL" if partial else "COMPLETE"
    shown = f"{offset + 1}-{end}" if page else "none"
    next_offset = str(end) if partial else "none"
    lines = [
        f"Search status: {status}",
        f"total_matches: {total}",
        f"showing: {shown}",
        f"next_offset: {next_offset}",
    ]
    if partial:
        lines.append(
            "WARNING: This is only one page, not a complete inventory. "
            "Use next_offset or narrow/partition the pattern before drawing conclusions."
        )
    elif not page:
        lines.append("No results on this page; offset is at or beyond total_matches.")
    lines.extend(page)
    return "\n".join(lines)
