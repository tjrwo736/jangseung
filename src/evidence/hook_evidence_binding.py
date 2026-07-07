"""Phase 11-C-4 hook evidence binding.

This module binds Phase 11-C hook input, structured action candidates, and
hook decision candidates into an inert evidence record. It does not implement
a hook command, emit a substrate hook response, execute actions, grant
authority, or write runtime state.
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
    ClaudeCodePreToolUseInput,
    PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
)
from src.evidence.claude_code_tool_call_mapping import (
    PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
    ToolCallStructuredActionCandidate,
)
from src.evidence.hook_decision_adapter import (
    HookDecisionCandidate,
    PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
)

PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION = "phase11c_4_hook_evidence_binding_v0"
PHASE11C_4_COMPLETE_LABEL = (
    "PHASE11C_4_HOOK_EVIDENCE_BINDING_COMPLETE_NOT_HOOK_RUNTIME"
)

HOOK_EVIDENCE_BOUND = "HOOK_EVIDENCE_BOUND"
HOOK_EVIDENCE_BINDING_REJECTED = "HOOK_EVIDENCE_BINDING_REJECTED"
TOOL_INPUT_HASH_ALGORITHM = "sha256_canonical_json_v0"
TOOL_INPUT_REDACTION_POLICY = "fingerprint_only_redact_secret_like_values_v0"

_SECRET_KEY_MARKERS = frozenset(
    {
        ".env",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "bearer",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
)

_SECRET_VALUE_MARKERS = frozenset(
    {
        "api_key=",
        "apikey=",
        "authorization:",
        "bearer ",
        "password=",
        "private_key",
        "secret=",
        "token=",
    }
)

_SOURCE_FALSE_INVARIANT_FIELDS = (
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
)

_ACTION_FALSE_INVARIANT_FIELDS = (
    "mapping_output_is_execution",
    "mapping_output_is_permission_decision",
    "mapping_output_is_hook_response",
    "mapping_output_grants_write_authority",
    "mapping_output_applies_patch",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "hook_response_produced",
    "patch_application_performed",
)

_DECISION_FALSE_INVARIANT_FIELDS = (
    "adapter_output_is_actual_hook_response",
    "adapter_output_is_execution",
    "adapter_output_is_action_execution_engine",
    "adapter_output_grants_write_authority",
    "adapter_output_applies_patch",
    "adapter_output_mutates_filesystem",
    "adapter_output_emits_real_hook_response",
    "action_executed",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "hook_response_produced",
    "patch_application_performed",
    "not_checked_is_allow",
    "unsupported_unknown_or_not_checked_is_allow",
    "reported_only_trusted_as_judgment_basis",
)


@dataclass(frozen=True)
class HookEvidenceBinding:
    binding_id: str
    binding_hash: str
    binding_version: str
    completion_label: str
    binding_status: str
    binding_reasons: tuple[str, ...]
    tool_name: str
    tool_use_id: str
    tool_input_hash: str
    tool_input_hash_algorithm: str
    tool_input_redaction_policy: str
    tool_input_raw_stored: bool
    tool_input_redacted_metadata: Mapping[str, Any]
    source_tool_use_id: str
    action_id: str
    candidate_action_type: str
    candidate_status: str
    decision_candidate: str
    decision_candidate_status: str
    decision_reasons: tuple[str, ...]
    declared_risk: str
    risk_status: str
    capability_requirements: tuple[str, ...]
    target_scope_hash: str
    target_scope_redacted_metadata: Mapping[str, Any]
    payload_hash: str
    payload_redacted_metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]
    safe_default: str
    live_executor_authority: str
    trust_boundary: str
    evidence_binding_is_judgment_basis: bool = False
    evidence_binding_is_execution: bool = False
    evidence_binding_is_hook_response: bool = False
    evidence_binding_is_write_authority: bool = False
    evidence_binding_is_store_write: bool = False
    evidence_binding_mutates_filesystem: bool = False
    reported_only_trusted_as_judgment_basis: bool = False
    reported_only_is_judgment_basis: bool = False
    not_checked_is_pass: bool = False
    safe_default_changed: bool = False
    hook_command_implemented: bool = False
    hook_installation_implemented: bool = False
    claude_code_execution_performed: bool = False
    real_hook_response_emitted: bool = False
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
    filesystem_mutation_by_binding: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "binding_reasons", tuple(self.binding_reasons))
        object.__setattr__(self, "decision_reasons", tuple(self.decision_reasons))
        object.__setattr__(
            self,
            "capability_requirements",
            tuple(self.capability_requirements),
        )
        object.__setattr__(
            self,
            "tool_input_redacted_metadata",
            _freeze_value(self.tool_input_redacted_metadata),
        )
        object.__setattr__(
            self,
            "target_scope_redacted_metadata",
            _freeze_value(self.target_scope_redacted_metadata),
        )
        object.__setattr__(
            self,
            "payload_redacted_metadata",
            _freeze_value(self.payload_redacted_metadata),
        )
        object.__setattr__(self, "provenance", _freeze_value(self.provenance))

    def to_record(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "binding_hash": self.binding_hash,
            **_plain_json_data(_hook_evidence_binding_payload(self)),
        }


def build_hook_evidence_binding(
    *,
    hook_input: ClaudeCodePreToolUseInput,
    action_candidate: ToolCallStructuredActionCandidate,
    decision_candidate: HookDecisionCandidate,
) -> HookEvidenceBinding:
    """Bind hook input and candidate objects into a secret-safe evidence record."""

    if not isinstance(hook_input, ClaudeCodePreToolUseInput):
        raise TypeError("hook_input must be ClaudeCodePreToolUseInput")
    if not isinstance(action_candidate, ToolCallStructuredActionCandidate):
        raise TypeError("action_candidate must be ToolCallStructuredActionCandidate")
    if not isinstance(decision_candidate, HookDecisionCandidate):
        raise TypeError("decision_candidate must be HookDecisionCandidate")

    rejection_reasons = _binding_rejection_reasons(
        hook_input=hook_input,
        action_candidate=action_candidate,
        decision_candidate=decision_candidate,
    )
    binding_status = (
        HOOK_EVIDENCE_BINDING_REJECTED if rejection_reasons else HOOK_EVIDENCE_BOUND
    )
    binding_reasons = (
        *rejection_reasons,
        "hook_input_structured_action_and_decision_candidate_evidence_bound",
        "raw_tool_input_omitted_by_default",
        "tool_input_hash_bound",
        "binding_is_not_judgment_basis_execution_hook_response_or_write_authority",
        "safe_default_hold_current_state",
    )

    payload = {
        "binding_version": PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
        "completion_label": PHASE11C_4_COMPLETE_LABEL,
        "binding_status": binding_status,
        "binding_reasons": binding_reasons,
        "tool_name": hook_input.tool_name,
        "tool_use_id": hook_input.tool_use_id,
        "tool_input_hash": hash_hook_tool_input(hook_input.tool_input),
        "tool_input_hash_algorithm": TOOL_INPUT_HASH_ALGORITHM,
        "tool_input_redaction_policy": TOOL_INPUT_REDACTION_POLICY,
        "tool_input_raw_stored": False,
        "tool_input_redacted_metadata": build_redacted_value_metadata(
            hook_input.tool_input
        ),
        "source_tool_use_id": action_candidate.source_tool_use_id,
        "action_id": action_candidate.action_id,
        "candidate_action_type": action_candidate.candidate_action_type,
        "candidate_status": action_candidate.candidate_status,
        "decision_candidate": decision_candidate.decision_candidate,
        "decision_candidate_status": decision_candidate.candidate_status,
        "decision_reasons": decision_candidate.reasons,
        "declared_risk": action_candidate.declared_risk,
        "risk_status": action_candidate.risk_status,
        "capability_requirements": action_candidate.capability_requirements,
        "target_scope_hash": _sha256_json(action_candidate.target_scope),
        "target_scope_redacted_metadata": build_redacted_value_metadata(
            action_candidate.target_scope
        ),
        "payload_hash": _sha256_json(action_candidate.payload),
        "payload_redacted_metadata": build_redacted_value_metadata(
            action_candidate.payload
        ),
        "provenance": _binding_provenance(
            hook_input=hook_input,
            action_candidate=action_candidate,
            decision_candidate=decision_candidate,
        ),
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "evidence_binding_is_judgment_basis": False,
        "evidence_binding_is_execution": False,
        "evidence_binding_is_hook_response": False,
        "evidence_binding_is_write_authority": False,
        "evidence_binding_is_store_write": False,
        "evidence_binding_mutates_filesystem": False,
        "reported_only_trusted_as_judgment_basis": False,
        "reported_only_is_judgment_basis": False,
        "not_checked_is_pass": False,
        "safe_default_changed": False,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
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
        "filesystem_mutation_by_binding": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }
    binding_hash = _sha256_json(payload)
    return HookEvidenceBinding(
        binding_id=f"phase11c-4-hook-evidence:{binding_hash}",
        binding_hash=binding_hash,
        **payload,
    )


def hash_hook_tool_input(tool_input: Mapping[str, Any]) -> str:
    """Return the deterministic raw-input digest without retaining raw input."""

    return _sha256_json(tool_input)


def hook_evidence_binding_digest(record: HookEvidenceBinding) -> str:
    """Recompute the deterministic digest for a hook evidence binding record."""

    return _sha256_json(_hook_evidence_binding_payload(record))


def build_hook_evidence_binding_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
        "completion_label": PHASE11C_4_COMPLETE_LABEL,
        "source_contract_versions": {
            "hook_input": PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
            "structured_action_candidate": PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
            "hook_decision_candidate": PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
        },
        "required_bound_fields": (
            "tool_name",
            "tool_use_id",
            "tool_input_hash",
            "source_tool_use_id",
            "action_id",
            "candidate_action_type",
            "candidate_status",
            "decision_candidate",
            "decision_reasons",
            "declared_risk",
            "risk_status",
            "capability_requirements",
            "provenance",
            "safe_default",
            "live_executor_authority",
            "trust_boundary",
        ),
        "tool_input_hash_algorithm": TOOL_INPUT_HASH_ALGORITHM,
        "tool_input_redaction_policy": TOOL_INPUT_REDACTION_POLICY,
        "raw_tool_input_stored_by_default": False,
        "secret_like_values_redacted": True,
        "env_api_key_token_secret_like_values_redacted": True,
        "preserves_metadata_without_raw_secret_retention": True,
        "evidence_binding_is_judgment_basis": False,
        "evidence_binding_is_execution": False,
        "evidence_binding_is_hook_response": False,
        "evidence_binding_is_write_authority": False,
        "evidence_binding_is_store_write": False,
        "evidence_binding_mutates_filesystem": False,
        "reported_only_is_judgment_basis": False,
        "not_checked_is_pass": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
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
        "filesystem_mutation_by_binding": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def build_redacted_value_metadata(value: Any) -> dict[str, Any]:
    plain = _plain_json_data(value)
    paths: list[str] = []
    redacted_paths: list[str] = []
    secret_like_paths: list[str] = []
    raw_omitted_paths: list[str] = []
    value_kinds: dict[str, str] = {}
    string_fingerprints: dict[str, Mapping[str, Any]] = {}
    preview = _metadata_preview(
        plain,
        path="",
        paths=paths,
        redacted_paths=redacted_paths,
        secret_like_paths=secret_like_paths,
        raw_omitted_paths=raw_omitted_paths,
        value_kinds=value_kinds,
        string_fingerprints=string_fingerprints,
    )
    return {
        "metadata_version": TOOL_INPUT_REDACTION_POLICY,
        "raw_values_stored": False,
        "field_paths": tuple(sorted(paths)),
        "value_kinds": dict(sorted(value_kinds.items())),
        "raw_omitted_paths": tuple(sorted(raw_omitted_paths)),
        "redacted_paths": tuple(sorted(redacted_paths)),
        "secret_like_paths": tuple(sorted(secret_like_paths)),
        "string_fingerprints": dict(sorted(string_fingerprints.items())),
        "preview": preview,
    }


def _binding_rejection_reasons(
    *,
    hook_input: ClaudeCodePreToolUseInput,
    action_candidate: ToolCallStructuredActionCandidate,
    decision_candidate: HookDecisionCandidate,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if action_candidate.source_tool_name != hook_input.tool_name:
        reasons.append("source_tool_name_mismatch")
    if action_candidate.source_tool_use_id != hook_input.tool_use_id:
        reasons.append("source_tool_use_id_mismatch")
    if action_candidate.action_id != f"pretooluse:{hook_input.tool_use_id}":
        reasons.append("action_id_mismatch")
    if decision_candidate.source_tool_use_id != action_candidate.source_tool_use_id:
        reasons.append("decision_source_tool_use_id_mismatch")
    if decision_candidate.action_id != action_candidate.action_id:
        reasons.append("decision_action_id_mismatch")
    if (
        decision_candidate.source_candidate_action_type
        != action_candidate.candidate_action_type
    ):
        reasons.append("decision_candidate_action_type_mismatch")
    if decision_candidate.source_candidate_status != action_candidate.candidate_status:
        reasons.append("decision_candidate_status_mismatch")
    if hook_input.safe_default != SAFE_DEFAULT:
        reasons.append("hook_input_safe_default_mismatch")
    if action_candidate.safe_default != SAFE_DEFAULT:
        reasons.append("action_candidate_safe_default_mismatch")
    if decision_candidate.safe_default != SAFE_DEFAULT:
        reasons.append("decision_candidate_safe_default_mismatch")
    if hook_input.live_executor_authority != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("hook_input_live_executor_authority_not_on_hold")
    if action_candidate.live_executor_authority != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("action_candidate_live_executor_authority_not_on_hold")
    if decision_candidate.live_executor_authority != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("decision_candidate_live_executor_authority_not_on_hold")
    for field_name in _SOURCE_FALSE_INVARIANT_FIELDS:
        if getattr(hook_input, field_name) is True:
            reasons.append(f"hook_input_{field_name}_must_remain_false")
    for field_name in _ACTION_FALSE_INVARIANT_FIELDS:
        if getattr(action_candidate, field_name) is True:
            reasons.append(f"action_candidate_{field_name}_must_remain_false")
    for field_name in _DECISION_FALSE_INVARIANT_FIELDS:
        if getattr(decision_candidate, field_name) is True:
            reasons.append(f"decision_candidate_{field_name}_must_remain_false")
    return tuple(reasons)


def _binding_provenance(
    *,
    hook_input: ClaudeCodePreToolUseInput,
    action_candidate: ToolCallStructuredActionCandidate,
    decision_candidate: HookDecisionCandidate,
) -> dict[str, Any]:
    hook_metadata = {
        field_name: getattr(hook_input, field_name)
        for field_name in (
            "cwd",
            "session_id",
            "transcript_path",
            "substrate_name",
            "substrate_version",
            "project_root",
            "timestamp",
        )
        if getattr(hook_input, field_name) is not None
    }
    return {
        "hook_input": {
            "contract_version": hook_input.contract_version,
            "tool_name": hook_input.tool_name,
            "tool_use_id": hook_input.tool_use_id,
            "tool_input_hash": hash_hook_tool_input(hook_input.tool_input),
            "tool_input_raw_stored": False,
            "substrate_target": hook_input.substrate_target,
            "trust_boundary": hook_input.trust_boundary,
            "metadata": build_redacted_value_metadata(hook_metadata),
            "extra_untrusted_fields": build_redacted_value_metadata(
                hook_input.extra_untrusted_fields
            ),
        },
        "structured_action_candidate": {
            "contract_version": action_candidate.contract_version,
            "source_contract_version": action_candidate.source_contract_version,
            "source_tool_name": action_candidate.source_tool_name,
            "source_tool_use_id": action_candidate.source_tool_use_id,
            "action_id": action_candidate.action_id,
            "candidate_action_type": action_candidate.candidate_action_type,
            "candidate_status": action_candidate.candidate_status,
            "provenance": build_redacted_value_metadata(action_candidate.provenance),
        },
        "hook_decision_candidate": {
            "contract_version": decision_candidate.contract_version,
            "source_contract_version": decision_candidate.source_contract_version,
            "source_tool_use_id": decision_candidate.source_tool_use_id,
            "action_id": decision_candidate.action_id,
            "decision_candidate": decision_candidate.decision_candidate,
            "decision_candidate_status": decision_candidate.candidate_status,
            "source_provenance": build_redacted_value_metadata(
                decision_candidate.source_provenance
            ),
            "ignored_reported_only_fields": decision_candidate.ignored_reported_only_fields,
        },
    }


def _metadata_preview(
    value: Any,
    *,
    path: str,
    paths: list[str],
    redacted_paths: list[str],
    secret_like_paths: list[str],
    raw_omitted_paths: list[str],
    value_kinds: dict[str, str],
    string_fingerprints: dict[str, Mapping[str, Any]],
) -> Any:
    current_path = path or "$"
    if isinstance(value, Mapping):
        paths.append(current_path)
        value_kinds[current_path] = "mapping"
        return {
            str(key): _metadata_preview(
                nested,
                path=_join_path(path, str(key)),
                paths=paths,
                redacted_paths=redacted_paths,
                secret_like_paths=secret_like_paths,
                raw_omitted_paths=raw_omitted_paths,
                value_kinds=value_kinds,
                string_fingerprints=string_fingerprints,
            )
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if _is_sequence(value):
        paths.append(current_path)
        value_kinds[current_path] = "sequence"
        return tuple(
            _metadata_preview(
                nested,
                path=f"{current_path}[{index}]",
                paths=paths,
                redacted_paths=redacted_paths,
                secret_like_paths=secret_like_paths,
                raw_omitted_paths=raw_omitted_paths,
                value_kinds=value_kinds,
                string_fingerprints=string_fingerprints,
            )
            for index, nested in enumerate(value)
        )
    paths.append(current_path)
    raw_omitted_paths.append(current_path)
    kind = _value_kind(value)
    value_kinds[current_path] = kind
    if isinstance(value, str):
        secret_like = _is_secret_like(current_path, value)
        if secret_like:
            redacted_paths.append(current_path)
            secret_like_paths.append(current_path)
        fingerprint = {
            "kind": kind,
            "length": len(value),
            "sha256": _sha256_text(value),
            "raw_value_stored": False,
            "redacted": secret_like,
        }
        string_fingerprints[current_path] = fingerprint
        return fingerprint
    return {"kind": kind, "raw_value_stored": False}


def _is_secret_like(path: str, value: str) -> bool:
    normalized_path = path.lower()
    normalized_value = value.strip().lower()
    if any(marker in normalized_path for marker in _SECRET_KEY_MARKERS):
        return True
    if any(marker in normalized_value for marker in _SECRET_VALUE_MARKERS):
        return True
    if normalized_value.startswith(("sk-", "sk_proj_", "sk-proj-")):
        return True
    if _looks_like_env_path(normalized_value):
        return True
    return False


def _looks_like_env_path(value: str) -> bool:
    parts = _path_parts(value)
    return any(part == ".env" or part.startswith(".env.") for part in parts)


def _path_parts(value: str) -> tuple[str, ...]:
    parts: list[str] = []
    current: list[str] = []
    for character in value:
        if character in ("/", "\\"):
            if current:
                parts.append("".join(current))
                current = []
            continue
        current.append(character)
    if current:
        parts.append("".join(current))
    return tuple(part for part in parts if part)


def _join_path(parent: str, key: str) -> str:
    if not parent:
        return key
    return f"{parent}.{key}"


def _value_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return type(value).__name__


def _hook_evidence_binding_payload(record: HookEvidenceBinding) -> dict[str, Any]:
    return {
        "binding_version": record.binding_version,
        "completion_label": record.completion_label,
        "binding_status": record.binding_status,
        "binding_reasons": record.binding_reasons,
        "tool_name": record.tool_name,
        "tool_use_id": record.tool_use_id,
        "tool_input_hash": record.tool_input_hash,
        "tool_input_hash_algorithm": record.tool_input_hash_algorithm,
        "tool_input_redaction_policy": record.tool_input_redaction_policy,
        "tool_input_raw_stored": record.tool_input_raw_stored,
        "tool_input_redacted_metadata": record.tool_input_redacted_metadata,
        "source_tool_use_id": record.source_tool_use_id,
        "action_id": record.action_id,
        "candidate_action_type": record.candidate_action_type,
        "candidate_status": record.candidate_status,
        "decision_candidate": record.decision_candidate,
        "decision_candidate_status": record.decision_candidate_status,
        "decision_reasons": record.decision_reasons,
        "declared_risk": record.declared_risk,
        "risk_status": record.risk_status,
        "capability_requirements": record.capability_requirements,
        "target_scope_hash": record.target_scope_hash,
        "target_scope_redacted_metadata": record.target_scope_redacted_metadata,
        "payload_hash": record.payload_hash,
        "payload_redacted_metadata": record.payload_redacted_metadata,
        "provenance": record.provenance,
        "safe_default": record.safe_default,
        "live_executor_authority": record.live_executor_authority,
        "trust_boundary": record.trust_boundary,
        "evidence_binding_is_judgment_basis": record.evidence_binding_is_judgment_basis,
        "evidence_binding_is_execution": record.evidence_binding_is_execution,
        "evidence_binding_is_hook_response": record.evidence_binding_is_hook_response,
        "evidence_binding_is_write_authority": record.evidence_binding_is_write_authority,
        "evidence_binding_is_store_write": record.evidence_binding_is_store_write,
        "evidence_binding_mutates_filesystem": record.evidence_binding_mutates_filesystem,
        "reported_only_trusted_as_judgment_basis": (
            record.reported_only_trusted_as_judgment_basis
        ),
        "reported_only_is_judgment_basis": record.reported_only_is_judgment_basis,
        "not_checked_is_pass": record.not_checked_is_pass,
        "safe_default_changed": record.safe_default_changed,
        "hook_command_implemented": record.hook_command_implemented,
        "hook_installation_implemented": record.hook_installation_implemented,
        "claude_code_execution_performed": record.claude_code_execution_performed,
        "real_hook_response_emitted": record.real_hook_response_emitted,
        "codex_implementation_added": record.codex_implementation_added,
        "provider_model_network_implemented": record.provider_model_network_implemented,
        "llm_call_implemented": record.llm_call_implemented,
        "api_key_env_secret_loading_implemented": (
            record.api_key_env_secret_loading_implemented
        ),
        "network_client_implemented": record.network_client_implemented,
        "process_execution_implemented": record.process_execution_implemented,
        "shell_execution_implemented": record.shell_execution_implemented,
        "action_execution_engine_implemented": record.action_execution_engine_implemented,
        "tool_runtime_implemented": record.tool_runtime_implemented,
        "write_authority_granted": record.write_authority_granted,
        "state_store_module_changed": record.state_store_module_changed,
        "filesystem_mutation_by_binding": record.filesystem_mutation_by_binding,
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


__all__ = [
    "HOOK_EVIDENCE_BINDING_REJECTED",
    "HOOK_EVIDENCE_BOUND",
    "HookEvidenceBinding",
    "PHASE11C_4_COMPLETE_LABEL",
    "PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION",
    "TOOL_INPUT_HASH_ALGORITHM",
    "TOOL_INPUT_REDACTION_POLICY",
    "build_hook_evidence_binding",
    "build_hook_evidence_binding_contract_evidence",
    "build_redacted_value_metadata",
    "hash_hook_tool_input",
    "hook_evidence_binding_digest",
]
