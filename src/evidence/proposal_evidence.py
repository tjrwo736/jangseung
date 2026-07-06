"""Phase 11-B-3-3 proposal evidence binding and verification.

Proposal evidence binds a verified runtime-built PROPOSE_PATCH packet to inert
proposal metadata. It never applies a patch, writes to the store, grants write
authority, or treats proposal acceptance as proposal application.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION,
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    STRUCTURAL_CONTRACT_ENFORCEMENT_VERSION,
    bind_action_decision_packet_evidence,
    evaluate_store_adjacent_candidate_gate,
    verify_action_decision_packet_evidence,
)
from src.evidence.executor_output_ingress import (
    ActionDecisionPacket,
    RUNTIME_INGRESS_ADAPTER,
    is_runtime_built_action_decision_packet,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
)
from src.evidence.structured_actions import PROPOSE_PATCH, VALID_STRUCTURED_ACTION

PROPOSAL_EVIDENCE_BINDING_VERSION = (
    "phase11b_3_3_proposal_evidence_binding_v0"
)
PROPOSAL_EVIDENCE_VERIFY_ACCEPTED = "PROPOSAL_EVIDENCE_VERIFY_ACCEPTED"
PROPOSAL_EVIDENCE_VERIFY_REJECTED = "PROPOSAL_EVIDENCE_VERIFY_REJECTED"
PROPOSAL_OVERCLAIM_REJECTION_FIXTURES_VERSION = (
    "phase11b_3_3_proposal_overclaim_rejection_fixtures_v0"
)
RESTRICTED_STUB_PROPOSAL_EVIDENCE_BATCH_VERSION = (
    "phase11b_3_2_3_restricted_stub_executor_proposal_evidence_batch_v0"
)

_ALLOWED_PROPOSAL_GATE_RESULTS = frozenset(
    {
        CAPABILITY_GATE_ALLOWED,
        CAPABILITY_GATE_LIMITED_ALLOWED,
    }
)

_PROPOSAL_EVIDENCE_FIELDS = (
    "proposal_evidence_binding_version",
    "structural_contract_enforcement_version",
    "action_decision_packet_evidence_binding_version",
    "packet_id",
    "packet_created_by",
    "packet_runtime_owned",
    "packet_runtime_built_by_ingress",
    "packet_evidence_hash",
    "packet_evidence_verify_status",
    "metadata_candidate_gate_status",
    "metadata_only_candidate_accepted",
    "metadata_only_candidate_is_store_write",
    "proposal_id",
    "proposal_summary",
    "action_id",
    "action_type",
    "normalized_action_hash",
    "target_files",
    "patch_summary",
    "patch_plan",
    "patch_diff",
    "patch_diff_is_inert_data",
    "risk_classification",
    "capability_gate_result",
    "capability_gate_reason",
    "required_capabilities",
    "proposal_accepted",
    "proposal_applied",
    "patch_applied",
    "patch_proposal_claims_applied",
    "executor_claims_done",
    "executor_claims_safe",
    "executor_claims_verified",
    "executor_claims_write_authority",
    "executor_claims_mutation_authority",
    "propose_patch_is_write",
    "propose_patch_is_mutation",
    "propose_patch_is_store_write",
    "propose_patch_is_apply_patch",
    "proposal_evidence_is_patch_application",
    "valid_structured_action_is_authorized_capability",
    "authorized_capability_is_action_executed",
    "proposal_accepted_is_proposal_applied",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "store_routing_allowed",
    "store_path_reachable",
    "live_executor_ready",
    "live_executor_authority",
    "safe_default",
    "proposal_evidence_hash",
)

_FALSE_REQUIRED_FIELDS = (
    "metadata_only_candidate_is_store_write",
    "proposal_applied",
    "patch_applied",
    "patch_proposal_claims_applied",
    "executor_claims_done",
    "executor_claims_safe",
    "executor_claims_verified",
    "executor_claims_write_authority",
    "executor_claims_mutation_authority",
    "propose_patch_is_write",
    "propose_patch_is_mutation",
    "propose_patch_is_store_write",
    "propose_patch_is_apply_patch",
    "proposal_evidence_is_patch_application",
    "valid_structured_action_is_authorized_capability",
    "authorized_capability_is_action_executed",
    "proposal_accepted_is_proposal_applied",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "store_routing_allowed",
    "store_path_reachable",
    "live_executor_ready",
)

_BOOLEAN_FIELDS = (
    "packet_runtime_owned",
    "packet_runtime_built_by_ingress",
    "metadata_only_candidate_accepted",
    "metadata_only_candidate_is_store_write",
    "patch_diff_is_inert_data",
    "proposal_accepted",
    *_FALSE_REQUIRED_FIELDS,
)


@dataclass(frozen=True)
class ProposalEvidenceVerifyResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    verification_scope: str = "phase11b_3_3_proposal_evidence"
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(self.rejection_reasons),
        )


def bind_propose_patch_proposal_evidence(
    packet: ActionDecisionPacket,
) -> dict[str, Any]:
    """Build proposal evidence from a runtime-built PROPOSE_PATCH packet."""

    packet_evidence = bind_action_decision_packet_evidence(packet)
    packet_verify = verify_action_decision_packet_evidence(packet_evidence, packet)
    candidate_gate = evaluate_store_adjacent_candidate_gate(packet)
    action = packet.normalized_action if isinstance(packet.normalized_action, Mapping) else {}
    payload = action.get("payload") if isinstance(action.get("payload"), Mapping) else {}
    validation = packet.validation_result
    capability = packet.capability_result
    action_type = action.get("action_type")
    capability_gate_result = capability.gate_result if capability else None
    proposal_accepted = (
        action_type == PROPOSE_PATCH
        and validation is not None
        and validation.valid is True
        and validation.status == VALID_STRUCTURED_ACTION
        and capability_gate_result in _ALLOWED_PROPOSAL_GATE_RESULTS
        and packet_verify.accepted is True
        and candidate_gate.candidate_accepted is True
        and candidate_gate.gate_status == STORE_ADJACENT_CANDIDATE_ACCEPTED
        and not packet.ignored_reported_only_fields
        and packet.execution_allowed is False
        and packet.mutation_allowed is False
        and packet.write_authority_granted is False
        and packet.store_routing_allowed is False
        and packet.store_path_reachable is False
        and packet.live_executor_authority == LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    )

    record: dict[str, Any] = {
        "proposal_evidence_binding_version": PROPOSAL_EVIDENCE_BINDING_VERSION,
        "structural_contract_enforcement_version": (
            STRUCTURAL_CONTRACT_ENFORCEMENT_VERSION
        ),
        "action_decision_packet_evidence_binding_version": (
            ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION
        ),
        "packet_id": packet.packet_id,
        "packet_created_by": packet.created_by,
        "packet_runtime_owned": packet.created_by == RUNTIME_INGRESS_ADAPTER,
        "packet_runtime_built_by_ingress": (
            is_runtime_built_action_decision_packet(packet)
        ),
        "packet_evidence_hash": packet_evidence.get(
            "action_decision_packet_evidence_hash"
        ),
        "packet_evidence_verify_status": packet_verify.status,
        "metadata_candidate_gate_status": candidate_gate.gate_status,
        "metadata_only_candidate_accepted": candidate_gate.candidate_accepted,
        "metadata_only_candidate_is_store_write": False,
        "proposal_id": _proposal_id(packet),
        "proposal_summary": _string_or_empty(action.get("declared_intent")),
        "action_id": _string_or_empty(action.get("action_id")),
        "action_type": action_type,
        "normalized_action_hash": _optional_sha256_json(packet.normalized_action),
        "target_files": _string_tuple(payload.get("target_files")),
        "patch_summary": _string_or_empty(payload.get("patch_summary")),
        "patch_plan": _string_tuple(payload.get("patch_plan")),
        "patch_diff": _string_or_empty(payload.get("patch_diff")),
        "patch_diff_is_inert_data": True,
        "risk_classification": _string_or_empty(action.get("declared_risk")),
        "capability_gate_result": capability_gate_result,
        "capability_gate_reason": capability.gate_reason if capability else None,
        "required_capabilities": (
            tuple(capability.required_capabilities) if capability else tuple()
        ),
        "proposal_accepted": proposal_accepted,
        "proposal_applied": False,
        "patch_applied": False,
        "patch_proposal_claims_applied": False,
        "executor_claims_done": False,
        "executor_claims_safe": False,
        "executor_claims_verified": False,
        "executor_claims_write_authority": False,
        "executor_claims_mutation_authority": False,
        "propose_patch_is_write": False,
        "propose_patch_is_mutation": False,
        "propose_patch_is_store_write": False,
        "propose_patch_is_apply_patch": False,
        "proposal_evidence_is_patch_application": False,
        "valid_structured_action_is_authorized_capability": False,
        "authorized_capability_is_action_executed": False,
        "proposal_accepted_is_proposal_applied": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }
    record["proposal_evidence_hash"] = expected_proposal_evidence_hash(record)
    return record


def expected_proposal_evidence_hash(payload: Mapping[str, Any]) -> str:
    material = {
        field: payload.get(field)
        for field in _PROPOSAL_EVIDENCE_FIELDS
        if field != "proposal_evidence_hash"
    }
    return _sha256_json(material)


def verify_proposal_evidence(
    payload: Mapping[str, Any],
    packet: ActionDecisionPacket | None = None,
) -> ProposalEvidenceVerifyResult:
    """Verify proposal evidence and reject application or authority claims."""

    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        payload = {}
        reasons.append("proposal evidence must be a mapping")

    for field in _PROPOSAL_EVIDENCE_FIELDS:
        if field not in payload:
            reasons.append(f"missing proposal evidence field: {field}")

    _expect(
        reasons,
        payload,
        "proposal_evidence_binding_version",
        PROPOSAL_EVIDENCE_BINDING_VERSION,
    )
    _expect(
        reasons,
        payload,
        "structural_contract_enforcement_version",
        STRUCTURAL_CONTRACT_ENFORCEMENT_VERSION,
    )
    _expect(
        reasons,
        payload,
        "action_decision_packet_evidence_binding_version",
        ACTION_DECISION_PACKET_EVIDENCE_BINDING_VERSION,
    )
    _expect(reasons, payload, "packet_created_by", RUNTIME_INGRESS_ADAPTER)
    _expect(reasons, payload, "packet_runtime_owned", True)
    _expect(reasons, payload, "packet_runtime_built_by_ingress", True)
    _expect(
        reasons,
        payload,
        "packet_evidence_verify_status",
        ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    )
    _expect(
        reasons,
        payload,
        "metadata_candidate_gate_status",
        STORE_ADJACENT_CANDIDATE_ACCEPTED,
    )
    _expect(reasons, payload, "metadata_only_candidate_accepted", True)
    _expect(reasons, payload, "action_type", PROPOSE_PATCH)
    _expect(reasons, payload, "patch_diff_is_inert_data", True)
    _expect(reasons, payload, "proposal_accepted", True)
    _expect(
        reasons,
        payload,
        "live_executor_authority",
        LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    )
    _expect(reasons, payload, "safe_default", SAFE_DEFAULT)

    for field in _BOOLEAN_FIELDS:
        if not isinstance(payload.get(field), bool):
            reasons.append(f"{field} must be boolean")

    for field in _FALSE_REQUIRED_FIELDS:
        if payload.get(field) is True:
            reasons.append(f"{field}=true rejected")

    if payload.get("capability_gate_result") not in _ALLOWED_PROPOSAL_GATE_RESULTS:
        reasons.append("capability gate result must allow metadata-only proposal")

    for field in ("target_files", "patch_plan", "required_capabilities"):
        if not isinstance(payload.get(field), (list, tuple)):
            reasons.append(f"{field} must be a sequence")

    packet_id = payload.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.startswith(
        "action-decision-packet-"
    ):
        reasons.append("packet_id must identify an action decision packet")

    proposal_id = payload.get("proposal_id")
    if not isinstance(proposal_id, str) or not proposal_id.startswith("proposal-"):
        reasons.append("proposal_id must identify an inert proposal")

    evidence_hash = payload.get("proposal_evidence_hash")
    expected_hash = expected_proposal_evidence_hash(payload)
    if not isinstance(evidence_hash, str) or not _is_sha256_hex(evidence_hash):
        reasons.append("proposal_evidence_hash must be sha256 hex")
    elif evidence_hash != expected_hash:
        reasons.append("proposal_evidence_hash mismatch")

    if packet is None:
        reasons.append(
            "runtime-built ActionDecisionPacket required for proposal verification"
        )
    elif not is_runtime_built_action_decision_packet(packet):
        reasons.append("packet was not built by runtime ingress adapter")
    else:
        reasons.extend(_packet_proposal_mismatch_reasons(payload, packet))

    accepted = not reasons
    return ProposalEvidenceVerifyResult(
        accepted=accepted,
        status=(
            PROPOSAL_EVIDENCE_VERIFY_ACCEPTED
            if accepted
            else PROPOSAL_EVIDENCE_VERIFY_REJECTED
        ),
        rejection_reasons=_unique(reasons),
    )


def build_proposal_overclaim_rejection_fixture_results(
    packet: ActionDecisionPacket,
) -> tuple[dict[str, Any], ...]:
    """Return deterministic proposal evidence overclaim rejection outcomes."""

    base = bind_propose_patch_proposal_evidence(packet)
    records: list[dict[str, Any]] = []
    for field in _FALSE_REQUIRED_FIELDS:
        tampered = dict(base)
        tampered[field] = True
        tampered["proposal_evidence_hash"] = expected_proposal_evidence_hash(tampered)
        verify = verify_proposal_evidence(tampered, packet)
        records.append(
            {
                "fixture_set_version": PROPOSAL_OVERCLAIM_REJECTION_FIXTURES_VERSION,
                "fixture_name": f"{field}_true",
                "overclaim_field": field,
                "verify_status": verify.status,
                "accepted": verify.accepted,
                "rejection_reasons": verify.rejection_reasons,
                "execution_allowed": False,
                "mutation_allowed": False,
                "write_authority_granted": False,
                "store_routing_allowed": False,
                "store_path_reachable": False,
                "live_executor_ready": False,
                "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
                "safe_default": SAFE_DEFAULT,
            }
        )
    return tuple(records)


def build_restricted_stub_proposal_evidence_batch(
    packet: ActionDecisionPacket,
) -> dict[str, Any]:
    """Return batch evidence for 11-B-3-2/3 terminal proposal routing."""

    proposal_evidence = bind_propose_patch_proposal_evidence(packet)
    proposal_verify = verify_proposal_evidence(proposal_evidence, packet)
    overclaim_rejections = build_proposal_overclaim_rejection_fixture_results(packet)
    return {
        "restricted_stub_proposal_evidence_batch_version": (
            RESTRICTED_STUB_PROPOSAL_EVIDENCE_BATCH_VERSION
        ),
        "phase11b_3_2_restricted_propose_only_stub_executor": "COMPLETE",
        "phase11b_3_3_proposal_evidence_verify_binding": "COMPLETE",
        "flow": (
            "stub_executor_output",
            "raw_output_ingress",
            "parse_normalize",
            "validate_structured_action",
            "evaluate_action_capabilities",
            "runtime_built_action_decision_packet",
            "action_decision_packet_evidence_verify",
            "metadata_only_candidate",
            "proposal_evidence_verify",
            "stop",
        ),
        "proposal_evidence_verify_status": proposal_verify.status,
        "proposal_evidence_verify_accepted": proposal_verify.accepted,
        "proposal_evidence_hash": proposal_evidence["proposal_evidence_hash"],
        "proposal_overclaim_rejection_fixtures": overclaim_rejections,
        "proposal_overclaim_rejection_fixture_count": len(overclaim_rejections),
        "propose_patch_is_write": False,
        "propose_patch_is_mutation": False,
        "propose_patch_is_store_write": False,
        "propose_patch_is_apply_patch": False,
        "proposal_evidence_is_patch_application": False,
        "metadata_only_candidate_is_store_write": False,
        "valid_structured_action_is_authorized_capability": False,
        "authorized_capability_is_action_executed": False,
        "proposal_accepted_is_proposal_applied": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def _packet_proposal_mismatch_reasons(
    payload: Mapping[str, Any],
    packet: ActionDecisionPacket,
) -> list[str]:
    expected = bind_propose_patch_proposal_evidence(packet)
    reasons: list[str] = []
    for field in _PROPOSAL_EVIDENCE_FIELDS:
        if field == "proposal_evidence_hash":
            continue
        actual = payload.get(field)
        expected_value = expected.get(field)
        if isinstance(expected_value, tuple) and isinstance(actual, list):
            actual = tuple(actual)
        if actual != expected_value:
            reasons.append(f"{field} mismatch with runtime proposal evidence")
    return reasons


def _proposal_id(packet: ActionDecisionPacket) -> str:
    return f"proposal-{packet.raw_output_hash.removeprefix('sha256:')[:16]}"


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


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for item in value if isinstance(item, str))
    return tuple()


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


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
    "PROPOSAL_EVIDENCE_BINDING_VERSION",
    "PROPOSAL_EVIDENCE_VERIFY_ACCEPTED",
    "PROPOSAL_EVIDENCE_VERIFY_REJECTED",
    "PROPOSAL_OVERCLAIM_REJECTION_FIXTURES_VERSION",
    "ProposalEvidenceVerifyResult",
    "bind_propose_patch_proposal_evidence",
    "build_proposal_overclaim_rejection_fixture_results",
    "build_restricted_stub_proposal_evidence_batch",
    "expected_proposal_evidence_hash",
    "verify_proposal_evidence",
]
