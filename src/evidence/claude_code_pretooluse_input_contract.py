"""Phase 11-C-1 Claude Code PreToolUse input contract.

This module is contract-level only. It validates raw hook input shape and
records trust-boundary metadata; it does not implement a hook command or tool
runtime.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, NOT_CHECKED, SAFE_DEFAULT

PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION = (
    "phase11c_1_claude_code_pretooluse_input_contract_v0"
)
PHASE11C_1_COMPLETE_LABEL = (
    "PHASE11C_1_CLAUDE_CODE_PRETOOLUSE_INPUT_CONTRACT_COMPLETE_NOT_HOOK_RUNTIME"
)

UNTRUSTED_RAW_EXECUTOR_OUTPUT = "untrusted_raw_executor_output"
CLAUDE_CODE_PRETOOLUSE = "Claude Code PreToolUse"

REQUIRED_HOOK_INPUT_FIELDS = ("tool_name", "tool_input", "tool_use_id")
OPTIONAL_HOOK_METADATA_FIELDS = (
    "cwd",
    "session_id",
    "transcript_path",
    "substrate_name",
    "substrate_version",
    "project_root",
    "timestamp",
)
SUPPORTED_INITIAL_TARGET_TOOLS = (
    "Bash",
    "Write",
    "Edit",
    "Read",
    "PowerShell",
    "apply_patch",
)

VALID_PRETOOLUSE_INPUT_CONTRACT = "VALID_PRETOOLUSE_INPUT_CONTRACT"
INVALID_PRETOOLUSE_INPUT_CONTRACT = "INVALID_PRETOOLUSE_INPUT_CONTRACT"
SUPPORTED_INITIAL_TARGET = "SUPPORTED_INITIAL_TARGET"
UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED = "UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED"
HOOK_COVERAGE_REPORT_UNTRUSTED = "HOOK_COVERAGE_REPORT_UNTRUSTED"

_EXPLICIT_NOT_PASS_STATUSES = frozenset(
    {
        "UNSUPPORTED",
        "UNKNOWN",
        NOT_CHECKED,
        UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED,
    }
)


@dataclass(frozen=True)
class ClaudeCodePreToolUseInput:
    tool_name: str
    tool_input: Mapping[str, Any]
    tool_use_id: str
    cwd: str | None = None
    session_id: str | None = None
    transcript_path: str | None = None
    substrate_name: str | None = None
    substrate_version: str | None = None
    project_root: str | None = None
    timestamp: str | None = None
    extra_untrusted_fields: Mapping[str, Any] = field(default_factory=dict)
    contract_version: str = PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION
    substrate_target: str = CLAUDE_CODE_PRETOOLUSE
    trust_boundary: str = UNTRUSTED_RAW_EXECUTOR_OUTPUT
    hook_input_trusted_as_decision: bool = False
    hook_input_trusted_as_capability_grant: bool = False
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_input", _freeze_value(self.tool_input))
        object.__setattr__(
            self,
            "extra_untrusted_fields",
            _freeze_value(self.extra_untrusted_fields),
        )


@dataclass(frozen=True)
class PreToolUseInputValidationResult:
    valid: bool
    status: str
    reasons: tuple[str, ...]
    hook_input: ClaudeCodePreToolUseInput | None
    tool_support_status: str = UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED
    ignored_untrusted_fields: tuple[str, ...] = tuple()
    decision: str = SAFE_DEFAULT
    safe_default: str = SAFE_DEFAULT
    hook_input_trusted_as_decision: bool = False
    hook_input_trusted_as_capability_grant: bool = False
    hook_coverage_report_is_coverage_proof: bool = False
    unsupported_unknown_or_not_checked_is_pass: bool = False
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(
            self,
            "ignored_untrusted_fields",
            tuple(self.ignored_untrusted_fields),
        )


@dataclass(frozen=True)
class HookCoverageReportAssessment:
    report_status: str
    report_status_known: bool
    reasons: tuple[str, ...]
    assessment_status: str = HOOK_COVERAGE_REPORT_UNTRUSTED
    report_is_coverage_proof: bool = False
    pass_accepted: bool = False
    unsupported_unknown_or_not_checked_is_pass: bool = False
    decision: str = SAFE_DEFAULT
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))


def validate_claude_code_pretooluse_input(
    raw_hook_input: Mapping[str, Any],
) -> PreToolUseInputValidationResult:
    """Validate untrusted Claude Code PreToolUse input shape only."""

    if not isinstance(raw_hook_input, Mapping):
        return _invalid_result(
            ("raw_hook_input_must_be_mapping",),
            ignored_untrusted_fields=tuple(),
        )

    try:
        parsed = _clone_json_data(raw_hook_input)
    except TypeError as exc:
        return _invalid_result(
            (f"raw_hook_input_contains_unsupported_contract_value:{exc}",),
            ignored_untrusted_fields=tuple(),
        )

    reasons: list[str] = []
    for field_name in REQUIRED_HOOK_INPUT_FIELDS:
        if field_name not in parsed:
            reasons.append(f"missing_required_field:{field_name}")

    tool_name = parsed.get("tool_name")
    tool_input = parsed.get("tool_input")
    tool_use_id = parsed.get("tool_use_id")

    if "tool_name" in parsed and (
        not isinstance(tool_name, str) or not tool_name.strip()
    ):
        reasons.append("invalid_required_field:tool_name_must_be_non_empty_string")
    if "tool_input" in parsed and not isinstance(tool_input, Mapping):
        reasons.append("invalid_required_field:tool_input_must_be_mapping")
    if "tool_use_id" in parsed and (
        not isinstance(tool_use_id, str) or not tool_use_id.strip()
    ):
        reasons.append("invalid_required_field:tool_use_id_must_be_non_empty_string")

    tool_support_status = _tool_support_status(tool_name)
    if (
        isinstance(tool_name, str)
        and tool_name.strip()
        and tool_support_status != SUPPORTED_INITIAL_TARGET
    ):
        reasons.append(f"unsupported_or_unknown_tool_name:{tool_name}")

    for field_name in OPTIONAL_HOOK_METADATA_FIELDS:
        if field_name in parsed and parsed[field_name] is not None:
            if not isinstance(parsed[field_name], str) or not parsed[field_name].strip():
                reasons.append(
                    f"invalid_optional_metadata_field:{field_name}_must_be_string"
                )

    extra_fields = _extra_untrusted_fields(parsed)
    ignored_untrusted_fields = tuple(sorted(extra_fields))

    if reasons:
        return _invalid_result(
            tuple(reasons),
            tool_support_status=tool_support_status,
            ignored_untrusted_fields=ignored_untrusted_fields,
        )

    hook_input = ClaudeCodePreToolUseInput(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_use_id=tool_use_id,
        cwd=parsed.get("cwd"),
        session_id=parsed.get("session_id"),
        transcript_path=parsed.get("transcript_path"),
        substrate_name=parsed.get("substrate_name"),
        substrate_version=parsed.get("substrate_version"),
        project_root=parsed.get("project_root"),
        timestamp=parsed.get("timestamp"),
        extra_untrusted_fields=extra_fields,
    )

    return PreToolUseInputValidationResult(
        valid=True,
        status=VALID_PRETOOLUSE_INPUT_CONTRACT,
        reasons=("contract_shape_valid_authority_not_granted",),
        hook_input=hook_input,
        tool_support_status=SUPPORTED_INITIAL_TARGET,
        ignored_untrusted_fields=ignored_untrusted_fields,
    )


def assess_hook_coverage_report(report_status: Any) -> HookCoverageReportAssessment:
    """Classify a substrate coverage report as untrusted, never proof."""

    if isinstance(report_status, str) and report_status.strip():
        normalized = report_status.strip()
        known = normalized in (
            SUPPORTED_INITIAL_TARGET,
            *_EXPLICIT_NOT_PASS_STATUSES,
        )
    else:
        normalized = "UNKNOWN"
        known = False

    reasons = ["hook_coverage_report_is_not_coverage_proof"]
    if normalized in _EXPLICIT_NOT_PASS_STATUSES or not known:
        reasons.append("unsupported_unknown_or_not_checked_is_not_pass")
    else:
        reasons.append("supported_initial_target_report_is_still_not_proof")

    return HookCoverageReportAssessment(
        report_status=normalized,
        report_status_known=known,
        reasons=tuple(reasons),
    )


def build_claude_code_pretooluse_input_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
        "completion_label": PHASE11C_1_COMPLETE_LABEL,
        "substrate_target": CLAUDE_CODE_PRETOOLUSE,
        "required_fields": REQUIRED_HOOK_INPUT_FIELDS,
        "optional_metadata_fields": OPTIONAL_HOOK_METADATA_FIELDS,
        "supported_initial_tools": SUPPORTED_INITIAL_TARGET_TOOLS,
        "codex_apply_patch_tool_call_supported": True,
        "hook_input_trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "hook_input_trusted_as_decision": False,
        "hook_input_trusted_as_capability_grant": False,
        "hook_coverage_report_is_coverage_proof": False,
        "unsupported_unknown_or_not_checked_is_pass": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "codex_implementation_added": False,
        "provider_model_network_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "network_client_implemented": False,
        "action_execution_engine_implemented": False,
        "tool_runtime_implemented": False,
        "write_authority_granted": False,
        "filesystem_mutation_by_contract_validation": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "safe_default_changed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _invalid_result(
    reasons: tuple[str, ...],
    *,
    tool_support_status: str = UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED,
    ignored_untrusted_fields: tuple[str, ...],
) -> PreToolUseInputValidationResult:
    return PreToolUseInputValidationResult(
        valid=False,
        status=INVALID_PRETOOLUSE_INPUT_CONTRACT,
        reasons=reasons,
        hook_input=None,
        tool_support_status=tool_support_status,
        ignored_untrusted_fields=ignored_untrusted_fields,
    )


def _tool_support_status(tool_name: Any) -> str:
    if tool_name in SUPPORTED_INITIAL_TARGET_TOOLS:
        return SUPPORTED_INITIAL_TARGET
    return UNSUPPORTED_UNKNOWN_OR_NOT_CHECKED


def _extra_untrusted_fields(parsed: Mapping[str, Any]) -> dict[str, Any]:
    contract_fields = frozenset(
        (*REQUIRED_HOOK_INPUT_FIELDS, *OPTIONAL_HOOK_METADATA_FIELDS)
    )
    return {
        str(field_name): _clone_json_data(value)
        for field_name, value in parsed.items()
        if field_name not in contract_fields
    }


def _clone_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_data(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_clone_json_data(nested) for nested in value]
    if isinstance(value, tuple):
        return [_clone_json_data(nested) for nested in value]
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
