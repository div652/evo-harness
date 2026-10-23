"""Validation and loading for adapter-produced training evidence."""

from __future__ import annotations

import math
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .adapter import (
    EXTRA_EVIDENCE_ROOT,
    EvaluationRequest,
    EvaluationResult,
    EvaluationTrialFact,
    EvidenceBundle,
    MetricSummary,
)
from .errors import IntegrityError
from .evaluation import VerifiedEvaluationUnit, verify_evaluation_output
from .io import read_json, sha256_file


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class EvidenceTask(EvidenceModel):
    task_key: str
    task_id: str | None = None
    state: str
    detail_path: str
    detail_sha256: str
    trial_count: int = Field(gt=0)


class EvidenceArtifact(EvidenceModel):
    kind: str
    path: str
    sha256: str

    @field_validator("kind", "path", "sha256")
    @classmethod
    def require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence artifact fields must not be empty")
        return normalized


class EvidenceTrial(EvidenceModel):
    unit_id: str
    trial: int = Field(ge=0)
    seed: int
    outcome: str
    score: float | None = None
    termination_reason: str
    diagnostic_class: Literal["passing", "failing", "other"]
    artifacts: list[EvidenceArtifact] = Field(min_length=2)
    # AHE-016: optional text views written inside the evidence directory
    # (for example a trace with real line breaks, or a .docx as plain text).
    readable_artifacts: list[EvidenceArtifact] = Field(default_factory=list)

    @field_validator("unit_id", "outcome", "termination_reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence trial fields must not be empty")
        return normalized

    @field_validator("score")
    @classmethod
    def require_finite_score(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("evidence trial score must be finite")
        return value

    @model_validator(mode="after")
    def require_trace_and_result(self) -> EvidenceTrial:
        kinds = {artifact.kind for artifact in self.artifacts}
        if "trace" not in kinds:
            raise ValueError("evidence trial requires a trace artifact")
        if not kinds & {"result", "evaluator"}:
            raise ValueError("evidence trial requires a result or evaluator artifact")
        return self


class EvidenceTaskDetail(EvidenceModel):
    schema_version: int
    task_key: str
    task_id: str | None = None
    state: str
    trials: list[EvidenceTrial] = Field(min_length=1)


class EvidenceManifest(EvidenceModel):
    schema_version: int
    checkpoint: str
    supervision_policy: str
    true_task_ids_exposed: bool
    source_evaluation: str
    source_evaluation_id: str
    source_request_sha256: str
    source_evaluation_sha256: str
    metrics: MetricSummary
    tasks: list[EvidenceTask] = Field(default_factory=list)


def verify_evidence_bundle(
    bundle: EvidenceBundle,
    *,
    evidence_dir: Path,
    expected_checkpoint: str,
    evaluation_dir: Path,
    source_evaluation: EvaluationResult,
    source_request: EvaluationRequest,
    extra_request: EvaluationRequest | None = None,
    extra_evaluation: EvaluationResult | None = None,
) -> EvidenceManifest:
    """Verify adapter evidence against its source training evaluation.

    With ``extra_request``/``extra_evaluation`` (evidence-only extra training
    trials), each task the extra evaluation covers also carries its extra
    trials, numbered after the regular ones, marked ``evidence_only`` and
    with artifacts under ``EXTRA_EVIDENCE_ROOT``.
    """
    if (extra_request is None) != (extra_evaluation is None):
        raise IntegrityError("extra evidence needs both its request and result")
    root = evidence_dir.resolve()
    manifest_path = Path(bundle.manifest_path).resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as exc:
        raise IntegrityError("evidence manifest escapes its output directory") from exc
    if sha256_file(manifest_path) != bundle.manifest_sha256:
        raise IntegrityError("evidence manifest hash mismatch")
    value = read_json(manifest_path)
    try:
        manifest = EvidenceManifest.model_validate(value)
    except ValidationError as exc:
        raise IntegrityError(f"invalid evidence manifest: {exc}") from exc
    if bundle.schema_version != 3 or manifest.schema_version != 3:
        raise IntegrityError("unsupported evidence schema")
    if manifest.checkpoint != expected_checkpoint:
        raise IntegrityError("evidence checkpoint identity mismatch")
    if len(manifest.tasks) != bundle.task_count:
        raise IntegrityError("evidence task count mismatch")
    if manifest.supervision_policy != bundle.supervision_policy:
        raise IntegrityError("evidence supervision policy mismatch")
    source = (root / manifest.source_evaluation).resolve()
    expected_source = (evaluation_dir / "adapter_result.json").resolve()
    if source != expected_source:
        raise IntegrityError("evidence source evaluation path mismatch")
    if not source.is_file() or sha256_file(source) != manifest.source_evaluation_sha256:
        raise IntegrityError("evidence source evaluation hash mismatch")
    try:
        actual_source = EvaluationResult.model_validate(read_json(source))
    except ValidationError as exc:
        raise IntegrityError(f"invalid evidence source evaluation: {exc}") from exc
    if actual_source != source_evaluation:
        raise IntegrityError("evidence source evaluation content mismatch")
    verified_evaluation = verify_evaluation_output(
        source_request,
        source_evaluation,
    )
    if manifest.source_evaluation_id != source_evaluation.evaluation_id:
        raise IntegrityError("evidence source evaluation identity mismatch")
    if manifest.source_request_sha256 != source_evaluation.request_sha256:
        raise IntegrityError("evidence source request identity mismatch")
    if manifest.metrics != source_evaluation.summary:
        raise IntegrityError("evidence metrics are stale or inconsistent")
    source_states = {
        state.task_key: state for state in source_evaluation.summary.task_states
    }
    if set(source_states) != {task.task_key for task in manifest.tasks}:
        raise IntegrityError("evidence tasks do not cover the source evaluation")
    units = {(unit.task_key, unit.trial): unit for unit in verified_evaluation.units}
    trial_facts = {fact.unit_id: fact for fact in verified_evaluation.trial_facts}
    extra_units: dict[tuple[str, int], VerifiedEvaluationUnit] = {}
    extra_facts: dict[str, EvaluationTrialFact] = {}
    extra_trials = 0
    record = (manifest.model_extra or {}).get("extra_evaluation")
    if extra_request is None or extra_evaluation is None:
        if record is not None:
            raise IntegrityError("evidence cites an unverified extra evaluation")
    else:
        _verify_extra_record(record, extra_request, extra_evaluation)
        extra_verified = verify_evaluation_output(extra_request, extra_evaluation)
        extra_units = {
            (unit.task_key, unit.trial): unit for unit in extra_verified.units
        }
        extra_facts = {fact.unit_id: fact for fact in extra_verified.trial_facts}
        extra_trials = extra_request.trials
        if not {key for key, _ in extra_units} <= set(source_states):
            raise IntegrityError("extra evidence covers a task outside training")
    extra_task_keys = {key for key, _ in extra_units}
    seen: set[str] = set()
    for task in manifest.tasks:
        if task.task_key in seen:
            raise IntegrityError(f"duplicate evidence task key: {task.task_key}")
        seen.add(task.task_key)
        detail = _relative_path(
            root,
            task.detail_path,
            label="evidence task",
        )
        if not detail.is_file() or sha256_file(detail) != task.detail_sha256:
            raise IntegrityError(f"evidence task hash mismatch: {task.task_key}")
        try:
            detail_value = EvidenceTaskDetail.model_validate(read_json(detail))
        except ValidationError as exc:
            raise IntegrityError(
                f"invalid evidence task detail {task.task_key}: {exc}"
            ) from exc
        if detail_value.schema_version != 3:
            raise IntegrityError("unsupported evidence task detail schema")
        state = source_states[task.task_key]
        expected_task_id = state.task_id if manifest.true_task_ids_exposed else None
        if (
            detail_value.task_key != task.task_key
            or detail_value.task_id != task.task_id
            or detail_value.state != task.state
            or task.task_id != expected_task_id
            or task.state != state.state
        ):
            raise IntegrityError(f"evidence task identity mismatch: {task.task_key}")
        expected_trials = state.trials + (
            extra_trials if task.task_key in extra_task_keys else 0
        )
        if (
            task.trial_count != expected_trials
            or len(detail_value.trials) != expected_trials
        ):
            raise IntegrityError(f"evidence trial coverage mismatch: {task.task_key}")
        observed_trials: set[int] = set()
        for trial in detail_value.trials:
            if trial.trial in observed_trials:
                raise IntegrityError(
                    f"duplicate evidence trial: {task.task_key}/{trial.trial}"
                )
            observed_trials.add(trial.trial)
            native = trial.model_extra or {}
            is_extra = trial.trial >= state.trials
            if is_extra:
                unit = extra_units.get((task.task_key, trial.trial - state.trials))
                facts = extra_facts
                artifact_dir = (
                    extra_request.output_dir
                    if extra_request is not None
                    else evaluation_dir
                )
                root_ok = native.get("artifact_root") == EXTRA_EVIDENCE_ROOT
            else:
                unit = units.get((task.task_key, trial.trial))
                facts, artifact_dir = trial_facts, evaluation_dir
                root_ok = native.get("artifact_root", "raw_evaluation") == (
                    "raw_evaluation"
                )
            if (
                unit is None
                or trial.unit_id != unit.unit_id
                or trial.seed != unit.seed
                or bool(native.get("evidence_only", False)) != is_extra
                or not root_ok
            ):
                raise IntegrityError(
                    f"evidence trial lineage mismatch: {task.task_key}/{trial.trial}"
                )
            fact = facts[unit.unit_id]
            if (
                trial.outcome != fact.outcome
                or trial.score != fact.score
                or trial.termination_reason != fact.termination_reason
                or trial.diagnostic_class != fact.diagnostic_class
            ):
                raise IntegrityError(
                    f"evidence trial semantics mismatch: {task.task_key}/{trial.trial}"
                )
            declared_artifacts: dict[tuple[str, str], str] = {}
            for artifact in trial.artifacts:
                artifact_path = _evaluation_artifact_path(
                    artifact_dir,
                    artifact.path,
                )
                if (
                    not artifact_path.is_file()
                    or sha256_file(artifact_path) != artifact.sha256
                ):
                    raise IntegrityError(
                        f"evidence artifact hash mismatch: {artifact.path}"
                    )
                key = (artifact.path, artifact.sha256)
                if key in declared_artifacts:
                    raise IntegrityError(
                        f"duplicate evidence artifact: {artifact.path}"
                    )
                declared_artifacts[key] = artifact.kind
            readable_paths: set[str] = set()
            for artifact in trial.readable_artifacts:
                readable_path = _relative_path(
                    root,
                    artifact.path,
                    label="readable evidence artifact",
                )
                if (
                    not readable_path.is_file()
                    or sha256_file(readable_path) != artifact.sha256
                ):
                    raise IntegrityError(
                        f"readable evidence hash mismatch: {artifact.path}"
                    )
                if artifact.path in readable_paths:
                    raise IntegrityError(
                        f"duplicate readable evidence artifact: {artifact.path}"
                    )
                readable_paths.add(artifact.path)
            result_key = (unit.result_path, unit.result_sha256)
            trace_key = (unit.trace_path, unit.trace_sha256)
            if declared_artifacts.get(trace_key) != "trace":
                raise IntegrityError(
                    f"evidence trial omits its trace artifact: "
                    f"{task.task_key}/{trial.trial}"
                )
            if declared_artifacts.get(result_key) not in {"result", "evaluator"}:
                raise IntegrityError(
                    f"evidence trial omits its result artifact: "
                    f"{task.task_key}/{trial.trial}"
                )
            required = {result_key, trace_key}
            if unit.metadata_path is not None and unit.metadata_sha256 is not None:
                required.add((unit.metadata_path, unit.metadata_sha256))
            if not required <= set(declared_artifacts):
                raise IntegrityError(
                    f"evidence trial omits required artifacts: "
                    f"{task.task_key}/{trial.trial}"
                )
        if observed_trials != set(range(task.trial_count)):
            raise IntegrityError(
                f"evidence trial indices are incomplete: {task.task_key}"
            )
    return manifest


def _verify_extra_record(
    record: Any,
    request: EvaluationRequest,
    evaluation: EvaluationResult,
) -> None:
    """The manifest's ``extra_evaluation`` entry names exactly this result."""
    source = (request.output_dir / "adapter_result.json").resolve()
    if (
        not isinstance(record, dict)
        or Path(str(record.get("source_evaluation", ""))).resolve() != source
        or record.get("source_evaluation_id") != evaluation.evaluation_id
        or record.get("source_request_sha256") != evaluation.request_sha256
        or record.get("trials") != request.trials
    ):
        raise IntegrityError("evidence extra-evaluation record mismatch")
    if not source.is_file() or sha256_file(source) != record.get(
        "source_evaluation_sha256"
    ):
        raise IntegrityError("evidence extra-evaluation hash mismatch")
    if EvaluationResult.model_validate(read_json(source)) != evaluation:
        raise IntegrityError("evidence extra-evaluation content mismatch")


def load_evidence_manifest(path: Path) -> EvidenceManifest:
    return EvidenceManifest.model_validate(read_json(path))


def load_task_detail(
    evidence_dir: Path,
    task: EvidenceTask,
) -> dict[str, Any]:
    path = _relative_path(
        evidence_dir.resolve(),
        task.detail_path,
        label="evidence task",
    )
    return EvidenceTaskDetail.model_validate(read_json(path)).model_dump(mode="json")


def _evaluation_artifact_path(evaluation_dir: Path, relative: str) -> Path:
    return _relative_path(
        evaluation_dir.resolve(),
        relative,
        label="evidence artifact",
    )


def _relative_path(root: Path, relative: str, *, label: str) -> Path:
    candidate = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise IntegrityError(f"{label} path escapes its root")
    path = (root / Path(*candidate.parts)).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise IntegrityError(f"{label} path escapes its root") from exc
    return path
