"""Phase 11-B-4-1 deterministic no-provider model-like adapter.

The adapter accepts only named deterministic fixture input. It returns raw
executor output candidate data for the safe fixture and fails closed for
fixture shapes that resemble packets, tools, commands, provider/network request
attempts, filesystem mutation, runtime internal access, or authority
self-reports.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.structured_actions import PROPOSE_PATCH

DETERMINISTIC_MODEL_LIKE_ADAPTER_VERSION = (
    "phase11b_4_1_deterministic_no_provider_model_like_adapter_v0"
)

FIXTURE_INPUT_FIELD = "fixture_id"
SAFE_PROPOSAL_FIXTURE_ID = (
    "deterministic_model_like_safe_structured_proposal_v0"
)

MALFORMED_JSON_TEXT_FIXTURE_ID = "reject_malformed_json_text_v0"
SCALAR_JSON_TEXT_FIXTURE_ID = "reject_scalar_json_text_v0"
LIST_JSON_TEXT_FIXTURE_ID = "reject_list_json_text_v0"
MISSING_REQUIRED_FIELDS_FIXTURE_ID = "reject_missing_required_fields_v0"
COMPLETED_PACKET_SHAPED_OBJECT_FIXTURE_ID = (
    "reject_completed_action_decision_packet_shape_v0"
)
PACKET_ID_CREATED_BY_SPOOF_FIXTURE_ID = (
    "reject_packet_id_created_by_spoof_v0"
)
CAPABILITY_GATE_RESULT_SELF_REPORT_FIXTURE_ID = (
    "reject_capability_gate_result_self_report_v0"
)
EXECUTION_ALLOWED_TRUE_FIXTURE_ID = "reject_execution_allowed_true_v0"
MUTATION_ALLOWED_TRUE_FIXTURE_ID = "reject_mutation_allowed_true_v0"
WRITE_AUTHORITY_GRANTED_TRUE_FIXTURE_ID = (
    "reject_write_authority_granted_true_v0"
)
STORE_ROUTING_ALLOWED_TRUE_FIXTURE_ID = (
    "reject_store_routing_allowed_true_v0"
)
STORE_PATH_REACHABLE_TRUE_FIXTURE_ID = (
    "reject_store_path_reachable_true_v0"
)
TOOL_CALLS_FIXTURE_ID = "reject_tool_calls_v0"
FUNCTION_CALL_FIXTURE_ID = "reject_function_call_v0"
COMMAND_FIELD_FIXTURE_ID = "reject_command_field_v0"
CMD_FIELD_FIXTURE_ID = "reject_cmd_field_v0"
SHELL_FIELD_FIXTURE_ID = "reject_shell_field_v0"
RUN_FIELD_FIXTURE_ID = "reject_run_field_v0"
PROCESS_FIELD_FIXTURE_ID = "reject_process_field_v0"
SPAWN_FIELD_FIXTURE_ID = "reject_spawn_field_v0"
EXEC_FIELD_FIXTURE_ID = "reject_exec_field_v0"
EVAL_FIELD_FIXTURE_ID = "reject_eval_field_v0"
IMPORT_FIELD_FIXTURE_ID = "reject_import_field_v0"
WRITE_FILE_FIELD_FIXTURE_ID = "reject_write_file_field_v0"
DELETE_FILE_FIELD_FIXTURE_ID = "reject_delete_file_field_v0"
MOVE_FILE_FIELD_FIXTURE_ID = "reject_move_file_field_v0"
APPLY_PATCH_FIELD_FIXTURE_ID = "reject_apply_patch_field_v0"
STORE_WRITE_FIELD_FIXTURE_ID = "reject_store_write_field_v0"
LEDGER_APPEND_FIELD_FIXTURE_ID = "reject_ledger_append_field_v0"
RUNTIME_INTROSPECTION_FIXTURE_ID = "reject_runtime_introspection_v0"
INTERNAL_FUNCTION_CALL_FIXTURE_ID = "reject_internal_function_call_v0"
PROVIDER_REQUEST_FIXTURE_ID = "reject_provider_request_v0"
NETWORK_REQUEST_FIXTURE_ID = "reject_network_request_v0"
AUTHORITY_SELF_REPORT_FIXTURE_ID = "reject_authority_self_report_v0"
REPORTED_ONLY_SELF_REPORT_FIXTURE_ID = "reject_reported_only_self_report_v0"

ALLOWED_FIXTURE_IDS = (SAFE_PROPOSAL_FIXTURE_ID,)
REJECTION_FIXTURE_IDS = (
    MALFORMED_JSON_TEXT_FIXTURE_ID,
    SCALAR_JSON_TEXT_FIXTURE_ID,
    LIST_JSON_TEXT_FIXTURE_ID,
    MISSING_REQUIRED_FIELDS_FIXTURE_ID,
    COMPLETED_PACKET_SHAPED_OBJECT_FIXTURE_ID,
    PACKET_ID_CREATED_BY_SPOOF_FIXTURE_ID,
    CAPABILITY_GATE_RESULT_SELF_REPORT_FIXTURE_ID,
    EXECUTION_ALLOWED_TRUE_FIXTURE_ID,
    MUTATION_ALLOWED_TRUE_FIXTURE_ID,
    WRITE_AUTHORITY_GRANTED_TRUE_FIXTURE_ID,
    STORE_ROUTING_ALLOWED_TRUE_FIXTURE_ID,
    STORE_PATH_REACHABLE_TRUE_FIXTURE_ID,
    TOOL_CALLS_FIXTURE_ID,
    FUNCTION_CALL_FIXTURE_ID,
    COMMAND_FIELD_FIXTURE_ID,
    CMD_FIELD_FIXTURE_ID,
    SHELL_FIELD_FIXTURE_ID,
    RUN_FIELD_FIXTURE_ID,
    PROCESS_FIELD_FIXTURE_ID,
    SPAWN_FIELD_FIXTURE_ID,
    EXEC_FIELD_FIXTURE_ID,
    EVAL_FIELD_FIXTURE_ID,
    IMPORT_FIELD_FIXTURE_ID,
    WRITE_FILE_FIELD_FIXTURE_ID,
    DELETE_FILE_FIELD_FIXTURE_ID,
    MOVE_FILE_FIELD_FIXTURE_ID,
    APPLY_PATCH_FIELD_FIXTURE_ID,
    STORE_WRITE_FIELD_FIXTURE_ID,
    LEDGER_APPEND_FIELD_FIXTURE_ID,
    RUNTIME_INTROSPECTION_FIXTURE_ID,
    INTERNAL_FUNCTION_CALL_FIXTURE_ID,
    PROVIDER_REQUEST_FIXTURE_ID,
    NETWORK_REQUEST_FIXTURE_ID,
    AUTHORITY_SELF_REPORT_FIXTURE_ID,
    REPORTED_ONLY_SELF_REPORT_FIXTURE_ID,
)

_SAFE_PROPOSAL_OUTPUT: dict[str, Any] = {
    "action_type": PROPOSE_PATCH,
    "action_id": "deterministic-model-like-proposal-001",
    "declared_intent": (
        "Propose deterministic documentation-only review material as data."
    ),
    "declared_risk": "LOW",
    "capability_requirements": ["propose_patch"],
    "target_scope": {
        "repo_relative": True,
        "paths": ["docs/example_proposal.md"],
    },
    "payload": {
        "target_files": ["docs/example_proposal.md"],
        "patch_summary": (
            "Add a deterministic review-only proposal note."
        ),
        "patch_plan": [
            "Review the proposal data.",
            "Use only a later separately authorized path for any change.",
        ],
    },
}

_REJECTION_CANDIDATES: dict[str, Any] = {
    MALFORMED_JSON_TEXT_FIXTURE_ID: '{"action_type":',
    SCALAR_JSON_TEXT_FIXTURE_ID: '"NOOP"',
    LIST_JSON_TEXT_FIXTURE_ID: [{"action_type": "NOOP"}],
    MISSING_REQUIRED_FIELDS_FIXTURE_ID: {
        "action_type": PROPOSE_PATCH,
        "action_id": "missing-required-fields",
    },
    COMPLETED_PACKET_SHAPED_OBJECT_FIXTURE_ID: {
        "packet_id": "executor-spoofed-packet",
        "raw_output_hash": "sha256:executor-spoof",
        "parse_status": "PARSE_OK",
        "normalized_action": _SAFE_PROPOSAL_OUTPUT,
        "validation_result": {"status": "VALID_STRUCTURED_ACTION"},
        "capability_result": {"gate_result": "CAPABILITY_GATE_ALLOWED"},
        "decision_basis": ["executor self-report"],
        "adapter_version": "executor-authored",
        "created_by": "executor",
    },
    PACKET_ID_CREATED_BY_SPOOF_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "packet_id": "executor-spoofed-packet",
        "created_by": "executor",
    },
    CAPABILITY_GATE_RESULT_SELF_REPORT_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "capability_gate_result": "CAPABILITY_GATE_ALLOWED",
    },
    EXECUTION_ALLOWED_TRUE_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "execution_allowed": True,
    },
    MUTATION_ALLOWED_TRUE_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "mutation_allowed": True,
    },
    WRITE_AUTHORITY_GRANTED_TRUE_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "write_authority_granted": True,
    },
    STORE_ROUTING_ALLOWED_TRUE_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "store_routing_allowed": True,
    },
    STORE_PATH_REACHABLE_TRUE_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "store_path_reachable": True,
    },
    TOOL_CALLS_FIXTURE_ID: {"action": _SAFE_PROPOSAL_OUTPUT, "tool_calls": []},
    FUNCTION_CALL_FIXTURE_ID: {
        "action": _SAFE_PROPOSAL_OUTPUT,
        "function_call": {"name": "proposal"},
    },
    COMMAND_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"command": "do-not-run"},
    },
    CMD_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"cmd": "do-not-run"},
    },
    SHELL_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"shell": "do-not-run"},
    },
    RUN_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"run": "do-not-run"},
    },
    PROCESS_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"process": "do-not-run"},
    },
    SPAWN_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"spawn": "do-not-run"},
    },
    EXEC_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"exec": "do-not-run"},
    },
    EVAL_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"eval": "do-not-run"},
    },
    IMPORT_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"import": "do-not-run"},
    },
    WRITE_FILE_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"write_file": "do-not-write"},
    },
    DELETE_FILE_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"delete_file": "do-not-delete"},
    },
    MOVE_FILE_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"move_file": "do-not-move"},
    },
    APPLY_PATCH_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"apply_patch": "do-not-apply"},
    },
    STORE_WRITE_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"store_write": "do-not-store"},
    },
    LEDGER_APPEND_FIELD_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"ledger_append": "do-not-append"},
    },
    RUNTIME_INTROSPECTION_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"runtime_introspection": "do-not-inspect"},
    },
    INTERNAL_FUNCTION_CALL_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"internal_function_call": "do-not-call"},
    },
    PROVIDER_REQUEST_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"provider_request": "do-not-request"},
    },
    NETWORK_REQUEST_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "payload": {"network_request": "do-not-request"},
    },
    AUTHORITY_SELF_REPORT_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "authority": "executor-self-report",
    },
    REPORTED_ONLY_SELF_REPORT_FIXTURE_ID: {
        **_SAFE_PROPOSAL_OUTPUT,
        "reported_only": {"write_authority_granted": True},
    },
}

_REQUIRED_STRUCTURED_PROPOSAL_FIELDS = frozenset(
    {
        "action_type",
        "action_id",
        "declared_intent",
        "declared_risk",
        "capability_requirements",
        "target_scope",
        "payload",
    }
)

_BLOCKED_FIELD_NAMES = frozenset(
    {
        "adapter_version",
        "apply_patch",
        "authority",
        "capability_gate_result",
        "cmd",
        "command",
        "created_by",
        "delete_file",
        "eval",
        "exec",
        "execution_allowed",
        "function_call",
        "import",
        "internal_function_call",
        "ledger_append",
        "move_file",
        "mutation_allowed",
        "network_request",
        "normalized_action",
        "packet_id",
        "process",
        "provider_request",
        "raw_output_hash",
        "reported_only",
        "run",
        "runtime_introspection",
        "shell",
        "spawn",
        "store_path_reachable",
        "store_routing_allowed",
        "store_write",
        "tool_calls",
        "validation_result",
        "write_authority_granted",
        "write_file",
    }
)

_DIRECT_PACKET_FIELDS = frozenset(
    {
        "packet_id",
        "raw_output_hash",
        "parse_status",
        "normalized_action",
        "validation_result",
        "capability_result",
        "decision_basis",
        "adapter_version",
        "created_by",
    }
)


def build_deterministic_model_like_fixture_input(fixture_id: str) -> dict[str, str]:
    """Return the only accepted fixture input shape for the adapter."""

    if fixture_id not in ALLOWED_FIXTURE_IDS and fixture_id not in REJECTION_FIXTURE_IDS:
        raise ValueError(f"unknown deterministic model-like fixture id: {fixture_id}")
    return {FIXTURE_INPUT_FIELD: fixture_id}


def produce_deterministic_model_like_raw_output(
    fixture_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Return raw executor output for a safe fixture or fail closed."""

    fixture_id = _fixture_id_from_input(fixture_input)
    if fixture_id == SAFE_PROPOSAL_FIXTURE_ID:
        output = _clone_json_data(_SAFE_PROPOSAL_OUTPUT)
        rejection_reasons = _candidate_rejection_reasons(output)
        if rejection_reasons:
            joined = "; ".join(rejection_reasons)
            raise ValueError(f"safe fixture failed adapter validation: {joined}")
        return output

    candidate = _REJECTION_CANDIDATES[fixture_id]
    rejection_reasons = _candidate_rejection_reasons(candidate)
    reason = "; ".join(rejection_reasons) if rejection_reasons else "fixture rejected"
    raise ValueError(f"deterministic fixture rejected closed: {fixture_id}: {reason}")


