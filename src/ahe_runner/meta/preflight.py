"""Fresh observable-contract preflight for each model-backed stage attempt."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from ahe_runner.config import ModelSettings, TransportSettings
from ahe_runner.errors import InfrastructureError, IntegrityError
from ahe_runner.io import atomic_write_json

from .model_client import (
    _retry_after_seconds,
    estimated_request_tokens,
    gateway_pacer,
    host_block,
    is_gateway_rate_limit,
    is_infrastructure_exception,
    is_principal_blocked,
    is_transient_exception,
    openai_credential,
    record_host_block,
    responses_reasoning,
    token_window,
    transient_retry_delay,
)


def run_model_preflight(
    *,
    transport: TransportSettings,
    api_key: str,
    settings: ModelSettings,
    output_path: Path,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "checked_at": datetime.now(UTC).isoformat(),
        "base_url": transport.base_url,
        "api_mode": transport.api_mode,
        "stream": False,
        "requested_model": settings.model,
        "reasoning_effort": settings.reasoning_effort,
        "temperature": settings.temperature,
        "advertised_model_ids": None,
        "catalog_error": None,
        "positive_probe": None,
        "negative_control": None,
        "identity_scope": (
            "This verifies the endpoint's observable model label. An endpoint "
            "that synthesizes that label may not expose transparent upstream "
            "substitution."
        ),
    }
    if transport.provider != "gh_copilot_server":
        report["provider"] = transport.provider
    client = OpenAI(
        base_url=transport.base_url,
        api_key=openai_credential(transport, api_key),
        max_retries=0,
        timeout=transport.request_timeout_seconds,
    )
    advertised: list[str] | None = None
    catalog_error: str | None = None
    if transport.model_catalog != "disabled":
        try:
            advertised = sorted(str(item.id) for item in client.models.list().data)
        except Exception as exc:
            if is_infrastructure_exception(exc):
                report["status"] = "infrastructure_failed"
                report["catalog_error"] = f"{type(exc).__name__}: {exc}"
                atomic_write_json(output_path, report)
                raise InfrastructureError(str(exc)) from exc
            catalog_error = f"{type(exc).__name__}: {exc}"
            if transport.model_catalog == "required":
                report["status"] = "failed"
                report["catalog_error"] = catalog_error
                atomic_write_json(output_path, report)
                raise IntegrityError(
                    f"model catalog preflight failed: {catalog_error}"
                ) from exc
    report["advertised_model_ids"] = advertised
    report["catalog_error"] = catalog_error
    if advertised is not None and settings.model not in advertised:
        report["status"] = "failed"
        report["positive_probe"] = {
            "passed": False,
            "error": "requested model absent from catalog",
        }
        atomic_write_json(output_path, report)
        raise IntegrityError(
            f"exact model {settings.model!r} is absent from the endpoint catalog"
        )

    responses_api = transport.api_mode == "responses"
    positive_payload: dict[str, Any]
    if responses_api:
        positive_payload = {
            "model": settings.model,
            "input": "Reply with OK only.",
            "max_output_tokens": min(settings.max_tokens, 64),
            "stream": False,
        }
        if settings.temperature is not None:
            positive_payload["temperature"] = settings.temperature
        if settings.reasoning_effort is not None:
            positive_payload["reasoning"] = responses_reasoning(
                settings.reasoning_effort
            )
        create: Callable[..., Any] = client.responses.create
    else:
        positive_payload = {
            "model": settings.model,
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "max_tokens": min(settings.max_tokens, 64),
            "stream": False,
        }
        if settings.temperature is not None:
            positive_payload["temperature"] = settings.temperature
        if settings.reasoning_effort is not None:
            positive_payload["extra_body"] = {
                "reasoning": {"effort": settings.reasoning_effort}
            }
        create = client.chat.completions.create
    transient_errors: list[str] = []
    try:
        positive = _create_with_transient_retries(
            create, positive_payload, transport, transient_errors
        )
    except Exception as exc:
        report["positive_probe"] = {
            "passed": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "status_code": getattr(exc, "status_code", None),
        }
        if is_infrastructure_exception(exc):
            report["status"] = "infrastructure_failed"
            atomic_write_json(output_path, report)
            raise InfrastructureError(str(exc)) from exc
        report["status"] = "failed"
        atomic_write_json(output_path, report)
        raise
    returned_model = getattr(positive, "model", None)
    if returned_model != settings.model:
        report["status"] = "failed"
        report["positive_probe"] = {
            "passed": False,
            "returned_model": returned_model,
            "error": "observable model mismatch",
        }
        atomic_write_json(output_path, report)
        raise IntegrityError(
            f"positive probe returned {returned_model!r}; expected {settings.model!r}"
        )
    report["positive_probe"] = {
        "passed": True,
        "returned_model": returned_model,
    }
    if responses_api:
        report["positive_probe"]["status"] = getattr(positive, "status", None)
    if transient_errors:
        report["positive_probe"]["transient_errors"] = transient_errors

    negative: dict[str, Any] | None = None
    if transport.negative_control != "disabled":
        nonexistent = f"ahe-negative-control-{secrets.token_hex(16)}"
        negative_payload = dict(positive_payload)
        negative_payload["model"] = nonexistent
        try:
            response = create(**negative_payload)
        except Exception as exc:
            text = str(exc)
            identified_by = _negative_control_rejection(exc, nonexistent)
            passed = identified_by is not None
            negative = {
                "requested_model": nonexistent,
                "passed": passed,
                "identified_by": identified_by,
                "error_type": type(exc).__name__,
                "error": text,
                "status_code": getattr(exc, "status_code", None),
            }
            if not passed and transport.negative_control == "required":
                report["status"] = "failed"
                report["negative_control"] = negative
                atomic_write_json(output_path, report)
                raise IntegrityError(
                    "negative control failed without identifying the nonexistent "
                    f"model {nonexistent!r}"
                ) from exc
        else:
            negative = {
                "requested_model": nonexistent,
                "passed": False,
                "returned_model": getattr(response, "model", None),
                "error": "nonexistent model unexpectedly generated a response",
            }
            if transport.negative_control == "required":
                report["status"] = "failed"
                report["negative_control"] = negative
                atomic_write_json(output_path, report)
                raise IntegrityError(negative["error"])

    report["status"] = "completed"
    report["negative_control"] = negative
    atomic_write_json(output_path, report)
    return report


# Endpoints that reject an unknown model without naming it. Each phrase must
# say the model itself was refused, so a rejection for any other reason
# (bad input, auth) still fails the control.
_MODEL_REJECTION_PHRASES = (
    # CAO (copilot-api 2.7.30) on /responses, observed 2026-10-22.
    "this model does not support the responses endpoint",
)


def _negative_control_rejection(exc: BaseException, model: str) -> str | None:
    """How the error shows the nonexistent model was refused, if it does."""
    text = str(exc).casefold()
    if model.casefold() in text:
        return "model_name"
    if getattr(exc, "status_code", None) in (400, 404) and any(
        phrase in text for phrase in _MODEL_REJECTION_PHRASES
    ):
        return "model_rejection"
    return None


def _create_with_transient_retries(
    create: Callable[..., Any],
    payload: dict[str, Any],
    transport: TransportSettings,
    errors: list[str],
) -> Any:
    """Resend a probe rejected for rate limits or 5xx, as model calls are.

    With admission control or a gateway pause configured, the probe obeys
    them exactly like a recorded model call (campaign 14c, 2026-10-19: four
    trial preflights retried a gateway 429 on their own for 13 minutes and
    TRAPI blocked the principal): it stops at a host-wide block, waits for
    the shared gateway pause and the model's token window, shares any 429 as
    a pause for every client, and gives up after gateway_retries gateway
    refusals.
    """
    guarded = (
        transport.token_budget_per_minute is not None
        or transport.gateway_pause_seconds is not None
    )
    window = (
        token_window(transport, str(payload["model"]))
        if transport.token_budget_per_minute is not None
        else None
    )
    gateway = (
        gateway_pacer(transport.base_url)
        if transport.gateway_pause_seconds is not None
        else None
    )
    gateway_refusals = 0
    while True:
        if guarded:
            blocked = host_block(transport.base_url)
            if blocked is not None:
                raise InfrastructureError(
                    f"model provider blocked this principal on this host: {blocked}"
                )
            if gateway is not None:
                gateway.acquire(0.0)
            if window is not None:
                window.acquire(
                    estimated_request_tokens(
                        payload, transport.token_budget_chars_per_token
                    )
                )
        try:
            return create(**payload)
        except Exception as exc:
            if guarded and is_principal_blocked(exc):
                record_host_block(transport.base_url, str(exc))
                raise
            if guarded and is_gateway_rate_limit(exc):
                gateway_refusals += 1
                advised = _retry_after_seconds(getattr(exc, "response", None)) or 0.0
                if gateway is not None:
                    gateway.cool_down(
                        max(advised, transport.gateway_pause_seconds or 0.0)
                    )
                if window is not None:
                    window.cool_down(max(advised, 5.0))
                if gateway_refusals > transport.gateway_retries:
                    raise
                errors.append(f"{type(exc).__name__}: {exc}")
                continue
            if (
                not is_transient_exception(exc)
                or len(errors) >= transport.transient_retries
            ):
                raise
            errors.append(f"{type(exc).__name__}: {exc}")
            if guarded and window is not None and getattr(exc, "status_code", 0) == 429:
                window.cool_down(
                    max(_retry_after_seconds(getattr(exc, "response", None)) or 0, 5.0)
                )
                continue
            time.sleep(
                transient_retry_delay(
                    exc,
                    attempt=len(errors),
                    max_wait=transport.transient_max_wait_seconds,
                )
            )