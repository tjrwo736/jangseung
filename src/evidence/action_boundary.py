"""Phase 9 action boundary scaffold metadata.

This module records only no-op scaffold fields. It does not intercept actions,
wrap shells, grant capabilities, call providers, use the network, or execute
runtime behavior.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    ACTION_BOUNDARY_NOT_CHECKED,
    ACTION_BOUNDARY_SCAFFOLD_V0,
    ACTION_LOG_SOURCE_NONE,
    ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    NOT_CHECKED,
    REPORTED_ONLY,
)


def build_action_boundary_metadata(executor_result: dict[str, Any]) -> dict[str, Any]:
    intercepted_actions: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "action_boundary_version": ACTION_BOUNDARY_SCAFFOLD_V0,
        "action_interception_enabled": False,
        "action_boundary_status": ACTION_BOUNDARY_NOT_CHECKED,
        "action_log_source": ACTION_LOG_SOURCE_NONE,
        "action_log_source_trust_boundary": ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
        "intercepted_actions": intercepted_actions,
        "action_count": 0,
        "expected_action_count": 0,
        "action_risk": NOT_CHECKED,
        "executor_reported_actions": _executor_reported_actions(executor_result),
        "command_enumeration_only": False,
        "no_matched_dangerous_command": False,
        "capability_isolation_enabled": False,
        "raw_shell_authority_granted": False,
        "network_authority_granted": False,
        "provider_authority_granted": False,
        "remote_write_authority_granted": False,
    }
    metadata["computed_action_log_hash"] = expected_action_log_hash(metadata)
    return metadata


def expected_action_log_hash(packet: dict[str, Any]) -> str:
    payload = {
        "action_log_source": packet.get("action_log_source"),
        "action_log_source_trust_boundary": packet.get("action_log_source_trust_boundary"),
        "intercepted_actions": packet.get("intercepted_actions"),
        "action_count": packet.get("action_count"),
        "expected_action_count": packet.get("expected_action_count"),
    }
    return _sha256_json(payload)


def _executor_reported_actions(executor_result: dict[str, Any]) -> dict[str, Any]:
    actions = executor_result.get("actions")
    if not isinstance(actions, list):
        actions = []
    return {
        "actions": list(actions),
        "reported_action_count": len(actions),
        "trust_boundary": REPORTED_ONLY,
        "judgment_basis": False,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
