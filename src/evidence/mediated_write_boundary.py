"""Mediated write boundary scaffold metadata.

This records vocabulary, default-deny scaffold decisions, and deterministic
hashes only. It does not mediate filesystem writes, wrap tools or shells,
harden ``.aeg/`` permissions, or grant live executor authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    BINDING_DIGEST_PRESENT,
    DENIED_BY_MEDIATOR_SKELETON,
    DENIED_WRITE_DECISION_EVIDENCE_BOUND,
    DENY_ONLY_MEDIATOR_SKELETON_PRESENT,
    ENFORCEMENT_NOT_IMPLEMENTED,
    EVIDENCE_BINDING_PRESENT,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATED_WRITE_BOUNDARY_FIELDS,
    MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
    MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
    MEDIATED_WRITE_DIRECT_ALLOW_FIELDS,
    MEDIATED_WRITE_EVIDENCE_BINDING_V0,
    MEDIATED_WRITE_EVIDENCE_BOUND,
    MEDIATOR_DECISION_DENY,
    NO_MUTATION_OBSERVATION_BOUND,
    NOT_CHECKED,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_TAMPER_PROOF,
    NOT_WIRED_TO_WRITE_PATH,
    PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    REPORTED_ONLY,
    RUNTIME_WIRING_NOT_IMPLEMENTED,
    VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
    WBYP_IDS,
    WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
    WRITE_CLASSES,
    WRITE_CLASS_DEFAULT_MEDIATION_STATUSES,
)


def build_mediated_write_boundary_metadata() -> dict[str, Any]:
    decisions = dict(WRITE_CLASS_DEFAULT_MEDIATION_STATUSES)
    metadata: dict[str, Any] = {
        "mediated_write_boundary_scaffold_version": MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
        "mediated_write_boundary_scaffold_status": (
            MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED
        ),
        "mediated_write_boundary_enforcement_status": (
            MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED
        ),
        "write_mediation_enabled": False,
        "write_mediation_enforced": False,
        "write_classes_declared": list(WRITE_CLASSES),
        "write_classes_granted": [],
        "write_classes_denied": list(WRITE_CLASSES),
        "write_class_mediation_statuses": decisions,
        "write_mediation_decision_source": MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
        "write_mediation_evidence_status": NOT_CHECKED,
        "phase10e_write_mediation_component_status": (
            PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED
        ),
        "runtime_wiring_status": RUNTIME_WIRING_NOT_IMPLEMENTED,
        "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "mediator_contract_hash": expected_mediator_contract_hash(),
        "mediated_write_binding_hash": expected_mediated_write_binding_hash(),
        "bypass_fixture_result_hash": expected_bypass_fixture_result_hash(),
    }
    for field in MEDIATED_WRITE_DIRECT_ALLOW_FIELDS:
        metadata[field] = False
    metadata["write_mediation_decision_hash"] = expected_write_mediation_decision_hash(metadata)
    metadata["mediated_write_boundary_metadata_hash"] = expected_mediated_write_boundary_metadata_hash(metadata)
    return metadata


def mediated_write_boundary_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in MEDIATED_WRITE_BOUNDARY_FIELDS}


def expected_write_mediation_decision_hash(packet: dict[str, Any]) -> str:
    payload = {
        "write_classes_declared": packet.get("write_classes_declared"),
        "write_classes_granted": packet.get("write_classes_granted"),
        "write_classes_denied": packet.get("write_classes_denied"),
        "write_class_mediation_statuses": packet.get("write_class_mediation_statuses"),
        "write_mediation_decision_source": packet.get("write_mediation_decision_source"),
        "proof_available": False,
        "proof_kind": "metadata_scaffold_only_not_external_enforcement",
        "trust_boundary": REPORTED_ONLY,
        "judgment_basis": False,
    }
    return _sha256_json(payload)


def expected_mediated_write_boundary_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        field: packet.get(field)
        for field in MEDIATED_WRITE_BOUNDARY_FIELDS
        if field != "mediated_write_boundary_metadata_hash"
    }
    payload["proof_available"] = False
    payload["proof_kind"] = "mediated_write_boundary_scaffold_only_not_enforced"
    payload["external_enforcement"] = False
    payload["mediator_implementation"] = False
    payload["live_executor_authority_granted"] = False
    return _sha256_json(payload)


def expected_mediator_contract_hash() -> str:
    payload = {
        "component": "deny_only_mediator_skeleton",
        "skeleton_status": DENY_ONLY_MEDIATOR_SKELETON_PRESENT,
        "decision_status": MEDIATOR_DECISION_DENY,
        "decision_reason": DENIED_BY_MEDIATOR_SKELETON,
        "write_path_status": NOT_WIRED_TO_WRITE_PATH,
        "enforcement_status": ENFORCEMENT_NOT_IMPLEMENTED,
        "runtime_wiring_status": RUNTIME_WIRING_NOT_IMPLEMENTED,
        "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "judgment_basis": False,
    }
    return _sha256_json(payload)


def expected_mediated_write_binding_hash() -> str:
    payload = {
        "component": "mediated_write_evidence_binding",
        "binding_version": MEDIATED_WRITE_EVIDENCE_BINDING_V0,
        "binding_status": MEDIATED_WRITE_EVIDENCE_BOUND,
        "evidence_binding_status": EVIDENCE_BINDING_PRESENT,
        "denied_write_decision_evidence_status": DENIED_WRITE_DECISION_EVIDENCE_BOUND,
        "binding_digest_status": BINDING_DIGEST_PRESENT,
        "no_mutation_observation_status": NO_MUTATION_OBSERVATION_BOUND,
        "tamper_proof_status": NOT_TAMPER_PROOF,
        "external_anchor_status": NOT_EXTERNAL_ANCHORED,
        "verify_mismatch_rejection_status": VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
        "filesystem_enforcement_status": NOT_FILESYSTEM_ENFORCED,
        "external_enforcement_status": EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
        "raw_direct_write_status": RAW_DIRECT_WRITE_STILL_BYPASSABLE,
        "runtime_wiring_status": RUNTIME_WIRING_NOT_IMPLEMENTED,
        "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "judgment_basis": False,
    }
    return _sha256_json(payload)


def expected_bypass_fixture_result_hash() -> str:
    payload = {
        "component": "write_bypass_known_gap_fixture_results",
        "registry_ids": list(WBYP_IDS),
        "observed_result": WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
        "expected_red_marker": WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
        "known_gap_marker": WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
        "proof_source": WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
        "fixture_exists": False,
        "bypass_proven": False,
        "coverage_complete": False,
        "enforced_denial": False,
        "runtime_wiring_status": RUNTIME_WIRING_NOT_IMPLEMENTED,
        "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "judgment_basis": False,
    }
    return _sha256_json(payload)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
