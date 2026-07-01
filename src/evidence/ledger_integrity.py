"""Tamper-evident ledger scaffold metadata.

This module adds deterministic detection metadata only. It does not make
``.aeg/`` tamper-proof, executor-isolated, permission-hardened, or externally
anchored.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    EVIDENCE_BINDING_V1_FIELDS,
    LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
    LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED,
    LEDGER_INTEGRITY_FIELDS,
    LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD,
    LEDGER_INTEGRITY_SCAFFOLD_V0,
    LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
)

LEDGER_INTEGRITY_MANIFEST_HASH_FIELD = "ledger_integrity_manifest_hash"
_EVIDENCE_HASH_EXCLUDED_FIELDS = frozenset(
    (
        *LEDGER_INTEGRITY_FIELDS,
        *EVIDENCE_BINDING_V1_FIELDS,
        "reported_only",
    )
)
_MANIFEST_HASH_EXCLUDED_FIELDS = frozenset(
    (
        *LEDGER_INTEGRITY_FIELDS,
        LEDGER_INTEGRITY_MANIFEST_HASH_FIELD,
    )
)
_LEDGER_ENTRY_HASH_EXCLUDED_FIELDS = frozenset(
    (
        "manifest_hash",
        "current_ledger_entry_hash",
        "ledger_chain_hash",
        "ledger_integrity_metadata_hash",
    )
)
_EVIDENCE_HASH_EXCLUDED_CHECK_FIELDS = frozenset(
    (
        "evidence_binding_v1_required",
        "mutation_boundary_v1_required",
        "action_boundary_manifest_binding_required",
        "capability_isolation_manifest_binding_required",
        "tool_surface_manifest_binding_required",
        "executor_capability_exposure_manifest_binding_required",
        "evidence_store_trust_manifest_binding_required",
        "ledger_integrity_manifest_binding_required",
    )
)


def build_ledger_integrity_metadata(
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    ledger_entry: dict[str, Any],
    ledger_sequence_number: int,
    previous_ledger_hash: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "ledger_integrity_version": LEDGER_INTEGRITY_SCAFFOLD_V0,
        "ledger_integrity_mode": LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD,
        "ledger_integrity_status": LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
        "ledger_tamper_evident_enabled": True,
        "ledger_tamper_proof_claimed": False,
        "ledger_sequence_number": ledger_sequence_number,
        "previous_ledger_hash": previous_ledger_hash,
        "current_evidence_hash": expected_current_evidence_hash(evidence),
        "current_manifest_hash": expected_current_manifest_hash(manifest),
        "ledger_integrity_check_status": LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED,
        "ledger_integrity_check_reason": LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
    }
    entry_payload = {**ledger_entry, **metadata}
    metadata["current_ledger_entry_hash"] = expected_ledger_entry_hash(entry_payload)
    metadata["ledger_chain_hash"] = expected_ledger_chain_hash(metadata)
    metadata["ledger_integrity_metadata_hash"] = expected_ledger_integrity_metadata_hash(metadata)
    return metadata


def ledger_integrity_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in LEDGER_INTEGRITY_FIELDS}


def expected_current_evidence_hash(evidence: dict[str, Any]) -> str:
    return _sha256_json(
        {
            key: _normalize_evidence_hash_value(key, value)
            for key, value in evidence.items()
            if key not in _EVIDENCE_HASH_EXCLUDED_FIELDS
        }
    )


def expected_current_manifest_hash(manifest: dict[str, Any]) -> str:
    return _sha256_json(
        {
            key: value
            for key, value in manifest.items()
            if key not in _MANIFEST_HASH_EXCLUDED_FIELDS
        }
    )


def expected_ledger_entry_hash(entry: dict[str, Any]) -> str:
    return _sha256_json(
        {
            key: value
            for key, value in entry.items()
            if key not in _LEDGER_ENTRY_HASH_EXCLUDED_FIELDS
        }
    )


def expected_ledger_chain_hash(payload: dict[str, Any]) -> str:
    chain_payload = {
        "ledger_integrity_version": payload.get("ledger_integrity_version"),
        "ledger_integrity_mode": payload.get("ledger_integrity_mode"),
        "ledger_sequence_number": payload.get("ledger_sequence_number"),
        "previous_ledger_hash": payload.get("previous_ledger_hash"),
        "current_evidence_hash": payload.get("current_evidence_hash"),
        "current_manifest_hash": payload.get("current_manifest_hash"),
        "current_ledger_entry_hash": payload.get("current_ledger_entry_hash"),
        "ledger_tamper_evident_enabled": payload.get("ledger_tamper_evident_enabled"),
        "ledger_tamper_proof_claimed": payload.get("ledger_tamper_proof_claimed"),
    }
    return _sha256_json(chain_payload)


def expected_ledger_integrity_metadata_hash(payload: dict[str, Any]) -> str:
    metadata_payload = {
        field: payload.get(field)
        for field in LEDGER_INTEGRITY_FIELDS
        if field != "ledger_integrity_metadata_hash"
    }
    return _sha256_json(metadata_payload)


def is_sha256_hex(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _normalize_evidence_hash_value(key: str, value: Any) -> Any:
    if key == "checks" and isinstance(value, dict):
        return {
            check_key: check_value
            for check_key, check_value in value.items()
            if check_key not in _EVIDENCE_HASH_EXCLUDED_CHECK_FIELDS
        }
    return value


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
