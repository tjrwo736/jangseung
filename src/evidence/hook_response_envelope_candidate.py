"""Phase 11-C-6 inert hook response envelope candidate.

This module maps verified Phase 11-C evidence into an inert envelope candidate.
It does not implement a hook command, emit a real Claude Code hook response,
write hook output, execute actions, grant authority, or write state.
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
from src.evidence.hook_decision_adapter import (
    ALLOW,
    ASK,
    DEFER,
    DENY,
    HOOK_DECISION_CANDIDATES,
    HookDecisionCandidate,
    PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
)
from src.evidence.hook_evidence_binding import (
    HOOK_EVIDENCE_BINDING_REJECTED,
    HOOK_EVIDENCE_BOUND,
    HookEvidenceBinding,
    PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
)
from src.evidence.hook_evidence_verification_gate import (
    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
    HookEvidenceVerificationGateResult,
    PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION,
    REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
)

PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION = (
    "phase11c_6_hook_response_envelope_candidate_v0"
)
PHASE11C_6_COMPLETE_LABEL = (
    "PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_COMPLETE_NOT_HOOK_RUNTIME"
)

RESPONSE_ALLOW = ALLOW
RESPONSE_DENY = DENY
RESPONSE_ASK = ASK
RESPONSE_DEFER = DEFER
RESPONSE_HOLD_CURRENT_STATE = SAFE_DEFAULT
HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES = (
    RESPONSE_ALLOW,
    RESPONSE_DENY,
    RESPONSE_ASK,
    RESPONSE_DEFER,
    RESPONSE_HOLD_CURRENT_STATE,
)

ENVELOPE_HASH_ALGORITHM = "sha256_canonical_json_v0"
ENVELOPE_REDACTION_POLICY = "reason_codes_and_redacted_summary_only_v0"

_ENVELOPE_ID_PREFIX = "phase11c-6-hook-response-envelope:"
_AUDIT_SUMMARY_VERSION = "phase11c_6_redacted_audit_summary_v0"
_VERIFICATION_OUTPUTS = (
    VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
    HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
)


@dataclass(frozen=True)
class HookResponseEnvelopeCandidate:
    envelope_id: str
    envelope_hash: str
    envelope_version: str
    completion_label: str
    source_binding_id: str | None
    source_binding_hash: str | None
    source_verification_output: str
    source_decision_candidate: str | None
    source_tool_use_id: str | None
    action_id: str | None
    response_candidate_type: str
    response_reason_codes: tuple[str, ...]
    redacted_user_message: str
    audit_summary: Mapping[str, Any]
    safe_default: str
    live_executor_authority: str
    trust_boundary: str
    envelope_hash_algorithm: str = ENVELOPE_HASH_ALGORITHM
    envelope_redaction_policy: str = ENVELOPE_REDACTION_POLICY
    envelope_candidate_is_real_claude_code_hook_response: bool = False
    envelope_candidate_is_stdout_stderr_emission: bool = False
    envelope_candidate_is_hook_runtime: bool = False
    envelope_candidate_is_execution: bool = False
    envelope_candidate_is_action_execution_engine: bool = False
    envelope_candidate_is_write_authority: bool = False
    envelope_candidate_is_store_write: bool = False
    envelope_candidate_mutates_filesystem: bool = False
    allow_envelope_candidate_is_execution: bool = False
    deny_envelope_candidate_is_real_denial_response: bool = False
    ask_envelope_candidate_is_user_prompt_implementation: bool = False
    defer_or_hold_envelope_candidate_preserves_safe_default: bool = True
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
    filesystem_mutation_by_envelope: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "response_reason_codes",
            tuple(self.response_reason_codes),
        )
        object.__setattr__(self, "audit_summary", _freeze_value(self.audit_summary))

    def to_record(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "envelope_hash": self.envelope_hash,
            **_plain_json_data(_hook_response_envelope_payload(self)),
        }


def build_hook_response_envelope_candidate(
    *,
    verification_result: HookEvidenceVerificationGateResult | Mapping[str, Any] | Any,
    binding_record: HookEvidenceBinding | Mapping[str, Any] | Any,
    decision_candidate: HookDecisionCandidate | Mapping[str, Any] | None = None,
) -> HookResponseEnvelopeCandidate:
    """Build an inert response envelope candidate from verified 11-C evidence."""

    verification, verification_error = _coerce_verification_result(verification_result)
    binding, binding_error = _coerce_binding_record(binding_record)
    decision, decision_error = _coerce_decision_candidate(decision_candidate)

    if verification_error or binding_error or decision_error:
        return _build_hold_envelope(
            source_verification_output=HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
            response_reason_codes=(
                *_optional_code(verification_error),
                *_optional_code(binding_error),
                *_optional_code(decision_error),
                "malformed_source_input_maps_to_hold_current_state",
                "safe_default_hold_current_state",
            ),
        )

    if verification.get("verification_output") not in _VERIFICATION_OUTPUTS:
        return _build_hold_envelope(
            source_verification_output=HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
            response_reason_codes=(
                "unknown_source_verification_output",
                "unknown_source_verification_maps_to_hold_current_state",
                "safe_default_hold_current_state",
            ),
        )

    source_verification_output = _source_verification_output(verification)
    if source_verification_output == HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE:
        return _build_hold_envelope(
            source_verification_output=source_verification_output,
            response_reason_codes=(
                "source_verification_hold_current_state",
                *_verification_rejection_codes(verification),
                "hold_current_state_verification_maps_to_hold_current_state_envelope_candidate",
                "safe_default_hold_current_state",
            ),
        )

    source_mismatch_code = _source_mismatch_code(verification, binding, decision)
    if source_mismatch_code:
        return _build_hold_envelope(
            source_verification_output=source_verification_output,
            response_reason_codes=(
                source_mismatch_code,
                "source_mismatch_maps_to_hold_current_state",
                "safe_default_hold_current_state",
            ),
        )

    source_fields = _source_fields(binding, source_verification_output)
    if source_verification_output == REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE:
        return _build_envelope(
            **source_fields,
            response_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
            response_reason_codes=(
                "rejected_hook_evidence_binding_candidate",
                "rejected_binding_maps_to_hold_current_state_envelope_candidate",
                "not_real_claude_code_denial_response",
                "safe_default_hold_current_state",
            ),
        )

    source_decision = source_fields["source_decision_candidate"]
    if source_decision == ALLOW:
        return _build_envelope(
            **source_fields,
            response_candidate_type=RESPONSE_ALLOW,
            response_reason_codes=(
                "verified_hook_evidence_binding_candidate",
                "source_decision_allow_maps_to_allow_envelope_candidate",
                "allow_envelope_candidate_is_not_execution",
            ),
        )
    if source_decision == DENY:
        return _build_envelope(
            **source_fields,
            response_candidate_type=RESPONSE_DENY,
            response_reason_codes=(
                "verified_hook_evidence_binding_candidate",
                "source_decision_deny_maps_to_deny_envelope_candidate",
                "deny_envelope_candidate_is_not_real_denial_response",
            ),
        )
    if source_decision == ASK:
        return _build_envelope(
            **source_fields,
            response_candidate_type=RESPONSE_ASK,
            response_reason_codes=(
                "verified_hook_evidence_binding_candidate",
                "source_decision_ask_maps_to_ask_envelope_candidate",
                "ask_envelope_candidate_is_not_user_prompt_implementation",
            ),
        )
    if source_decision == DEFER:
        return _build_envelope(
            **source_fields,
            response_candidate_type=RESPONSE_DEFER,
            response_reason_codes=(
                "verified_hook_evidence_binding_candidate",
                "source_decision_defer_maps_to_defer_envelope_candidate",
                "defer_envelope_candidate_preserves_safe_default",
                "safe_default_hold_current_state",
            ),
        )

    return _build_hold_envelope(
        source_verification_output=source_verification_output,
        response_reason_codes=(
            "unknown_source_decision_candidate",
            "unknown_source_decision_maps_to_hold_current_state",
            "safe_default_hold_current_state",
        ),
    )


def hook_response_envelope_candidate_digest(
    record: HookResponseEnvelopeCandidate,
) -> str:
    """Recompute the deterministic digest for a response envelope candidate."""

    return _sha256_json(_hook_response_envelope_payload(record))


def build_hook_response_envelope_candidate_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION,
        "completion_label": PHASE11C_6_COMPLETE_LABEL,
        "input_contract_versions": {
            "hook_evidence_verification_gate": (
                PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION
            ),
            "hook_evidence_binding": PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
            "hook_decision_candidate": PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
        },
        "response_candidate_types": HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES,
        "verified_allow_policy": RESPONSE_ALLOW,
        "verified_deny_policy": RESPONSE_DENY,
        "verified_ask_policy": RESPONSE_ASK,
        "verified_defer_policy": RESPONSE_DEFER,
        "rejected_binding_policy": RESPONSE_HOLD_CURRENT_STATE,
        "hold_verification_policy": RESPONSE_HOLD_CURRENT_STATE,
        "unknown_malformed_input_policy": RESPONSE_HOLD_CURRENT_STATE,
        "raw_full_input_included": False,
        "raw_secret_bearing_path_content_command_text_included": False,
        "user_facing_message_uses_redacted_summary_and_reason_codes_only": True,
        "audit_summary_uses_redacted_summary_and_reason_codes_only": True,
        "envelope_candidate_is_real_claude_code_hook_response": False,
        "envelope_candidate_is_stdout_stderr_emission": False,
        "envelope_candidate_is_hook_runtime": False,
        "envelope_candidate_is_execution": False,
        "envelope_candidate_is_action_execution_engine": False,
        "envelope_candidate_is_write_authority": False,
        "envelope_candidate_is_store_write": False,
        "envelope_candidate_mutates_filesystem": False,
        "allow_envelope_candidate_is_execution": False,
        "deny_envelope_candidate_is_real_denial_response": False,
        "ask_envelope_candidate_is_user_prompt_implementation": False,
        "defer_or_hold_envelope_candidate_preserves_safe_default": True,
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
        "filesystem_mutation_by_envelope": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _build_hold_envelope(
    *,
    source_verification_output: str,
    response_reason_codes: tuple[str, ...],
) -> HookResponseEnvelopeCandidate:
    return _build_envelope(
        source_binding_id=None,
        source_binding_hash=None,
        source_verification_output=source_verification_output,
        source_decision_candidate=None,
        source_tool_use_id=None,
        action_id=None,
        response_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
        response_reason_codes=tuple(dict.fromkeys(response_reason_codes)),
    )


def _build_envelope(
    *,
    source_binding_id: str | None,
    source_binding_hash: str | None,
    source_verification_output: str,
    source_decision_candidate: str | None,
    source_tool_use_id: str | None,
    action_id: str | None,
    response_candidate_type: str,
    response_reason_codes: tuple[str, ...],
) -> HookResponseEnvelopeCandidate:
    response_reason_codes = tuple(dict.fromkeys(response_reason_codes))
    payload = {
        "envelope_version": PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION,
        "completion_label": PHASE11C_6_COMPLETE_LABEL,
        "source_binding_id": source_binding_id,
        "source_binding_hash": source_binding_hash,
        "source_verification_output": source_verification_output,
        "source_decision_candidate": source_decision_candidate,
        "source_tool_use_id": source_tool_use_id,
        "action_id": action_id,
        "response_candidate_type": response_candidate_type,
        "response_reason_codes": response_reason_codes,
        "redacted_user_message": _redacted_user_message(response_candidate_type),
        "audit_summary": _redacted_audit_summary(
            source_verification_output=source_verification_output,
            source_decision_candidate=source_decision_candidate,
            response_candidate_type=response_candidate_type,
            response_reason_codes=response_reason_codes,
            source_binding_hash_present=source_binding_hash is not None,
        ),
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "envelope_hash_algorithm": ENVELOPE_HASH_ALGORITHM,
        "envelope_redaction_policy": ENVELOPE_REDACTION_POLICY,
        "envelope_candidate_is_real_claude_code_hook_response": False,
        "envelope_candidate_is_stdout_stderr_emission": False,
        "envelope_candidate_is_hook_runtime": False,
        "envelope_candidate_is_execution": False,
        "envelope_candidate_is_action_execution_engine": False,
        "envelope_candidate_is_write_authority": False,
        "envelope_candidate_is_store_write": False,
        "envelope_candidate_mutates_filesystem": False,
        "allow_envelope_candidate_is_execution": False,
        "deny_envelope_candidate_is_real_denial_response": False,
        "ask_envelope_candidate_is_user_prompt_implementation": False,
        "defer_or_hold_envelope_candidate_preserves_safe_default": True,
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
        "filesystem_mutation_by_envelope": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }
    envelope_hash = _sha256_json(payload)
    return HookResponseEnvelopeCandidate(
        envelope_id=f"{_ENVELOPE_ID_PREFIX}{envelope_hash}",
        envelope_hash=envelope_hash,
        **payload,
    )


def _source_fields(
    binding: Mapping[str, Any],
    source_verification_output: str,
) -> dict[str, str | None]:
    return {
        "source_binding_id": _string_or_none(binding.get("binding_id")),
        "source_binding_hash": _string_or_none(binding.get("binding_hash")),
        "source_verification_output": source_verification_output,
        "source_decision_candidate": _string_or_none(binding.get("decision_candidate")),
        "source_tool_use_id": _string_or_none(binding.get("source_tool_use_id")),
        "action_id": _string_or_none(binding.get("action_id")),
    }


def _source_mismatch_code(
    verification: Mapping[str, Any],
    binding: Mapping[str, Any],
    decision: Mapping[str, Any] | None,
) -> str | None:
    if verification.get("verification_passed") is not True:
        return "source_verification_not_passed"
    if verification.get("safe_default") != SAFE_DEFAULT:
        return "source_verification_safe_default_mismatch"
    if verification.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        return "source_verification_live_executor_authority_not_on_hold"
    if verification.get("trust_boundary") != UNTRUSTED_RAW_EXECUTOR_OUTPUT:
        return "source_verification_trust_boundary_mismatch"
    if verification.get("binding_id") != binding.get("binding_id"):
        return "source_binding_id_mismatch"
    if verification.get("binding_hash") != binding.get("binding_hash"):
        return "source_binding_hash_mismatch"

    source_verification_output = _source_verification_output(verification)
    if (
        source_verification_output == VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE
        and binding.get("binding_status") != HOOK_EVIDENCE_BOUND
    ):
        return "verified_source_binding_status_mismatch"
    if (
        source_verification_output == REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE
        and binding.get("binding_status") != HOOK_EVIDENCE_BINDING_REJECTED
    ):
        return "rejected_source_binding_status_mismatch"

    source_decision = binding.get("decision_candidate")
    if source_decision not in HOOK_DECISION_CANDIDATES:
        return "source_decision_candidate_mismatch"
    if decision is not None:
        if decision.get("decision_candidate") != source_decision:
            return "optional_decision_candidate_mismatch"
        if decision.get("source_tool_use_id") != binding.get("source_tool_use_id"):
            return "optional_decision_source_tool_use_id_mismatch"
        if decision.get("action_id") != binding.get("action_id"):
            return "optional_decision_action_id_mismatch"
    return None


def _source_verification_output(verification: Mapping[str, Any]) -> str:
    value = verification.get("verification_output")
    if value in _VERIFICATION_OUTPUTS:
        return value
    return HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE


def _verification_rejection_codes(verification: Mapping[str, Any]) -> tuple[str, ...]:
    value = verification.get("rejection_codes")
    if not _is_sequence(value):
        return tuple()
    return tuple(item for item in value if isinstance(item, str))


def _redacted_user_message(response_candidate_type: str) -> str:
    return (
        "hook response envelope candidate only; "
        f"response_candidate_type={response_candidate_type}; "
        "no real hook response emitted"
    )


def _redacted_audit_summary(
    *,
    source_verification_output: str,
    source_decision_candidate: str | None,
    response_candidate_type: str,
    response_reason_codes: tuple[str, ...],
    source_binding_hash_present: bool,
) -> dict[str, Any]:
    return {
        "summary_version": _AUDIT_SUMMARY_VERSION,
        "source_verification_output": source_verification_output,
        "source_decision_candidate": source_decision_candidate,
        "response_candidate_type": response_candidate_type,
        "response_reason_codes": response_reason_codes,
        "response_reason_code_count": len(response_reason_codes),
        "source_binding_hash_present": source_binding_hash_present,
        "raw_full_input_included": False,
        "raw_secret_bearing_path_content_command_text_included": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "execution_performed": False,
        "write_authority_granted": False,
        "store_write_performed": False,
    }


def _coerce_verification_result(
    value: HookEvidenceVerificationGateResult | Mapping[str, Any] | Any,
) -> tuple[dict[str, Any], str | None]:
    try:
        if isinstance(value, HookEvidenceVerificationGateResult):
            return _plain_json_data(value.to_record()), None
        if isinstance(value, Mapping):
            record = _plain_json_data(value)
            missing = _missing_fields(
                record,
                (
                    "verification_output",
                    "verification_passed",
                    "binding_id",
                    "binding_hash",
                    "rejection_codes",
                    "safe_default",
                    "live_executor_authority",
                    "trust_boundary",
                ),
            )
            if missing:
                return {}, "malformed_verification_result"
            return record, None
    except TypeError:
        return {}, "malformed_verification_result"
    return {}, "malformed_verification_result"


def _coerce_binding_record(
    value: HookEvidenceBinding | Mapping[str, Any] | Any,
) -> tuple[dict[str, Any], str | None]:
    try:
        if isinstance(value, HookEvidenceBinding):
            return _plain_json_data(value.to_record()), None
        if isinstance(value, Mapping):
            record = _plain_json_data(value)
            missing = _missing_fields(
                record,
                (
                    "binding_id",
                    "binding_hash",
                    "binding_status",
                    "decision_candidate",
                    "source_tool_use_id",
                    "action_id",
                ),
            )
            if missing:
                return {}, "malformed_binding_record"
            return record, None
    except TypeError:
        return {}, "malformed_binding_record"
    return {}, "malformed_binding_record"


def _coerce_decision_candidate(
    value: HookDecisionCandidate | Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if value is None:
        return None, None
    try:
        if isinstance(value, HookDecisionCandidate):
            return {
                "decision_candidate": value.decision_candidate,
                "source_tool_use_id": value.source_tool_use_id,
                "action_id": value.action_id,
            }, None
        if isinstance(value, Mapping):
            record = _plain_json_data(value)
            missing = _missing_fields(
                record,
                ("decision_candidate", "source_tool_use_id", "action_id"),
            )
            if missing:
                return None, "malformed_decision_candidate"
            return record, None
    except TypeError:
        return None, "malformed_decision_candidate"
    return None, "malformed_decision_candidate"


def _missing_fields(record: Mapping[str, Any], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(field for field in fields if field not in record)


def _optional_code(value: str | None) -> tuple[str, ...]:
    if value is None:
        return tuple()
    return (value,)


def _hook_response_envelope_payload(
    record: HookResponseEnvelopeCandidate,
) -> dict[str, Any]:
    return {
        "envelope_version": record.envelope_version,
        "completion_label": record.completion_label,
        "source_binding_id": record.source_binding_id,
        "source_binding_hash": record.source_binding_hash,
        "source_verification_output": record.source_verification_output,
        "source_decision_candidate": record.source_decision_candidate,
        "source_tool_use_id": record.source_tool_use_id,
        "action_id": record.action_id,
        "response_candidate_type": record.response_candidate_type,
        "response_reason_codes": record.response_reason_codes,
        "redacted_user_message": record.redacted_user_message,
        "audit_summary": record.audit_summary,
        "safe_default": record.safe_default,
        "live_executor_authority": record.live_executor_authority,
        "trust_boundary": record.trust_boundary,
        "envelope_hash_algorithm": record.envelope_hash_algorithm,
        "envelope_redaction_policy": record.envelope_redaction_policy,
        "envelope_candidate_is_real_claude_code_hook_response": (
            record.envelope_candidate_is_real_claude_code_hook_response
        ),
        "envelope_candidate_is_stdout_stderr_emission": (
            record.envelope_candidate_is_stdout_stderr_emission
        ),
        "envelope_candidate_is_hook_runtime": record.envelope_candidate_is_hook_runtime,
        "envelope_candidate_is_execution": record.envelope_candidate_is_execution,
        "envelope_candidate_is_action_execution_engine": (
            record.envelope_candidate_is_action_execution_engine
        ),
        "envelope_candidate_is_write_authority": (
            record.envelope_candidate_is_write_authority
        ),
        "envelope_candidate_is_store_write": record.envelope_candidate_is_store_write,
        "envelope_candidate_mutates_filesystem": (
            record.envelope_candidate_mutates_filesystem
        ),
        "allow_envelope_candidate_is_execution": (
            record.allow_envelope_candidate_is_execution
        ),
        "deny_envelope_candidate_is_real_denial_response": (
            record.deny_envelope_candidate_is_real_denial_response
        ),
        "ask_envelope_candidate_is_user_prompt_implementation": (
            record.ask_envelope_candidate_is_user_prompt_implementation
        ),
        "defer_or_hold_envelope_candidate_preserves_safe_default": (
            record.defer_or_hold_envelope_candidate_preserves_safe_default
        ),
        "reported_only_is_judgment_basis": record.reported_only_is_judgment_basis,
        "not_checked_is_pass": record.not_checked_is_pass,
        "safe_default_changed": record.safe_default_changed,
        "hook_command_implemented": record.hook_command_implemented,
        "hook_installation_implemented": record.hook_installation_implemented,
        "claude_code_execution_performed": record.claude_code_execution_performed,
        "real_hook_response_emitted": record.real_hook_response_emitted,
        "stdout_stderr_hook_output_written": record.stdout_stderr_hook_output_written,
        "codex_implementation_added": record.codex_implementation_added,
        "provider_model_network_implemented": (
            record.provider_model_network_implemented
        ),
        "llm_call_implemented": record.llm_call_implemented,
        "api_key_env_secret_loading_implemented": (
            record.api_key_env_secret_loading_implemented
        ),
        "network_client_implemented": record.network_client_implemented,
        "process_execution_implemented": record.process_execution_implemented,
        "shell_execution_implemented": record.shell_execution_implemented,
        "action_execution_engine_implemented": (
            record.action_execution_engine_implemented
        ),
        "tool_runtime_implemented": record.tool_runtime_implemented,
        "write_authority_granted": record.write_authority_granted,
        "state_store_module_changed": record.state_store_module_changed,
        "filesystem_mutation_by_envelope": record.filesystem_mutation_by_envelope,
        "patch_application_implemented": record.patch_application_implemented,
        "public_release_performed": record.public_release_performed,
        "universal_prompt_injection_prevention_claimed": (
            record.universal_prompt_injection_prevention_claimed
        ),
        "sandbox_process_isolation_claimed": record.sandbox_process_isolation_claimed,
        "bash_safe_claimed": record.bash_safe_claimed,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    "ENVELOPE_HASH_ALGORITHM",
    "ENVELOPE_REDACTION_POLICY",
    "HOOK_RESPONSE_ENVELOPE_CANDIDATE_TYPES",
    "HookResponseEnvelopeCandidate",
    "PHASE11C_6_COMPLETE_LABEL",
    "PHASE11C_6_HOOK_RESPONSE_ENVELOPE_CANDIDATE_VERSION",
    "RESPONSE_ALLOW",
    "RESPONSE_ASK",
    "RESPONSE_DEFER",
    "RESPONSE_DENY",
    "RESPONSE_HOLD_CURRENT_STATE",
    "build_hook_response_envelope_candidate",
    "build_hook_response_envelope_candidate_contract_evidence",
    "hook_response_envelope_candidate_digest",
]
