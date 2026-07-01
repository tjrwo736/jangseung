"""Aeg state write capability denial scaffold metadata.

This records default-deny metadata for ``capability_write_aeg_state`` only. It
does not enforce shell/tool/file-write mediation, harden ``.aeg/`` permissions,
or make folder-local state executor-isolated.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS,
    AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    AEG_STATE_WRITE_DENIAL_FIELDS,
    AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD,
    AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY,
    AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0,
    AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
    AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY,
)


def build_aeg_state_write_denial_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "aeg_state_write_denial_version": AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0,
        "aeg_state_write_denial_mode": AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD,
        "aeg_state_write_denial_status": AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY,
        "capability_write_aeg_state_requested": False,
        "capability_write_aeg_state_granted": False,
        "capability_write_aeg_state_denied": True,
        "aeg_state_write_denial_enforcement_status": (
            AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED
        ),
        "aeg_state_write_denial_source": AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
        "aeg_state_write_denial_reason": AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY,
    }
    for field in AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS:
        metadata[field] = False
    metadata["aeg_state_write_denial_metadata_hash"] = expected_aeg_state_write_denial_metadata_hash(metadata)
    return metadata


def aeg_state_write_denial_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in AEG_STATE_WRITE_DENIAL_FIELDS}


def expected_aeg_state_write_denial_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        field: packet.get(field)
        for field in AEG_STATE_WRITE_DENIAL_FIELDS
        if field != "aeg_state_write_denial_metadata_hash"
    }
    payload["proof_available"] = False
    payload["proof_kind"] = "metadata_scaffold_only_not_external_enforcement"
    return _sha256_json(payload)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
