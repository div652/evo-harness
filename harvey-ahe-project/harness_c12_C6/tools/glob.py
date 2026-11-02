"""Find sandbox paths by glob pattern with explicit, deterministic pagination."""

from __future__ import annotations

from typing import Any

from tools._common import WorkspaceHandle, is_under, resolve_search_path, run_tool

DEFAULT_LIMIT = 100
MAX_LIMIT = 500
VALID_ITEM_TYPES = {"files", "directories", "all"}


def glob(
    pattern: str,
    agent_state: Any,
    path: str | None = None,
    offset: int = 0,
    limit: int = DEFAULT_LIMIT,
    item_type: str = "files",
) -> str:
    return run_tool(
        agent_state,
        lambda handle: _glob(handle, pattern, path, offset, limit, item_type),
    )


def _glob(
    handle: WorkspaceHandle,
    pattern: str,
    search_path: str | None,
    offset: int,
    limit: int,
    item_type: str,
) -> str:
    if not pattern:
        return "Error: pattern is required"
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return "Error: offset must be a non-negative integer"
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
        or limit > MAX_LIMIT
    ):
        return f"Error: limit must be an integer from 1 to {MAX_LIMIT}"
    if item_type not in VALID_ITEM_TYPES:
        return "Error: item_type must be one of: files, directories, all"

    sb_path = resolve_search_path(handle, search_path)
    if not handle.exists(sb_path):
        return f"Error: path does not exist: {search_path}"
    host_root = handle.to_host(sb_path)
    if not host_root.exists():
        return f"Error: path does not exist: {search_path}"
    root_resolved = host_root.resolve(strict=False)

    def selected(match: Any) -> bool:
        if not is_under(match, root_resolved):
            return False
        if item_type == "files":
            return match.is_file()
        if item_type == "directories":
            return match.is_dir()
        return match.is_file() or match.is_dir()

    matches = sorted(
        (match for match in host_root.glob(pattern) if selected(match)),
        key=lambda match: str(match.relative_to(host_root)).casefold(),
    )
    total = len(matches)
    if not matches:
        return (
            f"No {item_type} matching '{pattern}' in {sb_path}. "
            "This is a complete result (0 matches)."
        )
    if offset >= total:
        return (
            f"Glob page is empty: offset {offset} is beyond {total} total "
            f"{item_type} matching '{pattern}' in {sb_path}."
        )

    page = matches[offset : offset + limit]
    end = offset + len(page)
    header = (
        f"Glob results {offset + 1}-{end} of {total} {item_type} matching "
        f"'{pattern}' in {sb_path}."
    )
    if end < total:
        header += (
            f" TRUNCATED: {total - end} matches remain; call glob again with "
            f"offset={end} (and the same pattern, path, and item_type)."
        )
    else:
        header += " COMPLETE: no matches remain."

    paths = "\n".join(str(match.relative_to(host_root)) for match in page)
    return f"{header}\n{paths}"
