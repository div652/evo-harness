"""Find sandbox entries by glob pattern with explicit, stable pagination."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools._common import WorkspaceHandle, is_under, resolve_search_path, run_tool

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
ENTRY_TYPES = {"files", "directories", "all"}


def glob(
    pattern: str,
    agent_state: Any,
    path: str | None = None,
    offset: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    entry_type: str = "files",
) -> str:
    return run_tool(
        agent_state,
        lambda handle: _glob(handle, pattern, path, offset, limit, entry_type),
    )


def _glob(
    handle: WorkspaceHandle,
    pattern: str,
    search_path: str | None,
    offset: int,
    limit: int,
    entry_type: str,
) -> str:
    if not pattern:
        return "Error: pattern is required"
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return "Error: offset must be a non-negative integer"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        return f"Error: limit must be an integer from 1 to {MAX_PAGE_SIZE}"
    if entry_type not in ENTRY_TYPES:
        return "Error: entry_type must be 'files', 'directories', or 'all'"

    sb_path = resolve_search_path(handle, search_path)
    if not handle.exists(sb_path):
        return f"Error: path does not exist: {search_path}"
    host_root = handle.to_host(sb_path)
    if not host_root.exists():
        return f"Error: path does not exist: {search_path}"
    root_resolved = host_root.resolve(strict=False)

    entries: list[tuple[Path, str, int]] = []
    for match in host_root.glob(pattern):
        if not is_under(match, root_resolved):
            continue
        is_file = match.is_file()
        is_directory = match.is_dir()
        if entry_type == "files" and not is_file:
            continue
        if entry_type == "directories" and not is_directory:
            continue
        if entry_type == "all" and not (is_file or is_directory):
            continue
        try:
            modified_ns = match.stat().st_mtime_ns
        except OSError:
            continue
        relative = str(match.relative_to(host_root))
        entries.append((match, relative, modified_ns))

    # Newest-first behavior is preserved, with a relative-path tie-breaker so
    # offsets identify deterministic, non-overlapping pages in this read-only tree.
    entries.sort(key=lambda item: (-item[2], item[1].casefold(), item[1]))
    total = len(entries)
    page = entries[offset : offset + limit]
    end = offset + len(page)
    truncated = end < total
    next_offset = str(end) if truncated else "none"

    header = (
        f"Glob page: shown={len(page)} total={total} offset={offset} limit={limit} "
        f"truncated={'true' if truncated else 'false'} next_offset={next_offset} "
        f"entry_type={entry_type}"
    )
    if not page:
        return header
    return "\n".join([header, *(item[1] for item in page)])
