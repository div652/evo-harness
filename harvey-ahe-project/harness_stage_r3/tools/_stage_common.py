"""Shared state, reference data and critic calls for the stage protocol.

This file is kept identical (except the reference-file path) with
its twin (`tools/_stage_common.py` / `middleware/stage_common.py`): the harness conformance check attributes every
local module a tool imports to tool_implementations and every module a
middleware imports to middleware, so tools and middleware each need their
own copy.

Per-trial state lives in the agent state's global storage (several trials
run concurrently in one process), never in module globals. The critic and
the stage-fit checker are a different model from the evaluated one, reached
through the local CAO gateway (OpenAI-compatible chat completions).
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

STATE_KEY = "harvey_stage_state_v1"
STAGE_TOOLS = {"stage_start", "stage_end"}
NEW_STAGE = "new"
_REFERENCE_DOC = json.loads(
    (Path(__file__).parent.parent / "middleware" / "stage_reference.json").read_text(encoding="utf-8")
)
_REFERENCE = _REFERENCE_DOC["stages"]
STAGE_NAMES = list(_REFERENCE)

# Surfaced-but-not-opened tracking (benchmark-specific entity; see the
# "surfaced_not_opened" block of stage_reference.json).
SNO = _REFERENCE_DOC.get("surfaced_not_opened") or {"enabled": False}
SNO_ENABLED = bool(SNO.get("enabled")) and bool(SNO.get("entity_regex"))
ENTITY = re.compile(SNO["entity_regex"]) if SNO_ENABLED else None
SNO_MAX = int(SNO.get("max_entities_for_hit_list", 150))
SNO_STAGES = set(SNO.get("show_at_stages", []))
ENTITY_NAME = str(SNO.get("entity", "entity"))

CRITIC_URL = os.environ.get("STAGE_CRITIC_URL", "http://127.0.0.1:4141/v1/chat/completions")
CRITIC_MODEL = os.environ.get("STAGE_CRITIC_MODEL", "claude-sonnet-5-5")
FIT_MODEL = os.environ.get("STAGE_FIT_MODEL", "claude-haiku-5-5")
CRITIC_TIMEOUT = float(os.environ.get("STAGE_CRITIC_TIMEOUT", "180"))


def reference(stage: str) -> dict[str, Any] | None:
    return _REFERENCE.get(stage)


def load_state(agent_state: Any) -> dict[str, Any]:
    value = agent_state.get_global_value(STATE_KEY, None)
    if not isinstance(value, dict):
        value = {
            "open": None,          # {"stage", "label", "goal", "attempt", "calls": [...]}
            "history": [],         # closed stages: {"stage","label","goal","attempt","goal_reached","n_calls"}
            "request": "",
            "blocked_ids": [],
            "surfaced": {},        # matter -> first stage label where a search result showed it
            "opened": [],          # matters with a document read or listed
        }
    return value


def save_state(agent_state: Any, state: dict[str, Any]) -> None:
    agent_state.set_global_value(STATE_KEY, state)


def chat(model: str, system: str, user: str, max_tokens: int = 900) -> str:
    """One chat-completions call to the critic gateway; raises on failure."""
    key = os.environ.get("CAO_API_KEY", "")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        CRITIC_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=CRITIC_TIMEOUT) as response:
        payload = json.load(response)
    return str(payload["choices"][0]["message"]["content"] or "")


def parse_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def result_text(tool_output: Any) -> str:
    if isinstance(tool_output, dict):
        for key in ("result", "error", "content"):
            value = tool_output.get(key)
            if isinstance(value, str):
                return value
        return json.dumps(tool_output, ensure_ascii=False)[:20000]
    return tool_output if isinstance(tool_output, str) else str(tool_output)


def short(text: Any, limit: int) -> str:
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + f" …(+{len(text) - limit} chars)"
