"""Phase 11-A-0 rollback and kill-path evidence scaffold.

This module is in-memory evidence and verify replay only. It does not wire
``save_run``, activate a mediator, enforce filesystem policy, mutate runtime
configuration, call providers, use the network, spawn processes, or change live
executor authority.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    SAFE_DEFAULT,
)

PHASE11A_ROLLBACK_KILL_PATH_KIND = "phase11a_rollback_kill_path_evidence"
PHASE11A_ROLLBACK_KILL_PATH_VERSION = "phase11a_rollback_kill_path_v0"

PHASE11A_STEP = "11-A-0"
PHASE11A1_WIRING_STATUS_NOT_STARTED = "NOT_STARTED"
PHASE11B_STATUS_NOT_STARTED = "NOT_STARTED"

WRITE_PATH_STATUS_NOT_WIRED = "NOT_WIRED"
WRITE_PATH_STATUS_FALLBACK_READY = "FALLBACK_READY"
WRITE_PATH_STATUS_FALLBACK_USED = "FALLBACK_USED"
WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED = "WIRING_FAILED_FALLBACK_USED"
ALLOWED_WRITE_PATH_WIRING_STATUSES = (
    WRITE_PATH_STATUS_NOT_WIRED,
    WRITE_PATH_STATUS_FALLBACK_READY,
    WRITE_PATH_STATUS_FALLBACK_USED,
    WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED,
)

WRITE_PATH_MODE_ROLLBACK_KILL_PATH_ONLY = "rollback_kill_path_only"
WRITE_PATH_RUNTIME_MODE_NOT_WIRED = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
FALLBACK_TARGET_EXISTING_UNWIRED_PATH = "existing_unwired_path"

FALLBACK_REASON_NOT_NEEDED = "not_needed_no_candidate_wiring_attempted"
FALLBACK_REASON_MANUAL_KILL_PATH = "manual_kill_path_requested"
FALLBACK_REASON_CANDIDATE_RETURNED_FAILURE = "candidate_wired_path_returned_failure"
FALLBACK_REASON_CANDIDATE_RAISED_EXCEPTION = "candidate_wired_path_raised_exception"
FALLBACK_REASON_CANDIDATE_SUCCESS_OUT_OF_SCOPE = "candidate_wired_path_success_out_of_scope_in_11a0"
LEGACY_FALLBACK_REASON_CANDIDATE_SUCCESS_NOT_ACTIVATED = (
    "candidate_wired_path_success_not_activated_in_11a0"
)
CANDIDATE_SUCCESS_REJECTED_STATUS = "CANDIDATE_WIRED_PATH_SUCCESS_REJECTED_IN_11A0"
SUCCESS_LIKE_CANDIDATE_STATUSES = frozenset(
    {
        "candidate_returned_success",
        "completed_success",
        "ok",
        "returned_success",
        "success",
        "succeeded",
    }
)

VERIFY_REPLAY_ACCEPTED = "VERIFY_REPLAY_ACCEPTED"
VERIFY_REPLAY_REJECTED = "VERIFY_REPLAY_REJECTED"

AUTHORITY_SNAPSHOT = {
    "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "safe_default": SAFE_DEFAULT,
    "phase11a_step": PHASE11A_STEP,
    "phase11a1_wiring_status": PHASE11A1_WIRING_STATUS_NOT_STARTED,
    "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
}

NON_CLAIM_CAVEATS = (
    "11-A-0 records rollback and kill-path readiness only",
    "no save_run write path wiring",
    "no build_evidence_packet runtime mediation wiring",
    "no actual mediator activation",
    "no actual enforcement activation",
    "known-gap expected-red status is preserved",
    "no live executor authority grant",
    "no raw shell authority grant",
    "no write_file tool grant",
    "no run_command tool grant",
    "no process_spawn authority grant",
    "no provider model network authority grant",
    "no runtime write authority grant",
    "no Phase 11-B implementation",
)

_EVIDENCE_FIELDS = frozenset(
    {
        "record_kind",
        "record_version",
        "claim_type",
        "write_path_mode",
        "write_path_wiring_attempted",
        "write_path_wiring_status",
        "write_path_fallback_triggered",
        "write_path_fallback_reason",
        "write_path_fallback_target",
        "write_path_runtime_mode",
        "safe_default",
        "live_executor_authority",
        "phase11a_step",
        "phase11a1_wiring_status",
        "phase11b_status",
        "known_gap_status",
        "automatic_failure_fallback",
        "manual_kill_path_candidate",
        "candidate_wired_path_result",
        "fallback_result",
        "authority_snapshot",
        "non_claim_caveats",
        "deterministic_evidence_digest",
    }
)

_OVERCLAIM_KEYS = {
    "save_run_wiring_active": "save_run wiring active claim rejected",
    "runtime_mediation_wiring_active": "runtime mediation wiring active claim rejected",
    "actual_mediator_active": "actual mediator activation claim rejected",
    "actual_enforcement_active": "actual enforcement activation claim rejected",
    "runtime_write_authority_granted": "runtime write authority grant claim rejected",
    "live_executor_authority_granted": "live executor authority grant claim rejected",
    "phase11b_started": "Phase 11-B start claim rejected",
}


@dataclass(frozen=True)
class Phase11aKillPathConfig:
    """In-memory kill-path switch candidate for future config integration."""

    manual_kill_path_triggered: bool = False
    manual_kill_path_reason: str = FALLBACK_REASON_MANUAL_KILL_PATH


@dataclass(frozen=True)
class CandidateWiredPathResult:
    """In-memory result from a simulated candidate wired path."""

    success: bool
    reason: str
    result: Mapping[str, Any] | None = None


def existing_unwired_behavior_result() -> dict[str, Any]:
    """Return the stable current behavior marker without writing anything."""

    return {
        "behavior": "existing_unwired_behavior",
        "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        "safe_default": SAFE_DEFAULT,
        "write_performed": False,
    }


def execute_phase11a_rollback_kill_path(
    *,
    candidate_wired_path: Callable[[], CandidateWiredPathResult | Mapping[str, Any]] | None = None,
    existing_unwired_behavior: Callable[[], Mapping[str, Any]] = existing_unwired_behavior_result,
    config: Phase11aKillPathConfig | None = None,
) -> dict[str, Any]:
    """Run the in-memory rollback scaffold and return digest-bound evidence."""

    kill_config = config or Phase11aKillPathConfig()
    attempted = False
    fallback_triggered = False
    fallback_reason = FALLBACK_REASON_NOT_NEEDED
    candidate_result: dict[str, Any] = {
        "attempted": False,
        "status": "not_attempted",
        "reason": "no_candidate_wired_path_supplied",
    }

    if kill_config.manual_kill_path_triggered:
        fallback_triggered = True
        fallback_reason = kill_config.manual_kill_path_reason
        wiring_status = WRITE_PATH_STATUS_FALLBACK_USED
        candidate_result = {
            "attempted": False,
            "status": "skipped_by_manual_kill_path",
            "reason": fallback_reason,
        }
    elif candidate_wired_path is None:
        wiring_status = WRITE_PATH_STATUS_NOT_WIRED
    else:
        attempted = True
        try:
            raw_candidate_result = candidate_wired_path()
            candidate_result = _candidate_result_to_record(raw_candidate_result)
            if candidate_result.get("success") is True:
                fallback_reason = FALLBACK_REASON_CANDIDATE_SUCCESS_OUT_OF_SCOPE
                fallback_triggered = False
                wiring_status = CANDIDATE_SUCCESS_REJECTED_STATUS
            else:
                fallback_reason = FALLBACK_REASON_CANDIDATE_RETURNED_FAILURE
                fallback_triggered = True
                wiring_status = WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED
        except Exception as exc:  # noqa: BLE001 - rollback path must catch candidate failures.
            fallback_triggered = True
            fallback_reason = FALLBACK_REASON_CANDIDATE_RAISED_EXCEPTION
            wiring_status = WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED
            candidate_result = {
                "attempted": True,
                "success": False,
                "status": "raised_exception",
                "exception_type": exc.__class__.__name__,
                "reason": fallback_reason,
            }

    fallback_result = dict(existing_unwired_behavior())
    return build_phase11a_rollback_kill_path_evidence(
        write_path_wiring_attempted=attempted,
        write_path_wiring_status=wiring_status,
        write_path_fallback_triggered=fallback_triggered,
        write_path_fallback_reason=fallback_reason,
        candidate_wired_path_result=candidate_result,
        fallback_result=fallback_result,
    )


def build_phase11a_rollback_kill_path_evidence(
    *,
    write_path_wiring_attempted: bool,
    write_path_wiring_status: str,
    write_path_fallback_triggered: bool,
    write_path_fallback_reason: str,
    candidate_wired_path_result: Mapping[str, Any],
    fallback_result: Mapping[str, Any],
    write_path_fallback_target: str = FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
) -> dict[str, Any]:
    """Build a deterministic Phase 11-A-0 rollback evidence record."""

    record = {
        "record_kind": PHASE11A_ROLLBACK_KILL_PATH_KIND,
        "record_version": PHASE11A_ROLLBACK_KILL_PATH_VERSION,
        "claim_type": "rollback_kill_path_scaffold_not_runtime_wiring",
        "write_path_mode": WRITE_PATH_MODE_ROLLBACK_KILL_PATH_ONLY,
        "write_path_wiring_attempted": write_path_wiring_attempted,
        "write_path_wiring_status": write_path_wiring_status,
        "write_path_fallback_triggered": write_path_fallback_triggered,
        "write_path_fallback_reason": write_path_fallback_reason,
        "write_path_fallback_target": write_path_fallback_target,
        "write_path_runtime_mode": WRITE_PATH_RUNTIME_MODE_NOT_WIRED,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11a_step": PHASE11A_STEP,
        "phase11a1_wiring_status": PHASE11A1_WIRING_STATUS_NOT_STARTED,
        "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
        "known_gap_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
        "automatic_failure_fallback": {
            "trigger": "candidate_wired_path_failure_or_exception",
            "fallback_target": FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
            "process_crash_expected": False,
        },
        "manual_kill_path_candidate": {
            "mode": "in_memory_config_or_explicit_function_arg",
            "runtime_config_mutation": False,
            "env_file_access": False,
            "credential_material_access": False,
        },
        "candidate_wired_path_result": deepcopy(dict(candidate_wired_path_result)),
        "fallback_result": deepcopy(dict(fallback_result)),
        "authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
    }
    record["deterministic_evidence_digest"] = phase11a_rollback_evidence_digest(record)
    return record


def verify_phase11a_rollback_kill_path_evidence(
    evidence_record: Mapping[str, Any],
    *,
    expected_fallback_target: str = FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
) -> dict[str, Any]:
    """Verify schema, digest binding, authority preservation, and overclaims."""

    reasons: list[str] = []
    if not isinstance(evidence_record, Mapping):
        evidence_record = {}
        reasons.append("evidence record must be a mapping")

    unexpected_fields = sorted(set(evidence_record) - _EVIDENCE_FIELDS)
    for field in unexpected_fields:
        reasons.append(f"unexpected evidence record field: {field}")

    missing_fields = sorted(_EVIDENCE_FIELDS - set(evidence_record))
    for field in missing_fields:
        reasons.append(f"missing evidence record field: {field}")

    _expect_field(reasons, evidence_record, "record_kind", PHASE11A_ROLLBACK_KILL_PATH_KIND)
    _expect_field(reasons, evidence_record, "record_version", PHASE11A_ROLLBACK_KILL_PATH_VERSION)
    _expect_field(reasons, evidence_record, "claim_type", "rollback_kill_path_scaffold_not_runtime_wiring")
    _expect_field(reasons, evidence_record, "write_path_mode", WRITE_PATH_MODE_ROLLBACK_KILL_PATH_ONLY)
    _expect_field(reasons, evidence_record, "write_path_runtime_mode", WRITE_PATH_RUNTIME_MODE_NOT_WIRED)
    _expect_field(reasons, evidence_record, "safe_default", SAFE_DEFAULT)
    _expect_field(reasons, evidence_record, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
    _expect_field(reasons, evidence_record, "phase11a_step", PHASE11A_STEP)
    _expect_field(reasons, evidence_record, "phase11a1_wiring_status", PHASE11A1_WIRING_STATUS_NOT_STARTED)
    _expect_field(reasons, evidence_record, "phase11b_status", PHASE11B_STATUS_NOT_STARTED)
    _expect_field(reasons, evidence_record, "known_gap_status", B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
    _expect_field(reasons, evidence_record, "authority_snapshot", AUTHORITY_SNAPSHOT)

    if evidence_record.get("write_path_fallback_target") != expected_fallback_target:
        reasons.append("write_path_fallback_target mismatch")
    if evidence_record.get("write_path_fallback_target") != FALLBACK_TARGET_EXISTING_UNWIRED_PATH:
        reasons.append("fallback target must remain existing_unwired_path")

    _validate_bool_field(reasons, evidence_record, "write_path_wiring_attempted")
    _validate_bool_field(reasons, evidence_record, "write_path_fallback_triggered")
    _validate_status_consistency(reasons, evidence_record)
    _validate_candidate_wired_path_result(reasons, evidence_record)
    _validate_fallback_result(reasons, evidence_record.get("fallback_result"))
    _validate_manual_kill_path_candidate(reasons, evidence_record.get("manual_kill_path_candidate"))
    _validate_automatic_failure_fallback(reasons, evidence_record.get("automatic_failure_fallback"))

    supplied_digest = evidence_record.get("deterministic_evidence_digest")
    recomputed_digest = phase11a_rollback_evidence_digest(evidence_record)
    if supplied_digest != recomputed_digest:
        reasons.append("deterministic evidence digest mismatch")

    reasons.extend(_recursive_overclaim_rejections(evidence_record))
    reasons = _unique(reasons)
    accepted = not reasons
    return {
        "accepted": accepted,
        "status": VERIFY_REPLAY_ACCEPTED if accepted else VERIFY_REPLAY_REJECTED,
        "rejection_reasons": reasons,
        "verification_scope": "phase11a_rollback_kill_path_replay_only",
        "is_runtime_wiring": False,
        "is_runtime_enforcement": False,
        "safe_default": SAFE_DEFAULT,
    }


def phase11a_rollback_evidence_digest(evidence_record: Mapping[str, Any]) -> str:
    """Return the deterministic digest for the evidence payload."""

    payload = deepcopy(dict(evidence_record))
    payload.pop("deterministic_evidence_digest", None)
    return _sha256_json(payload)


def _candidate_result_to_record(value: CandidateWiredPathResult | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, CandidateWiredPathResult):
        return {
            "attempted": True,
            "success": value.success,
            "status": "returned_success" if value.success else "returned_failure",
            "reason": value.reason,
            "result": deepcopy(dict(value.result or {})),
        }
    if isinstance(value, Mapping):
        result = deepcopy(dict(value))
        result.setdefault("attempted", True)
        result.setdefault("success", False)
        result.setdefault("status", "returned_mapping")
        result.setdefault("reason", FALLBACK_REASON_CANDIDATE_RETURNED_FAILURE)
        return result
    return {
        "attempted": True,
        "success": False,
        "status": "invalid_candidate_result",
        "reason": FALLBACK_REASON_CANDIDATE_RETURNED_FAILURE,
    }


def _validate_status_consistency(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    status = evidence_record.get("write_path_wiring_status")
    attempted = evidence_record.get("write_path_wiring_attempted")
    fallback_triggered = evidence_record.get("write_path_fallback_triggered")
    fallback_reason = evidence_record.get("write_path_fallback_reason")

    if status not in ALLOWED_WRITE_PATH_WIRING_STATUSES:
        reasons.append(f"invalid write_path_wiring_status: {status}")
    if status == WRITE_PATH_STATUS_NOT_WIRED:
        if attempted is not False:
            reasons.append("NOT_WIRED status requires write_path_wiring_attempted false")
        if fallback_triggered is not False:
            reasons.append("NOT_WIRED status requires write_path_fallback_triggered false")
        if fallback_reason != FALLBACK_REASON_NOT_NEEDED:
            reasons.append("NOT_WIRED status requires not-needed fallback reason")
    if status == WRITE_PATH_STATUS_FALLBACK_READY:
        if attempted is not False or fallback_triggered is not False:
            reasons.append("FALLBACK_READY status cannot claim an attempted or used fallback")
    if status == WRITE_PATH_STATUS_FALLBACK_USED:
        if attempted is not False or fallback_triggered is not True:
            reasons.append("FALLBACK_USED status requires manual fallback without wiring attempt")
    if status == WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED:
        if attempted is not True or fallback_triggered is not True:
            reasons.append("failed wiring fallback status requires attempted wiring and triggered fallback")
        if fallback_reason not in (
            FALLBACK_REASON_CANDIDATE_RETURNED_FAILURE,
            FALLBACK_REASON_CANDIDATE_RAISED_EXCEPTION,
        ):
            reasons.append("failed wiring fallback status has invalid fallback reason")
    if fallback_reason == LEGACY_FALLBACK_REASON_CANDIDATE_SUCCESS_NOT_ACTIVATED:
        reasons.append("candidate wired path success is outside 11-A-0 scope")
    if fallback_reason == FALLBACK_REASON_CANDIDATE_SUCCESS_OUT_OF_SCOPE:
        reasons.append("candidate wired path success is outside 11-A-0 scope")


def _validate_candidate_wired_path_result(reasons: list[str], evidence_record: Mapping[str, Any]) -> None:
    value = evidence_record.get("candidate_wired_path_result")
    if not isinstance(value, Mapping):
        reasons.append("candidate_wired_path_result must be a mapping")
        return
    if value.get("success") is True:
        reasons.append("candidate wired path success is outside 11-A-0 scope")

    raw_status = value.get("status")
    if isinstance(raw_status, str):
        normalized_status = raw_status.strip().lower()
        if normalized_status in SUCCESS_LIKE_CANDIDATE_STATUSES:
            reasons.append("candidate wired path returned success in 11-A-0")


def _validate_fallback_result(reasons: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        reasons.append("fallback_result must be a mapping")
        return
    if value.get("behavior") != "existing_unwired_behavior":
        reasons.append("fallback_result behavior mismatch")
    if value.get("runtime_write_path") != NOT_WIRED_TO_EXECUTOR_WRITE_PATH:
        reasons.append("fallback_result runtime_write_path mismatch")
    if value.get("safe_default") != SAFE_DEFAULT:
        reasons.append("fallback_result safe_default mismatch")
    if value.get("write_performed") is not False:
        reasons.append("fallback_result must not record a write")


def _validate_manual_kill_path_candidate(reasons: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        reasons.append("manual_kill_path_candidate must be a mapping")
        return
    expected = {
        "mode": "in_memory_config_or_explicit_function_arg",
        "runtime_config_mutation": False,
        "env_file_access": False,
        "credential_material_access": False,
    }
    if dict(value) != expected:
        reasons.append("manual_kill_path_candidate mismatch")


def _validate_automatic_failure_fallback(reasons: list[str], value: Any) -> None:
    if not isinstance(value, Mapping):
        reasons.append("automatic_failure_fallback must be a mapping")
        return
    expected = {
        "trigger": "candidate_wired_path_failure_or_exception",
        "fallback_target": FALLBACK_TARGET_EXISTING_UNWIRED_PATH,
        "process_crash_expected": False,
    }
    if dict(value) != expected:
        reasons.append("automatic_failure_fallback mismatch")


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
    "ALLOWED_WRITE_PATH_WIRING_STATUSES",
    "AUTHORITY_SNAPSHOT",
    "CandidateWiredPathResult",
    "FALLBACK_TARGET_EXISTING_UNWIRED_PATH",
    "PHASE11A1_WIRING_STATUS_NOT_STARTED",
    "PHASE11A_ROLLBACK_KILL_PATH_KIND",
    "PHASE11A_ROLLBACK_KILL_PATH_VERSION",
    "PHASE11A_STEP",
    "PHASE11B_STATUS_NOT_STARTED",
    "Phase11aKillPathConfig",
    "VERIFY_REPLAY_ACCEPTED",
    "VERIFY_REPLAY_REJECTED",
    "WRITE_PATH_RUNTIME_MODE_NOT_WIRED",
    "WRITE_PATH_STATUS_FALLBACK_USED",
    "WRITE_PATH_STATUS_NOT_WIRED",
    "WRITE_PATH_STATUS_WIRING_FAILED_FALLBACK_USED",
    "build_phase11a_rollback_kill_path_evidence",
    "execute_phase11a_rollback_kill_path",
    "existing_unwired_behavior_result",
    "phase11a_rollback_evidence_digest",
    "verify_phase11a_rollback_kill_path_evidence",
]
