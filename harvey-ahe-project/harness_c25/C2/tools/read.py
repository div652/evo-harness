"""Read a sandbox file; office documents and PDFs are parsed in the sandbox."""

from __future__ import annotations

import shlex
from pathlib import PurePosixPath
from typing import Any

from tools._common import WorkspaceHandle, resolve_read_path, run_tool

PARSED_EXTENSIONS = ("docx", "pdf", "pptx", "xlsx")
PARSE_TIMEOUT_SECONDS = 120


def read(
    file_path: str,
    agent_state: Any,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    return run_tool(agent_state, lambda handle: _read(handle, file_path, offset, limit))


def _read(
    handle: WorkspaceHandle,
    file_path: str,
    offset: int | None,
    limit: int | None,
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
    content = _read_and_parse(handle, sb_path)
    return _format_result(sb_path, content, offset, limit)


def _format_result(
    sb_path: str,
    content: str,
    offset: int | None,
    limit: int | None,
) -> str:
    """Bind content to its source and make any line-window truncation explicit."""
    lines = content.split("\n")
    total_lines = len(lines)
    start = min(offset or 0, total_lines)
    requested_end = start + limit if limit is not None else total_lines
    end = min(requested_end, total_lines)
    truncated = end < total_lines
    failed = content.startswith("Error:")
    page = "\n".join(lines[start:end])
    next_offset = str(end) if truncated and not failed else "none"
    header = (
        "[read_result]\n"
        f"source: {sb_path}\n"
        f"status: {'error' if failed else 'ok'}\n"
        f"lines: {start}-{end} of {total_lines} (end exclusive)\n"
        f"complete: {str(not truncated and not failed).lower()}\n"
        f"next_offset: {next_offset}\n"
        "[/read_result]"
    )
    return f"{header}\n{page}"


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
