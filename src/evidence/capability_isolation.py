"""Phase 9 capability isolation scaffold metadata.

This module records only default-deny scaffold fields. It does not isolate
processes, wrap shells or tools, grant authority, call providers, use the
network, or enforce allow/deny lists.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    CAPABILITY_AUTHORITY_FIELDS,
    CAPABILITY_BOUNDARY_NOT_CHECKED,
    CAPABILITY_BOUNDARY_SOURCE_NONE,
    CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_SCAFFOLD_V0,
    REPORTED_ONLY,
)


def build_capability_isolation_metadata(executor_result: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "capability_isolation_version": CAPABILITY_ISOLATION_SCAFFOLD_V0,
        "capability_isolation_enabled": False,
        "capability_isolation_mode": CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED,
        "capability_boundary_status": CAPABILITY_BOUNDARY_NOT_CHECKED,
        "capability_boundary_source": CAPABILITY_BOUNDARY_SOURCE_NONE,
        "capability_boundary_trust_boundary": CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        "executor_reported_capabilities": _executor_reported_capabilities(executor_result),
    }
    for field in CAPABILITY_AUTHORITY_FIELDS:
        metadata[field] = False
    metadata["capability_matrix_hash"] = expected_capability_matrix_hash(metadata)
    metadata["capability_isolation_proof_hash"] = expected_capability_isolation_proof_hash(metadata)
    return metadata


def expected_capability_matrix_hash(packet: dict[str, Any]) -> str:
    return _sha256_json({field: packet.get(field) for field in CAPABILITY_AUTHORITY_FIELDS})


def expected_capability_isolation_proof_hash(packet: dict[str, Any]) -> str:
    payload = {
        "capability_isolation_version": packet.get("capability_isolation_version"),
        "capability_isolation_enabled": packet.get("capability_isolation_enabled"),
        "capability_isolation_mode": packet.get("capability_isolation_mode"),
        "capability_boundary_status": packet.get("capability_boundary_status"),
        "capability_boundary_source": packet.get("capability_boundary_source"),
        "capability_boundary_trust_boundary": packet.get("capability_boundary_trust_boundary"),
        "capability_matrix_hash": packet.get("capability_matrix_hash"),
        "proof_available": False,
        "proof_kind": "scaffold_unavailable",
    }
    return _sha256_json(payload)


def _executor_reported_capabilities(executor_result: dict[str, Any]) -> dict[str, Any]:
    capabilities = executor_result.get("capabilities")
    if not isinstance(capabilities, list):
        capabilities = []
    return {
        "capabilities": list(capabilities),
        "reported_capability_count": len(capabilities),
        "trust_boundary": REPORTED_ONLY,
        "judgment_basis": False,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
