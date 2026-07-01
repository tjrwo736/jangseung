"""Phase 9 tool surface authority grant scaffold metadata.

This module records only default-deny scaffold fields. It does not implement
tool wrappers, shell execution, network access, provider calls, file mutation,
telemetry, or any runtime authority grant.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    REPORTED_ONLY,
    TOOL_AUTHORITY_GRANT_FIELDS,
    TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0,
    TOOL_SURFACE_SCAFFOLD_ONLY,
    TOOL_SURFACE_SOURCE_NONE,
    TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
)


def build_tool_surface_metadata(executor_result: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "tool_surface_version": TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0,
        "tool_surface_enabled": False,
        "tool_surface_status": TOOL_SURFACE_SCAFFOLD_ONLY,
        "tool_surface_source": TOOL_SURFACE_SOURCE_NONE,
        "tool_surface_trust_boundary": TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        "requested_tool_capabilities": [],
        "granted_tool_capabilities": [],
        "denied_tool_capabilities": [],
        "tool_authority_grant_count": 0,
        "expected_tool_authority_grant_count": 0,
        "executor_reported_tool_usage": _executor_reported_tool_usage(executor_result),
    }
    for field in TOOL_AUTHORITY_GRANT_FIELDS:
        metadata[field] = False
    metadata["tool_authority_grant_hash"] = expected_tool_authority_grant_hash(metadata)
    metadata["tool_surface_metadata_hash"] = expected_tool_surface_metadata_hash(metadata)
    return metadata


def expected_tool_authority_grant_hash(packet: dict[str, Any]) -> str:
    payload = {
        "requested_tool_capabilities": packet.get("requested_tool_capabilities"),
        "granted_tool_capabilities": packet.get("granted_tool_capabilities"),
        "denied_tool_capabilities": packet.get("denied_tool_capabilities"),
        "tool_authority_grant_count": packet.get("tool_authority_grant_count"),
        "expected_tool_authority_grant_count": packet.get("expected_tool_authority_grant_count"),
        **{field: packet.get(field) for field in TOOL_AUTHORITY_GRANT_FIELDS},
    }
    return _sha256_json(payload)


def expected_tool_surface_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        "tool_surface_version": packet.get("tool_surface_version"),
        "tool_surface_enabled": packet.get("tool_surface_enabled"),
        "tool_surface_status": packet.get("tool_surface_status"),
        "tool_surface_source": packet.get("tool_surface_source"),
        "tool_surface_trust_boundary": packet.get("tool_surface_trust_boundary"),
        "tool_authority_grant_hash": packet.get("tool_authority_grant_hash"),
        "executor_reported_tool_usage": packet.get("executor_reported_tool_usage"),
        "proof_available": False,
        "proof_kind": "scaffold_unavailable",
    }
    return _sha256_json(payload)


def _executor_reported_tool_usage(executor_result: dict[str, Any]) -> dict[str, Any]:
    tools = executor_result.get("tool_usage")
    if not isinstance(tools, list):
        tools = executor_result.get("tools")
    if not isinstance(tools, list):
        tools = []
    return {
        "tools": list(tools),
        "reported_tool_count": len(tools),
        "trust_boundary": REPORTED_ONLY,
        "judgment_basis": False,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
