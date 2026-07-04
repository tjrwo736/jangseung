"""Phase 11-B-1b structured action schema contract.

This module is an import-safe contract and validator only. It treats executor
output as data, rejects executable action surfaces, and does not execute,
mediate, or apply any action.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, REPORTED_ONLY, SAFE_DEFAULT
from src.evidence.b3_capability_policy_contract import CAPABILITY_FIELDS

STRUCTURED_ACTION_CONTRACT_VERSION = "phase11b_structured_action_schema_contract_v0"
EXECUTOR_OUTPUT_MODEL_DATA_NOT_CODE = "DATA_NOT_CODE"
PR_81_STATUS_HOLD_OPEN_DRAFT = "HOLD_OPEN_DRAFT_UNTOUCHED"
PR_81_DRAFT_RELEASE_NOT_PERFORMED = "NOT_PERFORMED"
PR_81_MERGE_NOT_PERFORMED = "NOT_PERFORMED"

PROPOSE_PATCH = "PROPOSE_PATCH"
REQUEST_REPO_READ = "REQUEST_REPO_READ"
REQUEST_RISK_CLASSIFICATION = "REQUEST_RISK_CLASSIFICATION"
REQUEST_EXPLANATION = "REQUEST_EXPLANATION"
NOOP = "NOOP"

WRITE_AEG_STATE = "WRITE_AEG_STATE"
DIRECT_STORE_WRITE = "DIRECT_STORE_WRITE"
DIRECT_LEDGER_APPEND = "DIRECT_LEDGER_APPEND"
WRITE_FILE = "WRITE_FILE"
RUN_COMMAND = "RUN_COMMAND"
RAW_SHELL = "RAW_SHELL"
PROCESS_SPAWN = "PROCESS_SPAWN"
NETWORK_REQUEST = "NETWORK_REQUEST"
PROVIDER_MODEL_CALL = "PROVIDER_MODEL_CALL"
IMPORT_MODULE = "IMPORT_MODULE"
EVAL_EXEC = "EVAL_EXEC"
READ_ENV = "READ_ENV"
READ_SECRET = "READ_SECRET"
OPEN_ARBITRARY_PATH = "OPEN_ARBITRARY_PATH"
CALL_INTERNAL_FUNCTION = "CALL_INTERNAL_FUNCTION"
PYTHON_CODE = "PYTHON_CODE"

REQUEST_REPO_WRITE = "REQUEST_REPO_WRITE"

ALLOWED_ACTION_TYPES = frozenset(
    {
        PROPOSE_PATCH,
        REQUEST_REPO_READ,
        REQUEST_RISK_CLASSIFICATION,
        REQUEST_EXPLANATION,
        NOOP,
    }
)

FORBIDDEN_ACTION_TYPES = frozenset(
    {
        WRITE_AEG_STATE,
        DIRECT_STORE_WRITE,
        DIRECT_LEDGER_APPEND,
        WRITE_FILE,
        RUN_COMMAND,
        RAW_SHELL,
        PROCESS_SPAWN,
        NETWORK_REQUEST,
        PROVIDER_MODEL_CALL,
        IMPORT_MODULE,
        EVAL_EXEC,
        READ_ENV,
        READ_SECRET,
        OPEN_ARBITRARY_PATH,
        CALL_INTERNAL_FUNCTION,
        PYTHON_CODE,
    }
)

ALLOWED_UNDER_POLICY = "ALLOWED_UNDER_POLICY"
LIMITED = "LIMITED"
DENIED = "DENIED"
FUTURE_GATED = "FUTURE_GATED"
USER_GATED = "USER_GATED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
MEDIATED_AND_FUTURE_GATED = "MEDIATED_AND_FUTURE_GATED"
DENIED_UNTIL_EXPLICIT_GATE = "DENIED_UNTIL_EXPLICIT_GATE"

CAPABILITY_STATUS_VOCABULARY = frozenset(
    {
        ALLOWED_UNDER_POLICY,
        LIMITED,
        DENIED,
        FUTURE_GATED,
        USER_GATED,
        NOT_IMPLEMENTED,
        MEDIATED_AND_FUTURE_GATED,
        DENIED_UNTIL_EXPLICIT_GATE,
    }
)

VALID_STRUCTURED_ACTION = "VALID_STRUCTURED_ACTION"
INVALID_ACTION_SCHEMA = "INVALID_ACTION_SCHEMA"
UNKNOWN_ACTION_TYPE_REJECTED = "UNKNOWN_ACTION_TYPE_REJECTED"
FORBIDDEN_ACTION_TYPE_REJECTED = "FORBIDDEN_ACTION_TYPE_REJECTED"
FORBIDDEN_PAYLOAD_FIELD_REJECTED = "FORBIDDEN_PAYLOAD_FIELD_REJECTED"
CAPABILITY_DENIED = "CAPABILITY_DENIED"
FUTURE_GATE_REQUIRED = "FUTURE_GATE_REQUIRED"
USER_GATE_REQUIRED = "USER_GATE_REQUIRED"

VALIDATION_STATUS_VOCABULARY = frozenset(
    {
        VALID_STRUCTURED_ACTION,
        INVALID_ACTION_SCHEMA,
        UNKNOWN_ACTION_TYPE_REJECTED,
        FORBIDDEN_ACTION_TYPE_REJECTED,
        FORBIDDEN_PAYLOAD_FIELD_REJECTED,
        CAPABILITY_DENIED,
        FUTURE_GATE_REQUIRED,
        USER_GATE_REQUIRED,
    }
)

REQUIRED_STRUCTURED_ACTION_FIELDS = (
    "action_type",
    "action_id",
    "declared_intent",
    "declared_risk",
    "capability_requirements",
    "target_scope",
    "payload",
)

PROPOSE_PATCH_PAYLOAD_FIELDS = frozenset(
    {
        "target_files",
        "patch_summary",
        "patch_diff",
        "patch_plan",
    }
)

FORBIDDEN_PAYLOAD_FIELDS = frozenset(
    {
        "python_code",
        "eval_code",
        "exec_code",
        "shell",
        "command",
        "shell_command",
        "callback",
        "callback_name",
        "function_name",
        "function_pointer",
        "callable_reference",
        "module",
        "import_module",
        "import_path",
        "raw_file_write",
        "absolute_write_path",
        "aeg_path",
        "env_key",
        "secret_key",
        "provider",
        "network",
        "url",
        "process_spawn",
        "store_sink",
        "store_sink_direct_access",
        "direct_store_write",
        "direct_ledger_append",
        "ledger_append",
    }
)

PATH_SEMANTIC_FIELDS = frozenset(
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
        "write_path",
        "write_paths",
    }
)

ENV_SECRET_REQUEST_TOKENS = frozenset(
    {
        "read_env",
        "env_read",
        "read_secret",
        "secret_read",
        "read_environment",
        "environment_read",
    }
)


@dataclass(frozen=True)
class CapabilityMapping:
    action_type: str
    capability_name: str
    policy_status: str
    b3_capability_field: str | None
    note: str


@dataclass(frozen=True)
class StructuredActionValidationResult:
    valid: bool
    status: str
    reasons: tuple[str, ...]
    action_type: str | None
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    action_executed: bool = False
    filesystem_mutated: bool = False
    write_authority_granted: bool = False
    live_executor_ready: bool = False


ACTION_CAPABILITY_MAPPING = {
    PROPOSE_PATCH: CapabilityMapping(
        action_type=PROPOSE_PATCH,
        capability_name="propose_patch",
        policy_status=ALLOWED_UNDER_POLICY,
        b3_capability_field=None,
        note="Patch proposal data only; not repo write authority.",
    ),
    REQUEST_REPO_READ: CapabilityMapping(
        action_type=REQUEST_REPO_READ,
        capability_name="read_repo",
        policy_status=LIMITED,
        b3_capability_field=None,
        note="Bounded repository read request; not unrestricted filesystem read.",
    ),
    REQUEST_REPO_WRITE: CapabilityMapping(
        action_type=REQUEST_REPO_WRITE,
        capability_name="write_repo",
        policy_status=MEDIATED_AND_FUTURE_GATED,
        b3_capability_field="write_file_authority",
        note="Mediated future repo write request; not raw write_file authority.",
    ),
    REQUEST_RISK_CLASSIFICATION: CapabilityMapping(
        action_type=REQUEST_RISK_CLASSIFICATION,
        capability_name="risk_classification",
        policy_status=LIMITED,
        b3_capability_field=None,
        note="Risk classification request; not an authority grant.",
    ),
    REQUEST_EXPLANATION: CapabilityMapping(
        action_type=REQUEST_EXPLANATION,
        capability_name="explanation",
        policy_status=ALLOWED_UNDER_POLICY,
        b3_capability_field=None,
        note="Explanation data only.",
    ),
    NOOP: CapabilityMapping(
        action_type=NOOP,
        capability_name="noop",
        policy_status=ALLOWED_UNDER_POLICY,
        b3_capability_field=None,
        note="No hidden action, no mutation, and no authority grant.",
    ),
    WRITE_AEG_STATE: CapabilityMapping(
        action_type=WRITE_AEG_STATE,
        capability_name="aeg_state_write",
        policy_status=DENIED,
        b3_capability_field="aeg_state_write_authority",
        note="Executor-authored .aeg state writes are denied.",
    ),
    DIRECT_STORE_WRITE: CapabilityMapping(
        action_type=DIRECT_STORE_WRITE,
        capability_name="store_sink_direct_access",
        policy_status=DENIED,
        b3_capability_field="aeg_state_write_authority",
        note="Direct store sink access is denied.",
    ),
    DIRECT_LEDGER_APPEND: CapabilityMapping(
        action_type=DIRECT_LEDGER_APPEND,
        capability_name="ledger_append_direct_access",
        policy_status=DENIED,
        b3_capability_field="aeg_state_write_authority",
        note="Direct ledger append is denied.",
    ),
    WRITE_FILE: CapabilityMapping(
        action_type=WRITE_FILE,
        capability_name="general_write_file",
        policy_status=DENIED,
        b3_capability_field="write_file_authority",
        note="Generic file write authority is denied.",
    ),
    RAW_SHELL: CapabilityMapping(
        action_type=RAW_SHELL,
        capability_name="raw_shell",
        policy_status=DENIED,
        b3_capability_field="raw_shell_authority",
        note="Raw shell authority is denied.",
    ),
    RUN_COMMAND: CapabilityMapping(
        action_type=RUN_COMMAND,
        capability_name="run_command",
        policy_status=DENIED,
        b3_capability_field="run_command_authority",
        note="Command runner authority is denied.",
    ),
    PROCESS_SPAWN: CapabilityMapping(
        action_type=PROCESS_SPAWN,
        capability_name="process_spawn",
        policy_status=DENIED,
        b3_capability_field="process_spawn_authority",
        note="Process spawn authority is denied.",
    ),
    NETWORK_REQUEST: CapabilityMapping(
        action_type=NETWORK_REQUEST,
        capability_name="network",
        policy_status=DENIED,
        b3_capability_field="network_authority",
        note="Network authority is denied.",
    ),
    PROVIDER_MODEL_CALL: CapabilityMapping(
        action_type=PROVIDER_MODEL_CALL,
        capability_name="provider_model_call",
        policy_status=DENIED_UNTIL_EXPLICIT_GATE,
        b3_capability_field="provider_model_call_authority",
        note="Provider/model calls are denied until an explicit future gate.",
    ),
    READ_ENV: CapabilityMapping(
        action_type=READ_ENV,
        capability_name="env_read",
        policy_status=DENIED,
        b3_capability_field="env_read_authority",
        note="Environment reads are denied.",
    ),
    READ_SECRET: CapabilityMapping(
        action_type=READ_SECRET,
        capability_name="secret_read",
        policy_status=DENIED,
        b3_capability_field="secret_read_authority",
        note="Secret reads are denied.",
    ),
    OPEN_ARBITRARY_PATH: CapabilityMapping(
        action_type=OPEN_ARBITRARY_PATH,
        capability_name="open_arbitrary_path",
        policy_status=DENIED,
        b3_capability_field="repo_outside_write_authority",
        note="Arbitrary path access is denied.",
    ),
    CALL_INTERNAL_FUNCTION: CapabilityMapping(
        action_type=CALL_INTERNAL_FUNCTION,
        capability_name="call_internal_function",
        policy_status=DENIED,
        b3_capability_field=None,
        note="Internal function calls are denied.",
    ),
    IMPORT_MODULE: CapabilityMapping(
        action_type=IMPORT_MODULE,
        capability_name="import_module",
        policy_status=DENIED,
        b3_capability_field=None,
        note="Dynamic module import requests are denied.",
    ),
    EVAL_EXEC: CapabilityMapping(
        action_type=EVAL_EXEC,
        capability_name="eval_exec",
        policy_status=DENIED,
        b3_capability_field=None,
        note="Eval/exec requests are denied.",
    ),
    PYTHON_CODE: CapabilityMapping(
        action_type=PYTHON_CODE,
        capability_name="python_code",
        policy_status=DENIED,
        b3_capability_field=None,
        note="Arbitrary Python code is denied.",
    ),
}

CAPABILITY_POLICY_BY_NAME = {
    mapping.capability_name: mapping.policy_status for mapping in ACTION_CAPABILITY_MAPPING.values()
}
CAPABILITY_POLICY_BY_NAME.update(
    {
        "read_repo": LIMITED,
        "write_repo": MEDIATED_AND_FUTURE_GATED,
        "propose_patch": ALLOWED_UNDER_POLICY,
        "risk_classification": LIMITED,
        "explanation": ALLOWED_UNDER_POLICY,
        "noop": ALLOWED_UNDER_POLICY,
    }
)

B3_CAPABILITY_REFERENCES = frozenset(
    mapping.b3_capability_field
    for mapping in ACTION_CAPABILITY_MAPPING.values()
    if mapping.b3_capability_field is not None
)
B3_CAPABILITY_REFERENCE_MISMATCHES = B3_CAPABILITY_REFERENCES - frozenset(CAPABILITY_FIELDS)

STRUCTURED_ACTION_CONTRACT_EVIDENCE = {
    "structured_action_contract_version": STRUCTURED_ACTION_CONTRACT_VERSION,
    "executor_output_model": EXECUTOR_OUTPUT_MODEL_DATA_NOT_CODE,
    "structured_action_schema_enforced": True,
    "arbitrary_python_execution_allowed": False,
    "eval_exec_allowed": False,
    "import_allowed": False,
    "raw_shell_allowed": False,
    "run_command_allowed": False,
    "process_spawn_allowed": False,
    "store_sink_direct_access_allowed": False,
    "aeg_state_write_allowed": False,
    "general_write_file_allowed": False,
    "network_allowed": False,
    "provider_model_call_allowed": False,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "pr_81_status": PR_81_STATUS_HOLD_OPEN_DRAFT,
    "pr_81_draft_release": PR_81_DRAFT_RELEASE_NOT_PERFORMED,
    "pr_81_merge": PR_81_MERGE_NOT_PERFORMED,
    "safe_default": SAFE_DEFAULT,
}


def build_structured_action_contract_evidence() -> dict[str, Any]:
    return dict(STRUCTURED_ACTION_CONTRACT_EVIDENCE)


def validate_structured_action(action: Mapping[str, Any]) -> StructuredActionValidationResult:
    reasons: list[str] = []
    action_type = _schema_action_type(action, reasons)
    if reasons:
        return _result(False, INVALID_ACTION_SCHEMA, reasons, action_type)

    if action_type in FORBIDDEN_ACTION_TYPES:
        mapping = ACTION_CAPABILITY_MAPPING.get(action_type)
        if mapping is not None:
            reasons.append(f"{action_type} maps to {mapping.capability_name}={mapping.policy_status}")
        reasons.append(f"forbidden action type rejected: {action_type}")
        if mapping is not None and mapping.policy_status == DENIED_UNTIL_EXPLICIT_GATE:
            return _result(False, FUTURE_GATE_REQUIRED, reasons, action_type)
        return _result(False, FORBIDDEN_ACTION_TYPE_REJECTED, reasons, action_type)

    if action_type not in ALLOWED_ACTION_TYPES:
        reasons.append(f"unknown action type rejected: {action_type}")
        return _result(False, UNKNOWN_ACTION_TYPE_REJECTED, reasons, action_type)

    _validate_schema_fields(action, reasons)
    if reasons:
        return _result(False, INVALID_ACTION_SCHEMA, reasons, action_type)

    forbidden_payload_reasons = _forbidden_payload_reasons(action)
    if forbidden_payload_reasons:
        return _result(
            False,
            FORBIDDEN_PAYLOAD_FIELD_REJECTED,
            forbidden_payload_reasons,
            action_type,
        )

    capability_reasons, capability_status = _capability_reasons(action)
    if capability_reasons:
        return _result(False, capability_status, capability_reasons, action_type)

    return _result(True, VALID_STRUCTURED_ACTION, [], action_type)


def _schema_action_type(action: Mapping[str, Any], reasons: list[str]) -> str | None:
    if not isinstance(action, Mapping):
        reasons.append("structured action must be a mapping")
        return None
    if "action_type" not in action:
        reasons.append("missing required field: action_type")
        return None
    action_type = action.get("action_type")
    if not isinstance(action_type, str) or not action_type:
        reasons.append("action_type must be a non-empty string")
        return None
    return action_type


def _validate_schema_fields(action: Mapping[str, Any], reasons: list[str]) -> None:
    for field in REQUIRED_STRUCTURED_ACTION_FIELDS:
        if field not in action:
            reasons.append(f"missing required field: {field}")

    for field in ("action_id", "declared_intent", "declared_risk"):
        value = action.get(field)
        if not isinstance(value, str) or not value:
            reasons.append(f"{field} must be a non-empty string")

    capability_requirements = action.get("capability_requirements")
    if not isinstance(capability_requirements, list):
        reasons.append("capability_requirements must be a list")
    elif not all(isinstance(item, (str, Mapping)) for item in capability_requirements):
        reasons.append("capability_requirements entries must be strings or mappings")

    target_scope = action.get("target_scope")
    if not isinstance(target_scope, Mapping):
        reasons.append("target_scope must be a mapping")

    payload = action.get("payload")
    if not isinstance(payload, Mapping):
        reasons.append("payload must be a mapping")


def _forbidden_payload_reasons(action: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for root_field in ("payload", "target_scope"):
        _scan_forbidden_payload(action.get(root_field), root_field, reasons, parent_key=None)
    return reasons


def _scan_forbidden_payload(
    value: Any,
    location: str,
    reasons: list[str],
    parent_key: str | None,
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in FORBIDDEN_PAYLOAD_FIELDS:
                reasons.append(f"forbidden payload field rejected: {nested_location}")
            _scan_forbidden_payload(nested, nested_location, reasons, normalized_key)
        return

    if isinstance(value, str):
        normalized_value = _normalize_key(value)
        if parent_key in PATH_SEMANTIC_FIELDS and _is_absolute_path(value):
            reasons.append(f"absolute path rejected: {location}")
        if parent_key in PATH_SEMANTIC_FIELDS and _contains_aeg_path(value):
            reasons.append(f".aeg target rejected: {location}")
        if normalized_value in ENV_SECRET_REQUEST_TOKENS:
            reasons.append(f"env/secret read request rejected: {location}")
        return

    if _is_sequence(value):
        for index, nested in enumerate(value):
            _scan_forbidden_payload(nested, f"{location}[{index}]", reasons, parent_key)


def _capability_reasons(action: Mapping[str, Any]) -> tuple[list[str], str]:
    reasons: list[str] = []
    status = CAPABILITY_DENIED
    for requirement in action.get("capability_requirements", []):
        if isinstance(requirement, Mapping):
            requirement_reasons, requirement_status = _capability_mapping_requirement_reason(requirement)
        else:
            requirement_reasons, requirement_status = _capability_string_requirement_reason(requirement)
        if requirement_reasons:
            reasons.extend(requirement_reasons)
            status = requirement_status
    return reasons, status


def _capability_mapping_requirement_reason(requirement: Mapping[str, Any]) -> tuple[list[str], str]:
    reasons: list[str] = []
    if requirement.get("grant_source") == REPORTED_ONLY or requirement.get("source") == REPORTED_ONLY:
        reasons.append("reported_only capability grant rejected")
    if requirement.get("granted") is True:
        reasons.append("capability grant claims are not accepted by the structured action validator")

    capability_name = requirement.get("capability_name") or requirement.get("capability")
    if isinstance(capability_name, str):
        string_reasons, status = _capability_string_requirement_reason(capability_name)
        reasons.extend(string_reasons)
        if string_reasons:
            return reasons, status

    return reasons, CAPABILITY_DENIED


def _capability_string_requirement_reason(requirement: str) -> tuple[list[str], str]:
    capability_name = _normalize_key(requirement)
    policy_status = CAPABILITY_POLICY_BY_NAME.get(capability_name)
    if policy_status is None:
        return [f"unknown capability requirement rejected: {requirement}"], CAPABILITY_DENIED
    if policy_status == DENIED_UNTIL_EXPLICIT_GATE:
        return [f"future gate required for capability: {capability_name}"], FUTURE_GATE_REQUIRED
    if policy_status in {DENIED, NOT_IMPLEMENTED}:
        return [f"capability denied: {capability_name}"], CAPABILITY_DENIED
    if policy_status in {FUTURE_GATED, MEDIATED_AND_FUTURE_GATED}:
        return [f"future gate required for capability: {capability_name}"], FUTURE_GATE_REQUIRED
    if policy_status == USER_GATED:
        return [f"user gate required for capability: {capability_name}"], USER_GATE_REQUIRED
    return [], VALID_STRUCTURED_ACTION


def _result(
    valid: bool,
    status: str,
    reasons: Sequence[str],
    action_type: str | None,
) -> StructuredActionValidationResult:
    return StructuredActionValidationResult(
        valid=valid,
        status=status,
        reasons=tuple(reasons),
        action_type=action_type,
    )


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized


def _is_absolute_path(value: str) -> bool:
    candidate = value.strip()
    if candidate.startswith("/"):
        return True
    if len(candidate) >= 3 and candidate[1] == ":" and candidate[2] in ("\\", "/"):
        return candidate[0].isalpha()
    return False


def _contains_aeg_path(value: str) -> bool:
    normalized = value.replace("\\", "/").strip()
    return normalized == ".aeg" or normalized.startswith(".aeg/") or "/.aeg/" in normalized


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
