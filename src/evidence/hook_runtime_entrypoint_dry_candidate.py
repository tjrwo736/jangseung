"""Phase 11-C dry runtime-readiness entrypoint candidate.

This module provides an in-memory dry-run helper for the Phase 11-C candidate
chain. It accepts an already-provided Claude Code PreToolUse mapping and
returns a dry-run result record only. It does not read stdin, write stdout or
stderr, call exit, install hooks, execute tools, call providers, load secrets,
write state, or mutate the filesystem.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.claude_code_pretooluse_input_contract import (
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.hook_decision_adapter import (
    adapt_structured_action_candidate_to_hook_decision_candidate,
)
from src.evidence.hook_evidence_binding import build_hook_evidence_binding
from src.evidence.hook_evidence_verification_gate import (
    verify_hook_evidence_binding_candidate,
)
from src.evidence.hook_response_envelope_candidate import (
    RESPONSE_DEFER,
    RESPONSE_HOLD_CURRENT_STATE,
    build_hook_response_envelope_candidate,
)
from src.evidence.hook_response_serialization_candidate import (
    build_hook_response_serialization_candidate,
)
from src.evidence.claude_code_pretooluse_response_schema_candidate import (
    PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
    build_claude_code_pretooluse_response_schema_candidate,
)

PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION = (
    "phase11c_hook_runtime_entrypoint_dry_candidate_v0"
)
DRY_RUNTIME_RESULT_HASH_ALGORITHM = "sha256_canonical_json_v0"

_DRY_RUN_RESULT_ID_PREFIX = "phase11c-dry-runtime-result:"

_RUNTIME_TRUE_FLAG_KEYS = frozenset(
    {
        "action_execution_engine_implemented",
        "api_key_env_secret_loading_implemented",
        "claude_code_execution_performed",
        "execution_allowed",
        "execution_performed",
        "filesystem_mutation_performed",
        "hook_command_implemented",
        "hook_installation_implemented",
        "install_performed",
        "llm_call_implemented",
        "mutation_allowed",
        "network_client_implemented",
        "provider_model_network_implemented",
        "real_hook_response_emitted",
        "runtime",
        "runtime_enabled",
        "runtime_flag",
        "shell_execution_implemented",
        "state_store_module_changed",
        "store_write_performed",
        "tool_runtime_implemented",
        "write_authority_granted",
    }
)

_DRY_RUN_RESULT_PAYLOAD_FIELDS = (
    "dry_run_result_version",
    "completion_label",
    "source_tool_use_id",
    "resulting_candidate_type",
    "response_schema_candidate_hash",
    "would_emit_stdout",
    "stdout_payload",
    "stderr_payload",
    "install_performed",
    "execution_performed",
    "safe_default",
    "live_executor_authority",
    "dry_run_result_hash_algorithm",
    "dry_runtime_entrypoint_candidate_is_hook_runtime",
    "dry_runtime_entrypoint_candidate_is_installed_hook",
    "dry_runtime_entrypoint_candidate_is_execution",
    "dry_runtime_entrypoint_candidate_is_action_execution_engine",
    "dry_runtime_entrypoint_candidate_is_write_authority",
    "dry_runtime_entrypoint_candidate_is_store_write",
    "dry_runtime_entrypoint_mutates_filesystem",
    "dry_runtime_entrypoint_reads_stdin",
    "dry_runtime_entrypoint_writes_stdout",
    "dry_runtime_entrypoint_writes_stderr",
    "dry_runtime_entrypoint_calls_exit",
    "dry_runtime_entrypoint_executes_claude_code",
    "dry_runtime_entrypoint_executes_tools",
    "dry_runtime_entrypoint_calls_provider_model_network",
    "dry_runtime_entrypoint_loads_api_keys_env_secrets",
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
    "filesystem_mutation_by_dry_entrypoint",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)


@dataclass(frozen=True)
class HookRuntimeDryRunResultCandidate:
    dry_run_result_id: str
    dry_run_result_hash: str
    dry_run_result_version: str
    completion_label: str
    source_tool_use_id: str | None
    resulting_candidate_type: str
    response_schema_candidate_hash: str
    would_emit_stdout: bool
    stdout_payload: None
    stderr_payload: None
    install_performed: bool
    execution_performed: bool
    safe_default: str
    live_executor_authority: str
    dry_run_result_hash_algorithm: str = DRY_RUNTIME_RESULT_HASH_ALGORITHM
    dry_runtime_entrypoint_candidate_is_hook_runtime: bool = False
    dry_runtime_entrypoint_candidate_is_installed_hook: bool = False
    dry_runtime_entrypoint_candidate_is_execution: bool = False
    dry_runtime_entrypoint_candidate_is_action_execution_engine: bool = False
    dry_runtime_entrypoint_candidate_is_write_authority: bool = False
    dry_runtime_entrypoint_candidate_is_store_write: bool = False
    dry_runtime_entrypoint_mutates_filesystem: bool = False
    dry_runtime_entrypoint_reads_stdin: bool = False
    dry_runtime_entrypoint_writes_stdout: bool = False
    dry_runtime_entrypoint_writes_stderr: bool = False
    dry_runtime_entrypoint_calls_exit: bool = False
    dry_runtime_entrypoint_executes_claude_code: bool = False
    dry_runtime_entrypoint_executes_tools: bool = False
    dry_runtime_entrypoint_calls_provider_model_network: bool = False
    dry_runtime_entrypoint_loads_api_keys_env_secrets: bool = False
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
    filesystem_mutation_by_dry_entrypoint: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "dry_run_result_id": self.dry_run_result_id,
            "dry_run_result_hash": self.dry_run_result_hash,
            **_plain_json_data(_dry_run_result_payload(self)),
        }


def run_pretooluse_dry_runtime_entrypoint_candidate(
    raw_pretooluse_input: Mapping[str, Any] | Any,
) -> HookRuntimeDryRunResultCandidate:
    """Run the Phase 11-C candidate chain in memory and return a dry result."""

    source_tool_use_id: str | None = None
    if _contains_runtime_true_flag(raw_pretooluse_input):
        response_schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
            {"phase11c_dry_entrypoint_rejection": "runtime_true_flag_detected"}
        )
        return _build_dry_run_result(
            source_tool_use_id=None,
            resulting_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
            response_schema_candidate_hash=(
                response_schema_candidate.response_schema_candidate_hash
            ),
        )

    validation = validate_claude_code_pretooluse_input(raw_pretooluse_input)
    if not validation.valid or validation.hook_input is None:
        response_schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
            {"phase11c_dry_entrypoint_rejection": "invalid_pretooluse_input"}
        )
        return _build_dry_run_result(
            source_tool_use_id=None,
            resulting_candidate_type=RESPONSE_HOLD_CURRENT_STATE,
            response_schema_candidate_hash=(
                response_schema_candidate.response_schema_candidate_hash
            ),
        )

    source_tool_use_id = validation.hook_input.tool_use_id
    action_candidate = map_pretooluse_input_to_structured_action_candidate(
        validation.hook_input
    )
    decision_candidate = adapt_structured_action_candidate_to_hook_decision_candidate(
        action_candidate
    )
    binding = build_hook_evidence_binding(
        hook_input=validation.hook_input,
        action_candidate=action_candidate,
        decision_candidate=decision_candidate,
    )
    verification = verify_hook_evidence_binding_candidate(binding)
    envelope = build_hook_response_envelope_candidate(
        verification_result=verification,
        binding_record=binding,
        decision_candidate=decision_candidate,
    )
    serialization = build_hook_response_serialization_candidate(
        envelope_candidate=envelope
    )
    response_schema_candidate = build_claude_code_pretooluse_response_schema_candidate(
        serialization
    )

    return _build_dry_run_result(
        source_tool_use_id=source_tool_use_id,
        resulting_candidate_type=_dry_resulting_candidate_type(
            response_schema_candidate.response_schema_candidate_type
        ),
        response_schema_candidate_hash=(
            response_schema_candidate.response_schema_candidate_hash
        ),
    )


def hook_runtime_dry_run_result_candidate_digest(
    record: HookRuntimeDryRunResultCandidate | Mapping[str, Any],
) -> str:
    """Recompute the deterministic digest for a dry runtime result."""

    if isinstance(record, HookRuntimeDryRunResultCandidate):
        return _sha256_json(_dry_run_result_payload(record))
    if isinstance(record, Mapping):
        missing = _missing_fields(record, _DRY_RUN_RESULT_PAYLOAD_FIELDS)
        if missing:
            raise ValueError(f"missing dry runtime result payload fields: {missing!r}")
        return _sha256_json(
            {field: record[field] for field in _DRY_RUN_RESULT_PAYLOAD_FIELDS}
        )
    raise TypeError(type(record).__name__)


def build_hook_runtime_entrypoint_dry_candidate_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION,
        "completion_label": PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        "input": "raw PreToolUse mapping fixture already provided in memory",
        "output": "HookRuntimeDryRunResultCandidate in-memory object only",
        "source_chain": (
            "11-C-1 ClaudeCodePreToolUseInput",
            "11-C-2 ToolCallStructuredActionCandidate",
            "11-C-3 HookDecisionCandidate",
            "11-C-4 HookEvidenceBinding",
            "11-C-5 HookEvidenceVerificationGateResult",
            "11-C-6 HookResponseEnvelopeCandidate",
            "11-C-7 HookResponseSerializationCandidate",
            "11-C runtime-readiness response schema candidate",
            "11-C dry entrypoint candidate",
        ),
        "would_emit_stdout": False,
        "stdout_payload": None,
        "stderr_payload": None,
        "install_performed": False,
        "execution_performed": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "malformed_input_policy": RESPONSE_HOLD_CURRENT_STATE,
        "runtime_true_flag_policy": RESPONSE_HOLD_CURRENT_STATE,
        "dry_runtime_entrypoint_candidate_is_hook_runtime": False,
        "dry_runtime_entrypoint_candidate_is_installed_hook": False,
        "dry_runtime_entrypoint_candidate_is_execution": False,
        "dry_runtime_entrypoint_candidate_is_action_execution_engine": False,
        "dry_runtime_entrypoint_candidate_is_write_authority": False,
        "dry_runtime_entrypoint_candidate_is_store_write": False,
        "dry_runtime_entrypoint_mutates_filesystem": False,
        "dry_runtime_entrypoint_reads_stdin": False,
        "dry_runtime_entrypoint_writes_stdout": False,
        "dry_runtime_entrypoint_writes_stderr": False,
        "dry_runtime_entrypoint_calls_exit": False,
        "dry_runtime_entrypoint_executes_claude_code": False,
        "dry_runtime_entrypoint_executes_tools": False,
        "dry_runtime_entrypoint_calls_provider_model_network": False,
        "dry_runtime_entrypoint_loads_api_keys_env_secrets": False,
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
        "filesystem_mutation_by_dry_entrypoint": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _build_dry_run_result(
    *,
    source_tool_use_id: str | None,
    resulting_candidate_type: str,
    response_schema_candidate_hash: str,
) -> HookRuntimeDryRunResultCandidate:
    payload = {
        "dry_run_result_version": PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION,
        "completion_label": PHASE11C_RUNTIME_READINESS_COMPLETION_LABEL,
        "source_tool_use_id": source_tool_use_id,
        "resulting_candidate_type": resulting_candidate_type,
        "response_schema_candidate_hash": response_schema_candidate_hash,
        "would_emit_stdout": False,
        "stdout_payload": None,
        "stderr_payload": None,
        "install_performed": False,
        "execution_performed": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "dry_run_result_hash_algorithm": DRY_RUNTIME_RESULT_HASH_ALGORITHM,
        "dry_runtime_entrypoint_candidate_is_hook_runtime": False,
        "dry_runtime_entrypoint_candidate_is_installed_hook": False,
        "dry_runtime_entrypoint_candidate_is_execution": False,
        "dry_runtime_entrypoint_candidate_is_action_execution_engine": False,
        "dry_runtime_entrypoint_candidate_is_write_authority": False,
        "dry_runtime_entrypoint_candidate_is_store_write": False,
        "dry_runtime_entrypoint_mutates_filesystem": False,
        "dry_runtime_entrypoint_reads_stdin": False,
        "dry_runtime_entrypoint_writes_stdout": False,
        "dry_runtime_entrypoint_writes_stderr": False,
        "dry_runtime_entrypoint_calls_exit": False,
        "dry_runtime_entrypoint_executes_claude_code": False,
        "dry_runtime_entrypoint_executes_tools": False,
        "dry_runtime_entrypoint_calls_provider_model_network": False,
        "dry_runtime_entrypoint_loads_api_keys_env_secrets": False,
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
        "filesystem_mutation_by_dry_entrypoint": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }
    dry_run_result_hash = _sha256_json(payload)
    return HookRuntimeDryRunResultCandidate(
        dry_run_result_id=f"{_DRY_RUN_RESULT_ID_PREFIX}{dry_run_result_hash}",
        dry_run_result_hash=dry_run_result_hash,
        **payload,
    )


def _contains_runtime_true_flag(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in _RUNTIME_TRUE_FLAG_KEYS and nested is True:
                return True
            if _contains_runtime_true_flag(nested):
                return True
        return False
    if _is_sequence(value):
        return any(_contains_runtime_true_flag(nested) for nested in value)
    return False


def _dry_resulting_candidate_type(response_schema_candidate_type: str) -> str:
    if response_schema_candidate_type == RESPONSE_DEFER:
        return RESPONSE_HOLD_CURRENT_STATE
    return response_schema_candidate_type


def _dry_run_result_payload(record: HookRuntimeDryRunResultCandidate) -> dict[str, Any]:
    return {field: getattr(record, field) for field in _DRY_RUN_RESULT_PAYLOAD_FIELDS}


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


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


__all__ = [
    "DRY_RUNTIME_RESULT_HASH_ALGORITHM",
    "PHASE11C_DRY_RUNTIME_ENTRYPOINT_CANDIDATE_VERSION",
    "HookRuntimeDryRunResultCandidate",
    "build_hook_runtime_entrypoint_dry_candidate_contract_evidence",
    "hook_runtime_dry_run_result_candidate_digest",
    "run_pretooluse_dry_runtime_entrypoint_candidate",
]
