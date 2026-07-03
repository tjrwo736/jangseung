"""Phase 11-A-1 pre-live ``save_run`` write routing evidence.

This module models the ``save_run`` write path as an in-memory request and
routes it through guard/mediator-compatible records. It does not call
``save_run``, write ``.aeg`` state, grant runtime authority, call providers,
use the network, spawn processes, or start Phase 11-B.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_NOT_PROTECTED_TARGET,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    RUNS_DIR,
    SAFE_DEFAULT,
    STATE_DIR,
    WRITE_CLASS_AEG_STATE_WRITE,
)
from src.evidence.b1_aeg_integrity_guard import (
    B1AegIntegrityGuardDecision,
    decide_b1_aeg_integrity_guard,
)
from src.evidence.deny_only_mediator import (
    WriteMediationDecision,
    WriteMediationRequest,
    decide_write_request,
)
from src.evidence.phase11a_rollback_kill_path import (
    CandidateWiredPathResult,
    FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
    VERIFY_REPLAY_ACCEPTED as ROLLBACK_VERIFY_REPLAY_ACCEPTED,
    execute_phase11a_rollback_kill_path,
    existing_unwired_behavior_result,
    verify_phase11a_rollback_kill_path_evidence,
)

PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND = "phase11a_save_run_write_routing_evidence"
PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION = "phase11a_save_run_write_routing_v0"
PHASE11A_STEP = "11-A-1"
PHASE11B_STATUS_NOT_STARTED = "NOT_STARTED"

SAVE_RUN_ROUTE_NOT_ATTEMPTED = "SAVE_RUN_ROUTE_NOT_ATTEMPTED"
SAVE_RUN_ROUTE_PRELIVE_READY = "SAVE_RUN_ROUTE_PRELIVE_READY"
SAVE_RUN_ROUTE_ATTEMPTED = "SAVE_RUN_ROUTE_ATTEMPTED"
SAVE_RUN_ROUTE_FAILED_FALLBACK_USED = "SAVE_RUN_ROUTE_FAILED_FALLBACK_USED"
SAVE_RUN_ROUTE_REJECTED_BY_GUARD = "SAVE_RUN_ROUTE_REJECTED_BY_GUARD"
SAVE_RUN_ROUTE_ACCEPTED_PRELIVE = "SAVE_RUN_ROUTE_ACCEPTED_PRELIVE"
ALLOWED_SAVE_RUN_ROUTE_STATUSES = (
    SAVE_RUN_ROUTE_NOT_ATTEMPTED,
    SAVE_RUN_ROUTE_PRELIVE_READY,
    SAVE_RUN_ROUTE_ATTEMPTED,
    SAVE_RUN_ROUTE_FAILED_FALLBACK_USED,
    SAVE_RUN_ROUTE_REJECTED_BY_GUARD,
    SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,
)

SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE = "SAVE_RUN_ROUTE_GUARD_MEDIATOR_COMPATIBLE"
SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK = FALLBACK_TARGET_EXISTING_UNWIRED_PATH
SAVE_RUN_ROUTE_TARGET_GUARD_REJECTED = "guard_rejected_non_aeg_target"

GUARD_DECISION_DENIED = DENIED_BY_B1_AEG_INTEGRITY_GUARD
GUARD_DECISION_NOT_PROTECTED = B1_AEG_NOT_PROTECTED_TARGET
GUARD_DECISION_NOT_EVALUATED = "GUARD_DECISION_NOT_EVALUATED"
ALLOWED_GUARD_DECISION_STATUSES = (
    GUARD_DECISION_DENIED,
    GUARD_DECISION_NOT_PROTECTED,
    GUARD_DECISION_NOT_EVALUATED,
)

FALLBACK_REASON_NOT_NEEDED = "not_needed_route_completed"
FALLBACK_REASON_ROUTE_NOT_ATTEMPTED = "not_needed_route_not_attempted"
FALLBACK_REASON_ROUTE_FAILED = "save_run_route_failed"
FALLBACK_REASON_ROUTE_EXCEPTION = "save_run_route_exception"
FALLBACK_REASON_GUARD_REJECTED = "save_run_route_rejected_by_guard"
ALLOWED_FALLBACK_REASONS = (
    FALLBACK_REASON_NOT_NEEDED,
    FALLBACK_REASON_ROUTE_NOT_ATTEMPTED,
    FALLBACK_REASON_ROUTE_FAILED,
    FALLBACK_REASON_ROUTE_EXCEPTION,
    FALLBACK_REASON_GUARD_REJECTED,
)

RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY = NOT_WIRED_TO_EXECUTOR_WRITE_PATH

VERIFY_REPLAY_ACCEPTED = "VERIFY_REPLAY_ACCEPTED"
VERIFY_REPLAY_REJECTED = "VERIFY_REPLAY_REJECTED"

AUTHORITY_SNAPSHOT = {
    "runtime_write_path_status": RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_step": PHASE11A_STEP,
    "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
    "safe_default": SAFE_DEFAULT,
}

NON_CLAIM_CAVEATS = (
    "11-A-1 records pre-live save_run routing evidence only",
    "no save_run call is performed by this adapter",
    "no .aeg state write is performed by this adapter",
    "no runtime write authority is granted",
    "no live executor authority is granted",
    "no provider model network authority is granted",
    "no command runner authority is granted",
    "no actual enforcement is activated",
    "known-gap expected-red status is preserved",
    "Phase 11-B remains not started",
)

_EVIDENCE_FIELDS = frozenset(
    {
        "record_kind",
        "record_version",
        "claim_type",
        "phase11a_step",
        "save_run_route_attempted",
        "save_run_route_status",
        "save_run_route_target",
        "mediator_route_used",
        "guard_decision_status",
        "fallback_available",
        "fallback_triggered",
        "fallback_reason",
        "runtime_write_path_status",
        "live_executor_authority",
        "phase11b_status",
        "safe_default",
        "known_gap_status",
        "request",
        "guard_decision",
        "mediator_request",
        "mediator_decision",
        "route_result",
        "fallback_evidence",
        "fallback_verify",
        "authority_snapshot",
        "non_claim_caveats",
        "deterministic_evidence_digest",
    }
)

_OVERCLAIM_KEYS = {
    "runtime_write_authority_granted": "runtime write authority grant claim rejected",
    "live_executor_authority_granted": "live executor authority grant claim rejected",
    "phase11b_started": "Phase 11-B start claim rejected",
    "save_run_write_path_wired": "save_run routing overclaim rejected",
    "executor_write_path_wired": "runtime write path wiring claim rejected",
    "actual_enforcement_active": "actual enforcement activation claim rejected",
    "provider_authority_granted": "provider authority grant claim rejected",
    "network_authority_granted": "network authority grant claim rejected",
    "model_authority_granted": "model authority grant claim rejected",
    "raw_shell_authority_granted": "raw shell authority grant claim rejected",
    "command_runner_authority_granted": "command runner authority grant claim rejected",
}

_FORBIDDEN_ROUTE_STATUS_OVERCLAIMS = frozenset(
    {
        "WRITE_" + "PATH_WIRED",
        "MEDIATION_" + "ACTIVE",
        "ENFORCEMENT_" + "ACTIVE",
        "LIVE_EXECUTOR_" + "READY",
        "SAFE_" + "TO_RUN",
        "PHASE_11B_" + "STARTED",
        "RUNTIME_WRITE_AUTHORITY_" + "GRANTED",
    }
)


@dataclass(frozen=True)
class SaveRunWriteRequest:
    """In-memory model for one ``save_run`` target write."""

    request_id: str
    run_id: str
    target_relative_path: str
    intended_operation: str
    payload_digest: str
    payload_metadata: Mapping[str, str] = field(default_factory=dict)
    request_source: str = "phase11a_save_run_pre_live_adapter"
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    runtime_write_path_status: str = RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY
    write_performed: bool = False

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["payload_metadata"] = dict(self.payload_metadata)
        return record


def build_save_run_write_request(
    *,
    run_id: str,
    target_filename: str = "run.json",
    intended_operation: str = "create",
    payload: str | bytes | None = None,
    payload_metadata: Mapping[str, str] | None = None,
    request_id: str | None = None,
) -> SaveRunWriteRequest:
    """Build a deterministic pre-live request for a ``save_run`` target."""

    metadata = dict(payload_metadata or {})
    target_relative_path = str(Path(STATE_DIR) / RUNS_DIR / run_id / target_filename)
    payload_digest = _payload_digest(payload=payload, payload_metadata=metadata)
    return SaveRunWriteRequest(
        request_id=request_id
        or _request_id(
            run_id=run_id,
            target_relative_path=target_relative_path,
            intended_operation=intended_operation,
            payload_digest=payload_digest,
            payload_metadata=metadata,
        ),
        run_id=run_id,
        target_relative_path=target_relative_path,
        intended_operation=intended_operation,
        payload_digest=payload_digest,
        payload_metadata=metadata,
    )


def route_save_run_write_request(
    *,
    repo_root: str | Path,
    request: SaveRunWriteRequest,
    mediator_route: Callable[[WriteMediationRequest], WriteMediationDecision | Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Route a pre-live ``save_run`` request through guard/mediator records."""

    route_callable = mediator_route or decide_write_request
    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=request.target_relative_path,
    )
    guard_status = GUARD_DECISION_DENIED if guard_decision.protected_target else GUARD_DECISION_NOT_PROTECTED

    if not guard_decision.protected_target:
        fallback_evidence = execute_phase11a_rollback_kill_path()
        return _build_evidence_record(
            request=request,
            save_run_route_attempted=True,
            save_run_route_status=SAVE_RUN_ROUTE_REJECTED_BY_GUARD,
            save_run_route_target=SAVE_RUN_ROUTE_TARGET_GUARD_REJECTED,
            mediator_route_used=False,
            guard_decision_status=guard_status,
            fallback_available=True,
            fallback_triggered=False,
            fallback_reason=FALLBACK_REASON_GUARD_REJECTED,
            guard_decision=guard_decision,
            mediator_request=None,
            mediator_decision=None,
            route_result={"status": "guard_rejected", "success": False},
            fallback_evidence=fallback_evidence,
        )

    mediator_request = _build_mediator_request(request=request, guard_decision=guard_decision)
    try:
        raw_route_result = route_callable(mediator_request)
        mediator_decision, route_result = _normalize_route_result(raw_route_result)
    except Exception as exc:  # noqa: BLE001 - pre-live fallback must record route exceptions.
        fallback_evidence = _fallback_for_route_failure(
            reason=FALLBACK_REASON_ROUTE_EXCEPTION,
            detail=exc.__class__.__name__,
        )
        return _build_evidence_record(
            request=request,
            save_run_route_attempted=True,
            save_run_route_status=SAVE_RUN_ROUTE_FAILED_FALLBACK_USED,
            save_run_route_target=SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
            mediator_route_used=True,
            guard_decision_status=guard_status,
            fallback_available=True,
            fallback_triggered=True,
            fallback_reason=FALLBACK_REASON_ROUTE_EXCEPTION,
            guard_decision=guard_decision,
            mediator_request=mediator_request,
            mediator_decision=None,
            route_result={
                "status": "raised_exception",
                "success": False,
                "exception_type": exc.__class__.__name__,
            },
            fallback_evidence=fallback_evidence,
        )

    route_success = route_result.get("success") is not False and route_result.get("status") != "failed"
    if not route_success:
        fallback_evidence = _fallback_for_route_failure(
            reason=FALLBACK_REASON_ROUTE_FAILED,
            detail=str(route_result.get("reason", "mediator route returned failure")),
        )
        return _build_evidence_record(
            request=request,
            save_run_route_attempted=True,
            save_run_route_status=SAVE_RUN_ROUTE_FAILED_FALLBACK_USED,
            save_run_route_target=SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK,
            mediator_route_used=True,
            guard_decision_status=guard_status,
            fallback_available=True,
            fallback_triggered=True,
            fallback_reason=FALLBACK_REASON_ROUTE_FAILED,
            guard_decision=guard_decision,
            mediator_request=mediator_request,
            mediator_decision=mediator_decision,
            route_result=route_result,
            fallback_evidence=fallback_evidence,
        )

    fallback_evidence = execute_phase11a_rollback_kill_path()
    return _build_evidence_record(
        request=request,
        save_run_route_attempted=True,
        save_run_route_status=SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,
        save_run_route_target=SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
        mediator_route_used=True,
        guard_decision_status=guard_status,
        fallback_available=True,
        fallback_triggered=False,
        fallback_reason=FALLBACK_REASON_NOT_NEEDED,
        guard_decision=guard_decision,
        mediator_request=mediator_request,
        mediator_decision=mediator_decision,
        route_result=route_result,
        fallback_evidence=fallback_evidence,
    )


