"""Offline checks for the optional azure_entra provider and the Responses API."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from ahe_runner.config import ModelSettings, TransportSettings
from ahe_runner.errors import (
    PROVIDER_BLOCKED_MARKER,
    ConfigurationError,
    InfrastructureError,
    IntegrityError,
    ProviderBlockedError,
)
from ahe_runner.meta import model_client as client_module
from ahe_runner.meta.model_client import (
    AzureCliTokenProvider,
    RecordedExactModelClient,
    nexau_api_type,
    nexau_reasoning,
    openai_credential,
    transient_retry_delay,
)
from ahe_runner.meta.preflight import run_model_preflight

AZURE_URL = "https://models.example.invalid/openai/v1"
SCOPE = "api://example/.default"


def _azure(**update: Any) -> TransportSettings:
    return TransportSettings(
        provider="azure_entra",
        base_url=AZURE_URL,
        token_scope=SCOPE,
        api_mode="responses",
        model_catalog="disabled",
        negative_control="disabled",
        **update,
    )


def _settings(**update: Any) -> ModelSettings:
    values: dict[str, Any] = {
        "model": "exact-model",
        "max_tokens": 256,
        "reasoning_effort": "high",
        "temperature": None,
    }
    values.update(update)
    return ModelSettings(**values)


# --------------------------------------------------------------------------
# Configuration


def test_default_transport_serialization_is_unchanged() -> None:
    transport = TransportSettings(
        base_url="http://127.0.0.1:3141/v1",
        model_catalog="required",
        negative_control="required",
        hung_call_retries=2,
    )
    assert transport.model_dump(mode="json") == {
        "base_url": "http://127.0.0.1:3141/v1",
        "api_key_env": None,
        "api_mode": "chat_completions",
        "stream": False,
        "request_timeout_seconds": 300.0,
        "observable_model_policy": "exact",
        "model_catalog": "required",
        "negative_control": "required",
        "max_concurrent_requests": None,
        "hung_call_retries": 2,
    }
    assert TransportSettings.model_validate(transport.model_dump()) == transport


def test_non_default_provider_fields_are_serialized() -> None:
    dumped = _azure(transient_retries=5).model_dump(mode="json")
    assert dumped["provider"] == "azure_entra"
    assert dumped["token_scope"] == SCOPE
    assert dumped["api_mode"] == "responses"
    assert dumped["transient_retries"] == 5
    assert "transient_max_wait_seconds" not in dumped
    assert TransportSettings.model_validate(dumped) == _azure(transient_retries=5)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"provider": "azure_entra", "base_url": AZURE_URL}, "token_scope"),
        (
            {
                "provider": "azure_entra",
                "base_url": AZURE_URL,
                "token_scope": SCOPE,
                "api_key_env": "SOME_KEY",
            },
            "api_key_env",
        ),
        (
            {
                "provider": "azure_entra",
                "base_url": "http://models.example.invalid/v1",
                "token_scope": SCOPE,
            },
            "https",
        ),
        (
            {"base_url": "http://127.0.0.1:3141/v1", "token_scope": SCOPE},
            "token_scope",
        ),
        (
            {"base_url": "http://127.0.0.1:3141/v1", "transient_max_wait_seconds": 0},
            "transient_max_wait_seconds",
        ),
    ],
)
def test_provider_validation(values: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TransportSettings.model_validate(values)


def test_nexau_wire_settings() -> None:
    copilot = TransportSettings(base_url="http://127.0.0.1:3141/v1")
    assert nexau_api_type(copilot) == "openai_chat_completion"
    assert nexau_reasoning(copilot, "high") == {"effort": "high"}
    assert nexau_api_type(_azure()) == "openai_responses"
    assert nexau_reasoning(_azure(), "high") == {"effort": "high", "summary": "auto"}
    assert nexau_reasoning(_azure(), None) is None


# --------------------------------------------------------------------------
# Azure CLI token


def _token_json(token: str, expires_on: float) -> str:
    return json.dumps({"accessToken": token, "expires_on": int(expires_on)})


def test_token_provider_caches_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [1_000_000.0]
    commands: list[list[str]] = []

    def run(command: list[str], **_: Any) -> Any:
        commands.append(command)
        token = f"token-{len(commands)}"
        return SimpleNamespace(
            returncode=0, stdout=_token_json(token, now[0] + 3600), stderr=""
        )

    monkeypatch.setattr(client_module.subprocess, "run", run)
    monkeypatch.setattr(client_module.time, "time", lambda: now[0])
    provider = AzureCliTokenProvider(SCOPE)
    assert provider() == "token-1"
    assert provider() == "token-1"
    assert commands == [
        [
            "az",
            "account",
            "get-access-token",
            "--scope",
            SCOPE,
            "--output",
            "json",
        ]
    ]
    now[0] += 3600 - 60
    assert provider() == "token-2"


def test_token_provider_failures_are_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed(*_: Any, **__: Any) -> Any:
        return SimpleNamespace(returncode=1, stdout="", stderr="Please run az login")

    monkeypatch.setattr(client_module.subprocess, "run", failed)
    with pytest.raises(ConfigurationError, match="az login"):
        AzureCliTokenProvider(SCOPE)()

    def timeout(command: list[str], **_: Any) -> Any:
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(client_module.subprocess, "run", timeout)
    with pytest.raises(InfrastructureError):
        AzureCliTokenProvider(SCOPE)()


def test_credential_is_a_token_provider_only_for_azure() -> None:
    copilot = TransportSettings(base_url="http://127.0.0.1:3141/v1")
    assert openai_credential(copilot, "placeholder") == "placeholder"
    credential = openai_credential(_azure(), "placeholder")
    assert callable(credential)
    assert credential is openai_credential(_azure(), "ignored")


# --------------------------------------------------------------------------
# Recorded Responses client


class _Raw:
    def __init__(self, response: Any, headers: dict[str, str]) -> None:
        self._response = response
        self.headers = httpx.Headers(headers)

    def parse(self) -> Any:
        return self._response


def _response(model: str = "exact-model", status: str = "completed") -> Any:
    return SimpleNamespace(
        model=model,
        status=status,
        error=None,
        output_text="OK",
        model_dump=lambda mode="json": {"model": model, "status": status},
    )


def _responses_client(
    tmp_path: Path, outcomes: list[Any], transport: TransportSettings | None = None
) -> tuple[RecordedExactModelClient, list[dict[str, Any]]]:
    sent: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        sent.append(json.loads(json.dumps(kwargs)))
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Raw(
            outcome,
            {
                "x-ratelimit-remaining-tokens": "999000",
                "x-request-id": "req-1",
                "set-cookie": "secret",
            },
        )

    client = RecordedExactModelClient(
        transport=transport or _azure(),
        api_key="unused",
        settings=_settings(),
        log_dir=tmp_path / "calls",
    )
    client._base = SimpleNamespace(  # type: ignore[attr-defined]
        responses=SimpleNamespace(with_raw_response=SimpleNamespace(create=create))
    )
    return client, sent


def test_responses_call_enforces_settings_and_records_headers(tmp_path: Path) -> None:
    client, sent = _responses_client(tmp_path, [_response()])
    response = client.responses.create(
        model="exact-model", input="hello", max_output_tokens=256
    )
    assert response.output_text == "OK"
    assert sent == [
        {
            "model": "exact-model",
            "input": "hello",
            "max_output_tokens": 256,
            "stream": False,
            "reasoning": {"effort": "high", "summary": "auto"},
        }
    ]
    call = tmp_path / "calls" / "call-0001"
    request = json.loads((call / "request.json").read_text("utf-8"))
    assert request["api"] == "responses"
    recorded = json.loads((call / "response.json").read_text("utf-8"))
    assert recorded["returned_model"] == "exact-model"
    assert recorded["response_headers"] == {
        "x-ratelimit-remaining-tokens": "999000",
        "x-request-id": "req-1",
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": "other-model", "max_output_tokens": 256}, "model"),
        ({"model": "exact-model", "max_output_tokens": 64}, "max_output_tokens"),
        ({"model": "exact-model", "max_tokens": 256}, "max_tokens"),
        ({"model": "exact-model", "temperature": 0.5}, "temperature"),
        ({"model": "exact-model", "reasoning_effort": "high"}, "reasoning"),
        ({"model": "exact-model", "reasoning": {"effort": "low"}}, "reasoning"),
        ({"model": "exact-model", "stream": True}, "stream"),
    ],
)
def test_responses_overrides_are_rejected_before_any_request(
    tmp_path: Path, kwargs: dict[str, Any], message: str
) -> None:
    client, sent = _responses_client(tmp_path, [])
    with pytest.raises(IntegrityError, match=message):
        client.responses.create(input="hello", **kwargs)
    assert sent == []


def test_responses_proxy_exposes_only_create(tmp_path: Path) -> None:
    client, _ = _responses_client(tmp_path, [])
    with pytest.raises(IntegrityError):
        client.responses.retrieve  # noqa: B018


def test_resent_tool_calls_use_api_field_names(tmp_path: Path) -> None:
    from openai.types.responses import ResponseFunctionToolCall

    # What NexAU 0.3.9 resends: the SDK item dumped with Python names.
    dumped = ResponseFunctionToolCall(
        arguments="{}", call_id="call_1", name="glob", type="function_call"
    ).model_dump(mode="json")
    flagged = dict(dumped, async_=True)
    output = {"type": "function_call_output", "call_id": "call_1", "output": None}
    client, sent = _responses_client(tmp_path, [_response()])
    client.responses.create(
        model="exact-model",
        input=[dumped, flagged, output],
        max_output_tokens=256,
    )
    call = {"arguments": "{}", "call_id": "call_1", "name": "glob"}
    assert sent[0]["input"] == [
        {**call, "type": "function_call"},
        {**call, "type": "function_call", "async": True},
        output,
    ]
    request = json.loads(
        (tmp_path / "calls" / "call-0001" / "request.json").read_text("utf-8")
    )
    assert "async_" not in json.dumps(request)


def test_responses_mismatch_and_failed_status_fail_closed(tmp_path: Path) -> None:
    client, _ = _responses_client(
        tmp_path, [_response(model="other-model"), _response(status="failed")]
    )
    with pytest.raises(IntegrityError, match="other-model"):
        client.responses.create(model="exact-model", input="hello")
    with pytest.raises(InfrastructureError, match="failed"):
        client.responses.create(model="exact-model", input="hello")
    assert (tmp_path / "calls" / "call-0002" / "error.json").is_file()


def _status_error(status: int, headers: dict[str, str]) -> Exception:
    request = httpx.Request("POST", f"{AZURE_URL}/responses")
    response = httpx.Response(status, headers=headers, request=request)
    error_class = openai.RateLimitError if status == 429 else openai.InternalServerError
    return error_class("busy", response=response, body=None)


def test_transient_errors_wait_and_are_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(client_module.random, "uniform", lambda *_: 0.0)
    client, sent = _responses_client(
        tmp_path,
        [
            _status_error(429, {"retry-after": "7"}),
            _status_error(503, {}),
            _response(),
        ],
        _azure(transient_retries=2),
    )
    client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 3 and sent[0] == sent[1] == sent[2]
    assert sleeps == [7.0, 10.0]
    call = tmp_path / "calls" / "call-0001"
    recorded = json.loads((call / "response.json").read_text("utf-8"))
    assert [row["retry_delay_seconds"] for row in recorded["transient_attempts"]] == [
        7.0,
        10.0,
    ]
    assert (call / "transient-attempt-2.json").is_file()


def test_transient_retries_are_bounded_and_off_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    client, sent = _responses_client(
        tmp_path / "default", [_status_error(429, {}), _response()]
    )
    with pytest.raises(InfrastructureError):
        client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 1

    client, sent = _responses_client(
        tmp_path / "bounded",
        [_status_error(429, {})] * 3,
        _azure(transient_retries=1),
    )
    with pytest.raises(InfrastructureError):
        client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 2
    error = json.loads(
        (tmp_path / "bounded" / "calls" / "call-0001" / "error.json").read_text()
    )
    assert len(error["transient_attempts"]) == 1


def test_bad_requests_are_not_transient(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = httpx.Request("POST", f"{AZURE_URL}/responses")
    bad = openai.BadRequestError(
        "bad", response=httpx.Response(400, request=request), body=None
    )
    client, sent = _responses_client(
        tmp_path, [bad, _response()], _azure(transient_retries=3)
    )
    with pytest.raises(openai.BadRequestError):
        client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 1


def test_retry_delay_honours_retry_after_and_caps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module.random, "uniform", lambda *_: 0.0)
    # Exponential back-off from 5 s is the floor, even under a shorter hint.
    assert transient_retry_delay(
        _status_error(429, {"retry-after-ms": "1500"}), attempt=1, max_wait=120
    ) == pytest.approx(5.0)
    assert transient_retry_delay(
        _status_error(429, {"retry-after": "56"}), attempt=2, max_wait=120
    ) == pytest.approx(56.0)
    assert transient_retry_delay(
        _status_error(429, {"retry-after": "60"}), attempt=1, max_wait=30
    ) == pytest.approx(30.0)
    assert [
        transient_retry_delay(_status_error(503, {}), attempt=n, max_wait=120)
        for n in (1, 2, 3, 4, 5, 6, 8)
    ] == pytest.approx([5.0, 10.0, 20.0, 40.0, 80.0, 120.0, 120.0])


def test_retry_delay_jitter_spreads_synchronised_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bounds: list[tuple[float, float]] = []

    def uniform(low: float, high: float) -> float:
        bounds.append((low, high))
        return high

    monkeypatch.setattr(client_module.random, "uniform", uniform)
    delay = transient_retry_delay(
        _status_error(429, {"retry-after": "56"}), attempt=1, max_wait=120
    )
    assert bounds == [(0.0, 28.0)] and delay == pytest.approx(84.0)


def _blocked_error() -> Exception:
    request = httpx.Request("POST", f"{AZURE_URL}/responses")
    body = {
        "error": "PrincipalBlocked",
        "message": "TRAPI: Request blocked. Your client sent excessive retries.",
        "reason": "retry-flood",
        "scope": "principal",
    }
    return openai.PermissionDeniedError(
        f"Error code: 403 - {body}",
        response=httpx.Response(403, request=request),
        body=body,
    )


def test_principal_block_stops_all_requests_to_the_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module, "_BLOCKED_ENDPOINTS", {})
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    client, sent = _responses_client(
        tmp_path / "first",
        [_status_error(429, {}), _blocked_error(), _response()],
        _azure(transient_retries=5),
    )
    with pytest.raises(ProviderBlockedError, match=PROVIDER_BLOCKED_MARKER):
        client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 2
    error = json.loads(
        (tmp_path / "first" / "calls" / "call-0001" / "error.json").read_text()
    )
    assert error["type"] == "ProviderBlockedError"
    assert len(error["transient_attempts"]) == 1

    # Any other client in the process refuses before sending anything.
    other, other_sent = _responses_client(tmp_path / "other", [_response()])
    with pytest.raises(ProviderBlockedError, match="earlier"):
        other.responses.create(model="exact-model", input="hello")
    assert other_sent == []
    refused = json.loads(
        (tmp_path / "other" / "calls" / "call-0001" / "error.json").read_text()
    )
    assert refused["sent"] is False
    assert isinstance(ProviderBlockedError("x"), InfrastructureError)


def test_other_403s_are_not_provider_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module, "_BLOCKED_ENDPOINTS", {})
    request = httpx.Request("POST", f"{AZURE_URL}/responses")
    denied = openai.PermissionDeniedError(
        "Error code: 403 - no access to deployment",
        response=httpx.Response(403, request=request),
        body=None,
    )
    client, _ = _responses_client(tmp_path, [denied, _response()])
    with pytest.raises(openai.PermissionDeniedError):
        client.responses.create(model="exact-model", input="hello")
    assert client_module._BLOCKED_ENDPOINTS == {}


def test_workload_id_header_is_stable_per_log_dir_and_azure_only(
    tmp_path: Path,
) -> None:
    def build(transport: TransportSettings, log_dir: Path) -> Any:
        return RecordedExactModelClient(
            transport=transport,
            api_key="unused",
            settings=_settings(),
            log_dir=log_dir,
        )

    first = build(_azure(), tmp_path / "a")
    again = build(_azure(), tmp_path / "a")
    other = build(_azure(), tmp_path / "b")
    header = "X-TRAPI-Workload-ID"
    value = first._base.default_headers[header]  # type: ignore[attr-defined]
    assert value.startswith("ahe-runner-") and len(value) == len("ahe-runner-") + 16
    assert again._base.default_headers[header] == value  # type: ignore[attr-defined]
    assert other._base.default_headers[header] != value  # type: ignore[attr-defined]

    local = build(
        TransportSettings(base_url="http://127.0.0.1:9/v1"), tmp_path / "local"
    )
    assert header not in local._base.default_headers  # type: ignore[attr-defined]

    client, _ = _responses_client(tmp_path / "rec", [_response()])
    client.responses.create(model="exact-model", input="hello")
    request = json.loads(
        (tmp_path / "rec" / "calls" / "call-0001" / "request.json").read_text()
    )
    assert request["workload_id"].startswith("ahe-runner-")


# --------------------------------------------------------------------------
# Preflight


class _FakeResponsesOpenAI:
    def __init__(self, callback: Any) -> None:
        self.responses = SimpleNamespace(create=callback)


def test_preflight_responses_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []
    built: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        seen.append(kwargs)
        return SimpleNamespace(model="exact-model", status="completed")

    def make_client(**kwargs: Any) -> Any:
        built.append(kwargs)
        return _FakeResponsesOpenAI(create)

    monkeypatch.setattr("ahe_runner.meta.preflight.OpenAI", make_client)
    report = run_model_preflight(
        transport=_azure(),
        api_key="unused",
        settings=_settings(),
        output_path=tmp_path / "preflight.json",
    )
    assert report["status"] == "completed"
    assert report["provider"] == "azure_entra"
    assert report["positive_probe"]["returned_model"] == "exact-model"
    assert len(seen) == 1
    probe = seen[0]
    assert probe["model"] == "exact-model"
    assert "input" in probe and "messages" not in probe
    assert probe["reasoning"] == {"effort": "high", "summary": "auto"}
    assert "temperature" not in probe
    assert callable(built[0]["api_key"])
    assert "api_key" not in json.dumps(report)


def _http_error(status: int, message: str) -> openai.APIStatusError:
    request = httpx.Request("POST", "http://127.0.0.1:4141/v1/responses")
    response = httpx.Response(
        status, json={"error": {"message": message}}, request=request
    )
    cls = {400: openai.BadRequestError, 401: openai.AuthenticationError}[status]
    return cls(f"Error code: {status} - {message}", response=response, body=None)


# CAO (copilot-api) rejects an unknown model on /responses without naming it.
CAO_UNKNOWN_MODEL = (
    "This model does not support the responses endpoint. "
    "Please choose a different model."
)

# The same on /chat/completions.
CAO_UNKNOWN_CHAT_MODEL = (
    '{"error":{"message":"The requested model is not supported.",'
    '"code":"model_not_supported","param":"model",'
    '"type":"invalid_request_error"}}'
)


@pytest.mark.parametrize(
    ("status", "message", "passed", "identified_by"),
    [
        (400, CAO_UNKNOWN_MODEL, True, "model_rejection"),
        (400, CAO_UNKNOWN_CHAT_MODEL, True, "model_rejection"),
        (400, "Invalid value for 'input': expected a string.", False, None),
        (401, CAO_UNKNOWN_MODEL, False, None),
    ],
)
def test_negative_control_accepts_a_model_rejection_that_omits_the_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    message: str,
    passed: bool,
    identified_by: str | None,
) -> None:
    def create(**kwargs: Any) -> Any:
        if kwargs["model"].startswith("ahe-negative-control-"):
            raise _http_error(status, message)
        return SimpleNamespace(model="exact-model", status="completed")

    monkeypatch.setattr(
        "ahe_runner.meta.preflight.OpenAI", lambda **_: _FakeResponsesOpenAI(create)
    )
    transport = TransportSettings(
        base_url="http://127.0.0.1:4141/v1",
        api_key_env="CAO_API_KEY",
        api_mode="responses",
        model_catalog="disabled",
        negative_control="required",
    )
    run = lambda: run_model_preflight(  # noqa: E731
        transport=transport,
        api_key="unused",
        settings=_settings(),
        output_path=tmp_path / "preflight.json",
    )
    if not passed:
        with pytest.raises(IntegrityError, match="negative control failed"):
            run()
        report = json.loads((tmp_path / "preflight.json").read_text())
        assert report["negative_control"]["passed"] is False
        return
    report = run()
    assert report["status"] == "completed"
    assert report["negative_control"]["passed"] is True
    assert report["negative_control"]["identified_by"] == identified_by
    assert report["negative_control"]["status_code"] == status


def test_negative_control_still_prefers_an_error_naming_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def create(**kwargs: Any) -> Any:
        if kwargs["model"].startswith("ahe-negative-control-"):
            raise _http_error(400, f"Unknown model {kwargs['model']}")
        return SimpleNamespace(model="exact-model", status="completed")

    monkeypatch.setattr(
        "ahe_runner.meta.preflight.OpenAI", lambda **_: _FakeResponsesOpenAI(create)
    )
    report = run_model_preflight(
        transport=TransportSettings(
            base_url="http://127.0.0.1:4141/v1",
            api_mode="responses",
            model_catalog="disabled",
            negative_control="required",
        ),
        api_key="unused",
        settings=_settings(),
        output_path=tmp_path / "preflight.json",
    )
    assert report["negative_control"]["passed"] is True
    assert report["negative_control"]["identified_by"] == "model_name"


# --------------------------------------------------------------------------
# Token pacing


def test_token_pacing_is_off_by_default_and_not_serialized() -> None:
    assert "token_pacing_fraction" not in _azure().model_dump(mode="json")
    assert _azure(token_pacing_fraction=0.85).model_dump(mode="json")[
        "token_pacing_fraction"
    ] == 0.85


def test_pacer_waits_for_the_window_when_the_budget_is_spent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path))
    clock = [1000.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(client_module.time, "sleep", sleep)
    monkeypatch.setattr(client_module.random, "uniform", lambda *_: 0.0)
    pacer = client_module.TokenPacer(AZURE_URL, "exact-model", 0.8)
    # No budget known yet: send at once.
    assert pacer.acquire(500_000) == 0.0
    pacer.observe(
        {
            "x-ratelimit-limit-tokens": "1000000",
            "x-ratelimit-remaining-tokens": "500000",
            "x-ratelimit-reset-tokens": "30",
        }
    )
    # 500k - 200k leaves 300k >= the 200k floor: send.
    assert pacer.acquire(200_000) == 0.0
    # 300k - 200k would leave 100k < 200k: wait for the 30 s reset.
    assert pacer.acquire(200_000) == 30.0
    # A fresh window admits even a call larger than the paced share.
    pacer.cool_down(12.0)
    assert pacer.acquire(900_000) == 12.0
    # Another pacer (another process) sees the same state file.
    other = client_module.TokenPacer(AZURE_URL, "exact-model", 0.8)
    assert other.path == pacer.path
    assert client_module.TokenPacer(AZURE_URL, "other-model", 0.8).path != pacer.path


def test_rate_limits_cool_down_every_client_of_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path / "pacing"))
    sleeps: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(client_module.random, "uniform", lambda *_: 0.0)
    client, sent = _responses_client(
        tmp_path,
        [_status_error(429, {"retry-after": "7"}), _response()],
        _azure(transient_retries=1, token_pacing_fraction=0.85),
    )
    client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 2
    state = json.loads(client._pacer.path.read_text())  # type: ignore[attr-defined]
    assert state["cooldown_until"] > 0 and state["remaining"] == 0.0
    # The client slept the retry delay; the pacer (same 7 s) then let it pass.
    assert sleeps[0] == 7.0


def _gateway_error(retry_after: str = "5") -> Exception:
    request = httpx.Request("POST", f"{AZURE_URL}/responses")
    headers = {"retry-after": retry_after}
    response = httpx.Response(429, headers=headers, request=request)
    return openai.RateLimitError(
        f"TRAPI: Rate Limit Exceeded, retry after {retry_after} seconds.",
        response=response,
        body=None,
    )


def test_gateway_rate_limit_pauses_all_clients_and_caps_refusals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path / "pacing"))
    monkeypatch.setattr(client_module, "_BLOCKED_ENDPOINTS", {})
    clock = [1000.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(client_module.time, "sleep", sleep)
    monkeypatch.setattr(client_module.random, "uniform", lambda a, b: a)
    transport = _azure(
        transient_retries=10,
        token_pacing_fraction=0.85,
        gateway_pause_seconds=300,
        gateway_retries=1,
    )
    client, sent = _responses_client(
        tmp_path / "a", [_gateway_error(), _gateway_error(), _response()], transport
    )
    # The first refusal pauses for 300 s (not the advised 5); the second
    # exceeds gateway_retries and fails the call.
    with pytest.raises(InfrastructureError, match="gateway rate limit"):
        client.responses.create(model="exact-model", input="hello")
    assert len(sent) == 2
    assert sum(sleeps) == pytest.approx(300.0)
    # Another client of the endpoint (any model) waits out the shared pause.
    other, other_sent = _responses_client(tmp_path / "b", [_response()], transport)
    sleeps.clear()
    other.responses.create(model="exact-model", input="hello")
    assert len(other_sent) == 1
    assert sum(sleeps) == pytest.approx(300.0)


def test_any_block_stops_every_paced_client_on_the_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path / "pacing"))
    monkeypatch.setattr(client_module, "_BLOCKED_ENDPOINTS", {})
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    transport = _azure(transient_retries=2, token_pacing_fraction=0.85)
    client, _ = _responses_client(tmp_path / "a", [_blocked_error()], transport)
    with pytest.raises(ProviderBlockedError):
        client.responses.create(model="exact-model", input="hello")
    # A new process starts with no in-memory record, but the host file stops it.
    monkeypatch.setattr(client_module, "_BLOCKED_ENDPOINTS", {})
    other, other_sent = _responses_client(tmp_path / "b", [_response()], transport)
    with pytest.raises(ProviderBlockedError, match="on this host"):
        other.responses.create(model="exact-model", input="hello")
    assert other_sent == []


def test_token_window_admits_only_what_fits_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path))
    clock = [1000.0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(client_module.time, "sleep", sleep)
    monkeypatch.setattr(client_module.random, "uniform", lambda a, b: a)
    window = client_module.TokenWindow(AZURE_URL, "exact-model", 600_000)
    assert window.acquire(250_000) == 0.0
    clock[0] += 10
    assert window.acquire(250_000) == 0.0
    clock[0] += 5
    # 750k would exceed 600k: wait until the first entry leaves the window.
    assert window.acquire(250_000) == pytest.approx(45.0)
    clock[0] += 200
    # An empty window admits even a request above the budget.
    assert window.acquire(900_000) == 0.0
    # A 429 cuts the budget by 30% and pauses every client.
    window.cool_down(30.0)
    clock[0] += 61
    assert window.acquire(400_000) == 0.0
    assert window.acquire(100_000) == pytest.approx(60.0)


def test_window_cut_floor_recovery_and_chars_are_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path))
    clock = [1000.0]
    monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(client_module.time, "sleep", lambda s: None)
    transport = _azure(
        token_budget_per_minute=1_000_000,
        token_budget_chars_per_token=4.0,
        token_budget_cut=0.9,
        token_budget_floor=0.6,
        token_budget_recover_seconds=120.0,
    )
    window = client_module.token_window(transport, "exact-model")
    window.cool_down(0.0)
    with window._state() as state:  # type: ignore[attr-defined]
        assert state["budget"] == pytest.approx(900_000)
    for _ in range(10):
        window.cool_down(0.0)
    with window._state() as state:  # type: ignore[attr-defined]
        assert state["budget"] == pytest.approx(600_000)
    clock[0] += 121
    with window._state() as state:  # type: ignore[attr-defined]
        assert window._budget(state, clock[0]) == pytest.approx(660_000)
    # A budget saved by a run with a larger maximum is capped by this one.
    smaller = client_module.TokenWindow(AZURE_URL, "exact-model", 500_000)
    with smaller._state() as state:  # type: ignore[attr-defined]
        assert smaller._budget(state, clock[0]) == pytest.approx(500_000)
    client, _ = _responses_client(tmp_path, [], transport)
    assert client._chars_per_token == 4.0  # type: ignore[attr-defined]
    # The defaults keep earlier campaign identities unchanged.
    dumped = _azure(token_budget_per_minute=1).model_dump(mode="json")
    assert "token_budget_cut" not in dumped
    assert "token_budget_chars_per_token" not in dumped


def test_budget_setting_selects_the_window(tmp_path: Path) -> None:
    transport = _azure(token_budget_per_minute=600_000, token_pacing_fraction=0.85)
    client, _ = _responses_client(tmp_path, [], transport)
    pacer = client._pacer  # type: ignore[attr-defined]
    assert isinstance(pacer, client_module.TokenWindow)
    assert "token_budget_per_minute" not in _azure().model_dump(mode="json")


def test_preflight_retries_obey_gateway_pause_and_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ahe_runner.meta import preflight

    monkeypatch.setenv("AHE_PACING_DIR", str(tmp_path))
    clock = [1000.0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
    monkeypatch.setattr(client_module.time, "sleep", sleep)
    monkeypatch.setattr(preflight.time, "sleep", sleep)
    monkeypatch.setattr(client_module.random, "uniform", lambda a, b: a)
    transport = _azure(
        transient_retries=8,
        token_budget_per_minute=600_000,
        gateway_pause_seconds=120,
        gateway_retries=2,
    )
    calls: list[float] = []

    def create(**_: Any) -> Any:
        calls.append(clock[0])
        raise _gateway_error()

    with pytest.raises(openai.RateLimitError):
        preflight._create_with_transient_retries(
            create, {"model": "exact-model", "input": "OK"}, transport, []
        )
    # Three refusals (the cap is 2 retries), each after the shared pause.
    assert len(calls) == 3
    assert calls[1] - calls[0] >= 120 and calls[2] - calls[1] >= 120
