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
    MEDIATED_WRITE_BOUNDARY_FIELDS,
    MEDIATED_WRITE_BOUNDARY_SCAFFOLD_V0,
    MEDIATED_WRITE_BOUNDARY_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    MEDIATED_WRITE_DECISION_SOURCE_AEGIS_RUNTIME_METADATA,
    MEDIATED_WRITE_DIRECT_ALLOW_FIELDS,
    NOT_CHECKED,
    REPORTED_ONLY,
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


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
