"""Pre-live executor integrity gate scaffold metadata.

This binds Candidate E prerequisite scaffolds before any live executor grant. It
does not grant executor authority, enforce denial externally, isolate ``.aeg/``,
or implement shell/tool/file mediation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
    PRE_LIVE_EXECUTOR_GATE_FIELDS,
    PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD,
    PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY,
    PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0,
    PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD,
    SAFE_DEFAULT,
)


def build_pre_live_executor_gate_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "pre_live_executor_gate_version": PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0,
        "pre_live_executor_gate_mode": PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD,
        "pre_live_executor_gate_status": PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD,
        "live_executor_authority_requested": False,
        "live_executor_authority_granted": False,
        "live_executor_authority_hold_reason": LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
        "requires_tamper_evident_ledger": True,
        "tamper_evident_ledger_present": True,
        "requires_aeg_state_write_denial": True,
        "aeg_state_write_denial_present": True,
        "requires_external_enforcement": True,
        "external_enforcement_present": False,
        "evidence_store_executor_isolated_required": True,
        "evidence_store_executor_isolated_present": False,
        "pre_live_executor_gate_result": PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
        "pre_live_executor_gate_reason": PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY,
    }
    metadata["pre_live_executor_gate_metadata_hash"] = expected_pre_live_executor_gate_metadata_hash(metadata)
    return metadata


def pre_live_executor_gate_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in PRE_LIVE_EXECUTOR_GATE_FIELDS}


def expected_pre_live_executor_gate_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        field: packet.get(field)
        for field in PRE_LIVE_EXECUTOR_GATE_FIELDS
        if field != "pre_live_executor_gate_metadata_hash"
    }
    payload["proof_available"] = False
    payload["proof_kind"] = "pre_live_executor_gate_scaffold_only_not_external_enforcement"
    payload["safe_default"] = SAFE_DEFAULT
    return _sha256_json(payload)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