def build_pre_live_ready_evidence(*, request: SaveRunWriteRequest) -> dict[str, Any]:
    """Build a non-attempted readiness record for schema/replay fixtures."""

    fallback_evidence = execute_phase11a_rollback_kill_path()
    return _build_evidence_record(
        request=request,
        save_run_route_attempted=False,
        save_run_route_status=SAVE_RUN_ROUTE_PRELIVE_READY,
        save_run_route_target=SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
        mediator_route_used=False,
        guard_decision_status=GUARD_DECISION_NOT_EVALUATED,
        fallback_available=True,
        fallback_triggered=False,
        fallback_reason=FALLBACK_REASON_ROUTE_NOT_ATTEMPTED,
        guard_decision=None,
        mediator_request=None,
        mediator_decision=None,
        route_result={"status": "prelive_ready", "success": None},
        fallback_evidence=fallback_evidence,
    )


def verify_phase11a_save_run_write_routing_evidence(
    evidence_record: Mapping[str, Any],
    *,
    expected_route_target: str = SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
    expected_guard_decision_status: str = GUARD_DECISION_DENIED,
    expected_fallback_triggered: bool | None = None,
) -> dict[str, Any]:
    """Verify schema, digest binding, route semantics, fallback, and authority."""

    reasons: list[str] = []
    if not isinstance(evidence_record, Mapping):
        reasons.append("evidence record must be a mapping")
        evidence_record = {}

    unexpected_fields = sorted(set(evidence_record) - _EVIDENCE_FIELDS)
    for field in unexpected_fields:
        reasons.append(f"unexpected evidence record field: {field}")

    missing_fields = sorted(_EVIDENCE_FIELDS - set(evidence_record))
    for field in missing_fields:
        reasons.append(f"missing evidence record field: {field}")

    _expect_field(reasons, evidence_record, "record_kind", PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND)
    _expect_field(reasons, evidence_record, "record_version", PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION)
    _expect_field(reasons, evidence_record, "claim_type", "pre_live_save_run_route_not_runtime_wiring")
    _expect_field(reasons, evidence_record, "phase11a_step", PHASE11A_STEP)
    _expect_field(reasons, evidence_record, "runtime_write_path_status", RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY)
    _expect_field(reasons, evidence_record, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
    _expect_field(reasons, evidence_record, "phase11b_status", PHASE11B_STATUS_NOT_STARTED)
    _expect_field(reasons, evidence_record, "safe_default", SAFE_DEFAULT)
    _expect_field(reasons, evidence_record, "known_gap_status", B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
    _expect_field(reasons, evidence_record, "authority_snapshot", AUTHORITY_SNAPSHOT)

    status = evidence_record.get("save_run_route_status")
    if status not in ALLOWED_SAVE_RUN_ROUTE_STATUSES:
        reasons.append(f"invalid save_run_route_status: {status}")
    if status in _FORBIDDEN_ROUTE_STATUS_OVERCLAIMS:
        reasons.append("save_run routing overclaim rejected")
    if evidence_record.get("save_run_route_target") != expected_route_target:
        reasons.append("save_run_route_target mismatch")
    if evidence_record.get("guard_decision_status") != expected_guard_decision_status:
        reasons.append("guard_decision_status mismatch")

    _validate_bool_field(reasons, evidence_record, "save_run_route_attempted")
    _validate_bool_field(reasons, evidence_record, "mediator_route_used")
    _validate_bool_field(reasons, evidence_record, "fallback_available")
    _validate_bool_field(reasons, evidence_record, "fallback_triggered")
    _validate_status_consistency(reasons, evidence_record)
    if expected_fallback_triggered is not None and evidence_record.get("fallback_triggered") is not expected_fallback_triggered:
        reasons.append("fallback_triggered mismatch")

    _validate_request(reasons, evidence_record.get("request"))
    _validate_guard_decision(reasons, evidence_record)
    _validate_mediator_records(reasons, evidence_record)
    _validate_route_result(reasons, evidence_record.get("route_result"))
    _validate_fallback_evidence(reasons, evidence_record)

    supplied_digest = evidence_record.get("deterministic_evidence_digest")
    recomputed_digest = phase11a_save_run_routing_evidence_digest(evidence_record)
    if supplied_digest != recomputed_digest:
        reasons.append("deterministic evidence digest mismatch")

    reasons.extend(_recursive_overclaim_rejections(evidence_record))
    reasons = _unique(reasons)
    accepted = not reasons
    return {
        "accepted": accepted,
        "status": VERIFY_REPLAY_ACCEPTED if accepted else VERIFY_REPLAY_REJECTED,
        "rejection_reasons": reasons,
        "verification_scope": "phase11a_save_run_write_routing_replay_only",
        "is_runtime_wiring": False,
        "is_runtime_enforcement": False,
        "safe_default": SAFE_DEFAULT,
    }


def phase11a_save_run_routing_evidence_digest(evidence_record: Mapping[str, Any]) -> str:
    """Return the deterministic digest for the 11-A-1 evidence payload."""

    payload = deepcopy(dict(evidence_record))
    payload.pop("deterministic_evidence_digest", None)
    return _sha256_json(payload)


def _build_mediator_request(
    *,
    request: SaveRunWriteRequest,
    guard_decision: B1AegIntegrityGuardDecision,
) -> WriteMediationRequest:
    return WriteMediationRequest(
        request_id=f"phase11a-save-run-mediator:{request.request_id}",
        actor=request.request_source,
        operation=request.intended_operation,
        write_class=WRITE_CLASS_AEG_STATE_WRITE,
        submitted_target=guard_decision.submitted_path,
        canonical_target=guard_decision.resolved_path,
        declared_scope="phase11a_save_run_write_routing_v0",
        repo_boundary="repo_root_resolved_by_b1_guard",
        aeg_boundary=guard_decision.protected_target_status,
        action_summary="pre-live save_run target routed before state mutation",
        metadata={
            "run_id": request.run_id,
            "payload_digest": request.payload_digest,
            "guard_decision_id": guard_decision.decision_id,
            "runtime_write_path_status": RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY,
            "mediator_write_path_status": NOT_WIRED_TO_WRITE_PATH,
            "expected_mediator_decision": MEDIATOR_DECISION_DENY,
        },
    )


def _normalize_route_result(
    raw_route_result: WriteMediationDecision | Mapping[str, Any],
) -> tuple[WriteMediationDecision | None, dict[str, Any]]:
    if isinstance(raw_route_result, WriteMediationDecision):
        return raw_route_result, {
            "status": "mediator_decision_returned",
            "success": True,
            "decision_status": raw_route_result.decision_status,
            "write_path_status": raw_route_result.write_path_status,
            "write_performed": raw_route_result.write_performed,
        }
    if isinstance(raw_route_result, Mapping):
        result = deepcopy(dict(raw_route_result))
        result.setdefault("status", "returned_mapping")
        result.setdefault("success", True)
        return None, result
    return None, {
        "status": "invalid_route_result",
        "success": False,
        "reason": "mediator route returned unsupported result",
    }


def _fallback_for_route_failure(*, reason: str, detail: str) -> dict[str, Any]:
    return execute_phase11a_rollback_kill_path(
        candidate_wired_path=lambda: CandidateWiredPathResult(
            success=False,
            reason=f"{reason}:{detail}",
        ),
        existing_unwired_behavior=existing_unwired_behavior_result,
    )


def _build_evidence_record(
    *,
    request: SaveRunWriteRequest,
    save_run_route_attempted: bool,
    save_run_route_status: str,
    save_run_route_target: str,
    mediator_route_used: bool,
    guard_decision_status: str,
    fallback_available: bool,
    fallback_triggered: bool,
    fallback_reason: str,
    guard_decision: B1AegIntegrityGuardDecision | None,
    mediator_request: WriteMediationRequest | None,
    mediator_decision: WriteMediationDecision | None,
    route_result: Mapping[str, Any],
    fallback_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    fallback_verify = verify_phase11a_rollback_kill_path_evidence(fallback_evidence)
    record = {
        "record_kind": PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND,
        "record_version": PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION,
        "claim_type": "pre_live_save_run_route_not_runtime_wiring",
        "phase11a_step": PHASE11A_STEP,
        "save_run_route_attempted": save_run_route_attempted,
        "save_run_route_status": save_run_route_status,
        "save_run_route_target": save_run_route_target,
        "mediator_route_used": mediator_route_used,
        "guard_decision_status": guard_decision_status,
        "fallback_available": fallback_available,
        "fallback_triggered": fallback_triggered,
        "fallback_reason": fallback_reason,
        "runtime_write_path_status": RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
        "safe_default": SAFE_DEFAULT,
        "known_gap_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
        "request": request.to_record(),
        "guard_decision": guard_decision.to_record() if guard_decision else None,
        "mediator_request": mediator_request.to_record() if mediator_request else None,
        "mediator_decision": mediator_decision.to_record() if mediator_decision else None,
        "route_result": deepcopy(dict(route_result)),
        "fallback_evidence": deepcopy(dict(fallback_evidence)),
        "fallback_verify": {
            "accepted": fallback_verify.get("accepted"),
            "status": fallback_verify.get("status"),
            "verification_scope": fallback_verify.get("verification_scope"),
        },
        "authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
    }
    record["deterministic_evidence_digest"] = phase11a_save_run_routing_evidence_digest(record)
    return record


def _validate_status_consistency(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    status = evidence_record.get("save_run_route_status")
    attempted = evidence_record.get("save_run_route_attempted")
    mediator_used = evidence_record.get("mediator_route_used")
    fallback_triggered = evidence_record.get("fallback_triggered")
    fallback_reason = evidence_record.get("fallback_reason")
    route_target = evidence_record.get("save_run_route_target")

    if fallback_reason not in ALLOWED_FALLBACK_REASONS:
        reasons.append(f"invalid fallback_reason: {fallback_reason}")
    if evidence_record.get("fallback_available") is not True:
        reasons.append("fallback_available must remain true")

    if status == SAVE_RUN_ROUTE_PRELIVE_READY:
        if attempted is not False or mediator_used is not False or fallback_triggered is not False:
            reasons.append("PRELIVE_READY status requires no attempted route or fallback")
        if fallback_reason != FALLBACK_REASON_ROUTE_NOT_ATTEMPTED:
            reasons.append("PRELIVE_READY status requires route-not-attempted fallback reason")
    if status == SAVE_RUN_ROUTE_ACCEPTED_PRELIVE:
        if attempted is not True or mediator_used is not True or fallback_triggered is not False:
            reasons.append("ACCEPTED_PRELIVE status requires attempted mediator route without fallback")
        if route_target != SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE:
            reasons.append("ACCEPTED_PRELIVE status requires guard/mediator route target")
        if fallback_reason != FALLBACK_REASON_NOT_NEEDED:
            reasons.append("ACCEPTED_PRELIVE status requires not-needed fallback reason")
    if status == SAVE_RUN_ROUTE_FAILED_FALLBACK_USED:
        if attempted is not True or mediator_used is not True or fallback_triggered is not True:
            reasons.append("FAILED_FALLBACK_USED status requires attempted mediator route and fallback")
        if route_target != SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK:
            reasons.append("FAILED_FALLBACK_USED status requires existing fallback target")
        if fallback_reason not in (FALLBACK_REASON_ROUTE_FAILED, FALLBACK_REASON_ROUTE_EXCEPTION):
            reasons.append("FAILED_FALLBACK_USED status has invalid fallback reason")
    if status == SAVE_RUN_ROUTE_REJECTED_BY_GUARD:
        if attempted is not True or mediator_used is not False or fallback_triggered is not False:
            reasons.append("REJECTED_BY_GUARD status requires guard-only route rejection")
        if fallback_reason != FALLBACK_REASON_GUARD_REJECTED:
            reasons.append("REJECTED_BY_GUARD status requires guard rejection reason")
    if status == SAVE_RUN_ROUTE_NOT_ATTEMPTED:
        if attempted is not False or mediator_used is not False or fallback_triggered is not False:
            reasons.append("NOT_ATTEMPTED status requires no route or fallback")


def _validate_request(reasons: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        reasons.append("request must be a mapping")
        return
    if value.get("live_executor_authority_status") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("request live_executor_authority_status mismatch")
    if value.get("runtime_write_path_status") != RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY:
        reasons.append("request runtime_write_path_status mismatch")
    if value.get("write_performed") is not False:
        reasons.append("request must not record a write")
    target = value.get("target_relative_path")
    if isinstance(target, str):
        if not target.startswith(f"{STATE_DIR}/{RUNS_DIR}/"):
            reasons.append("request target_relative_path must stay under .aeg/runs")
    else:
        reasons.append("request target_relative_path must be a string")


def _validate_guard_decision(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    status = evidence_record.get("save_run_route_status")
    value = evidence_record.get("guard_decision")
    if status == SAVE_RUN_ROUTE_PRELIVE_READY:
        if value is not None:
            reasons.append("PRELIVE_READY guard_decision must be null")
        return
    if not isinstance(value, Mapping):
        reasons.append("guard_decision must be a mapping")
        return
    if value.get("wiring_status") != RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY:
        reasons.append("guard_decision wiring_status mismatch")
    if value.get("live_executor_authority_status") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("guard_decision live_executor_authority_status mismatch")
    if value.get("write_performed") is not False:
        reasons.append("guard_decision must not record a write")
    if value.get("filesystem_mutation_performed") is not False:
        reasons.append("guard_decision must not record filesystem mutation")
    if value.get("executor_write_path_wired") is not False:
        reasons.append("guard_decision executor_write_path_wired mismatch")


def _validate_mediator_records(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    status = evidence_record.get("save_run_route_status")
    mediator_request = evidence_record.get("mediator_request")
    mediator_decision = evidence_record.get("mediator_decision")
    if status in (SAVE_RUN_ROUTE_PRELIVE_READY, SAVE_RUN_ROUTE_REJECTED_BY_GUARD):
        if mediator_request is not None:
            reasons.append("mediator_request must be null when mediator route is unused")
        if mediator_decision is not None:
            reasons.append("mediator_decision must be null when mediator route is unused")
        return
    if not isinstance(mediator_request, Mapping):
        reasons.append("mediator_request must be a mapping")
    elif mediator_request.get("metadata", {}).get("runtime_write_path_status") != RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY:
        reasons.append("mediator_request runtime_write_path_status mismatch")
    if mediator_decision is None and status == SAVE_RUN_ROUTE_FAILED_FALLBACK_USED:
        return
    if not isinstance(mediator_decision, Mapping):
        reasons.append("mediator_decision must be a mapping")
        return
    if mediator_decision.get("decision_status") != MEDIATOR_DECISION_DENY:
        reasons.append("mediator_decision decision_status mismatch")
    if mediator_decision.get("write_path_status") != NOT_WIRED_TO_WRITE_PATH:
        reasons.append("mediator_decision write_path_status mismatch")
    if mediator_decision.get("write_performed") is not False:
        reasons.append("mediator_decision must not record a write")


def _validate_route_result(reasons: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        reasons.append("route_result must be a mapping")
        return
    if value.get("write_performed") is True:
        reasons.append("route_result must not record a write")


def _validate_fallback_evidence(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    fallback_evidence = evidence_record.get("fallback_evidence")
    fallback_verify = evidence_record.get("fallback_verify")
    verify = verify_phase11a_rollback_kill_path_evidence(
        fallback_evidence if isinstance(fallback_evidence, Mapping) else {}
    )
    if verify.get("status") != ROLLBACK_VERIFY_REPLAY_ACCEPTED:
        reasons.append("fallback evidence verify replay rejected")
    if not isinstance(fallback_verify, Mapping):
        reasons.append("fallback_verify must be a mapping")
        return
    expected = {
        "accepted": verify.get("accepted"),
        "status": verify.get("status"),
        "verification_scope": verify.get("verification_scope"),
    }
    if dict(fallback_verify) != expected:
        reasons.append("fallback_verify mismatch")


def _validate_bool_field(reasons: list[str], evidence_record: Mapping[str, Any], field: str) -> None:
    if not isinstance(evidence_record.get(field), bool):
        reasons.append(f"{field} must be boolean")


def _expect_field(reasons: list[str], record: Mapping[str, Any], field: str, expected: Any) -> None:
    if record.get(field) != expected:
        reasons.append(f"{field} mismatch")


def _recursive_overclaim_rejections(value: Any) -> list[str]:
    reasons: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _OVERCLAIM_KEYS and child is True:
                reasons.append(_OVERCLAIM_KEYS[key])
            reasons.extend(_recursive_overclaim_rejections(child))
    elif isinstance(value, list):
        for child in value:
            reasons.extend(_recursive_overclaim_rejections(child))
    return reasons


def _request_id(
    *,
    run_id: str,
    target_relative_path: str,
    intended_operation: str,
    payload_digest: str,
    payload_metadata: Mapping[str, str],
) -> str:
    digest = _sha256_json(
        {
            "run_id": run_id,
            "target_relative_path": target_relative_path,
            "intended_operation": intended_operation,
            "payload_digest": payload_digest,
            "payload_metadata": dict(payload_metadata),
        }
    )
    return f"phase11a-save-run-write-request:{digest}"


def _payload_digest(*, payload: str | bytes | None, payload_metadata: Mapping[str, str]) -> str:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
        payload_kind = "text"
    elif isinstance(payload, bytes):
        payload_bytes = payload
        payload_kind = "bytes"
    else:
        payload_bytes = json.dumps(
            {"payload_metadata": dict(payload_metadata)},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        payload_kind = "metadata_only"
    return _sha256_json(
        {
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "payload_kind": payload_kind,
            "payload_metadata": dict(payload_metadata),
        }
    )


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_SAVE_RUN_ROUTE_STATUSES",
    "AUTHORITY_SNAPSHOT",
    "GUARD_DECISION_DENIED",
    "PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND",
    "PHASE11A_SAVE_RUN_WRITE_ROUTING_VERSION",
    "PHASE11A_STEP",
    "PHASE11B_STATUS_NOT_STARTED",
    "RUNTIME_WRITE_PATH_STATUS_PRELIVE_ONLY",
    "SAVE_RUN_ROUTE_ACCEPTED_PRELIVE",
    "SAVE_RUN_ROUTE_FAILED_FALLBACK_USED",
    "SAVE_RUN_ROUTE_NOT_ATTEMPTED",
    "SAVE_RUN_ROUTE_PRELIVE_READY",
    "SAVE_RUN_ROUTE_REJECTED_BY_GUARD",
    "SAVE_RUN_ROUTE_TARGET_EXISTING_UNWIRED_FALLBACK",
    "SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE",
    "SaveRunWriteRequest",
    "VERIFY_REPLAY_ACCEPTED",
    "VERIFY_REPLAY_REJECTED",
    "build_pre_live_ready_evidence",
    "build_save_run_write_request",
    "phase11a_save_run_routing_evidence_digest",
    "route_save_run_write_request",
    "verify_phase11a_save_run_write_routing_evidence",
]
