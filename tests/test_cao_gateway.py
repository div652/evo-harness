"""Contract tests for running campaigns through the local CAO gateway.

CAO (npm @jeffreycao/copilot-api) serves Copilot models on an OpenAI
Responses endpoint at http://127.0.0.1:4141/v1. These tests drive the
runner's own code paths against it: the model preflight, the recorded
client, an evaluated-agent session with protected and internal tool calls,
the Responses rubric judge, error classification and concurrent calls.

Three modes, chosen by AHE_CAO_MODE:

- unset or ``replay`` (default): replay the HTTP exchanges saved in
  tests/fixtures/cao/ through httpx, offline. A test without a fixture is
  skipped.
- ``record``: send real requests to CAO and save the exchanges (bodies only;
  request headers, and with them the gateway key, are never saved). Costs
  roughly 25 Copilot premium requests.
- ``live``: send real requests and save nothing.

Live and record modes read the gateway key from CAO_API_KEY or
/home/agarwaldi/cao/profile/.gateway-key and check that CAO is signed in as
AHE_CAO_EXPECTED_LOGIN before any model request.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
import httpx2
import openai
import pytest

from ahe_runner.adapter import BenchmarkInterface, BenchmarkToolSpec
from ahe_runner.config import ModelSettings, TransportSettings, load_config
from ahe_runner.errors import InfrastructureError
from ahe_runner.harness import load_harness_manifest
from ahe_runner.meta.model_client import (
    RecordedExactModelClient,
    is_infrastructure_exception,
    is_transient_exception,
)
from ahe_runner.meta.preflight import run_model_preflight
from ahe_runner.runtime import (
    AgentInput,
    AgentInputMessage,
    AgentSessionRequest,
    EvaluatedAgentRuntime,
)

from .conftest import make_example_project

MODE = os.environ.get("AHE_CAO_MODE", "replay")
BASE = os.environ.get("AHE_CAO_BASE", "http://127.0.0.1:4141")
AGENT_MODEL = os.environ.get("AHE_CAO_AGENT_MODEL", "gpt-5.6-sol")
JUDGE_MODEL = os.environ.get("AHE_CAO_JUDGE_MODEL", "gpt-6.1-sol")
EXPECTED_LOGIN = os.environ.get("AHE_CAO_EXPECTED_LOGIN", "agarwaldi_microsoft")
KEY_FILE = Path("/home/agarwaldi/cao/profile/.gateway-key")
FIXTURES = Path(__file__).parent / "fixtures" / "cao"
NEGATIVE_MODEL = re.compile(r"ahe-negative-control-[0-9a-f]{32}")
# Response headers worth keeping in a fixture; everything else is dropped.
KEPT_HEADERS = ("content-type", "retry-after", "x-request-id")

assert MODE in {"replay", "record", "live"}, f"unknown AHE_CAO_MODE {MODE!r}"


def _api_key() -> str:
    if MODE == "replay":
        return "replay-placeholder-key"
    key = os.environ.get("CAO_API_KEY") or (
        KEY_FILE.read_text(encoding="utf-8").strip() if KEY_FILE.exists() else ""
    )
    if not key:
        pytest.skip("no CAO gateway key (CAO_API_KEY or the key file)")
    return key


class _Exchanges:
    """Record or replay every httpx request a test sends."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.saved: list[dict[str, Any]] = []
        self.queue: list[dict[str, Any]] = []
        if MODE == "replay":
            if not path.exists():
                pytest.skip(f"no CAO fixture {path.name}; run with AHE_CAO_MODE=record")
            self.queue = json.loads(path.read_text(encoding="utf-8"))

    def handle(self, lib: Any, real: Any, transport: Any, request: Any) -> Any:
        body = _json_or_text(request.content)
        if MODE == "replay":
            return self._replay(lib, request, body)
        response = real(transport, request)
        content = response.read()
        headers = {
            name: value
            for name, value in response.headers.items()
            if name.lower() in KEPT_HEADERS
        }
        if MODE == "record":
            with self.lock:
                self.saved.append(
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "request": body,
                        "status": response.status_code,
                        "headers": headers,
                        "body": content.decode("utf-8", errors="replace"),
                    }
                )
        return lib.Response(
            response.status_code, headers=headers, content=content, request=request
        )

    def _replay(self, lib: Any, request: Any, body: Any) -> Any:
        with self.lock:
            # Prefer the exchange with the same request body (parallel calls
            # arrive in any order); else the next one for the same path, as
            # agent prompts embed per-run temporary paths.
            same_path = [
                i
                for i, row in enumerate(self.queue)
                if row["method"] == request.method and row["path"] == request.url.path
            ]
            wanted = _normalized(body)
            index = next(
                (i for i in same_path if _normalized(self.queue[i]["request"]) == wanted),
                same_path[0] if same_path else None,
            )
            assert index is not None, (
                f"unexpected {request.method} {request.url.path}: no recorded "
                "exchange left for it"
            )
            row = self.queue.pop(index)
        content = row["body"]
        # The negative control names a fresh random model each run.
        sent = NEGATIVE_MODEL.search(json.dumps(body)) if body is not None else None
        if sent:
            content = NEGATIVE_MODEL.sub(sent.group(0), content)
        return lib.Response(
            row["status"],
            headers=row["headers"],
            content=content.encode("utf-8"),
            request=request,
        )

    def finish(self, passed: bool) -> None:
        if MODE == "record" and passed:
            assert self.saved, "the test sent no request through the recorder"
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.saved, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if MODE == "replay" and passed:
            assert not self.queue, f"{len(self.queue)} recorded exchanges were not used"


