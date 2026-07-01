"""Evidence-store trust boundary scaffold metadata.

The current ``.aeg/`` store is folder-local runtime state. This metadata binds
that boundary explicitly; it does not harden permissions, isolate executors, or
make the store tamper-proof.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    EVIDENCE_STORE_INTEGRITY_NOT_CHECKED,
    EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
    EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE,
    EVIDENCE_STORE_WRITER_AEGIS_RUNTIME,
    EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
)


def build_evidence_store_trust_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "evidence_store_trust_boundary": EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
        "evidence_store_writer": EVIDENCE_STORE_WRITER_AEGIS_RUNTIME,
        "executor_can_write_evidence_store": EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
        "evidence_store_is_executor_isolated": False,
        "evidence_store_write_source": EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE,
        "evidence_store_integrity_status": EVIDENCE_STORE_INTEGRITY_NOT_CHECKED,
    }
    metadata["evidence_store_trust_metadata_hash"] = expected_evidence_store_trust_metadata_hash(metadata)
    return metadata


def expected_evidence_store_trust_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        "evidence_store_trust_boundary": packet.get("evidence_store_trust_boundary"),
        "evidence_store_writer": packet.get("evidence_store_writer"),
        "executor_can_write_evidence_store": packet.get("executor_can_write_evidence_store"),
        "evidence_store_is_executor_isolated": packet.get("evidence_store_is_executor_isolated"),
        "evidence_store_write_source": packet.get("evidence_store_write_source"),
        "evidence_store_integrity_status": packet.get("evidence_store_integrity_status"),
        "proof_available": False,
        "proof_kind": "folder_local_not_executor_isolated",
    }
    return _sha256_json(payload)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
