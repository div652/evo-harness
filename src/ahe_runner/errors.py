"""Domain-specific errors used by the runner."""

from __future__ import annotations

import errno
from typing import Any


class AHERunnerError(RuntimeError):
    """Base error for operator-visible runner failures."""


class ConfigurationError(AHERunnerError):
    """Configuration or plugin identity is invalid."""


class IntegrityError(AHERunnerError):
    """A persisted artifact does not match its recorded identity."""


class InfrastructureError(AHERunnerError):
    """External infrastructure failed before producing a valid outcome."""


# Kept in the message so the block survives wrapping and process boundaries.
PROVIDER_BLOCKED_MARKER = "model provider blocked this principal"

# strerror(ENOSPC); also matched in recorded error messages.
DISK_FULL_MARKER = "no space left on device"


def is_disk_full(exc: BaseException) -> bool:
    """The host disk filled up: a transient condition, not a result."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, OSError) and current.errno == errno.ENOSPC:
            return True
        if DISK_FULL_MARKER in str(current).casefold():
            return True
        current = current.__cause__ or current.__context__
    return False


class ProviderBlockedError(InfrastructureError):
    """The model provider blocked this principal; stop sending it requests."""


class CandidateValidationError(AHERunnerError):
    """An evolved harness failed deterministic validation."""

    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        errors = report.get("errors") or ["candidate validation failed"]
        super().__init__("\n".join(str(error) for error in errors))


class StageInterruptedError(AHERunnerError):
    """A resumable stage attempt failed and was durably preserved."""

    def __init__(self, stage_name: str, attempt: int, message: str) -> None:
        self.stage_name = stage_name
        self.attempt = attempt
        super().__init__(message)


class StageBlockedError(AHERunnerError):
    """A stage cannot continue without operator intervention."""

    def __init__(self, stage_name: str, message: str) -> None:
        self.stage_name = stage_name
        super().__init__(message)
