"""Phase 11-B-1c structured action capability gate.

This module evaluates capability authorization for already-structured executor
action data. It is import-safe and result-only: it does not execute actions,
read files, write files, spawn processes, call providers, or use the network.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, REPORTED_ONLY, SAFE_DEFAULT
from src.evidence.structured_actions import (
    ACTION_CAPABILITY_MAPPING,
    ALLOWED_UNDER_POLICY,
    DENIED,
    DIRECT_LEDGER_APPEND,
    DIRECT_STORE_WRITE,
    EVAL_EXEC,
    FORBIDDEN_ACTION_TYPE_REJECTED,
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    FUTURE_GATED,
    FUTURE_GATE_REQUIRED,
    IMPORT_MODULE,
    INVALID_ACTION_SCHEMA,
    LIMITED,
    NETWORK_REQUEST,
    NOOP,
    NOT_IMPLEMENTED,
    PROCESS_SPAWN,
    PROPOSE_PATCH,
    PROVIDER_MODEL_CALL,
    RAW_SHELL,
    READ_ENV,
    READ_SECRET,
    REQUEST_EXPLANATION,
    REQUEST_REPO_READ,
    REQUEST_RISK_CLASSIFICATION,
    RUN_COMMAND,
    UNKNOWN_ACTION_TYPE_REJECTED,
    USER_GATED,
    VALID_STRUCTURED_ACTION,
    WRITE_AEG_STATE,
    WRITE_FILE,
    StructuredActionValidationResult,
    realpath_scope_rejection_reasons,
    validate_structured_action,
)

STRUCTURED_ACTION_CAPABILITY_GATE_VERSION = "phase11b_action_capability_gate_v0"

CAPABILITY_STATUS_VOCABULARY = frozenset(
    {
        ALLOWED_UNDER_POLICY,
        LIMITED,
        DENIED,
        FUTURE_GATED,
        USER_GATED,
        NOT_IMPLEMENTED,
    }
)

CAPABILITY_GATE_ALLOWED = "CAPABILITY_GATE_ALLOWED"
CAPABILITY_GATE_LIMITED_ALLOWED = "CAPABILITY_GATE_LIMITED_ALLOWED"
CAPABILITY_DENIED = "CAPABILITY_DENIED"
NOT_IMPLEMENTED_REJECTED = "NOT_IMPLEMENTED_REJECTED"
UNKNOWN_CAPABILITY_REJECTED = "UNKNOWN_CAPABILITY_REJECTED"
REPORTED_ONLY_CAPABILITY_GRANT_REJECTED = "REPORTED_ONLY_CAPABILITY_GRANT_REJECTED"
SCOPE_LIMIT_REJECTED = "SCOPE_LIMIT_REJECTED"
USER_GATE_REQUIRED = "USER_GATE_REQUIRED"

CAPABILITY_GATE_RESULT_VOCABULARY = frozenset(
    {
        CAPABILITY_GATE_ALLOWED,
        CAPABILITY_GATE_LIMITED_ALLOWED,
        CAPABILITY_DENIED,
        FUTURE_GATE_REQUIRED,
        USER_GATE_REQUIRED,
        NOT_IMPLEMENTED_REJECTED,
        UNKNOWN_CAPABILITY_REJECTED,
        REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
        SCOPE_LIMIT_REJECTED,
    }
)

DEFAULT_DENIED_CAPABILITIES = frozenset(
    {
        "raw_shell",
        "process_spawn",
        "network",
        "provider_model_call",
        "general_write_file",
        "write_file",
        "run_command",
        "eval_exec",
        "import_module",
        "store_sink_direct_access",
        "aeg_state_write",
        "direct_ledger_append",
        "ledger_append_direct_access",
        "env_read",
        "read_env",
        "secret_read",
        "read_secret",
    }
)

ACTION_DEFAULT_CAPABILITIES = {
    NOOP: ("noop",),
    REQUEST_EXPLANATION: ("explanation",),
    REQUEST_RISK_CLASSIFICATION: ("risk_classification",),
    PROPOSE_PATCH: ("propose_patch", "repo_target_scope"),
    REQUEST_REPO_READ: ("read_repo",),
}

CAPABILITY_POLICY_BY_NAME = {
    "noop": ALLOWED_UNDER_POLICY,
    "explanation": ALLOWED_UNDER_POLICY,
    "risk_classification": ALLOWED_UNDER_POLICY,
    "propose_patch": ALLOWED_UNDER_POLICY,
    "repo_target_scope": LIMITED,
    "read_repo": LIMITED,
    "raw_shell": DENIED,
    "process_spawn": DENIED,
    "network": DENIED,
    "provider_model_call": FUTURE_GATED,
    "general_write_file": DENIED,
    "write_file": DENIED,
    "run_command": DENIED,
    "eval_exec": DENIED,
    "import_module": DENIED,
    "store_sink_direct_access": DENIED,
    "aeg_state_write": DENIED,
    "direct_ledger_append": DENIED,
    "ledger_append_direct_access": DENIED,
    "env_read": DENIED,
    "read_env": DENIED,
    "secret_read": DENIED,
    "read_secret": DENIED,
    "write_repo": FUTURE_GATED,
    "remote_write": FUTURE_GATED,
    "user_gate": USER_GATED,
    "explicit_user_approval": USER_GATED,
    "filesystem_read": NOT_IMPLEMENTED,
    "open_arbitrary_path": DENIED,
    "call_internal_function": DENIED,
    "python_code": DENIED,
}

FORBIDDEN_ACTION_CAPABILITIES = {
    WRITE_AEG_STATE: "aeg_state_write",
    DIRECT_STORE_WRITE: "store_sink_direct_access",
    DIRECT_LEDGER_APPEND: "direct_ledger_append",
    WRITE_FILE: "general_write_file",
    RUN_COMMAND: "run_command",
    RAW_SHELL: "raw_shell",
    PROCESS_SPAWN: "process_spawn",
    NETWORK_REQUEST: "network",
    PROVIDER_MODEL_CALL: "provider_model_call",
    EVAL_EXEC: "eval_exec",
    IMPORT_MODULE: "import_module",
    READ_ENV: "env_read",
    READ_SECRET: "secret_read",
}

ALLOWED_LIMITED_ACTION_CAPABILITY_MAPPING = {
    NOOP: {"noop": ALLOWED_UNDER_POLICY},
    REQUEST_EXPLANATION: {"explanation": ALLOWED_UNDER_POLICY},
    REQUEST_RISK_CLASSIFICATION: {"risk_classification": ALLOWED_UNDER_POLICY},
    PROPOSE_PATCH: {
        "propose_patch": ALLOWED_UNDER_POLICY,
        "repo_target_scope": LIMITED,
    },
    REQUEST_REPO_READ: {"read_repo": LIMITED},
}

SELF_REPORT_TRUE_FIELDS = frozenset(
    {
        "capability_granted",
        "execution_allowed",
        "granted",
        "live_executor_ready",
        "mutation_allowed",
        "trusted",
        "approved_by_executor",
        "safe",
        "write_authority_granted",
    }
)
SELF_REPORT_AUTHORITY_FIELDS = frozenset(
    {
        "authority",
        "execution_authority",
        "live_executor_authority",
        "mutation_authority",
        "write_authority",
    }
)
REPORTED_ONLY_FIELDS = frozenset({"grant_source", "source", "basis"})

PATH_FIELDS = frozenset(
    {
        "path",
        "paths",
        "file",
        "files",
        "file_path",
        "file_paths",
        "target",
        "targets",
        "target_file",
        "target_files",
        "target_path",
        "target_paths",
    }
)

ENV_SECRET_TOKENS = frozenset(
    {
        "read_env",
        "env_read",
        "read_secret",
        "secret_read",
        "environment",
        "environment_variable",
        "secret",
        "secrets",
    }
)


@dataclass(frozen=True)
class CapabilityDecision:
    capability_name: str
    status: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class ActionCapabilityGateResult:
    action_type: str | None
    required_capabilities: tuple[str, ...]
    capability_decisions: tuple[CapabilityDecision, ...]
    gate_result: str
    gate_reason: str
    schema_validation_status: str
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    live_executor_ready: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD


def evaluate_action_capabilities(
    action: Mapping[str, Any],
    schema_validation: StructuredActionValidationResult | None = None,
    *,
    explicit_user_gate_evidence: bool | Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> ActionCapabilityGateResult:
    """Evaluate capability authorization after structured action validation.

    The returned gate result is not an execution permit. All execution,
    mutation, write-authority, and live-executor flags remain false.
    """

    validation = schema_validation or validate_structured_action(action, repo_root=repo_root)
    action_type = validation.action_type
    required_capabilities = _required_capabilities(action, action_type)

    if not validation.valid:
        return _schema_rejection_result(validation, required_capabilities)

    self_report_reasons = _self_report_rejection_reasons(action)
    if self_report_reasons:
        decisions = tuple(
            CapabilityDecision(
                capability_name=capability_name,
                status=DENIED,
                allowed=False,
                reason="; ".join(self_report_reasons),
            )
            for capability_name in required_capabilities
        )
        return _gate_result(
            action_type=action_type,
            required_capabilities=required_capabilities,
            capability_decisions=decisions,
            gate_result=REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
            gate_reason="; ".join(self_report_reasons),
            schema_validation_status=validation.status,
        )

    decisions: list[CapabilityDecision] = []
    limited_seen = False
    for capability_name in required_capabilities:
        status = CAPABILITY_POLICY_BY_NAME.get(capability_name)
        if status is None:
            decisions.append(
                CapabilityDecision(
                    capability_name=capability_name,
                    status=DENIED,
                    allowed=False,
                    reason=f"unknown capability rejected: {capability_name}",
                )
            )
            return _gate_result(
                action_type=action_type,
                required_capabilities=required_capabilities,
                capability_decisions=tuple(decisions),
                gate_result=UNKNOWN_CAPABILITY_REJECTED,
                gate_reason=f"unknown capability rejected: {capability_name}",
                schema_validation_status=validation.status,
            )

        if status == DENIED:
            decisions.append(
                CapabilityDecision(
                    capability_name=capability_name,
                    status=status,
                    allowed=False,
                    reason=f"capability denied: {capability_name}",
                )
            )
            return _gate_result(
                action_type=action_type,
                required_capabilities=required_capabilities,
                capability_decisions=tuple(decisions),
                gate_result=CAPABILITY_DENIED,
                gate_reason=f"capability denied: {capability_name}",
                schema_validation_status=validation.status,
            )

        if status == NOT_IMPLEMENTED:
            decisions.append(
                CapabilityDecision(
                    capability_name=capability_name,
                    status=status,
                    allowed=False,
                    reason=f"capability not implemented: {capability_name}",
                )
            )
            return _gate_result(
                action_type=action_type,
                required_capabilities=required_capabilities,
                capability_decisions=tuple(decisions),
                gate_result=NOT_IMPLEMENTED_REJECTED,
                gate_reason=f"capability not implemented: {capability_name}",
                schema_validation_status=validation.status,
            )

        if status == FUTURE_GATED:
            decisions.append(
                CapabilityDecision(
                    capability_name=capability_name,
                    status=status,
                    allowed=False,
                    reason=f"future gate required for capability: {capability_name}",
                )
            )
            return _gate_result(
                action_type=action_type,
                required_capabilities=required_capabilities,
                capability_decisions=tuple(decisions),
                gate_result=FUTURE_GATE_REQUIRED,
                gate_reason=f"future gate required for capability: {capability_name}",
                schema_validation_status=validation.status,
            )

        if status == USER_GATED and not _has_explicit_user_gate(
            explicit_user_gate_evidence,
            capability_name,
        ):
            decisions.append(
                CapabilityDecision(
                    capability_name=capability_name,
                    status=status,
                    allowed=False,
                    reason=f"user gate required for capability: {capability_name}",
                )
            )
            return _gate_result(
                action_type=action_type,
                required_capabilities=required_capabilities,
                capability_decisions=tuple(decisions),
                gate_result=USER_GATE_REQUIRED,
                gate_reason=f"user gate required for capability: {capability_name}",
                schema_validation_status=validation.status,
            )

        if status == LIMITED:
            scope_reasons = _limited_scope_rejection_reasons(
                action_type,
                action,
                repo_root=repo_root,
            )
            if scope_reasons:
                decisions.append(
                    CapabilityDecision(
                        capability_name=capability_name,
                        status=status,
                        allowed=False,
                        reason="; ".join(scope_reasons),
                    )
                )
                return _gate_result(
                    action_type=action_type,
                    required_capabilities=required_capabilities,
                    capability_decisions=tuple(decisions),
                    gate_result=SCOPE_LIMIT_REJECTED,
                    gate_reason="; ".join(scope_reasons),
                    schema_validation_status=validation.status,
                )
            limited_seen = True

        decisions.append(
            CapabilityDecision(
                capability_name=capability_name,
                status=status,
                allowed=True,
                reason=f"capability allowed under gate policy: {capability_name}",
            )
        )

    return _gate_result(
        action_type=action_type,
        required_capabilities=required_capabilities,
        capability_decisions=tuple(decisions),
        gate_result=CAPABILITY_GATE_LIMITED_ALLOWED if limited_seen else CAPABILITY_GATE_ALLOWED,
        gate_reason=(
            "limited capability scope accepted"
            if limited_seen
            else "capabilities allowed under policy"
        ),
        schema_validation_status=validation.status,
    )


def build_action_capability_gate_evidence() -> dict[str, Any]:
    """Return deterministic contract evidence for the Phase 11-B-1c gate."""

    return {
        "capability_gate_version": STRUCTURED_ACTION_CAPABILITY_GATE_VERSION,
        "schema_validation_function": "validate_structured_action",
        "capability_gate_function": "evaluate_action_capabilities",
        "capability_status_vocabulary": sorted(CAPABILITY_STATUS_VOCABULARY),
        "capability_gate_result_vocabulary": sorted(CAPABILITY_GATE_RESULT_VOCABULARY),
        "default_denied_capabilities": sorted(DEFAULT_DENIED_CAPABILITIES),
        "allowed_limited_action_capability_mapping": _jsonable_mapping(
            ALLOWED_LIMITED_ACTION_CAPABILITY_MAPPING
        ),
        "reported_only_grants_rejected": True,
        "executor_self_report_authority_rejected": True,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def _schema_rejection_result(
    validation: StructuredActionValidationResult,
    required_capabilities: tuple[str, ...],
) -> ActionCapabilityGateResult:
    action_type = validation.action_type
    gate_result = CAPABILITY_DENIED
    gate_reason = "; ".join(validation.reasons) or validation.status
    decisions: tuple[CapabilityDecision, ...] = tuple(
        CapabilityDecision(
            capability_name=capability_name,
            status=CAPABILITY_POLICY_BY_NAME.get(capability_name, DENIED),
            allowed=False,
            reason=gate_reason,
        )
        for capability_name in required_capabilities
    )

    if validation.status == UNKNOWN_ACTION_TYPE_REJECTED:
        gate_result = UNKNOWN_CAPABILITY_REJECTED
    elif validation.status == FUTURE_GATE_REQUIRED:
        gate_result = FUTURE_GATE_REQUIRED
    elif validation.status == FORBIDDEN_PAYLOAD_FIELD_REJECTED and _is_scope_rejection(
        validation.reasons
    ):
        gate_result = SCOPE_LIMIT_REJECTED
    elif validation.status == FORBIDDEN_ACTION_TYPE_REJECTED:
        forbidden_capability = FORBIDDEN_ACTION_CAPABILITIES.get(action_type or "")
        if forbidden_capability is not None:
            required_capabilities = (forbidden_capability,)
            status = CAPABILITY_POLICY_BY_NAME.get(forbidden_capability, DENIED)
            if status == FUTURE_GATED:
                gate_result = FUTURE_GATE_REQUIRED
            decisions = (
                CapabilityDecision(
                    capability_name=forbidden_capability,
                    status=status,
                    allowed=False,
                    reason=gate_reason,
                ),
            )
    elif validation.status == INVALID_ACTION_SCHEMA:
        gate_result = CAPABILITY_DENIED

    return _gate_result(
        action_type=action_type,
        required_capabilities=required_capabilities,
        capability_decisions=decisions,
        gate_result=gate_result,
        gate_reason=gate_reason,
        schema_validation_status=validation.status,
    )


def _gate_result(
    *,
    action_type: str | None,
    required_capabilities: tuple[str, ...],
    capability_decisions: tuple[CapabilityDecision, ...],
    gate_result: str,
    gate_reason: str,
    schema_validation_status: str,
) -> ActionCapabilityGateResult:
    return ActionCapabilityGateResult(
        action_type=action_type,
        required_capabilities=required_capabilities,
        capability_decisions=capability_decisions,
        gate_result=gate_result,
        gate_reason=gate_reason,
        schema_validation_status=schema_validation_status,
    )


def _required_capabilities(
    action: Mapping[str, Any],
    action_type: str | None,
) -> tuple[str, ...]:
    names: list[str] = []
    for capability_name in ACTION_DEFAULT_CAPABILITIES.get(action_type or "", ()):
        _append_unique(names, capability_name)

    requirements = action.get("capability_requirements", []) if isinstance(action, Mapping) else []
    if isinstance(requirements, Sequence) and not isinstance(requirements, (str, bytes, bytearray)):
        for requirement in requirements:
            capability_name = _capability_name_from_requirement(requirement)
            if capability_name is not None:
                _append_unique(names, capability_name)

    if not names and action_type in ACTION_CAPABILITY_MAPPING:
        _append_unique(names, ACTION_CAPABILITY_MAPPING[action_type].capability_name)
    return tuple(names)


def _capability_name_from_requirement(requirement: Any) -> str | None:
    if isinstance(requirement, str):
        return _normalize_key(requirement)
    if isinstance(requirement, Mapping):
        capability_name = requirement.get("capability_name") or requirement.get("capability")
        if isinstance(capability_name, str) and capability_name:
            return _normalize_key(capability_name)
    return None


def _self_report_rejection_reasons(action: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    _scan_self_report_claims(action, "action", reasons)
    return _unique(reasons)


def _scan_self_report_claims(value: Any, location: str, reasons: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in REPORTED_ONLY_FIELDS and nested == REPORTED_ONLY:
                reasons.append(f"reported_only capability grant rejected: {nested_location}")
            if normalized_key in SELF_REPORT_TRUE_FIELDS and nested is True:
                reasons.append(f"executor self-claimed authority rejected: {nested_location}")
            if normalized_key in SELF_REPORT_AUTHORITY_FIELDS and nested:
                reasons.append(f"executor self-claimed authority rejected: {nested_location}")
            _scan_self_report_claims(nested, nested_location, reasons)
        return

    if _is_sequence(value):
        for index, nested in enumerate(value):
            _scan_self_report_claims(nested, f"{location}[{index}]", reasons)


def _limited_scope_rejection_reasons(
    action_type: str | None,
    action: Mapping[str, Any],
    *,
    repo_root: str | Path | None,
) -> list[str]:
    reasons: list[str] = []
    target_scope = action.get("target_scope")
    if not isinstance(target_scope, Mapping):
        return ["limited capability requires target_scope mapping"]

    if target_scope.get("repo_relative") is not True:
        reasons.append("limited capability requires repo_relative target_scope")

    for location, value in _path_values(action):
        if not isinstance(value, str):
            reasons.append(f"limited scope path must be a string: {location}")
            continue
        if _is_absolute_path(value):
            reasons.append(f"limited scope absolute path rejected: {location}")
        if _contains_parent_traversal(value):
            reasons.append(f"limited scope parent traversal rejected: {location}")
        if _contains_aeg_path(value):
            reasons.append(f"limited scope .aeg target rejected: {location}")
        if _is_env_secret_target(value):
            reasons.append(f"limited scope env/secret target rejected: {location}")
        if repo_root is not None:
            reasons.extend(realpath_scope_rejection_reasons(value, location, repo_root))

    if action_type == REQUEST_REPO_READ:
        for requirement in action.get("capability_requirements", []):
            capability_name = _capability_name_from_requirement(requirement)
            if capability_name in {"env_read", "read_env", "secret_read", "read_secret"}:
                reasons.append(f"limited repo read cannot request {capability_name}")

    return _unique(reasons)


def _path_values(action: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    values: list[tuple[str, Any]] = []
    for root_field in ("target_scope", "payload"):
        _collect_path_values(action.get(root_field), root_field, values, parent_key=None)
    return tuple(values)


def _collect_path_values(
    value: Any,
    location: str,
    values: list[tuple[str, Any]],
    parent_key: str | None,
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in PATH_FIELDS:
                _collect_declared_path_values(nested, nested_location, values)
            else:
                _collect_path_values(nested, nested_location, values, normalized_key)
        return

    if parent_key in PATH_FIELDS:
        values.append((location, value))


def _collect_declared_path_values(
    value: Any,
    location: str,
    values: list[tuple[str, Any]],
) -> None:
    if isinstance(value, str):
        values.append((location, value))
        return
    if _is_sequence(value):
        for index, nested in enumerate(value):
            _collect_declared_path_values(nested, f"{location}[{index}]", values)
        return
    values.append((location, value))


def _has_explicit_user_gate(
    explicit_user_gate_evidence: bool | Mapping[str, Any] | None,
    capability_name: str,
) -> bool:
    if explicit_user_gate_evidence is True:
        return True
    if not isinstance(explicit_user_gate_evidence, Mapping):
        return False
    approved = explicit_user_gate_evidence.get("approved_capabilities", ())
    return capability_name in approved


def _is_scope_rejection(reasons: Sequence[str]) -> bool:
    for reason in reasons:
        lowered = reason.lower()
        if (
            ".aeg" in lowered
            or "absolute path" in lowered
            or "parent traversal" in lowered
            or "env/secret" in lowered
            or "outside repo" in lowered
            or "realpath" in lowered
            or "resolution failed closed" in lowered
        ):
            return True
    return False


def _jsonable_mapping(mapping: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, str]]:
    return {
        action_type: {capability: status for capability, status in capabilities.items()}
        for action_type, capabilities in sorted(mapping.items())
    }


def _normalize_key(value: str) -> str:
    normalized_spaces = "_".join(value.strip().lower().split())
    return "_".join(normalized_spaces.split("-"))


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _is_absolute_path(value: str) -> bool:
    candidate = value.strip()
    if candidate.startswith("/"):
        return True
    if len(candidate) >= 3 and candidate[1] == ":" and candidate[2] in ("\\", "/"):
        return candidate[0].isalpha()
    return False


def _contains_parent_traversal(value: str) -> bool:
    parts = _slash_normalized(value).split("/")
    return ".." in parts


def _contains_aeg_path(value: str) -> bool:
    normalized = _slash_normalized(value).strip()
    return normalized == ".aeg" or normalized.startswith(".aeg/") or "/.aeg/" in normalized


def _is_env_secret_target(value: str) -> bool:
    normalized = _slash_normalized(value).strip().lower()
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return False
    if parts[-1].startswith(".env"):
        return True
    if any(part in {"secret", "secrets"} for part in parts):
        return True
    return any(_normalize_key(part) in ENV_SECRET_TOKENS for part in parts)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _slash_normalized(value: str) -> str:
    return "/".join(value.split("\\"))
