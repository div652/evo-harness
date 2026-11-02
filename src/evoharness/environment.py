"""Operator environment variables, with the names used before the rename.

The project was called ahe-runner before 0.10.0 and its variables were
prefixed ``AHE_``. Each ``EVOHARNESS_`` variable still falls back to its old
name, with a deprecation warning.
"""

from __future__ import annotations

import os
import warnings

PREFIX = "EVOHARNESS_"
LEGACY_NAMES = {
    "EVOHARNESS_PRE_STAGE_COMMAND": "AHE_PRE_STAGE_COMMAND",
    "EVOHARNESS_PRE_STAGE_TIMEOUT_SECONDS": "AHE_PRE_STAGE_TIMEOUT_SECONDS",
    "EVOHARNESS_STATE_DIR": "AHE_RUNNER_STATE_DIR",
}


def env_value(name: str) -> str | None:
    """The variable's value, or its pre-0.10.0 name's value when only that is set."""

    value = os.environ.get(name)
    if value is not None:
        return value
    legacy = LEGACY_NAMES.get(name)
    if legacy is not None and legacy in os.environ:
        warnings.warn(
            f"{legacy} is deprecated; set {name} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return os.environ[legacy]
    return None
