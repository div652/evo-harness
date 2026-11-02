"""Deterministically bound model-facing tool output to protect the context window."""

from __future__ import annotations

from typing import Any

from nexau.archs.main_sub.execution.hooks import AfterToolHookInput, HookResult, Middleware


class BoundedToolOutput(Middleware):
    """Clip unexpectedly large string results while preserving useful boundaries."""

    def __init__(
        self,
        max_chars: int = 60000,
        head_chars: int = 30000,
        tail_chars: int = 10000,
    ) -> None:
        if max_chars < 1000:
            raise ValueError("max_chars must be at least 1000")
        if head_chars < 1 or tail_chars < 1:
            raise ValueError("head_chars and tail_chars must be positive")
        if head_chars + tail_chars >= max_chars:
            raise ValueError("head_chars plus tail_chars must be less than max_chars")
        self.max_chars = max_chars
        self.head_chars = head_chars
        self.tail_chars = tail_chars

    def after_tool(self, hook_input: AfterToolHookInput) -> HookResult:
        output = hook_input.tool_output
        clipped = self._clip_output(output, hook_input.tool_name)
        if clipped is output:
            return HookResult.no_changes()
        return HookResult.with_modifications(tool_output=clipped)

    def _clip_output(self, output: Any, tool_name: str) -> Any:
        if isinstance(output, str):
            return self._clip_text(output, tool_name)
        if not isinstance(output, dict):
            return output

        changed = dict(output)
        modified = False
        for key in ("result", "content", "returnDisplay"):
            value = changed.get(key)
            if isinstance(value, str):
                bounded = self._clip_text(value, tool_name)
                if bounded != value:
                    changed[key] = bounded
                    modified = True
        return changed if modified else output

    def _clip_text(self, text: str, tool_name: str) -> str:
        if len(text) <= self.max_chars:
            return text
        omitted = len(text) - self.head_chars - self.tail_chars
        marker = (
            "\n\n[OUTPUT TRUNCATED BY HARNESS: "
            f"tool={tool_name}; original_chars={len(text)}; omitted_chars={omitted}. "
            "This result is partial and must not be treated as complete. Narrow the "
            "scope, redirect bulk output to a /workspace scratch file, then inspect "
            "bounded portions with read offset/limit or targeted searches.]\n\n"
        )
        return text[: self.head_chars] + marker + text[-self.tail_chars :]