def _normalized(body: Any) -> str:
    return NEGATIVE_MODEL.sub("ahe-negative-control-*", json.dumps(body, sort_keys=True))


def _json_or_text(content: bytes) -> Any:
    if not content:
        return None
    try:
        return json.loads(content)
    except ValueError:
        return content.decode("utf-8", errors="replace")


@pytest.fixture
def cao(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Route every HTTP request of the test through the recorder.

    The openai SDK (3.x) sends through ``httpx2``; plain ``httpx`` is hooked
    too for direct calls. A test that sends nothing it could replay fails.
    """
    exchanges = _Exchanges(FIXTURES / f"{request.node.name}.json")
    if MODE != "replay":
        _require_expected_identity()
    for lib in (httpx, httpx2):
        real = lib.HTTPTransport.handle_request

        def handle_request(
            self: Any, req: Any, _lib: Any = lib, _real: Any = real
        ) -> Any:
            return exchanges.handle(_lib, _real, self, req)

        monkeypatch.setattr(lib.HTTPTransport, "handle_request", handle_request)
    yield
    report = getattr(request.node, "rep_call", None)
    exchanges.finish(bool(report and report.passed))


def _require_expected_identity() -> None:
    """Fail closed before any model request if CAO is the wrong account."""
    response = httpx.get(
        f"{BASE}/usage",
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=30,
    )
    if response.status_code != 200:
        pytest.fail(f"CAO /usage returned HTTP {response.status_code}")
    login = response.json().get("login")
    if login != EXPECTED_LOGIN:
        pytest.fail(f"CAO is signed in as {login!r}, expected {EXPECTED_LOGIN!r}")


def _transport(**updates: Any) -> TransportSettings:
    values: dict[str, Any] = {
        "provider": "gh_copilot_server",
        "base_url": f"{BASE}/v1",
        "api_key_env": "CAO_API_KEY",
        "api_mode": "responses",
        "stream": False,
        "request_timeout_seconds": 600,
        "observable_model_policy": "exact",
        "model_catalog": "required",
        "negative_control": "required",
        "max_concurrent_requests": 12,
        "hung_call_retries": 1,
        "transient_retries": 2,
        "transient_max_wait_seconds": 30,
    }
    values.update(updates)
    return TransportSettings(**values)


def _agent_settings() -> ModelSettings:
    # Campaign 19's evaluated-agent settings.
    return ModelSettings(
        model=AGENT_MODEL, max_tokens=32768, reasoning_effort="high", temperature=None
    )


def _judge_settings() -> ModelSettings:
    # Campaign 19's single judge.
    return ModelSettings(
        model=JUDGE_MODEL, max_tokens=8192, reasoning_effort="high", temperature=None
    )


def _call_records(root: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """(request.json, response.json) of each recorded model call, in order."""
    pairs = []
    for request_path in sorted(root.rglob("call-*/request.json")):
        response_path = request_path.with_name("response.json")
        assert response_path.exists(), f"no response recorded for {request_path}"
        pairs.append(
            (
                json.loads(request_path.read_text(encoding="utf-8")),
                json.loads(response_path.read_text(encoding="utf-8")),
            )
        )
    return pairs


# --- configuration and identity -------------------------------------------


def test_cao_transport_settings_validate() -> None:
    transport = _transport()
    assert transport.provider == "gh_copilot_server"
    assert transport.api_mode == "responses"
    assert transport.base_url == f"{BASE}/v1"


def test_identity_and_catalog(cao: None) -> None:
    key = _api_key()
    usage = httpx.get(f"{BASE}/usage", headers={"Authorization": f"Bearer {key}"})
    assert usage.status_code == 200
    assert usage.json()["login"] == EXPECTED_LOGIN
    catalog = openai.OpenAI(base_url=f"{BASE}/v1", api_key=key).models.list()
    ids = {model.id for model in catalog.data}
    assert {AGENT_MODEL, JUDGE_MODEL} <= ids


# --- preflight ----------------------------------------------------------------


@pytest.mark.parametrize("which", ["agent", "judge"])
def test_preflight_passes(cao: None, tmp_path: Path, which: str) -> None:
    settings = _agent_settings() if which == "agent" else _judge_settings()
    report = run_model_preflight(
        transport=_transport(),
        api_key=_api_key(),
        settings=settings,
        output_path=tmp_path / "preflight.json",
    )
    assert report["status"] == "completed"
    assert settings.model in report["advertised_model_ids"]
    assert report["positive_probe"]["passed"] is True
    assert report["positive_probe"]["returned_model"] == settings.model
    assert report["positive_probe"]["status"] == "completed"
    assert report["negative_control"]["passed"] is True


# --- recorded client ------------------------------------------------------


def test_recorded_client_returns_exact_model_and_reasoning(
    cao: None, tmp_path: Path
) -> None:
    client = RecordedExactModelClient(
        transport=_transport(),
        api_key=_api_key(),
        settings=_agent_settings(),
        log_dir=tmp_path / "calls",
    )
    response = client.responses.create(
        model=AGENT_MODEL,
        # Hard enough that the model reasons; trivial prompts get no
        # reasoning item at all (0 reasoning tokens).
        input=(
            "How many positive integers n <= 1000 make n^2 + n + 1 divisible "
            "by 7? Reply with the number only."
        ),
        include=["reasoning.encrypted_content"],
    )
    assert response.model == AGENT_MODEL
    assert response.status == "completed"
    assert "286" in response.output_text
    reasoning = [item for item in response.output if item.type == "reasoning"]
    assert reasoning and reasoning[0].encrypted_content
    assert response.usage is not None and response.usage.output_tokens > 0
    [(sent, record)] = _call_records(tmp_path / "calls")
    assert sent["api"] == "responses"
    assert sent["kwargs"]["max_output_tokens"] == 32768
    assert sent["kwargs"]["reasoning"] == {"effort": "high", "summary": "auto"}
    assert record["returned_model"] == AGENT_MODEL


# --- evaluated-agent sessions (NexAU on the Responses API) ----------------

LOOKUP_TOOL = BenchmarkToolSpec(
    name="lookup_account",
    description="Read one account from the protected benchmark environment.",
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {"account_id": {"type": "string"}},
        "required": ["account_id"],
    },
)


@pytest.fixture
def agent_runtime(tmp_path: Path) -> Iterator[EvaluatedAgentRuntime]:
    config = load_config(make_example_project(tmp_path))
    runtime = EvaluatedAgentRuntime(
        harness_dir=config.harness_dir,
        manifest=load_harness_manifest(config.harness_manifest_path),
        benchmark_interface=BenchmarkInterface(
            description="Protected account lookup benchmark.",
            input_kinds=("prompt", "environment"),
            tool_delivery="structured",
            protected_tools=(LOOKUP_TOOL,),
        ),
        model=_agent_settings(),
        transport=_transport(),
        api_key=_api_key(),
        artifact_root=tmp_path / "runtime-artifacts",
    )
    try:
        yield runtime
    finally:
        runtime.close()


def test_agent_protected_tool_round_trip(
    cao: None, tmp_path: Path, agent_runtime: EvaluatedAgentRuntime
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifact_dir = tmp_path / "runtime-artifacts" / "protected"
    session = agent_runtime.open_session(
        AgentSessionRequest(
            session_id="protected",
            artifact_dir=artifact_dir,
            working_directory=workspace,
            benchmark_tools=(LOOKUP_TOOL,),
        )
    )
    first = session.run(
        AgentInput(
            messages=(
                AgentInputMessage(
                    role="user",
                    # The account number takes real reasoning, so the first
                    # call returns a reasoning item that must be resent.
                    content=(
                        "The account ID is 'A-' followed by the number of "
                        "positive integers n <= 1000 for which n^2 + n + 1 is "
                        "divisible by 7. Work it out, then call the "
                        "lookup_account tool for that account without asking "
                        "anything first. When you have its result, reply with "
                        "the account status as one word."
                    ),
                ),
            )
        )
    )
    [action] = first.external_actions
    assert action.name == "lookup_account"
    assert action.arguments == {"account_id": "A-286"}
    second = session.run(
        AgentInput(
            messages=(
                AgentInputMessage(
                    role="tool",
                    tool_call_id=action.tool_call_id,
                    content={"account_id": "A-286", "status": "suspended"},
                ),
            )
        )
    )
    session.close()
    assert "suspended" in second.final_text.casefold()

    calls = _call_records(artifact_dir)
    assert len(calls) >= 2
    for sent, record in calls:
        assert sent["api"] == "responses"
        assert record["returned_model"] == AGENT_MODEL
        assert "reasoning.encrypted_content" in sent["kwargs"]["include"]
    # The follow-up call resends the tool call, its result and every
    # reasoning item the model returned (with its encrypted content), so the
    # reasoning chain survives across turns.
    follow_up = [item for item in calls[1][0]["kwargs"]["input"] if isinstance(item, dict)]
    calls_sent = [item for item in follow_up if item.get("type") == "function_call"]
    assert [item["call_id"] for item in calls_sent] == [action.tool_call_id]
    outputs = [item for item in follow_up if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in outputs] == [action.tool_call_id]
    returned = [
        item
        for item in calls[0][1]["response"]["output"]
        if item.get("type") == "reasoning"
    ]
    assert returned, "the first call returned no reasoning to resend"
    assert all(item.get("encrypted_content") for item in returned)
    resent = [item for item in follow_up if item.get("type") == "reasoning"]
    assert [item["encrypted_content"] for item in resent] == [
        item["encrypted_content"] for item in returned
    ]


def test_agent_internal_tool_loop(
    cao: None, tmp_path: Path, agent_runtime: EvaluatedAgentRuntime
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    artifact_dir = tmp_path / "runtime-artifacts" / "internal"
    session = agent_runtime.open_session(
        AgentSessionRequest(
            session_id="internal",
            artifact_dir=artifact_dir,
            working_directory=workspace,
            benchmark_tools=(LOOKUP_TOOL,),
        )
    )
    result = session.run(
        AgentInput(
            messages=(
                AgentInputMessage(
                    role="user",
                    content=(
                        "Use the record_note tool once to record the note "
                        "'cao-check'. Then reply with the single word DONE."
                    ),
                ),
            )
        )
    )
    session.close()
    assert result.external_actions == ()
    assert "done" in result.final_text.casefold()
    calls = _call_records(artifact_dir)
    assert len(calls) >= 2
    assert any(
        item.get("type") == "function_call_output"
        for sent, _ in calls[1:]
        for item in sent["kwargs"]["input"]
        if isinstance(item, dict)
    )
    assert "cao-check" in json.dumps([sent for sent, _ in calls])


# --- rubric judge -----------------------------------------------------------


def test_responses_judge_scores_a_criterion(cao: None, tmp_path: Path) -> None:
    from harvey_ahe.grading import RecordedCopilotJudge

    judge = RecordedCopilotJudge(
        settings=_judge_settings(),
        transport=_transport(),
        api_key=_api_key(),
        artifact_dir=tmp_path / "judge",
        max_prompt_chars=240_000,
        judge_api="openai_responses",
    )
    try:
        verdicts = {
            answer: judge.evaluate_from_file(
                "rubric_criterion",
                {
                    "task_description": "Name the capital of France.",
                    "agent_output": answer,
                    "criterion_title": "Correct capital",
                    "match_criteria": "The output states that the capital is Paris.",
                },
            )["verdict"]
            for answer in ("The capital of France is Paris.", "It is Lyon.")
        }
    finally:
        judge.close()
    assert verdicts == {"The capital of France is Paris.": "pass", "It is Lyon.": "fail"}
    # Both verdicts came from the first, json_schema-constrained attempt.
    assert len(judge.model_observations) == 2
    assert all(row["matched"] for row in judge.model_observations)
    calls = _call_records(tmp_path / "judge" / "model_calls")
    assert all(
        sent["kwargs"]["text"]["format"]["type"] == "json_schema" for sent, _ in calls
    )


# --- error classification -------------------------------------------------


def test_wrong_gateway_key_fails_fast_without_retries(
    cao: None, tmp_path: Path
) -> None:
    client = RecordedExactModelClient(
        transport=_transport(),
        api_key="definitely-not-the-gateway-key",
        settings=_agent_settings(),
        log_dir=tmp_path / "calls",
    )
    with pytest.raises(openai.AuthenticationError) as caught:
        client.responses.create(model=AGENT_MODEL, input="Reply with OK only.")
    assert not is_transient_exception(caught.value)
    assert not is_infrastructure_exception(caught.value)
    [call_dir] = (tmp_path / "calls").iterdir()
    assert (call_dir / "error.json").exists()
    assert not list(call_dir.glob("transient-attempt-*"))


def test_rejected_request_is_not_retried_or_infrastructure(
    cao: None, tmp_path: Path
) -> None:
    client = RecordedExactModelClient(
        transport=_transport(),
        api_key=_api_key(),
        settings=_agent_settings(),
        log_dir=tmp_path / "calls",
    )
    with pytest.raises(openai.BadRequestError) as caught:
        client.responses.create(
            model=AGENT_MODEL,
            input=[{"type": "function_call_output", "call_id": "no-such-call", "output": "x"}],
        )
    assert not isinstance(caught.value, InfrastructureError)
    assert not is_transient_exception(caught.value)
    assert not is_infrastructure_exception(caught.value)
    [call_dir] = (tmp_path / "calls").iterdir()
    assert not list(call_dir.glob("transient-attempt-*"))


# --- concurrency ------------------------------------------------------------


def test_concurrent_calls_all_complete(cao: None, tmp_path: Path) -> None:
    client = RecordedExactModelClient(
        transport=_transport(),
        api_key=_api_key(),
        settings=_agent_settings(),
        log_dir=tmp_path / "calls",
    )

    def ask(n: int) -> str:
        response = client.responses.create(
            model=AGENT_MODEL, input=f"What is {n} + {n}? Reply with the number only."
        )
        assert response.model == AGENT_MODEL
        return response.output_text

    with ThreadPoolExecutor(max_workers=6) as pool:
        answers = list(pool.map(ask, range(1, 7)))
    assert [str(2 * n) in answer for n, answer in zip(range(1, 7), answers)] == [True] * 6
    assert len(_call_records(tmp_path / "calls")) == 6
