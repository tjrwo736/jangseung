"""Phase 11-C Claude Code PreToolUse response schema candidate.

This module maps Phase 11-C-7 inert serialization candidates into the current
documented Claude Code PreToolUse ``hookSpecificOutput`` candidate shape. It is
data-only runtime-readiness work: it does not implement a hook command, emit
stdout/stderr output, install hooks, execute actions, grant authority, or write
state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.claude_code_pretooluse_input_contract import (
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
)
from src.evidence.hook_response_envelope_candidate import (
    RESPONSE_ALLOW,
    RESPONSE_ASK,
    RESPONSE_DEFER,
    RESPONSE_DENY,
    RESPONSE_HOLD_CURRENT_STATE,
)
from src.evidence.hook_response_serialization_candidate import (
    PHASE11C_7_COMPLETE_LABEL,
    PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION,
    RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME,
    RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
    HookResponseSerializationCandidate,
    hook_response_serialization_candidate_digest,
    serialized_payload_candidate_digest,
)

PHASE11C_PRETOOLUSE_RESPONSE_SCHEMA_CANDIDATE_VERSION = (
    "phase11c_claude_code_pretooluse_response_schema_candidate_v0"
)
PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL = (
    "PHASE11C_RUNTIME_READINESS_COMPLETION_BUNDLE_COMPLETE_NOT_INSTALLED_NOT_LIVE_RUNTIME"
)

CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE = "PreToolUse"
RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME = (
    "claude_code_pretooluse_candidate_not_runtime"
)
DOCS_CHECKED_DATE = "2026-07-07"
DOCS_SOURCE_TYPE = "Claude Code Hooks reference"
DOCS_SOURCE_STATUS = "current_docs_checked_but_runtime_not_executed"

RESPONSE_SCHEMA_HASH_ALGORITHM = "sha256_canonical_json_v0"
PRETOOLUSE_PERMISSION_DECISIONS = (
    RESPONSE_ALLOW,
    RESPONSE_DENY,
    RESPONSE_ASK,
    RESPONSE_DEFER,
)

_RESPONSE_SCHEMA_ID_PREFIX = "phase11c-pretooluse-response-schema:"
_SERIALIZATION_ID_PREFIX = "phase11c-7-hook-response-serialization:"
_SERIALIZED_PAYLOAD_VERSION = "phase11c_7_serialized_payload_candidate_v0"

_SERIALIZATION_FALSE_FIELDS = (
    "serialization_candidate_is_real_claude_code_hook_response",
    "serialization_candidate_is_stdout_stderr_emission",
    "serialization_candidate_is_hook_runtime",
    "serialization_candidate_is_hook_command",
    "serialization_candidate_is_execution",
    "serialization_candidate_is_action_execution_engine",
    "serialization_candidate_is_write_authority",
    "serialization_candidate_is_store_write",
    "serialization_candidate_mutates_filesystem",
    "allow_serialization_candidate_is_execution",
    "deny_serialization_candidate_is_real_denial_response",
    "ask_serialization_candidate_is_user_prompt_implementation",
    "reported_only_is_judgment_basis",
    "not_checked_is_pass",
    "safe_default_changed",
    "hook_command_implemented",
    "hook_installation_implemented",
    "claude_code_execution_performed",
    "real_hook_response_emitted",
    "stdout_stderr_hook_output_written",
    "codex_implementation_added",
    "provider_model_network_implemented",
    "llm_call_implemented",
    "api_key_env_secret_loading_implemented",
    "network_client_implemented",
    "process_execution_implemented",
    "shell_execution_implemented",
    "action_execution_engine_implemented",
    "tool_runtime_implemented",
    "write_authority_granted",
    "state_store_module_changed",
    "filesystem_mutation_by_serialization",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)

_SERIALIZATION_REQUIRED_FIELDS = (
    "serialization_id",
    "serialization_hash",
    "serialization_version",
    "completion_label",
    "source_envelope_id",
    "source_envelope_hash",
    "source_response_candidate_type",
    "serialized_payload_candidate",
    "serialized_payload_hash",
    "response_transport_candidate",
    "response_schema_status",
    "redacted_user_message",
    "reason_codes",
    "audit_summary",
    "safe_default",
    "live_executor_authority",
    "trust_boundary",
    "serialization_hash_algorithm",
    "serialized_payload_hash_algorithm",
    "serialization_redaction_policy",
    *_SERIALIZATION_FALSE_FIELDS,
)

_RESPONSE_SCHEMA_PAYLOAD_FIELDS = (
    "response_schema_candidate_version",
    "completion_label",
    "source_serialization_id",
    "source_serialization_hash",
    "source_response_candidate_type",
    "response_schema_candidate_type",
    "claude_code_hook_event_name",
    "hook_specific_output_candidate",
    "permission_decision_candidate",
    "permission_decision_reason_redacted",
    "response_transport_candidate",
    "response_schema_status",
    "docs_checked_date",
    "docs_source_status",
    "safe_default",
    "live_executor_authority",
    "trust_boundary",
    "response_schema_hash_algorithm",
    "response_schema_candidate_is_real_claude_code_hook_response",
    "response_schema_candidate_is_stdout_stderr_emission",
    "response_schema_candidate_is_hook_runtime",
    "response_schema_candidate_is_hook_command",
    "response_schema_candidate_is_execution",
    "response_schema_candidate_is_action_execution_engine",
    "response_schema_candidate_is_write_authority",
    "response_schema_candidate_is_store_write",
    "response_schema_candidate_mutates_filesystem",
    "allow_candidate_is_execution",
    "allow_candidate_is_write_authority",
    "allow_candidate_is_installed_hook_output",
    "deny_candidate_is_actual_denial_response",
    "ask_candidate_is_user_prompt_implementation",
    "defer_candidate_is_actual_subprocess_defer_behavior",
    "hold_candidate_preserves_safe_default",
    "reported_only_is_judgment_basis",
    "not_checked_is_pass",
    "safe_default_changed",
    "hook_command_implemented",
    "hook_installation_implemented",
    "claude_code_execution_performed",
    "real_hook_response_emitted",
    "stdout_stderr_hook_output_written",
    "codex_implementation_added",
    "provider_model_network_implemented",
    "llm_call_implemented",
    "api_key_env_secret_loading_implemented",
    "network_client_implemented",
    "process_execution_implemented",
    "shell_execution_implemented",
    "action_execution_engine_implemented",
    "tool_runtime_implemented",
    "write_authority_granted",
    "state_store_module_changed",
    "filesystem_mutation_by_response_schema_candidate",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)


@dataclass(frozen=True)
class ClaudeCodePreToolUseResponseSchemaCandidate:
    response_schema_candidate_id: str
    response_schema_candidate_hash: str
    response_schema_candidate_version: str
    completion_label: str
    source_serialization_id: str | None
    source_serialization_hash: str | None
    source_response_candidate_type: str | None
    response_schema_candidate_type: str
    claude_code_hook_event_name: str
    hook_specific_output_candidate: Mapping[str, Any]
    permission_decision_candidate: str
    permission_decision_reason_redacted: str
    response_transport_candidate: str
    response_schema_status: str
    docs_checked_date: str
    docs_source_status: str
    safe_default: str
    live_executor_authority: str
    trust_boundary: str
    response_schema_hash_algorithm: str = RESPONSE_SCHEMA_HASH_ALGORITHM
    response_schema_candidate_is_real_claude_code_hook_response: bool = False
    response_schema_candidate_is_stdout_stderr_emission: bool = False
    response_schema_candidate_is_hook_runtime: bool = False
    response_schema_candidate_is_hook_command: bool = False
    response_schema_candidate_is_execution: bool = False
    response_schema_candidate_is_action_execution_engine: bool = False
    response_schema_candidate_is_write_authority: bool = False
    response_schema_candidate_is_store_write: bool = False
    response_schema_candidate_mutates_filesystem: bool = False
    allow_candidate_is_execution: bool = False
    allow_candidate_is_write_authority: bool = False
    allow_candidate_is_installed_hook_output: bool = False
    deny_candidate_is_actual_denial_response: bool = False
    ask_candidate_is_user_prompt_implementation: bool = False
    defer_candidate_is_actual_subprocess_defer_behavior: bool = False
    hold_candidate_preserves_safe_default: bool = True
    reported_only_is_judgment_basis: bool = False
    not_checked_is_pass: bool = False
    safe_default_changed: bool = False
    hook_command_implemented: bool = False
    hook_installation_implemented: bool = False
    claude_code_execution_performed: bool = False
    real_hook_response_emitted: bool = False
    stdout_stderr_hook_output_written: bool = False
    codex_implementation_added: bool = False
    provider_model_network_implemented: bool = False
    llm_call_implemented: bool = False
    api_key_env_secret_loading_implemented: bool = False
    network_client_implemented: bool = False
    process_execution_implemented: bool = False
    shell_execution_implemented: bool = False
    action_execution_engine_implemented: bool = False
    tool_runtime_implemented: bool = False
    write_authority_granted: bool = False
    state_store_module_changed: bool = False
    filesystem_mutation_by_response_schema_candidate: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def __post_init__(self) -> None:
        if self.permission_decision_candidate not in PRETOOLUSE_PERMISSION_DECISIONS:
            raise ValueError("permission_decision_candidate must be allow, deny, ask, or defer")
        object.__setattr__(
            self,
            "hook_specific_output_candidate",
            _freeze_value(self.hook_specific_output_candidate),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "response_schema_candidate_id": self.response_schema_candidate_id,
            "response_schema_candidate_hash": self.response_schema_candidate_hash,
            **_plain_json_data(_response_schema_candidate_payload(self)),
        }


def build_claude_code_pretooluse_response_schema_candidate(
    serialization_candidate: HookResponseSerializationCandidate | Mapping[str, Any] | Any,
) -> ClaudeCodePreToolUseResponseSchemaCandidate:
    """Map an inert 11-C-7 serialization candidate to a PreToolUse schema candidate."""

    serialization, source_error = _coerce_serialization_candidate(
        serialization_candidate
    )
    if source_error:
        return _build_hold_response_schema_candidate(
            source_error,
            "malformed_or_mismatched_serialization_maps_to_hold_current_state_schema_candidate",
        )

    consistency_error = _serialization_consistency_error(serialization)
    if consistency_error:
        return _build_hold_response_schema_candidate(
            consistency_error,
            "malformed_or_mismatched_serialization_maps_to_hold_current_state_schema_candidate",
        )

    serialized_payload = _serialized_payload(serialization)
    response_candidate_type = _response_schema_candidate_type(
        serialization,
        serialized_payload,
    )
    permission_decision = _permission_decision_for_candidate_type(
        response_candidate_type
    )

    return _build_response_schema_candidate(
        source_serialization_id=_string_or_none(serialization["serialization_id"]),
        source_serialization_hash=_string_or_none(serialization["serialization_hash"]),
        source_response_candidate_type=_string_or_none(
            serialization["source_response_candidate_type"]
        ),
        response_schema_candidate_type=response_candidate_type,
        permission_decision_candidate=permission_decision,
        permission_decision_reason_redacted=_permission_reason(
            response_candidate_type=response_candidate_type,
            source_valid=True,
        ),
    )


def claude_code_pretooluse_response_schema_candidate_digest(
    record: ClaudeCodePreToolUseResponseSchemaCandidate | Mapping[str, Any],
) -> str:
    """Recompute the deterministic digest for a PreToolUse schema candidate."""

    if isinstance(record, ClaudeCodePreToolUseResponseSchemaCandidate):
        return _sha256_json(_response_schema_candidate_payload(record))
    if isinstance(record, Mapping):
        missing = _missing_fields(record, _RESPONSE_SCHEMA_PAYLOAD_FIELDS)
        if missing:
            raise ValueError(f"missing response schema payload fields: {missing!r}")
        return _sha256_json(
            {field: record[field] for field in _RESPONSE_SCHEMA_PAYLOAD_FIELDS}
        )
    raise TypeError(type(record).__name__)


def build_claude_code_pretooluse_response_schema_candidate_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_PRETOOLUSE_RESPONSE_SCHEMA_CANDIDATE_VERSION,
        "completion_label": PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        "input_contract_version": PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION,
        "input_completion_label": PHASE11C_7_COMPLETE_LABEL,
        "docs_checked_date": DOCS_CHECKED_DATE,
        "docs_source_type": DOCS_SOURCE_TYPE,
        "docs_source_status": DOCS_SOURCE_STATUS,
        "claude_code_hook_event_name": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
        "pretooluse_response_shape_candidate": {
            "hookSpecificOutput": {
                "hookEventName": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
                "permissionDecision": PRETOOLUSE_PERMISSION_DECISIONS,
                "permissionDecisionReason": "redacted reason string",
            }
        },
        "deprecated_top_level_decision_reason_used": False,
        "allow_serialization_policy": RESPONSE_ALLOW,
        "deny_serialization_policy": RESPONSE_DENY,
        "ask_serialization_policy": RESPONSE_ASK,
        "defer_serialization_policy": RESPONSE_DEFER,
        "hold_current_state_serialization_policy": RESPONSE_DENY,
        "hold_current_state_policy_rationale": (
            "PreToolUse permissionDecision has no hold_current_state value; "
            "the inert candidate maps hold_current_state to deny while preserving "
            "safe_default and no live denial response."
        ),
        "unknown_malformed_serialization_policy": RESPONSE_HOLD_CURRENT_STATE,
        "unknown_malformed_serialization_copies_source_ids": False,
        "response_transport_candidate": RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        "response_schema_status": (
            RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME
        ),
        "response_schema_hash_recomputes_deterministically": True,
        "response_schema_candidate_id_matches_hash": True,
        "source_serialization_hash_must_match": True,
        "serialized_payload_hash_must_match": True,
        "raw_full_tool_input_in_response_schema_candidate": False,
        "raw_secret_bearing_path_content_command_text_in_response_schema_candidate": False,
        "permission_decision_reason_redacted": True,
        "response_schema_candidate_is_real_claude_code_hook_response": False,
        "response_schema_candidate_is_stdout_stderr_emission": False,
        "response_schema_candidate_is_hook_runtime": False,
        "response_schema_candidate_is_hook_command": False,
        "response_schema_candidate_is_execution": False,
        "response_schema_candidate_is_action_execution_engine": False,
        "response_schema_candidate_is_write_authority": False,
        "response_schema_candidate_is_store_write": False,
        "response_schema_candidate_mutates_filesystem": False,
        "allow_candidate_is_execution": False,
        "allow_candidate_is_write_authority": False,
        "allow_candidate_is_installed_hook_output": False,
        "deny_candidate_is_actual_denial_response": False,
        "ask_candidate_is_user_prompt_implementation": False,
        "defer_candidate_is_actual_subprocess_defer_behavior": False,
        "hold_candidate_preserves_safe_default": True,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "reported_only_is_judgment_basis": False,
        "not_checked_is_pass": False,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "codex_implementation_added": False,
        "provider_model_network_implemented": False,
        "llm_call_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "network_client_implemented": False,
        "process_execution_implemented": False,
        "shell_execution_implemented": False,
        "action_execution_engine_implemented": False,
        "tool_runtime_implemented": False,
        "write_authority_granted": False,
        "state_store_module_changed": False,
        "filesystem_mutation_by_response_schema_candidate": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _build_hold_response_schema_candidate(
    *reason_codes: str,
) -> ClaudeCodePreToolUseResponseSchemaCandidate:
    return _build_response_schema_candidate(
        source_serialization_id=None,
        source_serialization_hash=None,
        source_response_candidate_type=None,
        response_schema_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
        permission_decision_candidate=RESPONSE_DENY,
        permission_decision_reason_redacted=_permission_reason(
            response_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
            source_valid=False,
            reason_codes=reason_codes,
        ),
    )


def _build_response_schema_candidate(
    *,
    source_serialization_id: str | None,
    source_serialization_hash: str | None,
    source_response_candidate_type: str | None,
    response_schema_candidate_type: str,
    permission_decision_candidate: str,
    permission_decision_reason_redacted: str,
) -> ClaudeCodePreToolUseResponseSchemaCandidate:
    hook_specific_output_candidate = {
        "hookSpecificOutput": {
            "hookEventName": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
            "permissionDecision": permission_decision_candidate,
            "permissionDecisionReason": permission_decision_reason_redacted,
        }
    }
    payload = {
        "response_schema_candidate_version": (
            PHASE11C_PRETOOLUSE_RESPONSE_SCHEMA_CANDIDATE_VERSION
        ),
        "completion_label": PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        "source_serialization_id": source_serialization_id,
        "source_serialization_hash": source_serialization_hash,
        "source_response_candidate_type": source_response_candidate_type,
        "response_schema_candidate_type": response_schema_candidate_type,
        "claude_code_hook_event_name": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
        "hook_specific_output_candidate": hook_specific_output_candidate,
        "permission_decision_candidate": permission_decision_candidate,
        "permission_decision_reason_redacted": permission_decision_reason_redacted,
        "response_transport_candidate": RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        "response_schema_status": (
            RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME
        ),
        "docs_checked_date": DOCS_CHECKED_DATE,
        "docs_source_status": DOCS_SOURCE_STATUS,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "response_schema_hash_algorithm": RESPONSE_SCHEMA_HASH_ALGORITHM,
        "response_schema_candidate_is_real_claude_code_hook_response": False,
        "response_schema_candidate_is_stdout_stderr_emission": False,
        "response_schema_candidate_is_hook_runtime": False,
        "response_schema_candidate_is_hook_command": False,
        "response_schema_candidate_is_execution": False,
        "response_schema_candidate_is_action_execution_engine": False,
        "response_schema_candidate_is_write_authority": False,
        "response_schema_candidate_is_store_write": False,
        "response_schema_candidate_mutates_filesystem": False,
        "allow_candidate_is_execution": False,
        "allow_candidate_is_write_authority": False,
        "allow_candidate_is_installed_hook_output": False,
        "deny_candidate_is_actual_denial_response": False,
        "ask_candidate_is_user_prompt_implementation": False,
        "defer_candidate_is_actual_subprocess_defer_behavior": False,
        "hold_candidate_preserves_safe_default": True,
        "reported_only_is_judgment_basis": False,
        "not_checked_is_pass": False,
        "safe_default_changed": False,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "codex_implementation_added": False,
        "provider_model_network_implemented": False,
        "llm_call_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "network_client_implemented": False,
        "process_execution_implemented": False,
        "shell_execution_implemented": False,
        "action_execution_engine_implemented": False,
        "tool_runtime_implemented": False,
        "write_authority_granted": False,
        "state_store_module_changed": False,
        "filesystem_mutation_by_response_schema_candidate": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }
    response_schema_candidate_hash = _sha256_json(payload)
    return ClaudeCodePreToolUseResponseSchemaCandidate(
        response_schema_candidate_id=(
            f"{_RESPONSE_SCHEMA_ID_PREFIX}{response_schema_candidate_hash}"
        ),
        response_schema_candidate_hash=response_schema_candidate_hash,
        **payload,
    )


def _coerce_serialization_candidate(
    value: HookResponseSerializationCandidate | Mapping[str, Any] | Any,
) -> tuple[dict[str, Any], str | None]:
    try:
        if isinstance(value, HookResponseSerializationCandidate):
            return _plain_json_data(value.to_record()), None
        if isinstance(value, Mapping):
            record = _plain_json_data(value)
            missing = _missing_fields(record, _SERIALIZATION_REQUIRED_FIELDS)
            if missing:
                return {}, "malformed_source_serialization_candidate"
            return record, None
    except TypeError:
        return {}, "malformed_source_serialization_candidate"
    return {}, "malformed_source_serialization_candidate"


def _serialization_consistency_error(record: Mapping[str, Any]) -> str | None:
    if record.get("serialization_version") != PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION:
        return "source_serialization_version_mismatch"
    if record.get("completion_label") != PHASE11C_7_COMPLETE_LABEL:
        return "source_serialization_completion_label_mismatch"
    if record.get("response_transport_candidate") != RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT:
        return "source_serialization_transport_mismatch"
    if record.get("response_schema_status") != RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME:
        return "source_serialization_schema_status_mismatch"
    if record.get("safe_default") != SAFE_DEFAULT:
        return "source_serialization_safe_default_mismatch"
    if record.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        return "source_serialization_live_executor_authority_not_on_hold"
    if record.get("trust_boundary") != UNTRUSTED_RAW_EXECUTOR_OUTPUT:
        return "source_serialization_trust_boundary_mismatch"
    if record.get("defer_or_hold_serialization_candidate_preserves_safe_default") is not True:
        return "source_serialization_hold_safe_default_mismatch"
    for field in _SERIALIZATION_FALSE_FIELDS:
        if record.get(field) is not False:
            return "source_serialization_runtime_emission_authority_or_store_write_flag_mismatch"

    recomputed_hash = hook_response_serialization_candidate_digest(record)
    if record.get("serialization_hash") != recomputed_hash:
        return "source_serialization_hash_mismatch"
    if record.get("serialization_id") != f"{_SERIALIZATION_ID_PREFIX}{recomputed_hash}":
        return "source_serialization_id_mismatch"
    if (
        record.get("serialized_payload_hash")
        != serialized_payload_candidate_digest(record["serialized_payload_candidate"])
    ):
        return "source_serialized_payload_hash_mismatch"

    serialized_payload = _serialized_payload(record)
    if serialized_payload.get("serialized_payload_version") != _SERIALIZED_PAYLOAD_VERSION:
        return "source_serialized_payload_version_mismatch"
    response_candidate_type = serialized_payload.get("response_candidate_type")
    if response_candidate_type not in (
        *PRETOOLUSE_PERMISSION_DECISIONS,
        RESPONSE_HOLD_CURRENT_STATE,
    ):
        return "source_serialized_payload_response_candidate_type_unknown"
    if serialized_payload.get("response_transport_candidate") != RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT:
        return "source_serialized_payload_transport_mismatch"
    if serialized_payload.get("response_schema_status") != RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME:
        return "source_serialized_payload_schema_status_mismatch"
    if serialized_payload.get("safe_default") != SAFE_DEFAULT:
        return "source_serialized_payload_safe_default_mismatch"
    if serialized_payload.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        return "source_serialized_payload_live_executor_authority_not_on_hold"
    if serialized_payload.get("trust_boundary") != UNTRUSTED_RAW_EXECUTOR_OUTPUT:
        return "source_serialized_payload_trust_boundary_mismatch"

    source_response = record.get("source_response_candidate_type")
    if source_response is not None and source_response not in (
        *PRETOOLUSE_PERMISSION_DECISIONS,
        RESPONSE_HOLD_CURRENT_STATE,
    ):
        return "source_serialization_response_candidate_type_unknown"
    if source_response is not None and response_candidate_type != source_response:
        return "source_serialization_payload_response_type_mismatch"
    if source_response is None and response_candidate_type != RESPONSE_HOLD_CURRENT_STATE:
        return "source_serialization_payload_without_source_not_hold"
    return None


def _serialized_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(record["serialized_payload_candidate"])
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(value, Mapping):
        return _plain_json_data(value)
    return {}


def _response_schema_candidate_type(
    serialization: Mapping[str, Any],
    serialized_payload: Mapping[str, Any],
) -> str:
    source_response = serialization.get("source_response_candidate_type")
    if source_response in PRETOOLUSE_PERMISSION_DECISIONS:
        return str(source_response)
    if source_response == RESPONSE_HOLD_CURRENT_STATE:
        return RESPONSE_HOLD_CURRENT_STATE
    if serialized_payload.get("response_candidate_type") == RESPONSE_HOLD_CURRENT_STATE:
        return RESPONSE_HOLD_CURRENT_STATE
    return RESPONSE_HOLD_CURRENT_STATE


def _permission_decision_for_candidate_type(response_schema_candidate_type: str) -> str:
    if response_schema_candidate_type in PRETOOLUSE_PERMISSION_DECISIONS:
        return response_schema_candidate_type
    return RESPONSE_DENY


def _permission_reason(
    *,
    response_candidate_type: str,
    source_valid: bool,
    reason_codes: tuple[str, ...] = tuple(),
) -> str:
    source_status = "source_valid" if source_valid else "source_held"
    reason_suffix = ""
    if reason_codes:
        reason_suffix = "; reason_codes=" + ",".join(sorted(set(reason_codes)))
    return (
        "redacted_phase11c_pretooluse_candidate;"
        f" candidate={response_candidate_type};"
        f" {source_status};"
        f" transport={RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT};"
        " not_runtime;"
        f" safe_default={SAFE_DEFAULT}"
        f"{reason_suffix}"
    )


def _response_schema_candidate_payload(
    record: ClaudeCodePreToolUseResponseSchemaCandidate,
) -> dict[str, Any]:
    return {field: getattr(record, field) for field in _RESPONSE_SCHEMA_PAYLOAD_FIELDS}


def _missing_fields(record: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(field for field in fields if field not in record)


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _plain_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_data(nested) for key, nested in value.items()}
    if _is_sequence(value):
        return [_plain_json_data(nested) for nested in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(type(value).__name__)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(nested) for key, nested in value.items()}
        )
    if _is_sequence(value):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


__all__ = [
    "CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE",
    "DOCS_CHECKED_DATE",
    "DOCS_SOURCE_STATUS",
    "DOCS_SOURCE_TYPE",
    "PHASE11C_PRETOOLUSE_RESPONSE_SCHEMA_CANDIDATE_VERSION",
    "PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL",
    "PRETOOLUSE_PERMISSION_DECISIONS",
    "RESPONSE_SCHEMA_STATUS_CLAUDE_CODE_PRETOOLUSE_CANDIDATE_NOT_RUNTIME",
    "ClaudeCodePreToolUseResponseSchemaCandidate",
    "build_claude_code_pretooluse_response_schema_candidate",
    "build_claude_code_pretooluse_response_schema_candidate_contract_evidence",
    "claude_code_pretooluse_response_schema_candidate_digest",
]