def build_no_tool_model_like_adapter_structure() -> dict[str, Any]:
    """Return the structural no-tool surface for the deterministic adapter."""

    return {
        "available_tools": tuple(),
        "tool_schemas": tuple(),
        "tool_runtime": "disabled",
        "tool_choice": "none",
        "max_tool_calls": 0,
        "function_calling_allowed": False,
        "shell_process_allowed": False,
        "filesystem_mutation_allowed": False,
        "provider_network_allowed_by_model_executor": False,
        "runtime_internal_call_handles": tuple(),
        "trusted_context_handles": tuple(),
        "store_module_handles": tuple(),
    }


def build_deterministic_model_like_adapter_evidence() -> dict[str, Any]:
    """Return deterministic metadata for the no-provider adapter contract."""

    evidence: dict[str, Any] = {
        "adapter_version": DETERMINISTIC_MODEL_LIKE_ADAPTER_VERSION,
        "adapter_is_no_provider": True,
        "adapter_is_deterministic": True,
        "adapter_accepts_fixture_input_only": True,
        "adapter_output_is_raw_executor_output_only": True,
        "adapter_output_is_action_decision_packet": False,
        "adapter_submits_trusted_runtime_packet": False,
        "executor_output_ingress_required": True,
        "runtime_built_action_decision_packet_created_only_by_ingress": True,
        "provider_network_called": False,
        "tool_runtime_enabled": False,
        "tool_calls_allowed": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
        "provider_gate_required": True,
        "allowed_fixture_ids": ALLOWED_FIXTURE_IDS,
        "rejection_fixture_ids": REJECTION_FIXTURE_IDS,
    }
    evidence.update(build_no_tool_model_like_adapter_structure())
    return evidence


