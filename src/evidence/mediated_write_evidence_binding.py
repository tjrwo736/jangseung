"""Deterministic evidence binding for denied mediated writes.

This module binds an already-denied mediated write result to a stable evidence
record. It does not verify mismatches, harden permissions, intercept raw
filesystem writes, anchor records externally, or grant live executor authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    BINDING_DIGEST_PRESENT,
    DENIED_WRITE_DECISION_EVIDENCE_BOUND,
    EVIDENCE_BINDING_PRESENT,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATED_WRITE_EVIDENCE_BINDING_V0,
    MEDIATED_WRITE_EVIDENCE_BOUND,
    NO_MUTATION_OBSERVATION_BOUND,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_TAMPER_PROOF,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
)


@dataclass(frozen=True)
class DeniedWriteNoMutationObservation:
    """Digest-level observation supplied by the denied-write test harness."""

    canonical_target: str
    target_exists_before: bool
    target_exists_after: bool
    content_digest_before: str
    content_digest_after: str
    observation_source: str
    write_performed: bool
    mutation_observed: bool
    no_mutation_observed: bool
    observation_status: str = NO_MUTATION_OBSERVATION_BOUND
    filesystem_enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    external_enforcement_status: str = EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediatedWriteEvidenceRecord:
    """Stable binding record for a denied mediated write result."""

    binding_id: str
    binding_digest: str
    binding_version: str
    binding_status: str
    evidence_binding_status: str
    denied_write_decision_evidence_status: str
    binding_digest_status: str
    request_id: str
    decision_id: str
    write_class: str
    canonical_target: str
    denial_reason: str
    policy_source: str
    request: Mapping[str, Any]
    mediated_write_decision: Mapping[str, Any]
    mediator_decision: Mapping[str, Any]
    path_resolution: Mapping[str, Any]
    no_mutation_observation: Mapping[str, Any]
    no_mutation_observation_status: str
    tamper_proof_status: str
    external_anchor_status: str
    verify_mismatch_rejection_status: str
    filesystem_enforcement_status: str
    external_enforcement_status: str
    raw_direct_write_status: str
    live_executor_authority_granted: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "binding_digest": self.binding_digest,
            **_evidence_binding_payload(self),
        }


def build_denied_write_no_mutation_observation(
    *,
    canonical_target: str,
    target_exists_before: bool,
    target_exists_after: bool,
    content_digest_before: str,
    content_digest_after: str,
    observation_source: str,
    write_performed: bool = False,
) -> DeniedWriteNoMutationObservation:
    """Build the no-mutation observation that will be bound into evidence."""

    mutation_observed = (
        target_exists_before != target_exists_after
        or content_digest_before != content_digest_after
        or write_performed
    )
    return DeniedWriteNoMutationObservation(
        canonical_target=canonical_target,
        target_exists_before=target_exists_before,
        target_exists_after=target_exists_after,
        content_digest_before=content_digest_before,
        content_digest_after=content_digest_after,
        observation_source=observation_source,
        write_performed=write_performed,
        mutation_observed=mutation_observed,
        no_mutation_observed=not mutation_observed,
    )


def build_mediated_write_evidence_record(
    *,
    denied_result: Any,
    no_mutation_observation: DeniedWriteNoMutationObservation,
) -> MediatedWriteEvidenceRecord:
    """Bind a mediated denial result and supplied no-mutation observation.

    This helper intentionally does not reject mismatches between the denied
    result and observation. E6 owns mismatch rejection.
    """

    request = denied_result.request
    mediator_decision = denied_result.mediator_decision
    path_resolution = denied_result.path_resolution
    payload: dict[str, Any] = {
        "binding_version": MEDIATED_WRITE_EVIDENCE_BINDING_V0,
        "binding_status": MEDIATED_WRITE_EVIDENCE_BOUND,
        "evidence_binding_status": EVIDENCE_BINDING_PRESENT,
        "denied_write_decision_evidence_status": DENIED_WRITE_DECISION_EVIDENCE_BOUND,
        "binding_digest_status": BINDING_DIGEST_PRESENT,
        "request_id": request.request_id,
        "decision_id": denied_result.decision_id,
        "write_class": request.write_class,
        "canonical_target": path_resolution.canonical_target,
        "denial_reason": denied_result.decision_reason,
        "policy_source": request.declared_scope or "",
        "request": request.to_record(),
        "mediated_write_decision": _mediated_write_decision_record(denied_result),
        "mediator_decision": mediator_decision.to_record(),
        "path_resolution": path_resolution.to_record(),
        "no_mutation_observation": no_mutation_observation.to_record(),
        "no_mutation_observation_status": NO_MUTATION_OBSERVATION_BOUND,
        "tamper_proof_status": NOT_TAMPER_PROOF,
        "external_anchor_status": NOT_EXTERNAL_ANCHORED,
        "verify_mismatch_rejection_status": VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
        "filesystem_enforcement_status": NOT_FILESYSTEM_ENFORCED,
        "external_enforcement_status": EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
        "raw_direct_write_status": RAW_DIRECT_WRITE_STILL_BYPASSABLE,
        "live_executor_authority_granted": False,
    }
    binding_digest = _sha256_json(payload)
    return MediatedWriteEvidenceRecord(
        binding_id=f"mediated-write-evidence:{binding_digest}",
        binding_digest=binding_digest,
        **payload,
    )


def mediated_write_evidence_binding_digest(record: MediatedWriteEvidenceRecord) -> str:
    """Recompute the stable digest for a mediated write evidence record."""

    return _sha256_json(_evidence_binding_payload(record))


def _mediated_write_decision_record(denied_result: Any) -> dict[str, Any]:
    record = {
        "decision_id": denied_result.decision_id,
        "request_id": denied_result.request.request_id,
        "decision_status": denied_result.decision_status,
        "decision_reason": denied_result.decision_reason,
        "mediator_status": denied_result.mediator_status,
        "path_policy_status": getattr(denied_result, "path_policy_status", ""),
        "repo_boundary_policy_status": getattr(denied_result, "repo_boundary_policy_status", ""),
        "enforcement_status": denied_result.enforcement_status,
        "external_enforcement_status": denied_result.external_enforcement_status,
        "raw_direct_write_status": denied_result.raw_direct_write_status,
        "write_performed": denied_result.write_performed,
        "filesystem_interception_present": denied_result.filesystem_interception_present,
        "permission_hardening_present": denied_result.permission_hardening_present,
        "live_executor_authority_granted": denied_result.live_executor_authority_granted,
    }
    if hasattr(denied_result, "target_under_aeg"):
        record["target_under_aeg"] = denied_result.target_under_aeg
    if hasattr(denied_result, "target_outside_repo"):
        record["target_outside_repo"] = denied_result.target_outside_repo
    return record


def _evidence_binding_payload(record: MediatedWriteEvidenceRecord) -> dict[str, Any]:
    return {
        "binding_version": record.binding_version,
        "binding_status": record.binding_status,
        "evidence_binding_status": record.evidence_binding_status,
        "denied_write_decision_evidence_status": record.denied_write_decision_evidence_status,
        "binding_digest_status": record.binding_digest_status,
        "request_id": record.request_id,
        "decision_id": record.decision_id,
        "write_class": record.write_class,
        "canonical_target": record.canonical_target,
        "denial_reason": record.denial_reason,
        "policy_source": record.policy_source,
        "request": dict(record.request),
        "mediated_write_decision": dict(record.mediated_write_decision),
        "mediator_decision": dict(record.mediator_decision),
        "path_resolution": dict(record.path_resolution),
        "no_mutation_observation": dict(record.no_mutation_observation),
        "no_mutation_observation_status": record.no_mutation_observation_status,
        "tamper_proof_status": record.tamper_proof_status,
        "external_anchor_status": record.external_anchor_status,
        "verify_mismatch_rejection_status": record.verify_mismatch_rejection_status,
        "filesystem_enforcement_status": record.filesystem_enforcement_status,
        "external_enforcement_status": record.external_enforcement_status,
        "raw_direct_write_status": record.raw_direct_write_status,
        "live_executor_authority_granted": record.live_executor_authority_granted,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "DeniedWriteNoMutationObservation",
    "MediatedWriteEvidenceRecord",
    "build_denied_write_no_mutation_observation",
    "build_mediated_write_evidence_record",
    "mediated_write_evidence_binding_digest",
]
