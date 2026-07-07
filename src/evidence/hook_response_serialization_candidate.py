"""Phase 11-C-7 inert hook response serialization candidate.

This module serializes Phase 11-C-6 response envelope candidates into inert
data-only payload candidates. It does not implement a hook command, emit a real
Claude Code hook response, write hook output, execute actions, grant authority,
or write state.
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
    ENVELOPE_HASH_ALGORITHM,
    ENVELOPE_REDACTION_POLICY,
    HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES,
    HookResponseEnvelopeCandidate,
    PHASE11C_6_COMPLETE_LABEL,
    PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION,
    RESPONSE_ALLOW,
    RESPONSE_ASK,
    RESPONSE_DEFER,
    RESPONSE_DENY,
    RESPONSE_HOLD_CURRENT_STATE,
)

PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION = (
    "phase11c_7_hook_response_serialization_candidate_v0"
)
PHASE11C_7_COMPLETE_LABEL = (
    "PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_COMPLETE_NOT_HOOK_RUNTIME"
)

RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT = "data_only_not_stdout"
RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME = (
    "generic_candidate_not_substrate_runtime"
)
SERIALIZATION_HASH_ALGORITHM = "sha256_canonical_json_v0"
SERIALIZED_PAYLOAD_HASH_ALGORITHM = "sha256_canonical_json_v0"
SERIALIZATION_REDACTION_POLICY = (
    "response_candidate_type_redacted_message_reason_codes_hashes_and_safe_summaries_only_v0"
)

_SERIALIZATION_ID_PREFIX = "phase11c-7-hook-response-serialization:"
_SOURCE_ENVELOPE_ID_PREFIX = "phase11c-6-hook-response-envelope:"
_SERIALIZED_PAYLOAD_VERSION = "phase11c_7_serialized_payload_candidate_v0"
_AUDIT_SUMMARY_VERSION = "phase11c_7_redacted_serialization_audit_summary_v0"

_SOURCE_ENVELOPE_PAYLOAD_FIELDS = (
    "envelope_version",
    "completion_label",
    "source_binding_id",
    "source_binding_hash",
    "source_verification_output",
    "source_decision_candidate",
    "source_tool_use_id",
    "action_id",
    "response_candidate_type",
    "response_reason_codes",
    "redacted_user_message",
    "audit_summary",
    "safe_default",
    "live_executor_authority",
    "trust_boundary",
    "envelope_hash_algorithm",
    "envelope_redaction_policy",
    "envelope_candidate_is_real_claude_code_hook_response",
    "envelope_candidate_is_stdout_stderr_emission",
    "envelope_candidate_is_hook_runtime",
    "envelope_candidate_is_execution",
    "envelope_candidate_is_action_execution_engine",
    "envelope_candidate_is_write_authority",
    "envelope_candidate_is_store_write",
    "envelope_candidate_mutates_filesystem",
    "allow_envelope_candidate_is_execution",
    "deny_envelope_candidate_is_real_denial_response",
    "ask_envelope_candidate_is_user_prompt_implementation",
    "defer_or_hold_envelope_candidate_preserves_safe_default",
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
    "filesystem_mutation_by_envelope",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)

_SOURCE_ENVELOPE_RECORD_FIELDS = (
    "envelope_id",
    "envelope_hash",
    *_SOURCE_ENVELOPE_PAYLOAD_FIELDS,
)

_SOURCE_ENVELOPE_FALSE_FIELDS = (
    "envelope_candidate_is_real_claude_code_hook_response",
    "envelope_candidate_is_stdout_stderr_emission",
    "envelope_candidate_is_hook_runtime",
    "envelope_candidate_is_execution",
    "envelope_candidate_is_action_execution_engine",
    "envelope_candidate_is_write_authority",
    "envelope_candidate_is_store_write",
    "envelope_candidate_mutates_filesystem",
    "allow_envelope_candidate_is_execution",
    "deny_envelope_candidate_is_real_denial_response",
    "ask_envelope_candidate_is_user_prompt_implementation",
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
    "filesystem_mutation_by_envelope",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)

_SERIALIZATION_PAYLOAD_FIELDS = (
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
    "defer_or_hold_serialization_candidate_preserves_safe_default",
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


@dataclass(frozen=True)
class HookResponseSerializationCandidate:
    serialization_id: str
    serialization_hash: str
    serialization_version: str
    completion_label: str
    source_envelope_id: str | None
    source_envelope_hash: str | None
    source_response_candidate_type: str | None
    serialized_payload_candidate: str
    serialized_payload_hash: str
    response_transport_candidate: str
    response_schema_status: str
    redacted_user_message: str
    reason_codes: tuple[str, ...]
    audit_summary: Mapping[str, Any]
    safe_default: str
    live_executor_authority: str
    trust_boundary: str
    serialization_hash_algorithm: str = SERIALIZATION_HASH_ALGORITHM
    serialized_payload_hash_algorithm: str = SERIALIZED_PAYLOAD_HASH_ALGORITHM
    serialization_redaction_policy: str = SERIALIZATION_REDACTION_POLICY
    serialization_candidate_is_real_claude_code_hook_response: bool = False
    serialization_candidate_is_stdout_stderr_emission: bool = False
    serialization_candidate_is_hook_runtime: bool = False
    serialization_candidate_is_hook_command: bool = False
    serialization_candidate_is_execution: bool = False
    serialization_candidate_is_action_execution_engine: bool = False
    serialization_candidate_is_write_authority: bool = False
    serialization_candidate_is_store_write: bool = False
    serialization_candidate_mutates_filesystem: bool = False
    allow_serialization_candidate_is_execution: bool = False
    deny_serialization_candidate_is_real_denial_response: bool = False
    ask_serialization_candidate_is_user_prompt_implementation: bool = False
    defer_or_hold_serialization_candidate_preserves_safe_default: bool = True
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
    filesystem_mutation_by_serialization: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "audit_summary", _freeze_value(self.audit_summary))

    def to_record(self) -> dict[str, Any]:
        return {
            "serialization_id": self.serialization_id,
            "serialization_hash": self.serialization_hash,
            **_plain_json_data(_hook_response_serialization_payload(self)),
        }


def build_hook_response_serialization_candidate(
    *,
    envelope_candidate: HookResponseEnvelopeCandidate | Mapping[str, Any] | Any,
) -> HookResponseSerializationCandidate:
    """Build an inert data-only serialization candidate from an 11-C-6 envelope."""

    source_envelope, source_error = _coerce_source_envelope(envelope_candidate)
    if source_error:
        return _build_hold_serialization(
            reason_codes=(
                source_error,
                "malformed_or_mismatched_source_envelope_maps_to_hold_current_state_serialization_candidate",
                "safe_default_hold_current_state",
            )
        )

    consistency_error = _source_envelope_consistency_error(source_envelope)
    if consistency_error:
        return _build_hold_serialization(
            reason_codes=(
                consistency_error,
                "malformed_or_mismatched_source_envelope_maps_to_hold_current_state_serialization_candidate",
                "safe_default_hold_current_state",
            )
        )

    source_response = source_envelope["response_candidate_type"]
    if source_response == RESPONSE_ALLOW:
        mapping_reason = "allow_envelope_candidate_maps_to_allow_serialization_candidate_only"
    elif source_response == RESPONSE_DENY:
        mapping_reason = "deny_envelope_candidate_maps_to_deny_serialization_candidate_only"
    elif source_response == RESPONSE_ASK:
        mapping_reason = "ask_envelope_candidate_maps_to_ask_serialization_candidate_only"
    elif source_response == RESPONSE_DEFER:
        mapping_reason = "defer_envelope_candidate_maps_to_defer_serialization_candidate_only"
    elif source_response == RESPONSE_HOLD_CURRENT_STATE:
        mapping_reason = (
            "hold_current_state_envelope_candidate_maps_to_hold_current_state_serialization_candidate"
        )
    else:
        return _build_hold_serialization(
            reason_codes=(
                "unknown_source_response_candidate_type",
                "malformed_or_mismatched_source_envelope_maps_to_hold_current_state_serialization_candidate",
                "safe_default_hold_current_state",
            )
        )

    return _build_serialization(
        source_envelope_id=_string_or_none(source_envelope["envelope_id"]),
        source_envelope_hash=_string_or_none(source_envelope["envelope_hash"]),
        source_response_candidate_type=source_response,
        response_candidate_type=source_response,
        reason_codes=(
            "source_envelope_hash_recomputed",
            "source_envelope_consistency_checked",
            mapping_reason,
            *_response_specific_reason_codes(source_response),
            "serialization_candidate_is_data_only_not_stdout",
            "serialization_candidate_is_not_real_claude_code_hook_response",
        ),
        source_envelope_hash_matched=True,
        source_envelope_reason_code_count=_reason_code_count(
            source_envelope.get("response_reason_codes")
        ),
        source_envelope_audit_summary_hash=_sha256_json(
            source_envelope.get("audit_summary")
        ),
    )


def hook_response_serialization_candidate_digest(
    record: HookResponseSerializationCandidate | Mapping[str, Any],
) -> str:
    """Recompute the deterministic digest for a serialization candidate."""

    if isinstance(record, HookResponseSerializationCandidate):
        return _sha256_json(_hook_response_serialization_payload(record))
    if isinstance(record, Mapping):
        missing = _missing_fields(record, _SERIALIZATION_PAYLOAD_FIELDS)
        if missing:
            raise ValueError(f"missing serialization payload fields: {missing!r}")
        return _sha256_json({field: record[field] for field in _SERIALIZATION_PAYLOAD_FIELDS})
    raise TypeError(type(record).__name__)


def serialized_payload_candidate_digest(serialized_payload_candidate: str) -> str:
    """Recompute the deterministic digest for a serialized payload candidate."""

    if not isinstance(serialized_payload_candidate, str):
        raise TypeError(type(serialized_payload_candidate).__name__)
    return _sha256_text(serialized_payload_candidate)


def build_hook_response_serialization_candidate_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION,
        "completion_label": PHASE11C_7_COMPLETE_LABEL,
        "input_contract_versions": {
            "hook_response_envelope_candidate": (
                PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION
            ),
        },
        "serialization_candidate_fields": (
            "serialization_id",
            "serialization_hash",
            "serialization_version",
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
        ),
        "response_transport_candidate": RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        "response_schema_status": (
            RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME
        ),
        "allow_envelope_policy": RESPONSE_ALLOW,
        "deny_envelope_policy": RESPONSE_DENY,
        "ask_envelope_policy": RESPONSE_ASK,
        "defer_envelope_policy": RESPONSE_DEFER,
        "hold_current_state_envelope_policy": RESPONSE_HOLD_CURRENT_STATE,
        "unknown_malformed_envelope_policy": RESPONSE_HOLD_CURRENT_STATE,
        "serialization_hash_recomputes_deterministically": True,
        "serialized_payload_hash_recomputes_deterministically": True,
        "serialization_id_matches_serialization_hash": True,
        "source_envelope_hash_must_match_envelope_hash": True,
        "mismatched_source_envelope_copies_source_ids": False,
        "raw_full_tool_input_in_serialized_payload_candidate": False,
        "raw_secret_bearing_path_content_command_text_in_serialized_payload_candidate": False,
        "target_scope_payload_provenance_metadata_copied": False,
        "raw_decision_reason_strings_copied": False,
        "serialization_candidate_is_real_claude_code_hook_response": False,
        "serialization_candidate_is_stdout_stderr_emission": False,
        "serialization_candidate_is_hook_runtime": False,
        "serialization_candidate_is_hook_command": False,
        "serialization_candidate_is_execution": False,
        "serialization_candidate_is_action_execution_engine": False,
        "serialization_candidate_is_write_authority": False,
        "serialization_candidate_is_store_write": False,
        "serialization_candidate_mutates_filesystem": False,
        "allow_serialization_candidate_is_execution": False,
        "deny_serialization_candidate_is_real_denial_response": False,
        "ask_serialization_candidate_is_user_prompt_implementation": False,
        "defer_or_hold_serialization_candidate_preserves_safe_default": True,
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
        "filesystem_mutation_by_serialization": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _build_hold_serialization(
    *,
    reason_codes: tuple[str, ...],
) -> HookResponseSerializationCandidate:
    return _build_serialization(
        source_envelope_id=None,
        source_envelope_hash=None,
        source_response_candidate_type=None,
        response_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
        reason_codes=reason_codes,
        source_envelope_hash_matched=False,
        source_envelope_reason_code_count=0,
        source_envelope_audit_summary_hash=None,
    )


def _build_serialization(
    *,
    source_envelope_id: str | None,
    source_envelope_hash: str | None,
    source_response_candidate_type: str | None,
    response_candidate_type: str,
    reason_codes: tuple[str, ...],
    source_envelope_hash_matched: bool,
    source_envelope_reason_code_count: int,
    source_envelope_audit_summary_hash: str | None,
) -> HookResponseSerializationCandidate:
    reason_codes = tuple(dict.fromkeys(reason_codes))
    redacted_user_message = _redacted_user_message(response_candidate_type)
    audit_summary = _redacted_audit_summary(
        source_response_candidate_type=source_response_candidate_type,
        response_candidate_type=response_candidate_type,
        reason_codes=reason_codes,
        source_envelope_hash_present=source_envelope_hash is not None,
        source_envelope_hash_matched=source_envelope_hash_matched,
        source_envelope_reason_code_count=source_envelope_reason_code_count,
        source_envelope_audit_summary_hash=source_envelope_audit_summary_hash,
    )
    serialized_payload_object = _serialized_payload_object(
        source_envelope_hash=source_envelope_hash,
        source_response_candidate_type=source_response_candidate_type,
        response_candidate_type=response_candidate_type,
        redacted_user_message=redacted_user_message,
        reason_codes=reason_codes,
        audit_summary=audit_summary,
    )
    serialized_payload_candidate = _canonical_json(serialized_payload_object)
    serialized_payload_hash = _sha256_text(serialized_payload_candidate)
    payload = {
        "serialization_version": (
            PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION
        ),
        "completion_label": PHASE11C_7_COMPLETE_LABEL,
        "source_envelope_id": source_envelope_id,
        "source_envelope_hash": source_envelope_hash,
        "source_response_candidate_type": source_response_candidate_type,
        "serialized_payload_candidate": serialized_payload_candidate,
        "serialized_payload_hash": serialized_payload_hash,
        "response_transport_candidate": RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        "response_schema_status": (
            RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME
        ),
        "redacted_user_message": redacted_user_message,
        "reason_codes": reason_codes,
        "audit_summary": audit_summary,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "serialization_hash_algorithm": SERIALIZATION_HASH_ALGORITHM,
        "serialized_payload_hash_algorithm": SERIALIZED_PAYLOAD_HASH_ALGORITHM,
        "serialization_redaction_policy": SERIALIZATION_REDACTION_POLICY,
        "serialization_candidate_is_real_claude_code_hook_response": False,
        "serialization_candidate_is_stdout_stderr_emission": False,
        "serialization_candidate_is_hook_runtime": False,
        "serialization_candidate_is_hook_command": False,
        "serialization_candidate_is_execution": False,
        "serialization_candidate_is_action_execution_engine": False,
        "serialization_candidate_is_write_authority": False,
        "serialization_candidate_is_store_write": False,
        "serialization_candidate_mutates_filesystem": False,
        "allow_serialization_candidate_is_execution": False,
        "deny_serialization_candidate_is_real_denial_response": False,
        "ask_serialization_candidate_is_user_prompt_implementation": False,
        "defer_or_hold_serialization_candidate_preserves_safe_default": True,
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
        "filesystem_mutation_by_serialization": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }
    serialization_hash = _sha256_json(payload)
    return HookResponseSerializationCandidate(
        serialization_id=f"{_SERIALIZATION_ID_PREFIX}{serialization_hash}",
        serialization_hash=serialization_hash,
        **payload,
    )


def _serialized_payload_object(
    *,
    source_envelope_hash: str | None,
    source_response_candidate_type: str | None,
    response_candidate_type: str,
    redacted_user_message: str,
    reason_codes: tuple[str, ...],
    audit_summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "serialized_payload_version": _SERIALIZED_PAYLOAD_VERSION,
        "response_candidate_type": response_candidate_type,
        "source_envelope_hash": source_envelope_hash,
        "source_response_candidate_type": source_response_candidate_type,
        "response_transport_candidate": RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT,
        "response_schema_status": (
            RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME
        ),
        "redacted_user_message": redacted_user_message,
        "reason_codes": reason_codes,
        "audit_summary": audit_summary,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
    }


def _source_envelope_consistency_error(record: Mapping[str, Any]) -> str | None:
    if record.get("envelope_version") != PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION:
        return "source_envelope_version_mismatch"
    if record.get("completion_label") != PHASE11C_6_COMPLETE_LABEL:
        return "source_envelope_completion_label_mismatch"
    if record.get("envelope_hash_algorithm") != ENVELOPE_HASH_ALGORITHM:
        return "source_envelope_hash_algorithm_mismatch"
    if record.get("envelope_redaction_policy") != ENVELOPE_REDACTION_POLICY:
        return "source_envelope_redaction_policy_mismatch"

    recomputed_hash = _source_envelope_hash_from_record(record)
    if record.get("envelope_hash") != recomputed_hash:
        return "source_envelope_hash_mismatch"
    if record.get("envelope_id") != f"{_SOURCE_ENVELOPE_ID_PREFIX}{recomputed_hash}":
        return "source_envelope_id_mismatch"
    if record.get("response_candidate_type") not in HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES:
        return "unknown_source_response_candidate_type"
    if record.get("safe_default") != SAFE_DEFAULT:
        return "source_envelope_safe_default_mismatch"
    if record.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        return "source_envelope_live_executor_authority_not_on_hold"
    if record.get("trust_boundary") != UNTRUSTED_RAW_EXECUTOR_OUTPUT:
        return "source_envelope_trust_boundary_mismatch"
    if record.get("defer_or_hold_envelope_candidate_preserves_safe_default") is not True:
        return "source_envelope_defer_or_hold_safe_default_mismatch"
    for field in _SOURCE_ENVELOPE_FALSE_FIELDS:
        if record.get(field) is not False:
            return "source_envelope_runtime_emission_authority_or_store_write_flag_mismatch"
    return None


def _coerce_source_envelope(
    value: HookResponseEnvelopeCandidate | Mapping[str, Any] | Any,
) -> tuple[dict[str, Any], str | None]:
    try:
        if isinstance(value, HookResponseEnvelopeCandidate):
            return _plain_json_data(value.to_record()), None
        if isinstance(value, Mapping):
            record = _plain_json_data(value)
            missing = _missing_fields(record, _SOURCE_ENVELOPE_RECORD_FIELDS)
            if missing:
                return {}, "malformed_source_envelope"
            return record, None
    except TypeError:
        return {}, "malformed_source_envelope"
    return {}, "malformed_source_envelope"


def _response_specific_reason_codes(response_candidate_type: str) -> tuple[str, ...]:
    if response_candidate_type == RESPONSE_ALLOW:
        return ("allow_serialization_candidate_is_not_execution",)
    if response_candidate_type == RESPONSE_DENY:
        return ("deny_serialization_candidate_is_not_real_denial_response",)
    if response_candidate_type == RESPONSE_ASK:
        return ("ask_serialization_candidate_is_not_user_prompt_implementation",)
    if response_candidate_type in (RESPONSE_DEFER, RESPONSE_HOLD_CURRENT_STATE):
        return (
            "defer_or_hold_serialization_candidate_preserves_safe_default",
            "safe_default_hold_current_state",
        )
    return ("safe_default_hold_current_state",)


def _redacted_user_message(response_candidate_type: str) -> str:
    return (
        "hook response serialization candidate only; "
        f"response_candidate_type={response_candidate_type}; "
        f"transport={RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT}; "
        "no real hook response emitted"
    )


def _redacted_audit_summary(
    *,
    source_response_candidate_type: str | None,
    response_candidate_type: str,
    reason_codes: tuple[str, ...],
    source_envelope_hash_present: bool,
    source_envelope_hash_matched: bool,
    source_envelope_reason_code_count: int,
    source_envelope_audit_summary_hash: str | None,
) -> dict[str, Any]:
    return {
        "summary_version": _AUDIT_SUMMARY_VERSION,
        "source_response_candidate_type": source_response_candidate_type,
        "response_candidate_type": response_candidate_type,
        "reason_code_count": len(reason_codes),
        "source_envelope_hash_present": source_envelope_hash_present,
        "source_envelope_hash_matched": source_envelope_hash_matched,
        "source_envelope_reason_code_count": source_envelope_reason_code_count,
        "source_envelope_audit_summary_hash": source_envelope_audit_summary_hash,
        "source_envelope_audit_summary_copied": False,
        "raw_full_input_included": False,
        "raw_secret_bearing_path_content_command_text_included": False,
        "target_scope_payload_provenance_metadata_copied": False,
        "raw_decision_reason_strings_copied": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "execution_performed": False,
        "write_authority_granted": False,
        "store_write_performed": False,
        "filesystem_mutation_performed": False,
    }


def _reason_code_count(value: Any) -> int:
    if not _is_sequence(value):
        return 0
    return sum(1 for item in value if isinstance(item, str))


def _missing_fields(record: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(field for field in fields if field not in record)


def _source_envelope_hash_from_record(record: Mapping[str, Any]) -> str:
    return _sha256_json({field: record[field] for field in _SOURCE_ENVELOPE_PAYLOAD_FIELDS})


def _hook_response_serialization_payload(
    record: HookResponseSerializationCandidate,
) -> dict[str, Any]:
    return {field: getattr(record, field) for field in _SERIALIZATION_PAYLOAD_FIELDS}


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(payload: Any) -> str:
    return _sha256_text(_canonical_json(payload))


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    "HookResponseSerializationCandidate",
    "PHASE11C_7_COMPLETE_LABEL",
    "PHASE11C_7_HOOK_RESPONSE_SERIALIZATION_CANDIDATE_VERSION",
    "RESPONSE_SCHEMA_GENERIC_CANDIDATE_NOT_SUBSTRATE_RUNTIME",
    "RESPONSE_TRANSPORT_DATA_ONLY_NOT_STDOUT",
    "SERIALIZATION_HASH_ALGORITHM",
    "SERIALIZATION_REDACTION_POLICY",
    "SERIALIZED_PAYLOAD_HASH_ALGORITHM",
    "build_hook_response_serialization_candidate",
    "build_hook_response_serialization_candidate_contract_evidence",
    "hook_response_serialization_candidate_digest",
    "serialized_payload_candidate_digest",
]
