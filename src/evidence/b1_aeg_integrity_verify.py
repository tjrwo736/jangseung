"""Verify-only rejection for B1-C ``.aeg`` guard evidence records.

This module replays canonical digests and rejects mismatch, tamper, reported
only promotion, known-gap promotion, and scope overclaim fields. It does not
write records, harden permissions, wire executor writes, or change the B1-A
raw-path known-gap baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED,
    B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF,
    B1_AEG_GUARD_DECISION_BOUND,
    B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED,
    B1_AEG_GUARD_EVIDENCE_BINDING,
    B1_AEG_GUARD_EVIDENCE_DIGEST,
    B1_AEG_GUARD_EVIDENCE_OVERCLAIM_REJECTED,
    B1_AEG_GUARD_EVIDENCE_RECORD,
    B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED,
    B1_AEG_GUARD_EVIDENCE_REPLAY_CONSISTENT,
    B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION,
    B1_AEG_GUARD_FIELD_MISMATCH_REJECTED,
    B1_AEG_GUARD_NOT_CHECKED_PROMOTION_REJECTED,
    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED,
    B1_AEG_GUARD_REPORTED_ONLY_PROMOTION_REJECTED,
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_TAMPER_PROOF,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence.b1_aeg_integrity_evidence_binding import (
    B1_AEG_GUARD_EVIDENCE_BINDING_VERSION,
)

B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION_VERSION = (
    "B1_D_AEG_INTEGRITY_GUARD_EVIDENCE_VERIFY_REJECTION_V0"
)
B1_AEG_GUARD_EVIDENCE_REPLAY_REJECTED = "B1_AEG_GUARD_EVIDENCE_REPLAY_REJECTED"

_BOUND_FIELDS = (
    "submitted_path",
    "resolved_path",
    "protected_root",
    "target_class",
    "denial_reason",
    "wiring_status",
)

_PAYLOAD_FIELDS = (
    "binding_version",
    "component",
    "record_type",
    "guard_decision_binding_status",
    "no_mutation_observation_status",
    "digest_status",
    "guard_decision_id",
    "guard_decision_digest",
    "submitted_path",
    "resolved_path",
    "protected_root",
    "target_class",
    "denial_reason",
    "wiring_status",
    "guard_decision",
    "no_mutation_observation",
    "known_gap_baseline_status",
    "raw_direct_path_status",
    "tamper_proof_status",
    "external_anchor_status",
    "os_enforcement_status",
    "filesystem_enforcement_status",
    "live_executor_authority_status",
    "phase11a_status",
    "enforcement_complete_claimed",
    "executor_write_path_wired",
    "filesystem_mutation_performed",
)

_EXPECTED_TOP_LEVEL = {
    "binding_version": B1_AEG_GUARD_EVIDENCE_BINDING_VERSION,
    "component": B1_AEG_GUARD_EVIDENCE_BINDING,
    "record_type": B1_AEG_GUARD_EVIDENCE_RECORD,
    "guard_decision_binding_status": B1_AEG_GUARD_DECISION_BOUND,
    "no_mutation_observation_status": B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
    "digest_status": B1_AEG_GUARD_EVIDENCE_DIGEST,
    "known_gap_baseline_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    "raw_direct_path_status": WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    "tamper_proof_status": B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF,
    "external_anchor_status": B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED,
    "os_enforcement_status": NOT_OS_ENFORCED,
    "filesystem_enforcement_status": NOT_FILESYSTEM_ENFORCED,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "enforcement_complete_claimed": False,
    "executor_write_path_wired": False,
    "filesystem_mutation_performed": False,
}

_EXPECTED_OBSERVATION = {
    "observation_status": B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
    "os_enforcement_status": NOT_OS_ENFORCED,
    "filesystem_enforcement_status": NOT_FILESYSTEM_ENFORCED,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "write_performed": False,
    "filesystem_mutation_performed": False,
    "mutation_observed": False,
    "no_mutation_observed": True,
}

_PASSLIKE = frozenset(("PASS", "CLEAN", "ENFORCED"))
_OVERCLAIM_LABELS = frozenset(
    (
        "B1_" + "COMPLETE",
        "TAMPER_" + "PROOF",
        "EXECUTOR_" + "ISOLATED",
        "FILESYSTEM_" + "ENFORCED",
        "OS_" + "ENFORCED",
        "EXTERNALLY_" + "ENFORCED",
        "EXTERNAL_" + "ANCHOR_ACTIVE",
        "BYPASS_" + "IMPOSSIBLE",
        "LIVE_" + "EXECUTOR_READY",
        "SAFE_" + "TO_RUN",
        "WRITE_" + "AUTHORITY_SAFE",
    )
)
_OVERCLAIM_TRUE_FIELDS = frozenset(
    (
        "enforcement_complete_claimed",
        "executor_write_path_wired",
        "filesystem_mutation_performed",
        "tamper_proof_claimed",
        "external_anchor_active",
        "filesystem_enforced",
        "os_enforced",
        "executor_isolated",
        "live_executor_ready",
        "safe_to_run",
        "write_authority_safe",
    )
)


@dataclass(frozen=True)
class B1AegGuardEvidenceVerifyResult:
    """Result of verify-only replay for a B1-C guard evidence record."""

    component: str
    version: str
    status: str
    consistent: bool
    replay_status: str
    rejection_codes: tuple[str, ...]
    checks: tuple[str, ...]
    scope_status: str = B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT
    tamper_proof_status: str = NOT_TAMPER_PROOF
    external_anchor_status: str = NOT_EXTERNAL_ANCHORED
    os_enforcement_status: str = NOT_OS_ENFORCED
    filesystem_enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    wiring_status: str = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    phase11a_status: str = PHASE11A_NOT_STARTED


def verify_b1_aeg_guard_evidence_record(
    record: Mapping[str, Any] | Any,
) -> B1AegGuardEvidenceVerifyResult:
    """Replay and validate a B1-C guard evidence record without mutation."""

    evidence = _coerce_record(record)
    rejections: list[str] = []
    checks: list[str] = []

    _verify_guard_decision_digest(evidence, rejections, checks)
    _verify_evidence_record_digest(evidence, rejections, checks)
    _verify_bound_fields(evidence, rejections, checks)
    _verify_expected_scope_fields(evidence, rejections, checks)
    _verify_no_mutation_observation(evidence, rejections, checks)
    _verify_overclaims(evidence, rejections, checks)
    _verify_reported_only_promotion(evidence, rejections, checks)
    _verify_not_checked_or_known_gap_promotion(evidence, rejections, checks)

    rejection_codes = tuple(dict.fromkeys(rejections))
    consistent = not rejection_codes
    status = (
        B1_AEG_GUARD_EVIDENCE_REPLAY_CONSISTENT
        if consistent
        else B1_AEG_GUARD_EVIDENCE_REPLAY_REJECTED
    )
    if consistent:
        checks.append("B1-C guard evidence record replay matched canonical digests")
        checks.append("B1-A known-gap baseline remains preserved")
        checks.append("B1-B deny-only guard component remains preserved")
        checks.append("B1-C evidence binding remains preserved")

    return B1AegGuardEvidenceVerifyResult(
        component=B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION,
        version=B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION_VERSION,
        status=status,
        consistent=consistent,
        replay_status=status,
        rejection_codes=rejection_codes,
        checks=tuple(checks),
    )


def b1_aeg_guard_evidence_record_digest_from_mapping(record: Mapping[str, Any]) -> str:
    """Return the B1-C canonical payload digest for a mapping record."""

    return _sha256_json(_evidence_payload(record))


def _verify_guard_decision_digest(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    guard_decision = evidence.get("guard_decision")
    if not isinstance(guard_decision, Mapping):
        _reject(rejections, B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED)
        checks.append("guard_decision missing or not a mapping")
        return

    expected_digest = _sha256_json(dict(guard_decision))
    if evidence.get("guard_decision_digest") == expected_digest:
        checks.append("guard decision digest replay matched")
    else:
        _reject(rejections, B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED)
        checks.append("guard decision digest mismatch rejected")


def _verify_evidence_record_digest(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    expected_digest = b1_aeg_guard_evidence_record_digest_from_mapping(evidence)
    record_id = evidence.get("record_id")
    expected_record_id = f"b1-aeg-guard-evidence:{expected_digest}"

    if evidence.get("evidence_record_digest") == expected_digest and record_id == expected_record_id:
        checks.append("evidence record digest replay matched")
        return

    _reject(rejections, B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED)
    if evidence.get("evidence_record_digest") != expected_digest:
        checks.append("evidence record digest mismatch rejected")
    if record_id != expected_record_id:
        checks.append("same record canonical digest mismatch rejected")


def _verify_bound_fields(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    guard_decision = evidence.get("guard_decision")
    observation = evidence.get("no_mutation_observation")
    mismatch_found = False
    for field in _BOUND_FIELDS:
        top_level = evidence.get(field)
        if not isinstance(guard_decision, Mapping) or guard_decision.get(field) != top_level:
            mismatch_found = True
            checks.append(f"{field} guard decision mismatch rejected")
        if not isinstance(observation, Mapping) or observation.get(field) != top_level:
            mismatch_found = True
            checks.append(f"{field} no-mutation observation mismatch rejected")

    if mismatch_found:
        _reject(rejections, B1_AEG_GUARD_FIELD_MISMATCH_REJECTED)
    else:
        checks.append("submitted/resolved/protected/class/reason/wiring fields matched")


def _verify_expected_scope_fields(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    mismatch_found = False
    for field, expected in _EXPECTED_TOP_LEVEL.items():
        if evidence.get(field) != expected:
            mismatch_found = True
            checks.append(f"{field} expected {expected!r} but found {evidence.get(field)!r}")

    if mismatch_found:
        _reject(rejections, B1_AEG_GUARD_FIELD_MISMATCH_REJECTED)
    else:
        checks.append("B1-D verify-only scope fields remained non-enforcement")


def _verify_no_mutation_observation(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    observation = evidence.get("no_mutation_observation")
    if not isinstance(observation, Mapping):
        _reject(rejections, B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED)
        checks.append("no-mutation observation missing or not a mapping")
        return

    mismatch_found = False
    for field, expected in _EXPECTED_OBSERVATION.items():
        if observation.get(field) != expected:
            mismatch_found = True
            checks.append(f"no-mutation observation {field} mismatch rejected")

    if evidence.get("filesystem_mutation_performed") is not False:
        mismatch_found = True
        checks.append("top-level filesystem mutation mismatch rejected")

    if mismatch_found:
        _reject(rejections, B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED)
    else:
        checks.append("no-mutation observation replay matched")


def _verify_overclaims(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    overclaims: list[str] = []

    for path, value in _walk_values(evidence):
        if isinstance(value, str) and value in _OVERCLAIM_LABELS:
            overclaims.append(path)
        if path.rsplit(".", 1)[-1] in _OVERCLAIM_TRUE_FIELDS and value is True:
            overclaims.append(path)

    if overclaims:
        _reject(rejections, B1_AEG_GUARD_EVIDENCE_OVERCLAIM_REJECTED)
        checks.append("overclaim rejected at " + ", ".join(sorted(overclaims)))
    else:
        checks.append("no completion, anchor, hardening, isolation, live, or run-safety overclaim found")


def _verify_reported_only_promotion(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    reported_only_present = any(value == REPORTED_ONLY for _, value in _walk_values(evidence))
    reported_only_flag = any(
        path.rsplit(".", 1)[-1].endswith("reported_only") and value is True
        for path, value in _walk_values(evidence)
    )
    judgment_basis = evidence.get("judgment_basis")
    promotion = (
        judgment_basis is True
        or judgment_basis == REPORTED_ONLY
        or evidence.get("guard_denial_evidence_judgment_basis") is True
        or evidence.get("reported_only_judgment_basis_allowed") is True
    )

    if (reported_only_present or reported_only_flag) and promotion:
        _reject(rejections, B1_AEG_GUARD_REPORTED_ONLY_PROMOTION_REJECTED)
        checks.append("reported_only guard denial evidence promotion rejected")
    else:
        checks.append("reported_only guard denial evidence was not promoted to judgment basis")


def _verify_not_checked_or_known_gap_promotion(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    promotions: list[str] = []

    for path, value in _walk_values(evidence):
        field = path.rsplit(".", 1)[-1].lower()
        if not isinstance(value, str) or value not in _PASSLIKE:
            continue
        if "not_checked" in field or "known_gap" in field or field == "raw_direct_path_status":
            promotions.append(path)

    if evidence.get("not_checked_source") == NOT_CHECKED and evidence.get("not_checked_result") in _PASSLIKE:
        promotions.append("not_checked_result")
    if (
        evidence.get("known_gap_source") == B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE
        and evidence.get("known_gap_result") in _PASSLIKE
    ):
        promotions.append("known_gap_result")

    if promotions:
        _reject(rejections, B1_AEG_GUARD_NOT_CHECKED_PROMOTION_REJECTED)
        checks.append("NOT_CHECKED or known-gap promotion rejected at " + ", ".join(sorted(promotions)))
    else:
        checks.append("NOT_CHECKED and known-gap states were not promoted to passlike labels")


def _evidence_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {field: record.get(field) for field in _PAYLOAD_FIELDS}


def _coerce_record(record: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if hasattr(record, "to_record"):
        return dict(record.to_record())
    raise TypeError("record must be a mapping or expose to_record()")


def _walk_values(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(payload, Mapping):
        values: list[tuple[str, Any]] = []
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            values.extend(_walk_values(value, path))
        return values
    if isinstance(payload, list):
        values = []
        for index, value in enumerate(payload):
            values.extend(_walk_values(value, f"{prefix}[{index}]"))
        return values
    return [(prefix, payload)]


def _reject(rejections: list[str], code: str) -> None:
    if code not in rejections:
        rejections.append(code)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "B1_AEG_GUARD_EVIDENCE_REPLAY_REJECTED",
    "B1_AEG_GUARD_EVIDENCE_VERIFY_REJECTION_VERSION",
    "B1AegGuardEvidenceVerifyResult",
    "b1_aeg_guard_evidence_record_digest_from_mapping",
    "verify_b1_aeg_guard_evidence_record",
]
