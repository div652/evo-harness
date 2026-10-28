"""Regex search over sandbox text files with explicit, stable pagination."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools._common import WorkspaceHandle, is_under, resolve_search_path, run_tool

DEFAULT_PAGE_SIZE = 250
MAX_PAGE_SIZE = 500
OUTPUT_MODES = {"content", "files_with_matches", "count"}


def grep(
    pattern: str,
    agent_state: Any,
    path: str | None = None,
    glob: str | None = None,
    output_mode: str = "files_with_matches",
    offset: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    candidate_discovery: bool = False,
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
            candidate_discovery,
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
    candidate_discovery: bool = False,
) -> str:
    if not pattern_str:
        return "Error: pattern is required"
    if output_mode not in OUTPUT_MODES:
        return "Error: output_mode must be 'content', 'files_with_matches', or 'count'"
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return "Error: offset must be a non-negative integer"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        return f"Error: limit must be an integer from 1 to {MAX_PAGE_SIZE}"
    if not isinstance(candidate_discovery, bool):
        return "Error: candidate_discovery must be true or false"

    sb_path = resolve_search_path(handle, search_path)
    if not handle.exists(sb_path):
        return f"Error: path does not exist: {search_path}"
    try:
        regex = re.compile(pattern_str)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"

    host_root = handle.to_host(sb_path)
    root_resolved = host_root.resolve(strict=False)
    candidates: list[tuple[str, Path]] = []
    for file_path in host_root.glob(file_glob or "**/*"):
        if not file_path.is_file() or not is_under(file_path, root_resolved):
            continue
        relative = str(file_path.relative_to(host_root))
        candidates.append((relative, file_path))
    candidates.sort(key=lambda item: (item[0].casefold(), item[0]))

    results: list[str] = []
    for relative, file_path in candidates:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        matches = list(regex.finditer(text))
        if not matches:
            continue
        if output_mode == "files_with_matches":
            results.append(relative)
        elif output_mode == "count":
            results.append(f"{relative}: {len(matches)}")
        else:
            for number, line in enumerate(text.split("\n"), start=1):
                if regex.search(line):
                    results.append(f"{relative}:{number}: {line}")

    total = len(results)
    page = results[offset : offset + limit]
    end = offset + len(page)
    truncated = end < total
    next_offset = str(end) if truncated else "none"
    header = (
        f"Grep page: shown={len(page)} total={total} offset={offset} limit={limit} "
        f"truncated={'true' if truncated else 'false'} next_offset={next_offset} "
        f"output_mode={output_mode} "
        f"candidate_discovery={'true' if candidate_discovery else 'false'}"
    )
    if not page:
        return header
    return "\n".join([header, *page])
