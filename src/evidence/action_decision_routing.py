"""Phase 11-B-2 validator-enforced routing evidence and guard.

This module is pre-live metadata only. It binds runtime-owned
``ActionDecisionPacket`` fields, verifies the binding, and evaluates whether a
packet may be treated as store-adjacent candidate metadata. It does not call a
store sink, execute an action, mutate files, grant write authority, or promote
live executor authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.executor_output_ingress import (
    ActionDecisionPacket,
    PARSE_OK,
    RUNTIME_INGRESS_ADAPTER,
    ingest_executor_output,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
)
from src.evidence.structured_actions import (
    NOOP,
    VALID_STRUCTURED_ACTION,
)

ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION = (
    "phase11b_2_2_action_decision_packet_evidence_binding_v0"
)
STORE_ADJACENT_CANDIDATE_GATE_VERSION = (
    "phase11b_2_3_store_adjacent_candidate_gate_v0"
)
STORE_PATH_REJECTION_FIXTURES_VERSION = (
    "phase11b_2_4_store_path_rejection_fixtures_v0"
)
VALIDATOR_ENFORCED_ROUTING_BATCH_VERSION = (
    "phase11b_2_validator_enforced_routing_batch_v0"
)

ACTION_DECISION_PACKET_VERIFY_ACCEPTED = (
    "ACTION_DECISION_PACKET_EVIDENCE_VERIFY_ACCEPTED"
)
ACTION_DECISION_PACKET_VERIFY_REJECTED = (
    "ACTION_DECISION_PACKET_EVIDENCE_VERIFY_REJECTED"
)
ACTION_DECISION_PACKET_VERIFY_NOT_RUN = (
    "ACTION_DECISION_PACKET_EVIDENCE_VERIFY_NOT_RUN"
)

STORE_ADJACENT_CANDIDATE_ACCEPTED = "STORE_ADJACENT_CANDIDATE_ACCEPTED"
RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED = "RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED"
UNVALIDATED_ACTION_STORE_PATH_REJECTED = "UNVALIDATED_ACTION_STORE_PATH_REJECTED"
DENIED_CAPABILITY_STORE_PATH_REJECTED = "DENIED_CAPABILITY_STORE_PATH_REJECTED"
REPORTED_ONLY_STORE_PATH_REJECTED = "REPORTED_ONLY_STORE_PATH_REJECTED"
PACKET_EVIDENCE_STORE_PATH_REJECTED = "PACKET_EVIDENCE_STORE_PATH_REJECTED"

_ALLOWED_CANDIDATE_GATE_RESULTS = frozenset(
    {
        CAPABILITY_GATE_ALLOWED,
        CAPABILITY_GATE_LIMITED_ALLOWED,
    }
)

_ACTION_DECISION_PACKET_EVIDENCE_FIELDS = (
    "action_decision_packet_evidence_binding_version",
    "packet_id",
    "packet_created_by",
    "packet_runtime_owned",
    "raw_output_hash",
    "parse_status",
    "parse_error",
    "normalized_action_hash",
    "validation_status",
    "validation_valid",
    "validation_reasons",
    "capability_gate_result",
    "capability_gate_reason",
    "required_capabilities",
    "capability_decisions",
    "decision_basis",
    "decision_basis_hash",
    "ignored_reported_only_fields",
    "validator_enforced_routing_required",
    "executor_output_ingress_required",
    "structured_action_validation_required",
    "capability_gate_required",
    "raw_output_trusted_as_decision",
    "validated_action_forwarded_to_store",
    "raw_executor_output_reaches_store",
    "unvalidated_action_reaches_store",
    "denied_capability_reaches_store",
    "reported_only_authority_reaches_store",
    "store_path_accepts_only_runtime_owned_decision",
    "store_adjacent_candidate_eligible",
    "store_adjacent_candidate_gate_version",
    "store_adjacent_candidate_gate_metadata_only",
    "store_routing_allowed",
    "store_path_reachable",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "live_executor_ready",
    "live_executor_authority",
    "safe_default",
    "action_decision_packet_evidence_hash",
)


@dataclass(frozen=True)
class ActionDecisionPacketEvidenceVerifyResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    verification_scope: str = "phase11b_2_2_action_decision_packet_evidence"
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(self.rejection_reasons),
        )


@dataclass(frozen=True)
class StoreAdjacentCandidateGateResult:
    candidate_accepted: bool
    gate_status: str
    gate_reason: str
    packet_id: str | None
    packet_evidence_hash: str | None
    evidence_verification_status: str
    rejection_reasons: tuple[str, ...]
    store_adjacent_candidate: bool = False
    store_adjacent_candidate_gate_version: str = STORE_ADJACENT_CANDIDATE_GATE_VERSION
    store_adjacent_candidate_gate_metadata_only: bool = True
    store_routing_allowed: bool = False
    store_path_reachable: bool = False
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    live_executor_ready: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(self.rejection_reasons),
        )


def bind_action_decision_packet_evidence(
    packet: ActionDecisionPacket,
) -> dict[str, Any]:
    """Build digest-bound evidence from a runtime-owned decision packet."""

    validation_result = packet.validation_result
    capability_result = packet.capability_result
    validation_status = validation_result.status if validation_result else None
    validation_valid = validation_result.valid if validation_result else False
    capability_gate_result = capability_result.gate_result if capability_result else None
    store_adjacent_candidate_eligible = (
        packet.parse_status == PARSE_OK
        and validation_status == VALID_STRUCTURED_ACTION
        and validation_valid is True
        and capability_gate_result in _ALLOWED_CANDIDATE_GATE_RESULTS
        and packet.created_by == RUNTIME_INGRESS_ADAPTER
        and not packet.execution_allowed
        and not packet.mutation_allowed
        and not packet.write_authority_granted
        and not packet.store_routing_allowed
        and not packet.store_path_reachable
        and packet.live_executor_authority == LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    )
    record: dict[str, Any] = {
        "action_decision_packet_evidence_binding_version": (
            ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION
        ),
        "packet_id": packet.packet_id,
        "packet_created_by": packet.created_by,
        "packet_runtime_owned": packet.created_by == RUNTIME_INGRESS_ADAPTER,
        "raw_output_hash": packet.raw_output_hash,
        "parse_status": packet.parse_status,
        "parse_error": packet.parse_error,
        "normalized_action_hash": _optional_sha256_json(packet.normalized_action),
        "validation_status": validation_status,
        "validation_valid": validation_valid,
        "validation_reasons": (
            tuple(validation_result.reasons) if validation_result else tuple()
        ),
        "capability_gate_result": capability_gate_result,
        "capability_gate_reason": (
            capability_result.gate_reason if capability_result else None
        ),
        "required_capabilities": (
            tuple(capability_result.required_capabilities)
            if capability_result
            else tuple()
        ),
        "capability_decisions": (
            _capability_decision_records(capability_result.capability_decisions)
            if capability_result
            else tuple()
        ),
        "decision_basis": tuple(packet.decision_basis),
        "decision_basis_hash": _sha256_json(tuple(packet.decision_basis)),
        "ignored_reported_only_fields": tuple(packet.ignored_reported_only_fields),
        "validator_enforced_routing_required": True,
        "executor_output_ingress_required": True,
        "structured_action_validation_required": True,
        "capability_gate_required": True,
        "raw_output_trusted_as_decision": False,
        "validated_action_forwarded_to_store": False,
        "raw_executor_output_reaches_store": False,
        "unvalidated_action_reaches_store": False,
        "denied_capability_reaches_store": False,
        "reported_only_authority_reaches_store": False,
        "store_path_accepts_only_runtime_owned_decision": True,
        "store_adjacent_candidate_eligible": store_adjacent_candidate_eligible,
        "store_adjacent_candidate_gate_version": STORE_ADJACENT_CANDIDATE_GATE_VERSION,
        "store_adjacent_candidate_gate_metadata_only": True,
        "store_routing_allowed": packet.store_routing_allowed,
        "store_path_reachable": packet.store_path_reachable,
        "execution_allowed": packet.execution_allowed,
        "mutation_allowed": packet.mutation_allowed,
        "write_authority_granted": packet.write_authority_granted,
        "live_executor_ready": False,
        "live_executor_authority": packet.live_executor_authority,
        "safe_default": packet.safe_default,
    }
    record["action_decision_packet_evidence_hash"] = (
        expected_action_decision_packet_evidence_hash(record)
    )
    return record


def expected_action_decision_packet_evidence_hash(payload: Mapping[str, Any]) -> str:
    material = {
        field: payload.get(field)
        for field in _ACTION_DECISION_PACKET_EVIDENCE_FIELDS
        if field != "action_decision_packet_evidence_hash"
    }
    return _sha256_json(material)


def verify_action_decision_packet_evidence(
    payload: Mapping[str, Any],
    packet: ActionDecisionPacket | None = None,
) -> ActionDecisionPacketEvidenceVerifyResult:
    """Verify packet evidence and reject authority or store-route overclaims."""

    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        payload = {}
        reasons.append("action decision packet evidence must be a mapping")

    for field in _ACTION_DECISION_PACKET_EVIDENCE_FIELDS:
        if field not in payload:
            reasons.append(f"missing action decision packet evidence field: {field}")

    _expect(
        reasons,
        payload,
        "action_decision_packet_evidence_binding_version",
        ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION,
    )
    _expect(reasons, payload, "packet_created_by", RUNTIME_INGRESS_ADAPTER)
    _expect(reasons, payload, "packet_runtime_owned", True)
    _expect(reasons, payload, "validator_enforced_routing_required", True)
    _expect(reasons, payload, "executor_output_ingress_required", True)
    _expect(reasons, payload, "structured_action_validation_required", True)
    _expect(reasons, payload, "capability_gate_required", True)
    _expect(reasons, payload, "raw_output_trusted_as_decision", False)
    _expect(reasons, payload, "validated_action_forwarded_to_store", False)
    _expect(reasons, payload, "raw_executor_output_reaches_store", False)
    _expect(reasons, payload, "unvalidated_action_reaches_store", False)
    _expect(reasons, payload, "denied_capability_reaches_store", False)
    _expect(reasons, payload, "reported_only_authority_reaches_store", False)
    _expect(reasons, payload, "store_path_accepts_only_runtime_owned_decision", True)
    _expect(
        reasons,
        payload,
        "store_adjacent_candidate_gate_version",
        STORE_ADJACENT_CANDIDATE_GATE_VERSION,
    )
    _expect(reasons, payload, "store_adjacent_candidate_gate_metadata_only", True)
    _expect(reasons, payload, "store_routing_allowed", False)
    _expect(reasons, payload, "store_path_reachable", False)
    _expect(reasons, payload, "execution_allowed", False)
    _expect(reasons, payload, "mutation_allowed", False)
    _expect(reasons, payload, "write_authority_granted", False)
    _expect(reasons, payload, "live_executor_ready", False)
    _expect(reasons, payload, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
    _expect(reasons, payload, "safe_default", SAFE_DEFAULT)

    for field in (
        "packet_runtime_owned",
        "validation_valid",
        "validator_enforced_routing_required",
        "executor_output_ingress_required",
        "structured_action_validation_required",
        "capability_gate_required",
        "raw_output_trusted_as_decision",
        "validated_action_forwarded_to_store",
        "raw_executor_output_reaches_store",
        "unvalidated_action_reaches_store",
        "denied_capability_reaches_store",
        "reported_only_authority_reaches_store",
        "store_path_accepts_only_runtime_owned_decision",
        "store_adjacent_candidate_eligible",
        "store_adjacent_candidate_gate_metadata_only",
        "store_routing_allowed",
        "store_path_reachable",
        "execution_allowed",
        "mutation_allowed",
        "write_authority_granted",
        "live_executor_ready",
    ):
        if not isinstance(payload.get(field), bool):
            reasons.append(f"{field} must be boolean")

    for field in (
        "raw_executor_output_reaches_store",
        "unvalidated_action_reaches_store",
        "denied_capability_reaches_store",
        "reported_only_authority_reaches_store",
        "execution_allowed",
        "mutation_allowed",
        "write_authority_granted",
        "live_executor_ready",
    ):
        if payload.get(field) is True:
            reasons.append(f"{field}=true rejected")

    raw_output_hash = payload.get("raw_output_hash")
    if not _is_prefixed_sha256(raw_output_hash):
        reasons.append("raw_output_hash must be sha256-prefixed hex")

    packet_id = payload.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.startswith(
        "action-decision-packet-"
    ):
        reasons.append("packet_id must identify an action decision packet")
    elif isinstance(raw_output_hash, str) and raw_output_hash.startswith("sha256:"):
        expected_packet_id = (
            "action-decision-packet-"
            f"{raw_output_hash.removeprefix('sha256:')[:16]}"
        )
        if packet_id != expected_packet_id:
            reasons.append("packet_id mismatch for raw_output_hash")

    validation_status = payload.get("validation_status")
    validation_valid = payload.get("validation_valid")
    capability_gate_result = payload.get("capability_gate_result")
    expected_candidate_eligible = (
        payload.get("parse_status") == PARSE_OK
        and validation_status == VALID_STRUCTURED_ACTION
        and validation_valid is True
        and capability_gate_result in _ALLOWED_CANDIDATE_GATE_RESULTS
        and payload.get("packet_runtime_owned") is True
        and payload.get("execution_allowed") is False
        and payload.get("mutation_allowed") is False
        and payload.get("write_authority_granted") is False
        and payload.get("store_routing_allowed") is False
        and payload.get("store_path_reachable") is False
        and payload.get("live_executor_ready") is False
        and payload.get("live_executor_authority") == LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    )
    if payload.get("store_adjacent_candidate_eligible") is not expected_candidate_eligible:
        reasons.append("store_adjacent_candidate_eligible mismatch")
    if validation_valid is True and validation_status != VALID_STRUCTURED_ACTION:
        reasons.append("validation_valid=true without VALID_STRUCTURED_ACTION rejected")
    if (
        capability_gate_result in _ALLOWED_CANDIDATE_GATE_RESULTS
        and validation_status != VALID_STRUCTURED_ACTION
    ):
        reasons.append("capability gate allow without valid structured action rejected")

    decision_basis = payload.get("decision_basis")
    decision_basis_hash = payload.get("decision_basis_hash")
    if not isinstance(decision_basis, (list, tuple)):
        reasons.append("decision_basis must be a sequence")
    elif decision_basis_hash != _sha256_json(tuple(decision_basis)):
        reasons.append("decision_basis_hash mismatch")

    evidence_hash = payload.get("action_decision_packet_evidence_hash")
    expected_hash = expected_action_decision_packet_evidence_hash(payload)
    if not isinstance(evidence_hash, str) or not _is_sha256_hex(evidence_hash):
        reasons.append("action_decision_packet_evidence_hash must be sha256 hex")
    elif evidence_hash != expected_hash:
        reasons.append("action_decision_packet_evidence_hash mismatch")

    if packet is not None:
        reasons.extend(_packet_mismatch_reasons(payload, packet))

    accepted = not reasons
    return ActionDecisionPacketEvidenceVerifyResult(
        accepted=accepted,
        status=(
            ACTION_DECISION_PACKET_VERIFY_ACCEPTED
            if accepted
            else ACTION_DECISION_PACKET_VERIFY_REJECTED
        ),
        rejection_reasons=_unique(reasons),
    )


def evaluate_store_adjacent_candidate_gate(
    candidate: Any,
) -> StoreAdjacentCandidateGateResult:
    """Accept only verified runtime-owned packets as candidate metadata."""

    if not isinstance(candidate, ActionDecisionPacket):
        return _gate_rejection(
            gate_status=RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
            gate_reason="store-adjacent guard requires runtime-owned ActionDecisionPacket",
            packet_id=None,
            packet_evidence_hash=None,
            evidence_verification_status=ACTION_DECISION_PACKET_VERIFY_NOT_RUN,
            rejection_reasons=(
                "raw or unsupported executor output cannot reach store-adjacent path",
            ),
        )

    evidence = bind_action_decision_packet_evidence(candidate)
    verify = verify_action_decision_packet_evidence(evidence, candidate)
    packet_evidence_hash = evidence.get("action_decision_packet_evidence_hash")
    if not verify.accepted:
        return _gate_rejection(
            gate_status=PACKET_EVIDENCE_STORE_PATH_REJECTED,
            gate_reason="action decision packet evidence verification rejected",
            packet_id=candidate.packet_id,
            packet_evidence_hash=(
                packet_evidence_hash if isinstance(packet_evidence_hash, str) else None
            ),
            evidence_verification_status=verify.status,
            rejection_reasons=verify.rejection_reasons,
        )

    if candidate.parse_status != PARSE_OK:
        return _packet_gate_rejection(
            candidate,
            evidence,
            verify,
            UNVALIDATED_ACTION_STORE_PATH_REJECTED,
            "parsed structured action is required before store-adjacent candidate metadata",
        )

    validation = candidate.validation_result
    if (
        validation is None
        or not validation.valid
        or validation.status != VALID_STRUCTURED_ACTION
    ):
        return _packet_gate_rejection(
            candidate,
            evidence,
            verify,
            UNVALIDATED_ACTION_STORE_PATH_REJECTED,
            "valid structured action is required before store-adjacent candidate metadata",
        )

    capability = candidate.capability_result
    if capability is None:
        return _packet_gate_rejection(
            candidate,
            evidence,
            verify,
            DENIED_CAPABILITY_STORE_PATH_REJECTED,
            "capability gate result is required before store-adjacent candidate metadata",
        )
    if capability.gate_result == REPORTED_ONLY_CAPABILITY_GRANT_REJECTED:
        return _packet_gate_rejection(
            candidate,
            evidence,
            verify,
            REPORTED_ONLY_STORE_PATH_REJECTED,
            "reported-only authority cannot reach store-adjacent candidate metadata",
        )
    if capability.gate_result not in _ALLOWED_CANDIDATE_GATE_RESULTS:
        return _packet_gate_rejection(
            candidate,
            evidence,
            verify,
            DENIED_CAPABILITY_STORE_PATH_REJECTED,
            "denied capability cannot reach store-adjacent candidate metadata",
        )

    return StoreAdjacentCandidateGateResult(
        candidate_accepted=True,
        gate_status=STORE_ADJACENT_CANDIDATE_ACCEPTED,
        gate_reason=(
            "validated runtime-owned decision packet accepted as metadata-only "
            "store-adjacent candidate"
        ),
        packet_id=candidate.packet_id,
        packet_evidence_hash=evidence["action_decision_packet_evidence_hash"],
        evidence_verification_status=verify.status,
        rejection_reasons=tuple(),
        store_adjacent_candidate=True,
    )


def build_store_path_rejection_fixture_results() -> tuple[dict[str, Any], ...]:
    """Return deterministic 11-B-2-4 rejection fixture outcomes."""

    fixtures: tuple[tuple[str, Any, str], ...] = (
        (
            "raw_executor_output",
            _valid_noop_action("fixture-raw-direct"),
            RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
        ),
        (
            "unsupported_executor_output",
            ("opaque", "executor", "output"),
            RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
        ),
        (
            "unvalidated_action_packet",
            ingest_executor_output(
                {
                    "action_type": NOOP,
                    "action_id": "fixture-unvalidated-missing-fields",
                }
            ),
            UNVALIDATED_ACTION_STORE_PATH_REJECTED,
        ),
        (
            "denied_capability_packet",
            ingest_executor_output(
                _valid_noop_action(
                    "fixture-denied-capability",
                    capability_requirements=("network",),
                )
            ),
            DENIED_CAPABILITY_STORE_PATH_REJECTED,
        ),
        (
            "reported_only_authority_packet",
            ingest_executor_output(
                _valid_noop_action(
                    "fixture-reported-only-authority",
                    payload={
                        "authority": "write_file",
                        "approved_by_executor": True,
                    },
                )
            ),
            REPORTED_ONLY_STORE_PATH_REJECTED,
        ),
    )
    records: list[dict[str, Any]] = []
    for fixture_name, candidate, expected_status in fixtures:
        result = evaluate_store_adjacent_candidate_gate(candidate)
        records.append(
            {
                "fixture_set_version": STORE_PATH_REJECTION_FIXTURES_VERSION,
                "fixture_name": fixture_name,
                "expected_gate_status": expected_status,
                "actual_gate_status": result.gate_status,
                "candidate_accepted": result.candidate_accepted,
                "store_adjacent_candidate": result.store_adjacent_candidate,
                "store_routing_allowed": result.store_routing_allowed,
                "store_path_reachable": result.store_path_reachable,
                "execution_allowed": result.execution_allowed,
                "mutation_allowed": result.mutation_allowed,
                "write_authority_granted": result.write_authority_granted,
                "live_executor_ready": result.live_executor_ready,
                "live_executor_authority": result.live_executor_authority,
                "safe_default": result.safe_default,
            }
        )
    return tuple(records)


def build_validator_enforced_routing_batch_evidence() -> dict[str, Any]:
    """Return static 11-B-2 batch evidence for the pre-live routing contract."""

    rejection_fixtures = build_store_path_rejection_fixture_results()
    return {
        "validator_enforced_routing_batch_version": VALIDATOR_ENFORCED_ROUTING_BATCH_VERSION,
        "phase11b_2_2_action_decision_packet_evidence_binding": "COMPLETE",
        "phase11b_2_3_store_adjacent_routing_guard": "COMPLETE",
        "phase11b_2_4_rejection_fixtures": "COMPLETE",
        "flow": (
            "raw_executor_output",
            "executor_output_ingress_adapter",
            "parse_normalize",
            "validate_structured_action",
            "evaluate_action_capabilities",
            "runtime_owned_action_decision_packet",
            "action_decision_packet_evidence_binding",
            "verify_action_decision_packet_evidence",
            "store_adjacent_candidate_gate_metadata_only",
            "stop",
        ),
        "store_path_rejection_fixtures": rejection_fixtures,
        "store_path_rejection_fixture_count": len(rejection_fixtures),
        "validator_enforced_routing_required": True,
        "executor_output_ingress_required": True,
        "structured_action_validation_required": True,
        "capability_gate_required": True,
        "store_path_accepts_only_runtime_owned_decision": True,
        "store_adjacent_candidate_gate_metadata_only": True,
        "raw_executor_output_reaches_store": False,
        "unvalidated_action_reaches_store": False,
        "denied_capability_reaches_store": False,
        "reported_only_authority_reaches_store": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def _packet_mismatch_reasons(
    payload: Mapping[str, Any],
    packet: ActionDecisionPacket,
) -> list[str]:
    validation = packet.validation_result
    capability = packet.capability_result
    expected_values = {
        "packet_id": packet.packet_id,
        "packet_created_by": packet.created_by,
        "raw_output_hash": packet.raw_output_hash,
        "parse_status": packet.parse_status,
        "parse_error": packet.parse_error,
        "normalized_action_hash": _optional_sha256_json(packet.normalized_action),
        "validation_status": validation.status if validation else None,
        "validation_valid": validation.valid if validation else False,
        "validation_reasons": tuple(validation.reasons) if validation else tuple(),
        "capability_gate_result": capability.gate_result if capability else None,
        "capability_gate_reason": capability.gate_reason if capability else None,
        "required_capabilities": (
            tuple(capability.required_capabilities) if capability else tuple()
        ),
        "capability_decisions": (
            _capability_decision_records(capability.capability_decisions)
            if capability
            else tuple()
        ),
        "decision_basis": tuple(packet.decision_basis),
        "ignored_reported_only_fields": tuple(packet.ignored_reported_only_fields),
        "store_routing_allowed": packet.store_routing_allowed,
        "store_path_reachable": packet.store_path_reachable,
        "execution_allowed": packet.execution_allowed,
        "mutation_allowed": packet.mutation_allowed,
        "write_authority_granted": packet.write_authority_granted,
        "live_executor_authority": packet.live_executor_authority,
        "safe_default": packet.safe_default,
    }
    reasons: list[str] = []
    for field, expected in expected_values.items():
        actual = payload.get(field)
        if isinstance(expected, tuple) and isinstance(actual, list):
            actual = tuple(actual)
        if field == "capability_decisions" and isinstance(actual, list):
            actual = tuple(_jsonable(item) for item in actual)
        if actual != expected:
            reasons.append(f"{field} mismatch with runtime ActionDecisionPacket")
    return reasons


def _packet_gate_rejection(
    packet: ActionDecisionPacket,
    evidence: Mapping[str, Any],
    verify: ActionDecisionPacketEvidenceVerifyResult,
    gate_status: str,
    gate_reason: str,
) -> StoreAdjacentCandidateGateResult:
    evidence_hash = evidence.get("action_decision_packet_evidence_hash")
    return _gate_rejection(
        gate_status=gate_status,
        gate_reason=gate_reason,
        packet_id=packet.packet_id,
        packet_evidence_hash=evidence_hash if isinstance(evidence_hash, str) else None,
        evidence_verification_status=verify.status,
        rejection_reasons=(gate_reason,),
    )


def _gate_rejection(
    *,
    gate_status: str,
    gate_reason: str,
    packet_id: str | None,
    packet_evidence_hash: str | None,
    evidence_verification_status: str,
    rejection_reasons: tuple[str, ...],
) -> StoreAdjacentCandidateGateResult:
    return StoreAdjacentCandidateGateResult(
        candidate_accepted=False,
        gate_status=gate_status,
        gate_reason=gate_reason,
        packet_id=packet_id,
        packet_evidence_hash=packet_evidence_hash,
        evidence_verification_status=evidence_verification_status,
        rejection_reasons=rejection_reasons,
    )


def _capability_decision_records(decisions: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "capability_name": decision.capability_name,
            "status": decision.status,
            "allowed": decision.allowed,
            "reason": decision.reason,
        }
        for decision in decisions
    )


def _valid_noop_action(
    action_id: str,
    *,
    capability_requirements: Sequence[str] = ("noop",),
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "action_type": NOOP,
        "action_id": action_id,
        "declared_intent": "Fixture action data only.",
        "declared_risk": "LOW",
        "capability_requirements": list(capability_requirements),
        "target_scope": {"repo_relative": True, "paths": []},
        "payload": dict(payload or {}),
    }


def _optional_sha256_json(value: Any) -> str | None:
    if value is None:
        return None
    return _sha256_json(value)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _jsonable(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if _is_sequence(value):
        return [_jsonable(nested) for nested in value]
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _expect(
    reasons: list[str],
    record: Mapping[str, Any],
    field: str,
    expected: Any,
) -> None:
    if record.get(field) != expected:
        reasons.append(f"{field} mismatch")


def _is_prefixed_sha256(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and _is_sha256_hex(
        value.removeprefix("sha256:")
    )


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


__all__ = [
    "ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION",
    "ACTION_DECISION_PACKET_VERIFY_ACCEPTED",
    "ACTION_DECISION_PACKET_VERIFY_NOT_RUN",
    "ACTION_DECISION_PACKET_VERIFY_REJECTED",
    "DENIED_CAPABILITY_STORE_PATH_REJECTED",
    "PACKET_EVIDENCE_STORE_PATH_REJECTED",
    "RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED",
    "REPORTED_ONLY_STORE_PATH_REJECTED",
    "STORE_ADJACENT_CANDIDATE_ACCEPTED",
    "STORE_ADJACENT_CANDIDATE_GATE_VERSION",
    "STORE_PATH_REJECTION_FIXTURES_VERSION",
    "UNVALIDATED_ACTION_STORE_PATH_REJECTED",
    "VALIDATOR_ENFORCED_ROUTING_BATCH_VERSION",
    "ActionDecisionPacketEvidenceVerifyResult",
    "StoreAdjacentCandidateGateResult",
    "bind_action_decision_packet_evidence",
    "build_store_path_rejection_fixture_results",
    "build_validator_enforced_routing_batch_evidence",
    "evaluate_store_adjacent_candidate_gate",
    "expected_action_decision_packet_evidence_hash",
    "verify_action_decision_packet_evidence",
]
