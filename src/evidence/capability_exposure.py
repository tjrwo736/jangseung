"""Executor capability exposure scaffold metadata.

This records the capabilities exposed to the current no-op executor. It does
not enforce isolation, grant tools, wrap shells, call providers, read env, or
make structured tool calls safe.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    EXECUTOR_CAPABILITY_BOOL_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0,
    EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP,
    EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT,
    EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME,
    EXECUTOR_CAPABILITY_TRANSPORT_NONE,
    NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
    REPORTED_ONLY,
)


def build_capability_exposure_metadata(executor_result: dict[str, Any]) -> dict[str, Any]:
    actions = executor_result.get("actions")
    if not isinstance(actions, list):
        actions = []

    metadata: dict[str, Any] = {
        "executor_capability_exposure_version": EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0,
        "executor_capability_exposure_scope": EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP,
        "executor_capability_exposure_source": EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT,
        "executor_capability_exposure_trust_boundary": EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME,
        "executor_capability_transport": EXECUTOR_CAPABILITY_TRANSPORT_NONE,
        "current_executor_capability_status": NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
        "executor_capability_file_mutation": executor_result.get("file_mutation") is True,
        "executor_capability_provider_calls": executor_result.get("provider_calls") is True,
        "executor_capability_network_calls": executor_result.get("network_calls") is True,
        "executor_capability_actions": list(actions),
        "executor_capability_action_count": executor_result.get("action_count", len(actions)),
        "executor_capability_expected_action_count": executor_result.get("expected_action_count", 0),
        "executor_reported_capability_exposure": _executor_reported_capability_exposure(executor_result),
    }
    for field in EXECUTOR_CAPABILITY_BOOL_FIELDS:
        metadata[field] = False
    metadata["executor_capability_exposure_hash"] = expected_executor_capability_exposure_hash(metadata)
    metadata["executor_capability_exposure_metadata_hash"] = expected_executor_capability_exposure_metadata_hash(
        metadata
    )
    return metadata


def expected_executor_capability_exposure_hash(packet: dict[str, Any]) -> str:
    payload = {
        **{field: packet.get(field) for field in EXECUTOR_CAPABILITY_BOOL_FIELDS},
        "executor_capability_file_mutation": packet.get("executor_capability_file_mutation"),
        "executor_capability_provider_calls": packet.get("executor_capability_provider_calls"),
        "executor_capability_network_calls": packet.get("executor_capability_network_calls"),
        "executor_capability_actions": packet.get("executor_capability_actions"),
        "executor_capability_action_count": packet.get("executor_capability_action_count"),
        "executor_capability_expected_action_count": packet.get("executor_capability_expected_action_count"),
    }
    return _sha256_json(payload)


def expected_executor_capability_exposure_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        "executor_capability_exposure_version": packet.get("executor_capability_exposure_version"),
        "executor_capability_exposure_scope": packet.get("executor_capability_exposure_scope"),
        "executor_capability_exposure_source": packet.get("executor_capability_exposure_source"),
        "executor_capability_exposure_trust_boundary": packet.get("executor_capability_exposure_trust_boundary"),
        "executor_capability_transport": packet.get("executor_capability_transport"),
        "current_executor_capability_status": packet.get("current_executor_capability_status"),
        "executor_capability_exposure_hash": packet.get("executor_capability_exposure_hash"),
        "executor_reported_capability_exposure": packet.get("executor_reported_capability_exposure"),
        "proof_available": False,
        "proof_kind": "current_noop_executor_scaffold_only",
    }
    return _sha256_json(payload)


def _executor_reported_capability_exposure(executor_result: dict[str, Any]) -> dict[str, Any]:
    capabilities = executor_result.get("capabilities")
    if not isinstance(capabilities, list):
        capabilities = []
    tools = executor_result.get("tool_usage")
    if not isinstance(tools, list):
        tools = executor_result.get("tools")
    if not isinstance(tools, list):
        tools = []
    return {
        "capabilities": list(capabilities),
        "tools": list(tools),
        "reported_capability_count": len(capabilities),
        "reported_tool_count": len(tools),
        "trust_boundary": REPORTED_ONLY,
        "judgment_basis": False,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
