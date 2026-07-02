"""B1-C deterministic evidence binding for B1-B ``.aeg`` guard decisions.

This component binds an existing guard decision to a canonical evidence record.
It does not store records, harden permissions, wire executor writes, or change
the B1-A raw-path known-gap baseline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED,
    B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF,
    B1_AEG_GUARD_DECISION_BOUND,
    B1_AEG_GUARD_EVIDENCE_BINDING,
    B1_AEG_GUARD_EVIDENCE_DIGEST,
    B1_AEG_GUARD_EVIDENCE_RECORD,
    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)

B1_AEG_GUARD_EVIDENCE_BINDING_VERSION = "B1_C_AEG_INTEGRITY_GUARD_EVIDENCE_BINDING_V0"


@dataclass(frozen=True)
class B1AegGuardNoMutationObservation:
    """No-mutation observation bound to a denied B1-B guard decision."""

    submitted_path: str
    resolved_path: str
    protected_root: str
    target_class: str
    denial_reason: str
    wiring_status: str
    write_performed: bool
    filesystem_mutation_performed: bool
    mutation_observed: bool
    no_mutation_observed: bool
    observation_status: str = B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND
    os_enforcement_status: str = NOT_OS_ENFORCED
    filesystem_enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    phase11a_status: str = PHASE11A_NOT_STARTED

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class B1AegGuardEvidenceRecord:
    """Canonical evidence record for a denied B1-B guard decision."""

    record_id: str
    evidence_record_digest: str
    guard_decision_digest: str
    binding_version: str
    component: str
    record_type: str
    guard_decision_binding_status: str
    no_mutation_observation_status: str
    digest_status: str
    guard_decision_id: str
    submitted_path: str
    resolved_path: str
    protected_root: str
    target_class: str
    denial_reason: str
    wiring_status: str
    guard_decision: Mapping[str, Any]
    no_mutation_observation: Mapping[str, Any]
    known_gap_baseline_status: str
    raw_direct_path_status: str
    tamper_proof_status: str
    external_anchor_status: str
    os_enforcement_status: str
    filesystem_enforcement_status: str
    live_executor_authority_status: str
    phase11a_status: str
    enforcement_complete_claimed: bool
    executor_write_path_wired: bool
    filesystem_mutation_performed: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "evidence_record_digest": self.evidence_record_digest,
            "guard_decision_digest": self.guard_decision_digest,
            **_guard_evidence_payload(self),
        }


def build_b1_aeg_guard_no_mutation_observation(
    *,
    guard_decision: Any,
) -> B1AegGuardNoMutationObservation:
    """Build a no-mutation observation from a B1-B guard decision."""

    write_performed = bool(guard_decision.write_performed)
    filesystem_mutation_performed = bool(guard_decision.filesystem_mutation_performed)
    mutation_observed = write_performed or filesystem_mutation_performed
    return B1AegGuardNoMutationObservation(
        submitted_path=guard_decision.submitted_path,
        resolved_path=guard_decision.resolved_path,
        protected_root=guard_decision.protected_root,
        target_class=guard_decision.target_class,
        denial_reason=guard_decision.denial_reason,
        wiring_status=guard_decision.wiring_status,
        write_performed=write_performed,
        filesystem_mutation_performed=filesystem_mutation_performed,
        mutation_observed=mutation_observed,
        no_mutation_observed=not mutation_observed,
    )


def build_b1_aeg_guard_evidence_record(
    *,
    guard_decision: Any,
    no_mutation_observation: B1AegGuardNoMutationObservation | None = None,
) -> B1AegGuardEvidenceRecord:
    """Bind a B1-B guard decision to deterministic B1-C evidence."""

    observation = no_mutation_observation or build_b1_aeg_guard_no_mutation_observation(
        guard_decision=guard_decision,
    )
    guard_decision_record = guard_decision.to_record()
    guard_decision_digest = _sha256_json(guard_decision_record)
    payload: dict[str, Any] = {
        "binding_version": B1_AEG_GUARD_EVIDENCE_BINDING_VERSION,
        "component": B1_AEG_GUARD_EVIDENCE_BINDING,
        "record_type": B1_AEG_GUARD_EVIDENCE_RECORD,
        "guard_decision_binding_status": B1_AEG_GUARD_DECISION_BOUND,
        "no_mutation_observation_status": B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
        "digest_status": B1_AEG_GUARD_EVIDENCE_DIGEST,
        "guard_decision_id": guard_decision.decision_id,
        "guard_decision_digest": guard_decision_digest,
        "submitted_path": guard_decision.submitted_path,
        "resolved_path": guard_decision.resolved_path,
        "protected_root": guard_decision.protected_root,
        "target_class": guard_decision.target_class,
        "denial_reason": guard_decision.denial_reason,
        "wiring_status": guard_decision.wiring_status,
        "guard_decision": guard_decision_record,
        "no_mutation_observation": observation.to_record(),
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
    evidence_record_digest = _sha256_json(payload)
    return B1AegGuardEvidenceRecord(
        record_id=f"b1-aeg-guard-evidence:{evidence_record_digest}",
        evidence_record_digest=evidence_record_digest,
        **payload,
    )


def b1_aeg_guard_evidence_digest(record: B1AegGuardEvidenceRecord) -> str:
    """Recompute the canonical digest for a B1-C guard evidence record."""

    return _sha256_json(_guard_evidence_payload(record))


def _guard_evidence_payload(record: B1AegGuardEvidenceRecord) -> dict[str, Any]:
    return {
        "binding_version": record.binding_version,
        "component": record.component,
        "record_type": record.record_type,
        "guard_decision_binding_status": record.guard_decision_binding_status,
        "no_mutation_observation_status": record.no_mutation_observation_status,
        "digest_status": record.digest_status,
        "guard_decision_id": record.guard_decision_id,
        "guard_decision_digest": record.guard_decision_digest,
        "submitted_path": record.submitted_path,
        "resolved_path": record.resolved_path,
        "protected_root": record.protected_root,
        "target_class": record.target_class,
        "denial_reason": record.denial_reason,
        "wiring_status": record.wiring_status,
        "guard_decision": dict(record.guard_decision),
        "no_mutation_observation": dict(record.no_mutation_observation),
        "known_gap_baseline_status": record.known_gap_baseline_status,
        "raw_direct_path_status": record.raw_direct_path_status,
        "tamper_proof_status": record.tamper_proof_status,
        "external_anchor_status": record.external_anchor_status,
        "os_enforcement_status": record.os_enforcement_status,
        "filesystem_enforcement_status": record.filesystem_enforcement_status,
        "live_executor_authority_status": record.live_executor_authority_status,
        "phase11a_status": record.phase11a_status,
        "enforcement_complete_claimed": record.enforcement_complete_claimed,
        "executor_write_path_wired": record.executor_write_path_wired,
        "filesystem_mutation_performed": record.filesystem_mutation_performed,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "B1_AEG_GUARD_EVIDENCE_BINDING_VERSION",
    "B1AegGuardEvidenceRecord",
    "B1AegGuardNoMutationObservation",
    "b1_aeg_guard_evidence_digest",
    "build_b1_aeg_guard_evidence_record",
    "build_b1_aeg_guard_no_mutation_observation",
]