def _fixture_id_from_input(fixture_input: Mapping[str, Any]) -> str:
    if not isinstance(fixture_input, Mapping):
        raise TypeError("deterministic model-like adapter input must be a mapping")
    if tuple(fixture_input.keys()) != (FIXTURE_INPUT_FIELD,):
        raise ValueError(
            "deterministic model-like adapter accepts only fixture_id input"
        )

    fixture_id = fixture_input.get(FIXTURE_INPUT_FIELD)
    if fixture_id not in ALLOWED_FIXTURE_IDS and fixture_id not in REJECTION_FIXTURE_IDS:
        raise ValueError(f"unknown deterministic model-like fixture id: {fixture_id}")
    return str(fixture_id)


def _candidate_rejection_reasons(candidate: Any) -> tuple[str, ...]:
    reasons: list[str] = []
    if not isinstance(candidate, Mapping):
        reasons.append("raw executor output candidate must be a mapping")
        return tuple(reasons)

    normalized_keys = frozenset(_normalize_key(str(key)) for key in candidate)
    if _DIRECT_PACKET_FIELDS & normalized_keys:
        reasons.append("packet-shaped candidate rejected")
    missing_fields = _REQUIRED_STRUCTURED_PROPOSAL_FIELDS - normalized_keys
    if missing_fields:
        reasons.append("missing required structured proposal fields")

    _collect_blocked_field_reasons(candidate, "raw_output", reasons)
    return tuple(_unique(reasons))


def _collect_blocked_field_reasons(
    value: Any,
    location: str,
    reasons: list[str],
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in _BLOCKED_FIELD_NAMES:
                reasons.append(f"blocked raw output field rejected: {nested_location}")
            _collect_blocked_field_reasons(nested, nested_location, reasons)
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            _collect_blocked_field_reasons(nested, f"{location}[{index}]", reasons)


def _clone_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_data(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_clone_json_data(nested) for nested in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported fixture data type: {type(value).__name__}")


def _normalize_key(value: str) -> str:
    dash_normalized = "_".join(value.strip().lower().split("-"))
    return "_".join(dash_normalized.split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


__all__ = [
    "ALLOWED_FIXTURE_IDS",
    "DETERMINISTIC_MODEL_LIKE_ADAPTER_VERSION",
    "FIXTURE_INPUT_FIELD",
    "REJECTION_FIXTURE_IDS",
    "SAFE_PROPOSAL_FIXTURE_ID",
    "build_deterministic_model_like_adapter_evidence",
    "build_deterministic_model_like_fixture_input",
    "build_no_tool_model_like_adapter_structure",
    "produce_deterministic_model_like_raw_output",
]
