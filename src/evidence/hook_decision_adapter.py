"""Phase 11-C-3 structured action to hook decision candidate adapter.

This module is contract-level only. It adapts inert Phase 11-C-2 structured
action candidates into generic hook decision candidates; it does not implement
a hook command, emit a substrate hook response, execute actions, or grant
authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from src.contracts import LOW, NOT_CHECKED, SAFE_DEFAULT
from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence.claude_code_tool_call_mapping import (
    BASH_NOT_CHECKED,
    DENY_CANDIDATE,
    EDIT_FILE,
    HOLD_CURRENT_STATE,
    HOLD_CURRENT_STATE_CANDIDATE,
    INVALID_TOOL_INPUT,
    NORMAL_REPO_PATH,
    PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
    READ_REPO,
    RUN_COMMAND,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    WRITE_FILE,
    ToolCallStructuredActionCandidate,
)

PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION = "phase11c_3_hook_decision_adapter_v0"
PHASE11C_3_COMPLETE_LABEL = (
    "PHASE11C_3_HOOK_DECISION_ADAPTER_COMPLETE_NOT_HOOK_RUNTIME"
)

ALLOW = "allow"
DENY = "deny"
ASK = "ask"
DEFER = "defer"
HOOK_DECISION_CANDIDATES = (ALLOW, DENY, ASK, DEFER)

HOOK_DECISION_CANDIDATE_ONLY = "HOOK_DECISION_CANDIDATE_ONLY"
INVALID_HOOK_DECISION_ADAPTER_INPUT = "INVALID_HOOK_DECISION_ADAPTER_INPUT"

_SOURCE_FALSE_INVARIANT_FIELDS = (
    "mapping_output_is_execution",
    "mapping_output_is_permission_decision",
    "mapping_output_is_hook_response",
    "mapping_output_grants_write_authority",
    "mapping_output_applies_patch",
    "hook_input_trusted_as_decision",
    "hook_input_trusted_as_capability_grant",
    "unsupported_unknown_or_not_checked_is_pass",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "hook_response_produced",
    "patch_application_performed",
)

_UNCERTAIN_RISK_STATUSES = frozenset(
    {
        BASH_NOT_CHECKED,
        UNKNOWN_TOOL,
        INVALID_TOOL_INPUT,
    }
)

_REPORTED_ONLY_KEYS = frozenset(
    {
        "reported_only",
        "report_only",
        "self_report",
        "self_reported",
        "self_reported_allow",
        "self_reported_decision",
    }
)

_ALLOW_CLAIM_KEYS = frozenset(
    {
        "allow",
        "allowed",
        "decision",
        "hook_decision",
        "hook_decision_candidate",
        "permission_decision",
        "self_reported_decision",
    }
)


@dataclass(frozen=True)
class HookDecisionCandidate:
    decision_candidate: str
    reasons: tuple[str, ...]
    source_tool_use_id: str | None
    action_id: str | None
    source_tool_name: str | None
    source_candidate_action_type: str | None
    source_candidate_status: str | None
    source_declared_risk: str | None
    source_risk_status: str | None
    source_contract_version: str | None
    source_provenance: Mapping[str, Any] = field(default_factory=dict)
    ignored_reported_only_fields: tuple[str, ...] = tuple()
    contract_version: str = PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION
    completion_label: str = PHASE11C_3_COMPLETE_LABEL
    candidate_status: str = HOOK_DECISION_CANDIDATE_ONLY
    safe_default: str = SAFE_DEFAULT
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    adapter_output_is_hook_decision_candidate_only: bool = True
    adapter_output_is_actual_hook_response: bool = False
    adapter_output_is_execution: bool = False
    adapter_output_is_action_execution_engine: bool = False
    adapter_output_grants_write_authority: bool = False
    adapter_output_applies_patch: bool = False
    adapter_output_mutates_filesystem: bool = False
    adapter_output_emits_real_hook_response: bool = False
    action_executed: bool = False
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    hook_response_produced: bool = False
    patch_application_performed: bool = False
    not_checked_is_allow: bool = False
    unsupported_unknown_or_not_checked_is_allow: bool = False
    reported_only_trusted_as_judgment_basis: bool = False

    def __post_init__(self) -> None:
        if self.decision_candidate not in HOOK_DECISION_CANDIDATES:
            raise ValueError("decision_candidate must be allow, deny, ask, or defer")
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(
            self,
            "ignored_reported_only_fields",
            tuple(self.ignored_reported_only_fields),
        )
        object.__setattr__(
            self,
            "source_provenance",
            _freeze_value(self.source_provenance),
        )


def adapt_structured_action_candidate_to_hook_decision_candidate(
    source_candidate: Any,
) -> HookDecisionCandidate:
    """Adapt an inert structured action candidate into an inert decision candidate."""

    if not isinstance(source_candidate, ToolCallStructuredActionCandidate):
        return _build_decision_candidate(
            None,
            DEFER,
            (
                "invalid_input_not_structured_action_candidate",
                "invalid_input_maps_to_defer_candidate",
                "safe_default_hold_current_state",
            ),
            ignored_reported_only_fields=tuple(),
        )

    ignored_reported_only_fields = _ignored_reported_only_fields(source_candidate)
    reported_only_reason = _reported_only_reason(ignored_reported_only_fields)
    invariant_rejections = _source_invariant_rejections(source_candidate)
    if invariant_rejections:
        return _build_decision_candidate(
            source_candidate,
            DEFER,
            (
                *invariant_rejections,
                *reported_only_reason,
                "source_invariant_violation_maps_to_defer_candidate",
                "safe_default_hold_current_state",
            ),
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    if source_candidate.candidate_status == DENY_CANDIDATE:
        return _build_decision_candidate(
            source_candidate,
            DENY,
            (
                "source_deny_candidate_maps_to_deny_candidate",
                *reported_only_reason,
            ),
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    if _source_is_not_checked_or_unknown(source_candidate):
        return _build_decision_candidate(
            source_candidate,
            DEFER,
            (
                "source_not_checked_or_unknown_maps_to_defer_candidate",
                "not_checked_unknown_or_unsupported_never_maps_to_allow",
                *reported_only_reason,
                "safe_default_hold_current_state",
            ),
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    if _normal_read_low_candidate(source_candidate):
        return _build_decision_candidate(
            source_candidate,
            ALLOW,
            (
                "read_repo_low_normal_structured_candidate_maps_to_allow_candidate",
                "allow_candidate_is_not_execution_or_hook_response",
                *reported_only_reason,
            ),
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    if _normal_write_or_edit_candidate(source_candidate):
        return _build_decision_candidate(
            source_candidate,
            ASK,
            (
                "write_or_edit_normal_repo_path_maps_to_ask_candidate",
                "write_or_edit_not_allowed_by_default",
                *reported_only_reason,
            ),
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    return _build_decision_candidate(
        source_candidate,
        DEFER,
        (
            "unsupported_candidate_shape_maps_to_defer_candidate",
            "unsupported_unknown_or_not_checked_never_maps_to_allow",
            *reported_only_reason,
            "safe_default_hold_current_state",
        ),
        ignored_reported_only_fields=ignored_reported_only_fields,
    )


def build_hook_decision_adapter_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
        "completion_label": PHASE11C_3_COMPLETE_LABEL,
        "source_contract_version": PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
        "generic_decision_candidates": HOOK_DECISION_CANDIDATES,
        "read_repo_low_normal_policy": ALLOW,
        "write_file_normal_policy": ASK,
        "edit_file_normal_policy": ASK,
        "deny_candidate_policy": DENY,
        "protected_path_deny_candidate_policy": DENY,
        "dangerous_bash_deny_candidate_policy": DENY,
        "run_command_hold_current_state_policy": DEFER,
        "unknown_unsupported_not_checked_policy": DEFER,
        "invalid_input_policy": DEFER,
        "reported_only_allow_ignored": True,
        "adapter_output_is_hook_decision_candidate_only": True,
        "adapter_output_is_actual_hook_response": False,
        "adapter_output_is_execution": False,
        "adapter_output_is_action_execution_engine": False,
        "adapter_output_grants_write_authority": False,
        "adapter_output_applies_patch": False,
        "adapter_output_mutates_filesystem": False,
        "adapter_output_emits_real_hook_response": False,
        "source_tool_use_id_and_action_id_provenance_preserved": True,
        "safe_default": SAFE_DEFAULT,
        "not_checked_is_allow": False,
        "unsupported_unknown_or_not_checked_is_allow": False,
        "reported_only_trusted_as_judgment_basis": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
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
        "filesystem_mutation_by_adapter": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _build_decision_candidate(
    source_candidate: ToolCallStructuredActionCandidate | None,
    decision_candidate: str,
    reasons: tuple[str, ...],
    *,
    ignored_reported_only_fields: tuple[str, ...],
) -> HookDecisionCandidate:
    if source_candidate is None:
        return HookDecisionCandidate(
            decision_candidate=decision_candidate,
            reasons=reasons,
            source_tool_use_id=None,
            action_id=None,
            source_tool_name=None,
            source_candidate_action_type=None,
            source_candidate_status=INVALID_HOOK_DECISION_ADAPTER_INPUT,
            source_declared_risk=NOT_CHECKED,
            source_risk_status=INVALID_HOOK_DECISION_ADAPTER_INPUT,
            source_contract_version=None,
            source_provenance={},
            ignored_reported_only_fields=ignored_reported_only_fields,
        )

    return HookDecisionCandidate(
        decision_candidate=decision_candidate,
        reasons=reasons,
        source_tool_use_id=source_candidate.source_tool_use_id,
        action_id=source_candidate.action_id,
        source_tool_name=source_candidate.source_tool_name,
        source_candidate_action_type=source_candidate.candidate_action_type,
        source_candidate_status=source_candidate.candidate_status,
        source_declared_risk=source_candidate.declared_risk,
        source_risk_status=source_candidate.risk_status,
        source_contract_version=source_candidate.contract_version,
        source_provenance=source_candidate.provenance,
        ignored_reported_only_fields=ignored_reported_only_fields,
    )


def _source_invariant_rejections(
    source_candidate: ToolCallStructuredActionCandidate,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not source_candidate.mapping_output_is_structured_action_candidate_only:
        reasons.append("source_not_structured_action_candidate_only")
    if source_candidate.safe_default != SAFE_DEFAULT:
        reasons.append("source_safe_default_mismatch")
    if source_candidate.decision != SAFE_DEFAULT:
        reasons.append("source_decision_promoted_from_safe_default")
    if source_candidate.live_executor_authority != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("source_live_executor_authority_not_on_hold")
    for field_name in _SOURCE_FALSE_INVARIANT_FIELDS:
        if getattr(source_candidate, field_name) is True:
            reasons.append(f"source_{field_name}_must_remain_false")
    return tuple(reasons)


def _source_is_not_checked_or_unknown(
    source_candidate: ToolCallStructuredActionCandidate,
) -> bool:
    return (
        source_candidate.candidate_status == HOLD_CURRENT_STATE_CANDIDATE
        or source_candidate.candidate_action_type == HOLD_CURRENT_STATE
        or source_candidate.candidate_action_type == RUN_COMMAND
        or source_candidate.declared_risk == NOT_CHECKED
        or source_candidate.risk_status in _UNCERTAIN_RISK_STATUSES
    )


def _normal_read_low_candidate(
    source_candidate: ToolCallStructuredActionCandidate,
) -> bool:
    return (
        source_candidate.candidate_action_type == READ_REPO
        and source_candidate.candidate_status == STRUCTURED_ACTION_CANDIDATE
        and source_candidate.declared_risk == LOW
        and source_candidate.risk_status == NORMAL_REPO_PATH
    )


def _normal_write_or_edit_candidate(
    source_candidate: ToolCallStructuredActionCandidate,
) -> bool:
    return (
        source_candidate.candidate_action_type in (WRITE_FILE, EDIT_FILE)
        and source_candidate.candidate_status == STRUCTURED_ACTION_CANDIDATE
        and source_candidate.declared_risk == LOW
        and source_candidate.risk_status == NORMAL_REPO_PATH
    )


def _reported_only_reason(
    ignored_reported_only_fields: tuple[str, ...],
) -> tuple[str, ...]:
    if ignored_reported_only_fields:
        return ("reported_only_or_self_reported_allow_ignored",)
    return tuple()


def _ignored_reported_only_fields(
    source_candidate: ToolCallStructuredActionCandidate,
) -> tuple[str, ...]:
    ignored: list[str] = []
    for root_name, value in (
        ("payload", source_candidate.payload),
        ("provenance", source_candidate.provenance),
        ("target_scope", source_candidate.target_scope),
    ):
        ignored.extend(_walk_reported_only(root_name, value, reported_context=False))
    return tuple(sorted(set(ignored)))


def _walk_reported_only(
    path: str,
    value: Any,
    *,
    reported_context: bool,
) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        found: list[str] = []
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.lower()
            nested_path = f"{path}.{key_text}"
            nested_reported_context = (
                reported_context
                or normalized_key in _REPORTED_ONLY_KEYS
                or "reported_only" in normalized_key
                or "self_report" in normalized_key
            )
            if nested_reported_context and _is_allow_claim(normalized_key, nested):
                found.append(nested_path)
            found.extend(
                _walk_reported_only(
                    nested_path,
                    nested,
                    reported_context=nested_reported_context,
                )
            )
        return tuple(found)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        found = []
        for index, nested in enumerate(value):
            found.extend(
                _walk_reported_only(
                    f"{path}[{index}]",
                    nested,
                    reported_context=reported_context,
                )
            )
        return tuple(found)
    return tuple()


def _is_allow_claim(normalized_key: str, value: Any) -> bool:
    if normalized_key not in _ALLOW_CLAIM_KEYS:
        return False
    if isinstance(value, str):
        return value.strip().lower() == ALLOW
    if isinstance(value, bool):
        return value is True
    return False


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
