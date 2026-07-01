"""Evidence packet schema checks for v0.1."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    ACTION_AUTHORITY_FIELDS,
    ACTION_BOUNDARY_CLEAN,
    ACTION_BOUNDARY_FIELDS,
    ACTION_BOUNDARY_NOT_CHECKED,
    ACTION_BOUNDARY_SCAFFOLD_V0,
    ACTION_BOUNDARY_STATUSES,
    ACTION_HIGH_RISK_KINDS,
    ACTION_LOG_SOURCE_NONE,
    ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    ACTION_LOG_SOURCE_TRUST_BOUNDARIES,
    ACTION_LOG_SOURCES,
    AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS,
    AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUSES,
    AEG_STATE_WRITE_DENIAL_FIELDS,
    AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD,
    AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY,
    AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0,
    AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA,
    AEG_STATE_WRITE_DENIAL_STATUSES,
    AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY,
    AEG_VERSION,
    BINDING_STATUSES,
    BOUND,
    CAPABILITY_AUTHORITY_FIELDS,
    CAPABILITY_BOUNDARY_CLEAN,
    CAPABILITY_BOUNDARY_NOT_CHECKED,
    CAPABILITY_BOUNDARY_SOURCE_NONE,
    CAPABILITY_BOUNDARY_STATUSES,
    CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_FIELDS,
    CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED,
    CAPABILITY_ISOLATION_SCAFFOLD_V0,
    CHANGED_FILES_SOURCES,
    CLEAN_CORE,
    COMPLETION_CONTRACT_V0,
    CONTRACT_FIRST_NOOP,
    CITIZEN_ONE_EVIDENCE_FIELDS,
    CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_HOLD_REASON_NONE,
    CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_MODE_OFF,
    CITIZEN_ONE_MODE_PROPOSE,
    CITIZEN_ONE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED,
    CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
    CITIZEN_ONE_PROPOSAL_RECORDED,
    CITIZEN_ONE_STATUSES,
    DETERMINISTIC_STUB_PROPOSAL_ID,
    DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES,
    DETERMINISTIC_STUB_PROPOSAL_STEPS,
    DETERMINISTIC_STUB_PROPOSAL_SUMMARY,
    EVIDENCE_STORE_CLEAN,
    EVIDENCE_STORE_INTEGRITY_NOT_CHECKED,
    EVIDENCE_STORE_INTEGRITY_STATUSES,
    EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED,
    EVIDENCE_STORE_TRUST_FIELDS,
    EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE,
    EVIDENCE_STORE_WRITER_AEGIS_RUNTIME,
    EVIDENCE_BINDING_V1,
    EVIDENCE_BINDING_V1_FIELDS,
    EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY,
    EXECUTOR_CAPABILITY_BOOL_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_FIELDS,
    EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0,
    EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP,
    EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT,
    EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME,
    EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL,
    EXECUTOR_CAPABILITY_TRANSPORT_NONE,
    EXECUTOR_CAPABILITY_TRANSPORTS,
    FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS,
    GIT_STATUS_PORCELAIN_V1,
    HIGH,
    IMPACT_RISKS,
    LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY,
    LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED,
    LEDGER_INTEGRITY_CHECK_STATUSES,
    LEDGER_INTEGRITY_FIELDS,
    LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD,
    LEDGER_INTEGRITY_SCAFFOLD_V0,
    LEDGER_INTEGRITY_STATUSES,
    LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY,
    LEDGER_PREVIOUS_HASH_GENESIS,
    LEDGER_PREVIOUS_HASH_NOT_AVAILABLE,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NOT_CHECKED,
    NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION,
    MUTATION_BOUNDARY_CLEAN,
    MUTATION_BOUNDARY_STATUSES,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_DELTA_SOURCE_COMPUTED,
    MUTATION_DELTA_SOURCE_UNTRUSTED,
    PROVIDER_ADAPTER_DISABLED_FIELDS,
    PROVIDER_ADAPTER_DISABLED_REQUEST_ID,
    PROVIDER_ENV_LOADING_STATUS_DISABLED,
    PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED,
    PROVIDER_ENV_LOADING_STATUSES,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_NOT_REQUESTED,
    PROVIDER_MODES,
    PROVIDER_MODEL_NONE,
    PROVIDER_NAME_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED,
    PROVIDER_NETWORK_BLOCK_REASONS,
    PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
    PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN,
    PROVIDER_NETWORK_STATUS_NOT_REQUESTED,
    PROVIDER_NETWORK_STATUSES,
    PROVIDER_PROMPT_SOURCE_DISABLED,
    PROVIDER_PROMPT_SOURCE_NONE,
    PROVIDER_PROMPT_SOURCES,
    PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROVIDER_REDACTION_STATUSES,
    PROVIDER_REQUEST_METADATA_FIELDS,
    PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED,
    PROVIDER_REQUEST_STATUS_NOT_REQUESTED,
    PROVIDER_REQUEST_STATUSES,
    PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
    PROVIDER_RESPONSE_ERROR_CLASS_NONE,
    PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RESPONSE_ERROR_CLASSES,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
    PROVIDER_RESPONSE_SOURCE_NONE,
    PROVIDER_RESPONSE_SOURCES,
    PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RESPONSE_STATUSES,
    PROVIDER_RUNTIME_ERROR_CLASS_NONE,
    PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_ERROR_CLASSES,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED,
    PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_HOLD_REASONS,
    PROVIDER_RUNTIME_STATE_FIELDS,
    PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE,
    PROVIDER_RUNTIME_STATES,
    PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_STATUS_NOT_REQUESTED,
    PROVIDER_RUNTIME_STATUSES,
    PROVIDER_SECRET_ENV_METADATA_FIELDS,
    PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
    PROVIDER_SECRET_REDACTION_STATUSES,
    PROVIDER_SECRET_SOURCE_NONE,
    PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
    PROVIDER_SECRET_SOURCES,
    PROVIDER_SELECTION_METADATA_FIELDS,
    PROVIDER_SELECTION_SOURCE_DISABLED,
    PROVIDER_SELECTION_SOURCE_NOT_REQUESTED,
    PROVIDER_SELECTION_SOURCES,
    PROVIDER_SELECTION_STATUS_NOT_CONFIGURED,
    PROVIDER_SELECTION_STATUS_NOT_REQUESTED,
    PROVIDER_SELECTION_STATUSES,
    LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE,
    PRE_LIVE_EXECUTOR_GATE_FIELDS,
    PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD,
    PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS,
    PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY,
    PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE,
    PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    PRE_LIVE_EXECUTOR_GATE_RESULTS,
    PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0,
    PRE_LIVE_EXECUTOR_GATE_STATUSES,
    PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD,
    PROMPT_BUILD_STATUS_NOT_BUILT,
    PROMPT_BUILD_STATUS_PROVIDER_DISABLED,
    PROMPT_BUILD_STATUSES,
    PROMPT_REDACTION_METADATA_FIELDS,
    PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED,
    PROMPT_REDACTION_STATUSES,
    PROMPT_SOURCE_DISABLED,
    PROMPT_SOURCE_NONE,
    PROMPT_SOURCES,
    PROMPT_STORAGE_POLICIES,
    PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE,
    PROPOSAL_CONTRACT_FIELDS,
    PROPOSAL_HOLD_REASON_NONE,
    PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROPOSAL_KIND_DETERMINISTIC_STUB,
    PROPOSAL_KIND_NOT_GENERATED,
    PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROPOSAL_REDACTION_STATUSES,
    PROPOSAL_SOURCE_DETERMINISTIC_STUB,
    PROPOSAL_SOURCE_NONE,
    PROPOSAL_STATUSES,
    PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
    PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
    RISK_LEVELS,
    SAFE_DEFAULT,
    SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
    STATUSES,
    REPORTED_ONLY,
    RESPONSE_ERROR_CLASS_NONE,
    RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    RESPONSE_ERROR_CLASSES,
    RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED,
    RESPONSE_REDACTION_METADATA_FIELDS,
    RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED,
    RESPONSE_REDACTION_STATUSES,
    RESPONSE_SOURCE_DISABLED_ADAPTER,
    RESPONSE_SOURCE_NONE,
    RESPONSE_SOURCES,
    RESPONSE_STATUS_NOT_REQUESTED,
    RESPONSE_STATUS_PROVIDER_DISABLED,
    RESPONSE_STATUSES,
    TOOL_AUTHORITY_GRANT_FIELDS,
    TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0,
    TOOL_SURFACE_CLEAN,
    TOOL_SURFACE_FIELDS,
    TOOL_SURFACE_SCAFFOLD_ONLY,
    TOOL_SURFACE_SOURCE_NONE,
    TOOL_SURFACE_STATUSES,
    TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED,
)
from src.evidence.aeg_state_write_denial import expected_aeg_state_write_denial_metadata_hash
from src.evidence.action_boundary import expected_action_log_hash
from src.evidence.capability_exposure import (
    expected_executor_capability_exposure_hash,
    expected_executor_capability_exposure_metadata_hash,
)
from src.evidence.capability_isolation import (
    expected_capability_isolation_proof_hash,
    expected_capability_matrix_hash,
)
from src.evidence.evidence_store import expected_evidence_store_trust_metadata_hash
from src.evidence.ledger_integrity import (
    expected_current_evidence_hash,
    expected_ledger_chain_hash,
    expected_ledger_integrity_metadata_hash,
    is_sha256_hex,
)
from src.evidence.pre_live_executor_gate import expected_pre_live_executor_gate_metadata_hash
from src.evidence.tool_surface import (
    expected_tool_authority_grant_hash,
    expected_tool_surface_metadata_hash,
)


REQUIRED_FIELDS: tuple[str, ...] = (
    "aeg_version",
    "run_id",
    "task_text",
    "repo_root",
    "branch",
    "head_sha",
    "tree_sha",
    "is_dirty",
    "changed_files",
    "changed_files_source",
    "intent_risk",
    "impact_risk",
    "risk_level",
    "classification_reasons",
    "impact_reasons",
    "protected_paths_touched",
    "risk_escalation_applied",
    "final_risk_rule",
    "impact_checked_at",
    "checks",
    "status",
    "status_reasons",
    "safe_default",
    "pre_run_changed_files",
    "post_run_changed_files",
    "pre_snapshot_source",
    "post_snapshot_source",
    "snapshot_collector",
    "snapshot_trust_boundary",
    "executor_reported_changed_files",
    "executor_reported_mutation_delta",
    "computed_mutation_delta",
    "mutation_delta_source",
    "pre_existing_dirty_tree",
    "executor_created_mutation",
    "protected_path_mutation_detected",
    "mutation_boundary_status",
    *CITIZEN_ONE_EVIDENCE_FIELDS,
    *PROVIDER_ADAPTER_DISABLED_FIELDS,
    *PROVIDER_RUNTIME_STATE_FIELDS,
    *PROVIDER_SELECTION_METADATA_FIELDS,
    *PROVIDER_SECRET_ENV_METADATA_FIELDS,
    *PROVIDER_NETWORK_GUARD_METADATA_FIELDS,
    *PROVIDER_REQUEST_METADATA_FIELDS,
    *PROVIDER_RESPONSE_ERROR_METADATA_FIELDS,
    *PROMPT_REDACTION_METADATA_FIELDS,
    *RESPONSE_REDACTION_METADATA_FIELDS,
    *ACTION_BOUNDARY_FIELDS,
    *CAPABILITY_ISOLATION_FIELDS,
    *TOOL_SURFACE_FIELDS,
    *EXECUTOR_CAPABILITY_EXPOSURE_FIELDS,
    *EVIDENCE_STORE_TRUST_FIELDS,
    *AEG_STATE_WRITE_DENIAL_FIELDS,
    *PRE_LIVE_EXECUTOR_GATE_FIELDS,
    *LEDGER_INTEGRITY_FIELDS,
)

BINDING_REQUIRED_FIELDS: tuple[str, ...] = (
    "repo_root",
    "branch",
    "head_sha",
    "tree_sha",
    "changed_files",
    "changed_files_source",
    "risk_level",
    "status",
    "run_id",
)

BINDING_V1_REQUIRED_FIELDS: tuple[str, ...] = EVIDENCE_BINDING_V1_FIELDS

USER_GATE_REASON_CARD_FIELDS: tuple[str, ...] = (
    "risk_level",
    "status",
    "why_gate_is_required",
    "irreversible_action_blocked",
    "intent_risk",
    "impact_risk",
    "protected_paths_touched",
    "safe_default",
)


def validate_evidence_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in packet:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    _expect(packet, "aeg_version", str, errors)
    _expect(packet, "run_id", str, errors)
    _expect(packet, "task_text", str, errors)
    _expect(packet, "repo_root", str, errors)
    _expect(packet, "branch", str, errors)
    _expect(packet, "head_sha", str, errors)
    _expect(packet, "tree_sha", str, errors)
    _expect(packet, "is_dirty", bool, errors)
    _expect(packet, "changed_files", list, errors)
    _expect(packet, "changed_files_source", str, errors)
    _expect(packet, "classification_reasons", list, errors)
    _expect(packet, "impact_reasons", list, errors)
    _expect(packet, "protected_paths_touched", list, errors)
    _expect(packet, "risk_escalation_applied", bool, errors)
    _expect(packet, "final_risk_rule", str, errors)
    _expect(packet, "impact_checked_at", str, errors)
    _expect(packet, "checks", dict, errors)
    _expect(packet, "status_reasons", list, errors)
    _expect(packet, "safe_default", str, errors)
    _expect(packet, "pre_run_changed_files", list, errors)
    _expect(packet, "post_run_changed_files", list, errors)
    _expect(packet, "pre_snapshot_source", str, errors)
    _expect(packet, "post_snapshot_source", str, errors)
    _expect(packet, "snapshot_collector", str, errors)
    _expect(packet, "snapshot_trust_boundary", dict, errors)
    _expect(packet, "executor_reported_changed_files", list, errors)
    _expect(packet, "executor_reported_mutation_delta", list, errors)
    _expect(packet, "computed_mutation_delta", list, errors)
    _expect(packet, "mutation_delta_source", str, errors)
    _expect(packet, "pre_existing_dirty_tree", list, errors)
    _expect(packet, "executor_created_mutation", list, errors)
    _expect(packet, "protected_path_mutation_detected", bool, errors)
    _expect(packet, "mutation_boundary_status", str, errors)
    _validate_citizen_one_fields(packet, errors)
    _validate_provider_adapter_disabled_fields(packet, errors)
    _validate_provider_runtime_state_metadata(packet, errors)
    _validate_provider_selection_metadata(packet, errors)
    _validate_provider_secret_env_metadata(packet, errors)
    _validate_provider_network_guard_metadata(packet, errors)
    _validate_provider_request_metadata(packet, errors)
    _validate_provider_response_error_metadata(packet, errors)
    _validate_prompt_redaction_metadata_fields(packet, errors)
    _validate_response_redaction_metadata_fields(packet, errors)
    _validate_action_boundary_metadata(packet, errors)
    _validate_capability_isolation_metadata(packet, errors)
    _validate_tool_surface_metadata(packet, errors)
    _validate_executor_capability_exposure_metadata(packet, errors)
    _validate_evidence_store_trust_metadata(packet, errors)
    _validate_aeg_state_write_denial_metadata(packet, errors)
    _validate_pre_live_executor_gate_metadata(packet, errors)
    _validate_ledger_integrity_metadata(packet, errors)
    _validate_forbidden_raw_prompt_response_fields(packet, errors)

    if packet.get("aeg_version") != AEG_VERSION:
        errors.append(f"unsupported aeg_version: {packet.get('aeg_version')}")
    if packet.get("safe_default") != SAFE_DEFAULT:
        errors.append("safe_default must be hold_current_state")
    if packet.get("intent_risk") not in RISK_LEVELS:
        errors.append(f"invalid intent_risk: {packet.get('intent_risk')}")
    if packet.get("risk_level") not in RISK_LEVELS:
        errors.append(f"invalid risk_level: {packet.get('risk_level')}")
    if packet.get("impact_risk") not in IMPACT_RISKS:
        errors.append(f"invalid impact_risk: {packet.get('impact_risk')}")
    if packet.get("changed_files_source") not in CHANGED_FILES_SOURCES:
        errors.append(f"invalid changed_files_source: {packet.get('changed_files_source')}")
    if packet.get("status") not in STATUSES:
        errors.append(f"invalid status: {packet.get('status')}")
    if packet.get("mutation_boundary_status") not in MUTATION_BOUNDARY_STATUSES:
        errors.append(f"invalid mutation_boundary_status: {packet.get('mutation_boundary_status')}")
    if packet.get("pre_snapshot_source") != GIT_STATUS_PORCELAIN_V1:
        errors.append(f"invalid pre_snapshot_source: {packet.get('pre_snapshot_source')}")
    if packet.get("post_snapshot_source") != GIT_STATUS_PORCELAIN_V1:
        errors.append(f"invalid post_snapshot_source: {packet.get('post_snapshot_source')}")
    if packet.get("snapshot_collector") != SNAPSHOT_COLLECTOR_GIT_STATUS_V1:
        errors.append(f"invalid snapshot_collector: {packet.get('snapshot_collector')}")
    if packet.get("mutation_delta_source") not in (MUTATION_DELTA_SOURCE_COMPUTED, MUTATION_DELTA_SOURCE_UNTRUSTED):
        errors.append(f"invalid mutation_delta_source: {packet.get('mutation_delta_source')}")
    if packet.get("status") == "PASS":
        errors.append("PASS is not a valid Day-1 status")
    if not all(isinstance(item, str) for item in packet.get("changed_files", [])):
        errors.append("changed_files must contain only strings")
    if not all(isinstance(item, str) for item in packet.get("classification_reasons", [])):
        errors.append("classification_reasons must contain only strings")
    if not all(isinstance(item, str) for item in packet.get("impact_reasons", [])):
        errors.append("impact_reasons must contain only strings")
    if not all(isinstance(item, str) for item in packet.get("protected_paths_touched", [])):
        errors.append("protected_paths_touched must contain only strings")
    if not all(isinstance(item, str) for item in packet.get("status_reasons", [])):
        errors.append("status_reasons must contain only strings")
    if not all(isinstance(item, dict) for item in packet.get("pre_run_changed_files", [])):
        errors.append("pre_run_changed_files must contain only objects")
    if not all(isinstance(item, dict) for item in packet.get("post_run_changed_files", [])):
        errors.append("post_run_changed_files must contain only objects")
    if not all(isinstance(item, dict) for item in packet.get("computed_mutation_delta", [])):
        errors.append("computed_mutation_delta must contain only objects")
    if not all(isinstance(item, dict) for item in packet.get("pre_existing_dirty_tree", [])):
        errors.append("pre_existing_dirty_tree must contain only objects")
    if not all(isinstance(item, dict) for item in packet.get("executor_created_mutation", [])):
        errors.append("executor_created_mutation must contain only objects")

    trust_boundary = packet.get("snapshot_trust_boundary")
    if isinstance(trust_boundary, dict):
        if trust_boundary.get("executor_controlled") is not False:
            errors.append("INVALID_EVIDENCE: snapshot collector must be outside executor control")
        if trust_boundary.get("trust_boundary_satisfied") is not True:
            if packet.get("mutation_boundary_status") != MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT:
                errors.append("INVALID_EVIDENCE: untrusted snapshot boundary must not be marked clean")
        if packet.get("mutation_boundary_status") == MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT and packet.get("status") == CLEAN_CORE:
            errors.append("INVALID_EVIDENCE: untrusted snapshot boundary cannot be CLEAN_CORE")

    return errors


def _validate_citizen_one_fields(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "citizen_one_requested",
        "citizen_one_output_present",
        "citizen_one_reported_only",
        "provider_network_used",
        "provider_secret_observed",
    )
    string_fields = (
        "citizen_one_mode",
        "citizen_one_status",
        "citizen_one_provider_status",
        "citizen_one_output_trust_boundary",
        "citizen_one_hold_reason",
        "provider_config_source",
        "model_output_hash_candidate",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("citizen_one_status") not in CITIZEN_ONE_STATUSES:
        errors.append(f"invalid citizen_one_status: {packet.get('citizen_one_status')}")
    if packet.get("citizen_one_output_trust_boundary") != REPORTED_ONLY:
        errors.append("INVALID_EVIDENCE: Citizen One output trust boundary must be reported_only")
    if packet.get("citizen_one_reported_only") is not True:
        errors.append("INVALID_EVIDENCE: Citizen One output must be marked reported_only")
    if packet.get("provider_network_used") is not False:
        errors.append("INVALID_EVIDENCE: Citizen One provider_network_used must be false")
    if packet.get("provider_secret_observed") is not False:
        errors.append("INVALID_EVIDENCE: Citizen One provider_secret_observed must be false")
    if packet.get("model_output_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: model_output_hash_candidate must be empty when no model output exists")

    if packet.get("citizen_one_requested") is True:
        if packet.get("citizen_one_mode") != CITIZEN_ONE_MODE_PROPOSE:
            errors.append("INVALID_EVIDENCE: requested Citizen One mode must be propose")
        if packet.get("citizen_one_provider_status") != CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested Citizen One provider status must be not_configured")
        if packet.get("provider_config_source") != CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: requested Citizen One provider_config_source must be none")
        _validate_proposal_contract_fields(packet, errors)
        if packet.get("proposal_present") is True:
            if packet.get("citizen_one_status") != CITIZEN_ONE_PROPOSAL_RECORDED:
                errors.append("INVALID_EVIDENCE: deterministic proposal stub must record Citizen One proposal status")
            if packet.get("citizen_one_hold_reason") != CITIZEN_ONE_HOLD_REASON_NONE:
                errors.append("INVALID_EVIDENCE: deterministic proposal stub hold reason must be empty")
            if packet.get("citizen_one_output_present") is not True:
                errors.append("INVALID_EVIDENCE: deterministic proposal stub must mark Citizen One output present")
        else:
            if packet.get("citizen_one_status") != CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED:
                errors.append("INVALID_EVIDENCE: requested Citizen One must hold when provider is not configured")
            if packet.get("citizen_one_hold_reason") != CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED:
                errors.append("INVALID_EVIDENCE: requested Citizen One hold reason must be provider_not_configured")
            if packet.get("citizen_one_output_present") is not False:
                errors.append("INVALID_EVIDENCE: Citizen One output must be absent in provider-not-configured skeleton")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("citizen_one_mode") != CITIZEN_ONE_MODE_OFF:
            errors.append("INVALID_EVIDENCE: non-requested Citizen One mode must be off")
        if packet.get("citizen_one_status") != CITIZEN_ONE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested Citizen One status must be CITIZEN_ONE_NOT_REQUESTED")
        if packet.get("citizen_one_provider_status") != CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested Citizen One provider status must be not_requested")
        if packet.get("citizen_one_hold_reason") != CITIZEN_ONE_HOLD_REASON_NONE:
            errors.append("INVALID_EVIDENCE: non-requested Citizen One hold reason must be empty")
        if packet.get("provider_config_source") != CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested Citizen One provider_config_source must be not_requested")
        for field in PROPOSAL_CONTRACT_FIELDS:
            if field in packet:
                errors.append(f"INVALID_EVIDENCE: proposal field is opt-in only: {field}")
    else:
        errors.append("INVALID_EVIDENCE: citizen_one_requested must be boolean")


def _validate_provider_adapter_disabled_fields(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_network_opt_in",
        "provider_secret_observed",
        "provider_response_present",
        "provider_response_reported_only",
    )
    string_fields = (
        "provider_request_id",
        "provider_mode",
        "provider_name",
        "provider_model",
        "provider_prompt_source",
        "provider_prompt_hash_candidate",
        "provider_request_redaction_status",
        "provider_secret_source",
        "provider_response_status",
        "provider_response_source",
        "provider_response_trust_boundary",
        "provider_response_hash_candidate",
        "provider_response_redaction_status",
        "provider_response_error_class",
        "provider_response_error_safe_summary",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_mode") not in PROVIDER_MODES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_mode: {packet.get('provider_mode')}")
    if packet.get("provider_prompt_source") not in PROVIDER_PROMPT_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_prompt_source: {packet.get('provider_prompt_source')}")
    if packet.get("provider_request_redaction_status") not in PROVIDER_REDACTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_request_redaction_status: "
            f"{packet.get('provider_request_redaction_status')}"
        )
    if packet.get("provider_response_redaction_status") not in PROVIDER_REDACTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_response_redaction_status: "
            f"{packet.get('provider_response_redaction_status')}"
        )
    if packet.get("provider_secret_source") not in PROVIDER_SECRET_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_secret_source: {packet.get('provider_secret_source')}")
    if packet.get("provider_response_status") not in PROVIDER_RESPONSE_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_response_status: {packet.get('provider_response_status')}")
    if packet.get("provider_response_source") not in PROVIDER_RESPONSE_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_response_source: {packet.get('provider_response_source')}")
    if packet.get("provider_response_error_class") not in PROVIDER_RESPONSE_ERROR_CLASSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_response_error_class: "
            f"{packet.get('provider_response_error_class')}"
        )

    if packet.get("provider_name") != PROVIDER_NAME_NONE:
        errors.append("INVALID_EVIDENCE: provider_name must be none in disabled contract")
    if packet.get("provider_model") != PROVIDER_MODEL_NONE:
        errors.append("INVALID_EVIDENCE: provider_model must be none in disabled contract")
    if packet.get("provider_prompt_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: provider_prompt_hash_candidate must be empty")
    if packet.get("provider_response_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: provider_response_hash_candidate must be empty")
    if packet.get("provider_request_redaction_status") != PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: provider request redaction must declare no raw prompt/response storage")
    if packet.get("provider_response_redaction_status") != PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: provider response redaction must declare no raw prompt/response storage")
    if packet.get("provider_network_opt_in") is not False:
        errors.append("INVALID_EVIDENCE: provider_network_opt_in must be false in disabled contract")
    if packet.get("provider_secret_observed") is not False:
        errors.append("INVALID_EVIDENCE: provider_secret_observed must be false in disabled contract")
    if packet.get("provider_response_present") is not False:
        errors.append("INVALID_EVIDENCE: provider_response_present must be false in disabled contract")
    if packet.get("provider_response_reported_only") is not True:
        errors.append("INVALID_EVIDENCE: provider response must be marked reported_only")
    if packet.get("provider_response_trust_boundary") != REPORTED_ONLY:
        errors.append("INVALID_EVIDENCE: provider response trust boundary must be reported_only")

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_request_id") != PROVIDER_ADAPTER_DISABLED_REQUEST_ID:
            errors.append("INVALID_EVIDENCE: provider_request_id must be provider_adapter_disabled_v0")
        if packet.get("provider_mode") != PROVIDER_MODE_DISABLED:
            errors.append("INVALID_EVIDENCE: requested provider adapter mode must be disabled")
        if packet.get("provider_prompt_source") != PROVIDER_PROMPT_SOURCE_DISABLED:
            errors.append("INVALID_EVIDENCE: requested provider prompt source must be disabled")
        if packet.get("provider_secret_source") != PROVIDER_SECRET_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: requested provider secret source must be none")
        if packet.get("provider_response_status") != PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: provider response status must be provider_not_configured")
        if packet.get("provider_response_source") != PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER:
            errors.append("INVALID_EVIDENCE: provider response source must be disabled_adapter")
        if packet.get("provider_response_error_class") != PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: provider response error class must be provider_not_configured")
        if packet.get("provider_response_error_safe_summary") != PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: provider response safe summary mismatch")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_request_id") != "":
            errors.append("INVALID_EVIDENCE: non-requested provider_request_id must be empty")
        if packet.get("provider_mode") != PROVIDER_MODE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider adapter mode must be not_requested")
        if packet.get("provider_prompt_source") != PROVIDER_PROMPT_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider prompt source must be none")
        if packet.get("provider_secret_source") != PROVIDER_SECRET_SOURCE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider secret source must be not_requested")
        if packet.get("provider_response_status") != PROVIDER_RESPONSE_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider response status must be not_requested")
        if packet.get("provider_response_source") != PROVIDER_RESPONSE_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider response source must be none")
        if packet.get("provider_response_error_class") != PROVIDER_RESPONSE_ERROR_CLASS_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider response error class must be empty")
        if packet.get("provider_response_error_safe_summary") != PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider response safe summary must be empty")


def _validate_provider_runtime_state_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    string_fields = (
        "provider_runtime_state",
        "provider_runtime_status",
        "provider_runtime_hold_reason",
        "provider_runtime_error_class",
        "provider_runtime_error_safe_summary",
    )
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_runtime_state") not in PROVIDER_RUNTIME_STATES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_runtime_state: {packet.get('provider_runtime_state')}")
    if packet.get("provider_runtime_state") != PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE:
        errors.append("INVALID_EVIDENCE: provider_runtime_state must preserve hold_current_state")
    if packet.get("provider_runtime_status") not in PROVIDER_RUNTIME_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_runtime_status: {packet.get('provider_runtime_status')}")
    if packet.get("provider_runtime_hold_reason") not in PROVIDER_RUNTIME_HOLD_REASONS:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_runtime_hold_reason: "
            f"{packet.get('provider_runtime_hold_reason')}"
        )
    if packet.get("provider_runtime_error_class") not in PROVIDER_RUNTIME_ERROR_CLASSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_runtime_error_class: "
            f"{packet.get('provider_runtime_error_class')}"
        )

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_runtime_status") != PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider runtime must hold as provider_not_configured")
        if packet.get("provider_runtime_hold_reason") != PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider runtime hold reason must be provider_not_configured")
        if packet.get("provider_runtime_error_class") != PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider runtime error class must be provider_not_configured")
        if packet.get("provider_runtime_error_safe_summary") != PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider runtime safe summary mismatch")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_runtime_status") != PROVIDER_RUNTIME_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider runtime status must be not_requested")
        if packet.get("provider_runtime_hold_reason") != PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider runtime hold reason must be not_requested")
        if packet.get("provider_runtime_error_class") != PROVIDER_RUNTIME_ERROR_CLASS_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider runtime error class must be empty")
        if packet.get("provider_runtime_error_safe_summary") != PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider runtime safe summary must be empty")


def _validate_provider_selection_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_selection_requested",
        "provider_selected",
    )
    string_fields = (
        "provider_name",
        "provider_model",
        "provider_selection_source",
        "provider_selection_status",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_selected") is not False:
        errors.append("INVALID_EVIDENCE: provider_selected must be false while provider runtime is disabled")
    if packet.get("provider_name") != PROVIDER_NAME_NONE:
        errors.append("INVALID_EVIDENCE: provider_name must be none in selection metadata")
    if packet.get("provider_model") != PROVIDER_MODEL_NONE:
        errors.append("INVALID_EVIDENCE: provider_model must be none in selection metadata")
    if packet.get("provider_selection_source") not in PROVIDER_SELECTION_SOURCES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_selection_source: "
            f"{packet.get('provider_selection_source')}"
        )
    if packet.get("provider_selection_status") not in PROVIDER_SELECTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_selection_status: "
            f"{packet.get('provider_selection_status')}"
        )

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_selection_requested") is not True:
            errors.append("INVALID_EVIDENCE: Citizen One opt-in must record provider selection requested")
        if packet.get("provider_selection_source") != PROVIDER_SELECTION_SOURCE_DISABLED:
            errors.append("INVALID_EVIDENCE: requested provider selection source must be disabled")
        if packet.get("provider_selection_status") != PROVIDER_SELECTION_STATUS_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider selection status must be not_configured")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_selection_requested") is not False:
            errors.append("INVALID_EVIDENCE: default run must not request provider selection")
        if packet.get("provider_selection_source") != PROVIDER_SELECTION_SOURCE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider selection source must be not_requested")
        if packet.get("provider_selection_status") != PROVIDER_SELECTION_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider selection status must be not_requested")


def _validate_provider_secret_env_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_secret_required",
        "provider_secret_observed",
        "provider_secret_value_recorded",
        "provider_env_loading_requested",
    )
    string_fields = (
        "provider_secret_source",
        "provider_secret_redaction_status",
        "provider_env_loading_status",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_secret_required") is not False:
        errors.append("INVALID_EVIDENCE: provider_secret_required must be false without provider runtime")
    if packet.get("provider_secret_observed") is not False:
        errors.append("INVALID_EVIDENCE: provider_secret_observed must be false")
    if packet.get("provider_secret_value_recorded") is not False:
        errors.append("INVALID_EVIDENCE: provider_secret_value_recorded must be false")
    if packet.get("provider_secret_source") not in PROVIDER_SECRET_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_secret_source: {packet.get('provider_secret_source')}")
    if packet.get("provider_secret_redaction_status") not in PROVIDER_SECRET_REDACTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_secret_redaction_status: "
            f"{packet.get('provider_secret_redaction_status')}"
        )
    if packet.get("provider_secret_redaction_status") != PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED:
        errors.append("INVALID_EVIDENCE: provider secret redaction must declare no secret value recorded")
    if packet.get("provider_env_loading_requested") is not False:
        errors.append("INVALID_EVIDENCE: provider_env_loading_requested must be false")
    if packet.get("provider_env_loading_status") not in PROVIDER_ENV_LOADING_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_env_loading_status: "
            f"{packet.get('provider_env_loading_status')}"
        )

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_secret_source") != PROVIDER_SECRET_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: requested provider secret source must remain none")
        if packet.get("provider_env_loading_status") != PROVIDER_ENV_LOADING_STATUS_DISABLED:
            errors.append("INVALID_EVIDENCE: requested provider env loading status must be disabled")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_secret_source") != PROVIDER_SECRET_SOURCE_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider secret source must be not_requested")
        if packet.get("provider_env_loading_status") != PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider env loading status must be not_requested")


def _validate_provider_network_guard_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_network_opt_in_requested",
        "provider_network_opt_in_allowed",
        "provider_network_used",
    )
    string_fields = (
        "provider_network_status",
        "provider_network_block_reason",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_network_opt_in_requested") is not False:
        errors.append("INVALID_EVIDENCE: provider_network_opt_in_requested must be false")
    if packet.get("provider_network_opt_in_allowed") is not False:
        errors.append("INVALID_EVIDENCE: provider_network_opt_in_allowed must be false")
    if packet.get("provider_network_used") is not False:
        errors.append("INVALID_EVIDENCE: provider_network_used must be false")
    if packet.get("provider_network_status") not in PROVIDER_NETWORK_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_network_status: {packet.get('provider_network_status')}")
    if packet.get("provider_network_block_reason") not in PROVIDER_NETWORK_BLOCK_REASONS:
        errors.append(
            "INVALID_EVIDENCE: invalid provider_network_block_reason: "
            f"{packet.get('provider_network_block_reason')}"
        )

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_network_status") != PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN:
            errors.append("INVALID_EVIDENCE: requested provider network status must be blocked_no_opt_in")
        if packet.get("provider_network_block_reason") != PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: requested provider network block reason must record missing opt-in")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_network_status") != PROVIDER_NETWORK_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider network status must be not_requested")
        if packet.get("provider_network_block_reason") != PROVIDER_NETWORK_BLOCK_REASON_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider network block reason must be empty")


def _validate_provider_request_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_request_requested",
        "provider_request_raw_stored",
    )
    string_fields = (
        "provider_request_status",
        "provider_request_id",
        "provider_request_metadata_hash",
        "provider_request_redaction_status",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_request_requested") is not False:
        errors.append("INVALID_EVIDENCE: provider_request_requested must be false")
    if packet.get("provider_request_status") not in PROVIDER_REQUEST_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_request_status: {packet.get('provider_request_status')}")
    if packet.get("provider_request_redaction_status") != PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: provider request redaction must declare no raw prompt/response storage")
    if packet.get("provider_request_raw_stored") is not False:
        errors.append("INVALID_EVIDENCE: provider_request_raw_stored must be false")
    request_hash = packet.get("provider_request_metadata_hash")
    if not isinstance(request_hash, str) or not _is_sha256_hex(request_hash):
        errors.append("INVALID_EVIDENCE: provider_request_metadata_hash must be sha256 hex")
    elif request_hash != _expected_provider_request_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: provider_request_metadata_hash mismatch")

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_request_status") != PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider request status must be blocked_provider_not_configured")
        if packet.get("provider_request_id") != PROVIDER_ADAPTER_DISABLED_REQUEST_ID:
            errors.append("INVALID_EVIDENCE: requested provider request id must be provider_adapter_disabled_v0")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_request_status") != PROVIDER_REQUEST_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider request status must be not_requested")
        if packet.get("provider_request_id") != "":
            errors.append("INVALID_EVIDENCE: non-requested provider request id must be empty")


def _validate_provider_response_error_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "provider_response_present",
        "provider_response_reported_only",
        "provider_response_raw_stored",
    )
    string_fields = (
        "provider_response_status",
        "provider_response_trust_boundary",
        "provider_response_metadata_hash",
        "provider_response_redaction_status",
        "provider_error_class",
        "provider_error_safe_summary",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("provider_response_present") is not False:
        errors.append("INVALID_EVIDENCE: provider_response_present must be false")
    if packet.get("provider_response_reported_only") is not True:
        errors.append("INVALID_EVIDENCE: provider_response_reported_only must be true")
    if packet.get("provider_response_trust_boundary") != REPORTED_ONLY:
        errors.append("INVALID_EVIDENCE: provider_response_trust_boundary must be reported_only")
    if packet.get("provider_response_status") not in PROVIDER_RESPONSE_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_response_status: {packet.get('provider_response_status')}")
    if packet.get("provider_response_redaction_status") != PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: provider response redaction must declare no raw prompt/response storage")
    if packet.get("provider_response_raw_stored") is not False:
        errors.append("INVALID_EVIDENCE: provider_response_raw_stored must be false")
    if packet.get("provider_error_class") not in PROVIDER_RESPONSE_ERROR_CLASSES:
        errors.append(f"INVALID_EVIDENCE: invalid provider_error_class: {packet.get('provider_error_class')}")
    response_hash = packet.get("provider_response_metadata_hash")
    if not isinstance(response_hash, str) or not _is_sha256_hex(response_hash):
        errors.append("INVALID_EVIDENCE: provider_response_metadata_hash must be sha256 hex")
    elif response_hash != _expected_provider_response_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: provider_response_metadata_hash mismatch")

    if packet.get("provider_error_class") != packet.get("provider_response_error_class"):
        errors.append("INVALID_EVIDENCE: provider_error_class must mirror provider_response_error_class")
    if packet.get("provider_error_safe_summary") != packet.get("provider_response_error_safe_summary"):
        errors.append("INVALID_EVIDENCE: provider_error_safe_summary must mirror provider_response_error_safe_summary")

    if packet.get("citizen_one_requested") is True:
        if packet.get("provider_response_status") != PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider response status must be provider_not_configured")
        if packet.get("provider_error_class") != PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider error class must be provider_not_configured")
        if packet.get("provider_error_safe_summary") != PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested provider error safe summary mismatch")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("provider_response_status") != PROVIDER_RESPONSE_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested provider response status must be not_requested")
        if packet.get("provider_error_class") != PROVIDER_RESPONSE_ERROR_CLASS_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider error class must be empty")
        if packet.get("provider_error_safe_summary") != PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE:
            errors.append("INVALID_EVIDENCE: non-requested provider error safe summary must be empty")


def _validate_prompt_redaction_metadata_fields(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "prompt_build_requested",
        "prompt_secret_detected",
        "prompt_raw_stored",
    )
    string_fields = (
        "prompt_build_status",
        "prompt_source",
        "prompt_input_summary",
        "prompt_redaction_status",
        "prompt_hash_candidate",
        "prompt_storage_policy",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("prompt_build_status") not in PROMPT_BUILD_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid prompt_build_status: {packet.get('prompt_build_status')}")
    if packet.get("prompt_source") not in PROMPT_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid prompt_source: {packet.get('prompt_source')}")
    if packet.get("prompt_redaction_status") not in PROMPT_REDACTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid prompt_redaction_status: "
            f"{packet.get('prompt_redaction_status')}"
        )
    if packet.get("prompt_storage_policy") not in PROMPT_STORAGE_POLICIES:
        errors.append(f"INVALID_EVIDENCE: invalid prompt_storage_policy: {packet.get('prompt_storage_policy')}")

    if packet.get("prompt_build_requested") is not False:
        errors.append("INVALID_EVIDENCE: prompt_build_requested must be false while provider adapter is disabled")
    if packet.get("prompt_input_summary") != "":
        errors.append("INVALID_EVIDENCE: prompt_input_summary must be empty redaction metadata only")
    if packet.get("prompt_redaction_status") != PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED:
        errors.append("INVALID_EVIDENCE: prompt_redaction_status must declare no raw prompt storage")
    if packet.get("prompt_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: prompt_hash_candidate must be empty")
    if packet.get("prompt_storage_policy") != PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE:
        errors.append("INVALID_EVIDENCE: prompt_storage_policy must be no_raw_prompt_storage")
    if packet.get("prompt_secret_detected") is not False:
        errors.append("INVALID_EVIDENCE: prompt_secret_detected must be false")
    if packet.get("prompt_raw_stored") is not False:
        errors.append("INVALID_EVIDENCE: prompt_raw_stored must be false")

    if packet.get("citizen_one_requested") is True:
        if packet.get("prompt_build_status") != PROMPT_BUILD_STATUS_PROVIDER_DISABLED:
            errors.append("INVALID_EVIDENCE: requested prompt_build_status must be not_built_provider_disabled")
        if packet.get("prompt_source") != PROMPT_SOURCE_DISABLED:
            errors.append("INVALID_EVIDENCE: requested prompt_source must be disabled")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("prompt_build_status") != PROMPT_BUILD_STATUS_NOT_BUILT:
            errors.append("INVALID_EVIDENCE: non-requested prompt_build_status must be not_built")
        if packet.get("prompt_source") != PROMPT_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: non-requested prompt_source must be none")


def _validate_response_redaction_metadata_fields(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "response_present",
        "response_reported_only",
        "response_raw_stored",
    )
    string_fields = (
        "response_status",
        "response_source",
        "response_trust_boundary",
        "response_redaction_status",
        "response_hash_candidate",
        "response_error_class",
        "response_error_safe_summary",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("response_status") not in RESPONSE_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid response_status: {packet.get('response_status')}")
    if packet.get("response_source") not in RESPONSE_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid response_source: {packet.get('response_source')}")
    if packet.get("response_redaction_status") not in RESPONSE_REDACTION_STATUSES:
        errors.append(
            "INVALID_EVIDENCE: invalid response_redaction_status: "
            f"{packet.get('response_redaction_status')}"
        )
    if packet.get("response_error_class") not in RESPONSE_ERROR_CLASSES:
        errors.append(f"INVALID_EVIDENCE: invalid response_error_class: {packet.get('response_error_class')}")

    if packet.get("response_present") is not False:
        errors.append("INVALID_EVIDENCE: response_present must be false while provider adapter is disabled")
    if packet.get("response_reported_only") is not True:
        errors.append("INVALID_EVIDENCE: response metadata must be marked reported_only")
    if packet.get("response_trust_boundary") != REPORTED_ONLY:
        errors.append("INVALID_EVIDENCE: response trust boundary must be reported_only")
    if packet.get("response_redaction_status") != RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: response_redaction_status must declare no raw response storage")
    if packet.get("response_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: response_hash_candidate must be empty")
    if packet.get("response_raw_stored") is not False:
        errors.append("INVALID_EVIDENCE: response_raw_stored must be false")

    if packet.get("citizen_one_requested") is True:
        if packet.get("response_status") != RESPONSE_STATUS_PROVIDER_DISABLED:
            errors.append("INVALID_EVIDENCE: requested response_status must be provider_disabled")
        if packet.get("response_source") != RESPONSE_SOURCE_DISABLED_ADAPTER:
            errors.append("INVALID_EVIDENCE: requested response_source must be disabled_adapter")
        if packet.get("response_error_class") != RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED:
            errors.append("INVALID_EVIDENCE: requested response_error_class must be provider_not_configured")
        if packet.get("response_error_safe_summary") != RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED:
            errors.append("INVALID_EVIDENCE: requested response_error_safe_summary mismatch")
    elif packet.get("citizen_one_requested") is False:
        if packet.get("response_status") != RESPONSE_STATUS_NOT_REQUESTED:
            errors.append("INVALID_EVIDENCE: non-requested response_status must be not_requested")
        if packet.get("response_source") != RESPONSE_SOURCE_NONE:
            errors.append("INVALID_EVIDENCE: non-requested response_source must be none")
        if packet.get("response_error_class") != RESPONSE_ERROR_CLASS_NONE:
            errors.append("INVALID_EVIDENCE: non-requested response_error_class must be empty")
        if packet.get("response_error_safe_summary") != RESPONSE_ERROR_SAFE_SUMMARY_NONE:
            errors.append("INVALID_EVIDENCE: non-requested response_error_safe_summary must be empty")


def _validate_action_boundary_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "action_interception_enabled",
        "command_enumeration_only",
        "no_matched_dangerous_command",
        *ACTION_AUTHORITY_FIELDS,
    )
    string_fields = (
        "action_boundary_version",
        "action_boundary_status",
        "action_log_source",
        "action_log_source_trust_boundary",
        "action_risk",
        "computed_action_log_hash",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)
    _expect(packet, "intercepted_actions", list, errors)
    _expect(packet, "executor_reported_actions", dict, errors)

    for field in ("action_count", "expected_action_count"):
        value = packet.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be integer")
        elif value < 0:
            errors.append(f"INVALID_EVIDENCE: {field} must be non-negative")

    if packet.get("action_boundary_version") != ACTION_BOUNDARY_SCAFFOLD_V0:
        errors.append(f"INVALID_EVIDENCE: action_boundary_version must be {ACTION_BOUNDARY_SCAFFOLD_V0}")
    if packet.get("action_boundary_status") not in ACTION_BOUNDARY_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid action_boundary_status: {packet.get('action_boundary_status')}")
    if packet.get("action_log_source") not in ACTION_LOG_SOURCES:
        errors.append(f"INVALID_EVIDENCE: invalid action_log_source: {packet.get('action_log_source')}")
    if packet.get("action_log_source") != ACTION_LOG_SOURCE_NONE:
        errors.append("INVALID_EVIDENCE: action_log_source must be none in scaffold v0")
    if packet.get("action_log_source_trust_boundary") not in ACTION_LOG_SOURCE_TRUST_BOUNDARIES:
        errors.append(
            "INVALID_EVIDENCE: invalid action_log_source_trust_boundary: "
            f"{packet.get('action_log_source_trust_boundary')}"
        )
    if packet.get("action_log_source_trust_boundary") != ACTION_LOG_SOURCE_TRUST_BOUNDARY_NOT_IMPLEMENTED:
        errors.append("INVALID_EVIDENCE: action log trust boundary is not implemented in scaffold v0")

    intercepted_actions = packet.get("intercepted_actions")
    if not isinstance(intercepted_actions, list):
        intercepted_actions = []
    elif not all(isinstance(item, dict) for item in intercepted_actions):
        errors.append("INVALID_EVIDENCE: intercepted_actions must contain only objects")
        intercepted_actions = [item for item in intercepted_actions if isinstance(item, dict)]

    if packet.get("action_interception_enabled") is not False:
        errors.append("INVALID_EVIDENCE: action_interception_enabled must be false in scaffold v0")
    if packet.get("action_interception_enabled") is False and intercepted_actions:
        errors.append("INVALID_EVIDENCE: intercepted_actions must be empty when action interception is disabled")

    if packet.get("expected_action_count") != 0:
        errors.append("INVALID_EVIDENCE: expected_action_count must be 0 for no-op scaffold v0")
    if isinstance(packet.get("action_count"), int) and not isinstance(packet.get("action_count"), bool):
        if packet.get("action_count") != len(intercepted_actions):
            errors.append("INVALID_EVIDENCE: action_count must equal intercepted_actions length")
    if packet.get("action_count") != packet.get("expected_action_count"):
        errors.append("INVALID_EVIDENCE: action_count must equal expected_action_count for no-op scaffold v0")

    action_risk = packet.get("action_risk")
    if action_risk not in (NOT_CHECKED, LOW, MEDIUM, HIGH):
        errors.append(f"INVALID_EVIDENCE: invalid action_risk: {action_risk}")
    expected_risk = _expected_action_risk(intercepted_actions)
    if action_risk != expected_risk:
        errors.append(f"INVALID_EVIDENCE: action_risk mismatch: evidence={action_risk} replay={expected_risk}")

    action_hash = packet.get("computed_action_log_hash")
    if not isinstance(action_hash, str) or not _is_sha256_hex(action_hash):
        errors.append("INVALID_EVIDENCE: computed_action_log_hash must be sha256 hex")
    elif action_hash != expected_action_log_hash(packet):
        errors.append("INVALID_EVIDENCE: computed_action_log_hash mismatch")

    for field in ACTION_AUTHORITY_FIELDS:
        if packet.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must be false in scaffold v0")

    executor_reported = packet.get("executor_reported_actions")
    if isinstance(executor_reported, dict):
        reported_actions = executor_reported.get("actions")
        if not isinstance(reported_actions, list):
            errors.append("INVALID_EVIDENCE: executor_reported_actions.actions must be list")
            reported_actions = []
        if not isinstance(executor_reported.get("reported_action_count"), int) or isinstance(
            executor_reported.get("reported_action_count"), bool
        ):
            errors.append("INVALID_EVIDENCE: executor_reported_actions.reported_action_count must be integer")
        elif executor_reported.get("reported_action_count") != len(reported_actions):
            errors.append("INVALID_EVIDENCE: executor_reported_actions.reported_action_count mismatch")
        if executor_reported.get("trust_boundary") != REPORTED_ONLY:
            errors.append("INVALID_EVIDENCE: executor_reported_actions must be reported_only")
        if executor_reported.get("judgment_basis") is not False:
            errors.append("INVALID_EVIDENCE: executor_reported_actions cannot be judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_actions must be object")

    if packet.get("judgment_basis") == "executor_reported_actions":
        errors.append("INVALID_EVIDENCE: executor_reported_actions cannot become judgment basis")

    if packet.get("command_enumeration_only") is True:
        if any(packet.get(field) is True for field in ACTION_AUTHORITY_FIELDS):
            errors.append("INVALID_EVIDENCE: command enumeration alone cannot grant authority")
        if packet.get("action_boundary_status") == ACTION_BOUNDARY_CLEAN:
            errors.append("INVALID_EVIDENCE: command_enumeration_only cannot produce ACTION_BOUNDARY_CLEAN")

    if packet.get("no_matched_dangerous_command") is True and packet.get("action_boundary_status") == ACTION_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: NO_MATCHED_DANGEROUS_COMMAND != ACTION_BOUNDARY_CLEAN")

    if packet.get("action_boundary_status") == ACTION_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: ACTION_BOUNDARY_CLEAN is unavailable before action interception/capability isolation")
        if packet.get("action_risk") == HIGH or expected_risk == HIGH:
            errors.append("INVALID_EVIDENCE: HIGH action cannot be ACTION_BOUNDARY_CLEAN")
        if packet.get("mutation_boundary_status") == MUTATION_BOUNDARY_CLEAN:
            errors.append("INVALID_EVIDENCE: MUTATION_BOUNDARY_CLEAN does not imply ACTION_BOUNDARY_CLEAN")
        if packet.get("changed_files") == []:
            errors.append("INVALID_EVIDENCE: git diff clean does not imply action clean")

    if packet.get("action_boundary_status") != ACTION_BOUNDARY_NOT_CHECKED:
        errors.append("INVALID_EVIDENCE: action_boundary_status must remain ACTION_BOUNDARY_NOT_CHECKED in scaffold v0")


def _validate_capability_isolation_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "capability_isolation_enabled",
        *CAPABILITY_AUTHORITY_FIELDS,
    )
    string_fields = (
        "capability_isolation_version",
        "capability_isolation_mode",
        "capability_boundary_status",
        "capability_boundary_source",
        "capability_boundary_trust_boundary",
        "capability_isolation_proof_hash",
        "capability_matrix_hash",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)
    _expect(packet, "executor_reported_capabilities", dict, errors)

    if packet.get("capability_isolation_version") != CAPABILITY_ISOLATION_SCAFFOLD_V0:
        errors.append(
            "INVALID_EVIDENCE: capability_isolation_version must be "
            f"{CAPABILITY_ISOLATION_SCAFFOLD_V0}"
        )
    if packet.get("capability_isolation_enabled") is not False:
        errors.append("INVALID_EVIDENCE: capability_isolation_enabled must be false in scaffold v0")
    if packet.get("capability_isolation_mode") != CAPABILITY_ISOLATION_MODE_NOT_IMPLEMENTED:
        errors.append("INVALID_EVIDENCE: capability isolation mode is not implemented in scaffold v0")

    boundary_status = packet.get("capability_boundary_status")
    if boundary_status not in CAPABILITY_BOUNDARY_STATUSES and boundary_status != ACTION_BOUNDARY_CLEAN:
        errors.append(f"INVALID_EVIDENCE: invalid capability_boundary_status: {boundary_status}")
    if boundary_status in (CAPABILITY_BOUNDARY_CLEAN, ACTION_BOUNDARY_CLEAN):
        errors.append("INVALID_EVIDENCE: capability_boundary_status cannot claim CLEAN before isolation proof")
    if boundary_status != CAPABILITY_BOUNDARY_NOT_CHECKED:
        errors.append("INVALID_EVIDENCE: capability_boundary_status must remain CAPABILITY_BOUNDARY_NOT_CHECKED in scaffold v0")

    if packet.get("capability_boundary_source") != CAPABILITY_BOUNDARY_SOURCE_NONE:
        errors.append("INVALID_EVIDENCE: capability_boundary_source must be none in scaffold v0")
    if packet.get("capability_boundary_trust_boundary") != CAPABILITY_BOUNDARY_TRUST_BOUNDARY_NOT_IMPLEMENTED:
        errors.append("INVALID_EVIDENCE: capability boundary trust boundary is not implemented in scaffold v0")

    for field in CAPABILITY_AUTHORITY_FIELDS:
        if packet.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must be false in capability isolation scaffold v0")
            errors.append(
                "INVALID_EVIDENCE: authority_granted=true without implemented "
                f"capability isolation proof: {field}"
            )

    matrix_hash = packet.get("capability_matrix_hash")
    if not isinstance(matrix_hash, str) or not _is_sha256_hex(matrix_hash):
        errors.append("INVALID_EVIDENCE: capability_matrix_hash must be sha256 hex")
    elif matrix_hash != expected_capability_matrix_hash(packet):
        errors.append("INVALID_EVIDENCE: capability_matrix_hash mismatch")

    proof_hash = packet.get("capability_isolation_proof_hash")
    if not isinstance(proof_hash, str) or not _is_sha256_hex(proof_hash):
        errors.append("INVALID_EVIDENCE: capability_isolation_proof_hash must be sha256 hex")
    elif proof_hash != expected_capability_isolation_proof_hash(packet):
        errors.append("INVALID_EVIDENCE: capability_isolation_proof_hash mismatch")

    executor_reported = packet.get("executor_reported_capabilities")
    if isinstance(executor_reported, dict):
        reported_capabilities = executor_reported.get("capabilities")
        if not isinstance(reported_capabilities, list):
            errors.append("INVALID_EVIDENCE: executor_reported_capabilities.capabilities must be list")
            reported_capabilities = []
        if not isinstance(executor_reported.get("reported_capability_count"), int) or isinstance(
            executor_reported.get("reported_capability_count"), bool
        ):
            errors.append("INVALID_EVIDENCE: executor_reported_capabilities.reported_capability_count must be integer")
        elif executor_reported.get("reported_capability_count") != len(reported_capabilities):
            errors.append("INVALID_EVIDENCE: executor_reported_capabilities.reported_capability_count mismatch")
        if executor_reported.get("trust_boundary") != REPORTED_ONLY:
            errors.append("INVALID_EVIDENCE: executor_reported_capabilities must be reported_only")
        if executor_reported.get("judgment_basis") is not False:
            errors.append("INVALID_EVIDENCE: executor_reported_capabilities cannot be judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_capabilities must be object")

    if packet.get("judgment_basis") == "executor_reported_capabilities":
        errors.append("INVALID_EVIDENCE: executor_reported_capabilities cannot become judgment basis")
    if packet.get("command_enumeration_only") is True and boundary_status == CAPABILITY_BOUNDARY_CLEAN:
        errors.append("INVALID_EVIDENCE: command_enumeration_only cannot produce CAPABILITY_BOUNDARY_CLEAN")


def _validate_tool_surface_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "tool_surface_enabled",
        *TOOL_AUTHORITY_GRANT_FIELDS,
    )
    string_fields = (
        "tool_surface_version",
        "tool_surface_status",
        "tool_surface_source",
        "tool_surface_trust_boundary",
        "tool_authority_grant_hash",
        "tool_surface_metadata_hash",
    )
    list_fields = (
        "requested_tool_capabilities",
        "granted_tool_capabilities",
        "denied_tool_capabilities",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)
    for field in list_fields:
        _expect(packet, field, list, errors)
    _expect(packet, "executor_reported_tool_usage", dict, errors)

    if packet.get("tool_surface_version") != TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0:
        errors.append(
            "INVALID_EVIDENCE: tool_surface_version must be "
            f"{TOOL_SURFACE_AUTHORITY_GRANT_SCAFFOLD_V0}"
        )
    if packet.get("tool_surface_enabled") is not False:
        errors.append("INVALID_EVIDENCE: tool_surface_enabled must be false in scaffold v0")

    surface_status = packet.get("tool_surface_status")
    if surface_status not in TOOL_SURFACE_STATUSES and surface_status not in (
        ACTION_BOUNDARY_CLEAN,
        CAPABILITY_BOUNDARY_CLEAN,
    ):
        errors.append(f"INVALID_EVIDENCE: invalid tool_surface_status: {surface_status}")
    if surface_status in (TOOL_SURFACE_CLEAN, ACTION_BOUNDARY_CLEAN, CAPABILITY_BOUNDARY_CLEAN):
        errors.append("INVALID_EVIDENCE: tool_surface_status cannot claim CLEAN before tool surface proof")
    if surface_status != TOOL_SURFACE_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: tool_surface_status must remain TOOL_SURFACE_SCAFFOLD_ONLY in scaffold v0")

    if packet.get("tool_surface_source") != TOOL_SURFACE_SOURCE_NONE:
        errors.append("INVALID_EVIDENCE: tool_surface_source must be none in scaffold v0")
    if packet.get("tool_surface_trust_boundary") != TOOL_SURFACE_TRUST_BOUNDARY_NOT_IMPLEMENTED:
        errors.append("INVALID_EVIDENCE: tool surface trust boundary is not implemented in scaffold v0")

    for field in list_fields:
        value = packet.get(field)
        if isinstance(value, list) and not all(isinstance(item, str) for item in value):
            errors.append(f"INVALID_EVIDENCE: {field} must contain only strings")

    requested = packet.get("requested_tool_capabilities")
    granted = packet.get("granted_tool_capabilities")
    denied = packet.get("denied_tool_capabilities")
    if requested != []:
        errors.append("INVALID_EVIDENCE: requested_tool_capabilities must be empty in scaffold v0")
    if granted != []:
        errors.append("INVALID_EVIDENCE: granted_tool_capabilities must be empty in scaffold v0")
    if denied != []:
        errors.append("INVALID_EVIDENCE: denied_tool_capabilities must be empty in scaffold v0")

    for field in ("tool_authority_grant_count", "expected_tool_authority_grant_count"):
        value = packet.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be integer")
        elif value < 0:
            errors.append(f"INVALID_EVIDENCE: {field} must be non-negative")
    if packet.get("tool_authority_grant_count") != 0:
        errors.append("INVALID_EVIDENCE: tool_authority_grant_count must be 0 in scaffold v0")
    if packet.get("expected_tool_authority_grant_count") != 0:
        errors.append("INVALID_EVIDENCE: expected_tool_authority_grant_count must be 0 in scaffold v0")
    if packet.get("tool_authority_grant_count") != packet.get("expected_tool_authority_grant_count"):
        errors.append("INVALID_EVIDENCE: tool authority grant count must equal expected count")
    if isinstance(granted, list) and packet.get("tool_authority_grant_count") != len(granted):
        errors.append("INVALID_EVIDENCE: tool_authority_grant_count must equal granted_tool_capabilities length")

    for field in TOOL_AUTHORITY_GRANT_FIELDS:
        if packet.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must be false in tool surface scaffold v0")
            errors.append(
                "INVALID_EVIDENCE: authority_granted=true without implemented "
                f"tool surface proof/source/trust boundary: {field}"
            )

    grant_hash = packet.get("tool_authority_grant_hash")
    if not isinstance(grant_hash, str) or not _is_sha256_hex(grant_hash):
        errors.append("INVALID_EVIDENCE: tool_authority_grant_hash must be sha256 hex")
    elif grant_hash != expected_tool_authority_grant_hash(packet):
        errors.append("INVALID_EVIDENCE: tool_authority_grant_hash mismatch")

    surface_hash = packet.get("tool_surface_metadata_hash")
    if not isinstance(surface_hash, str) or not _is_sha256_hex(surface_hash):
        errors.append("INVALID_EVIDENCE: tool_surface_metadata_hash must be sha256 hex")
    elif surface_hash != expected_tool_surface_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: tool_surface_metadata_hash mismatch")

    executor_reported = packet.get("executor_reported_tool_usage")
    if isinstance(executor_reported, dict):
        reported_tools = executor_reported.get("tools")
        if not isinstance(reported_tools, list):
            errors.append("INVALID_EVIDENCE: executor_reported_tool_usage.tools must be list")
            reported_tools = []
        if not isinstance(executor_reported.get("reported_tool_count"), int) or isinstance(
            executor_reported.get("reported_tool_count"), bool
        ):
            errors.append("INVALID_EVIDENCE: executor_reported_tool_usage.reported_tool_count must be integer")
        elif executor_reported.get("reported_tool_count") != len(reported_tools):
            errors.append("INVALID_EVIDENCE: executor_reported_tool_usage.reported_tool_count mismatch")
        if executor_reported.get("trust_boundary") != REPORTED_ONLY:
            errors.append("INVALID_EVIDENCE: executor_reported_tool_usage must be reported_only")
        if executor_reported.get("judgment_basis") is not False:
            errors.append("INVALID_EVIDENCE: executor_reported_tool_usage cannot become judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_tool_usage must be object")

    if packet.get("judgment_basis") == "executor_reported_tool_usage":
        errors.append("INVALID_EVIDENCE: executor_reported_tool_usage cannot become judgment basis")
    if packet.get("command_enumeration_only") is True:
        if any(packet.get(field) is True for field in TOOL_AUTHORITY_GRANT_FIELDS):
            errors.append("INVALID_EVIDENCE: command denylist/enumeration alone cannot grant tool authority")
        if surface_status == TOOL_SURFACE_CLEAN:
            errors.append("INVALID_EVIDENCE: no requested or granted tool cannot produce TOOL_SURFACE_CLEAN")


def _validate_executor_capability_exposure_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        *EXECUTOR_CAPABILITY_BOOL_FIELDS,
        "executor_capability_file_mutation",
        "executor_capability_provider_calls",
        "executor_capability_network_calls",
    )
    string_fields = (
        "executor_capability_exposure_version",
        "executor_capability_exposure_scope",
        "executor_capability_exposure_source",
        "executor_capability_exposure_trust_boundary",
        "executor_capability_transport",
        "current_executor_capability_status",
        "executor_capability_exposure_hash",
        "executor_capability_exposure_metadata_hash",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)
    _expect(packet, "executor_capability_actions", list, errors)
    _expect(packet, "executor_reported_capability_exposure", dict, errors)

    for field in ("executor_capability_action_count", "executor_capability_expected_action_count"):
        value = packet.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"INVALID_EVIDENCE: {field} must be integer")
        elif value < 0:
            errors.append(f"INVALID_EVIDENCE: {field} must be non-negative")

    if packet.get("executor_capability_exposure_version") != EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0:
        errors.append(
            "INVALID_EVIDENCE: executor_capability_exposure_version must be "
            f"{EXECUTOR_CAPABILITY_EXPOSURE_SCAFFOLD_V0}"
        )
    if packet.get("executor_capability_exposure_scope") != EXECUTOR_CAPABILITY_EXPOSURE_SCOPE_CURRENT_NOOP:
        errors.append("INVALID_EVIDENCE: executor capability exposure applies only to the current no-op executor")
    if packet.get("executor_capability_exposure_source") != EXECUTOR_CAPABILITY_EXPOSURE_SOURCE_NOOP_CONTRACT:
        errors.append("INVALID_EVIDENCE: executor capability exposure source must be current_noop_executor_contract")
    if (
        packet.get("executor_capability_exposure_trust_boundary")
        != EXECUTOR_CAPABILITY_EXPOSURE_TRUST_BOUNDARY_AEGIS_RUNTIME
    ):
        errors.append("INVALID_EVIDENCE: executor capability exposure trust boundary mismatch")
    if packet.get("executor_capability_transport") not in EXECUTOR_CAPABILITY_TRANSPORTS:
        errors.append(
            "INVALID_EVIDENCE: invalid executor_capability_transport: "
            f"{packet.get('executor_capability_transport')}"
        )
    if packet.get("executor_capability_transport") != EXECUTOR_CAPABILITY_TRANSPORT_NONE:
        errors.append("INVALID_EVIDENCE: current no-op executor must not expose structured tool transport")
    if packet.get("current_executor_capability_status") != NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION:
        errors.append(
            "INVALID_EVIDENCE: current_executor_capability_status must be "
            f"{NO_SHELL_NO_NETWORK_NO_PROVIDER_NO_ACTION}"
        )

    for field in EXECUTOR_CAPABILITY_BOOL_FIELDS:
        if packet.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must default false for current no-op executor")

    for field in (
        "executor_capability_file_mutation",
        "executor_capability_provider_calls",
        "executor_capability_network_calls",
    ):
        if packet.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must be false for current no-op executor")

    actions = packet.get("executor_capability_actions")
    if not isinstance(actions, list):
        actions = []
    elif not all(isinstance(item, dict) for item in actions):
        errors.append("INVALID_EVIDENCE: executor_capability_actions must contain only objects")
        actions = [item for item in actions if isinstance(item, dict)]
    if actions != []:
        errors.append("INVALID_EVIDENCE: current no-op executor capability actions must be empty")
    if packet.get("executor_capability_action_count") != 0:
        errors.append("INVALID_EVIDENCE: executor_capability_action_count must be 0 for current no-op executor")
    if packet.get("executor_capability_expected_action_count") != 0:
        errors.append("INVALID_EVIDENCE: executor_capability_expected_action_count must be 0 for current no-op executor")
    if packet.get("executor_capability_action_count") != packet.get("executor_capability_expected_action_count"):
        errors.append("INVALID_EVIDENCE: executor capability action_count must equal expected_action_count")
    if packet.get("executor_capability_action_count") != len(actions):
        errors.append("INVALID_EVIDENCE: executor capability action_count must equal actions length")

    exposure_hash = packet.get("executor_capability_exposure_hash")
    if not isinstance(exposure_hash, str) or not _is_sha256_hex(exposure_hash):
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_hash must be sha256 hex")
    elif exposure_hash != expected_executor_capability_exposure_hash(packet):
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_hash mismatch")

    metadata_hash = packet.get("executor_capability_exposure_metadata_hash")
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_executor_capability_exposure_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: executor_capability_exposure_metadata_hash mismatch")

    dangerous_capabilities = _dangerous_executor_capability_fields(packet)
    if packet.get("capability_shell") is False and dangerous_capabilities:
        errors.append("INVALID_EVIDENCE: NO_RAW_SHELL != NO_DANGEROUS_CAPABILITY")
    if (
        packet.get("executor_capability_transport") == EXECUTOR_CAPABILITY_TRANSPORT_STRUCTURED_TOOL_CALL
        and dangerous_capabilities
    ):
        errors.append("INVALID_EVIDENCE: STRUCTURED_TOOL_CALL != SAFE_CAPABILITY")

    reported = packet.get("executor_reported_capability_exposure")
    if isinstance(reported, dict):
        reported_capabilities = reported.get("capabilities")
        reported_tools = reported.get("tools")
        if not isinstance(reported_capabilities, list):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.capabilities must be list")
            reported_capabilities = []
        if not isinstance(reported_tools, list):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.tools must be list")
            reported_tools = []
        if not isinstance(reported.get("reported_capability_count"), int) or isinstance(
            reported.get("reported_capability_count"), bool
        ):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.reported_capability_count must be integer")
        elif reported.get("reported_capability_count") != len(reported_capabilities):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.reported_capability_count mismatch")
        if not isinstance(reported.get("reported_tool_count"), int) or isinstance(
            reported.get("reported_tool_count"), bool
        ):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.reported_tool_count must be integer")
        elif reported.get("reported_tool_count") != len(reported_tools):
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure.reported_tool_count mismatch")
        if reported.get("trust_boundary") != REPORTED_ONLY:
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure must be reported_only")
        if reported.get("judgment_basis") is not False:
            errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure cannot become judgment basis")
    else:
        errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure must be object")

    if packet.get("judgment_basis") == "executor_reported_capability_exposure":
        errors.append("INVALID_EVIDENCE: executor_reported_capability_exposure cannot become judgment basis")


def _validate_evidence_store_trust_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    string_fields = (
        "evidence_store_trust_boundary",
        "evidence_store_writer",
        "evidence_store_write_source",
        "evidence_store_integrity_status",
        "evidence_store_trust_metadata_hash",
    )
    for field in string_fields:
        _expect(packet, field, str, errors)
    _expect(packet, "evidence_store_is_executor_isolated", bool, errors)

    can_write = packet.get("executor_can_write_evidence_store")
    if not isinstance(can_write, (str, bool)):
        errors.append("INVALID_EVIDENCE: executor_can_write_evidence_store must be string or boolean")

    if packet.get("evidence_store_trust_boundary") != EVIDENCE_STORE_TRUST_BOUNDARY_FOLDER_LOCAL_NOT_EXECUTOR_ISOLATED:
        errors.append("INVALID_EVIDENCE: .aeg/ folder-local state is not executor-isolated")
    if packet.get("evidence_store_writer") != EVIDENCE_STORE_WRITER_AEGIS_RUNTIME:
        errors.append("INVALID_EVIDENCE: evidence_store_writer must be aegis_runtime")
    if can_write != EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY:
        errors.append(
            "INVALID_EVIDENCE: executor_can_write_evidence_store must remain "
            "NOT_CHECKED_SAME_USER_AUTHORITY before executor isolation proof"
        )
    if packet.get("evidence_store_is_executor_isolated") is not False:
        errors.append("INVALID_EVIDENCE: AEG_FOLDER_LOCAL_STATE != EXECUTOR_ISOLATED_EVIDENCE_STORE")
    if packet.get("evidence_store_write_source") != EVIDENCE_STORE_WRITE_SOURCE_FOLDER_LOCAL_STATE:
        errors.append("INVALID_EVIDENCE: evidence_store_write_source must be folder_local_runtime_state")

    integrity_status = packet.get("evidence_store_integrity_status")
    if integrity_status not in EVIDENCE_STORE_INTEGRITY_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid evidence_store_integrity_status: {integrity_status}")
    if integrity_status != EVIDENCE_STORE_INTEGRITY_NOT_CHECKED:
        errors.append("INVALID_EVIDENCE: evidence_store_integrity_status must remain NOT_CHECKED in scaffold v0")
    if packet.get("evidence_store_is_executor_isolated") is False and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: evidence_store_is_executor_isolated=false cannot claim EVIDENCE_STORE_CLEAN")
    if can_write in (True, EXECUTOR_CAN_WRITE_EVIDENCE_STORE_NOT_CHECKED_SAME_USER_AUTHORITY) and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: executor write access true/NOT_CHECKED cannot promote evidence store CLEAN")
    if packet.get("binding_status") == BOUND and integrity_status == EVIDENCE_STORE_CLEAN:
        errors.append("INVALID_EVIDENCE: EVIDENCE_BINDING != EVIDENCE_STORE_TAMPER_PROOF")

    metadata_hash = packet.get("evidence_store_trust_metadata_hash")
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        errors.append("INVALID_EVIDENCE: evidence_store_trust_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_evidence_store_trust_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: evidence_store_trust_metadata_hash mismatch")


def _validate_aeg_state_write_denial_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "capability_write_aeg_state_requested",
        "capability_write_aeg_state_granted",
        "capability_write_aeg_state_denied",
        *AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS,
    )
    string_fields = (
        "aeg_state_write_denial_version",
        "aeg_state_write_denial_mode",
        "aeg_state_write_denial_status",
        "aeg_state_write_denial_enforcement_status",
        "aeg_state_write_denial_source",
        "aeg_state_write_denial_reason",
        "aeg_state_write_denial_metadata_hash",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("aeg_state_write_denial_version") != AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0:
        errors.append(
            "INVALID_EVIDENCE: aeg_state_write_denial_version must be "
            f"{AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0}"
        )
    if packet.get("aeg_state_write_denial_mode") != AEG_STATE_WRITE_DENIAL_MODE_METADATA_SCAFFOLD:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_mode must remain metadata scaffold")

    denial_status = packet.get("aeg_state_write_denial_status")
    if denial_status in ("CLEAN", "PASS", "ENFORCED", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_status cannot claim CLEAN/PASS/ENFORCED")
    if denial_status not in AEG_STATE_WRITE_DENIAL_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid aeg_state_write_denial_status: {denial_status}")
    if denial_status != AEG_STATE_WRITE_DENIAL_STATUS_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_status must remain DENIAL_SCAFFOLD_ONLY")

    if packet.get("capability_write_aeg_state_requested") is not False:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_requested must remain false")
    if packet.get("capability_write_aeg_state_granted") is not False:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_granted must remain false")
    if packet.get("capability_write_aeg_state_denied") is not True:
        errors.append("INVALID_EVIDENCE: capability_write_aeg_state_denied must be explicit true")

    bypass_flags_valid = True
    for field in AEG_STATE_WRITE_DENIAL_BYPASS_FIELDS:
        value = packet.get(field)
        if not isinstance(value, bool):
            bypass_flags_valid = False
        elif value is not False:
            errors.append(f"INVALID_EVIDENCE: {field} must remain false")
            bypass_flags_valid = False
    if not bypass_flags_valid:
        errors.append("INVALID_EVIDENCE: aeg state write bypass flags must default false")

    enforcement_status = packet.get("aeg_state_write_denial_enforcement_status")
    if enforcement_status in ("CLEAN", "PASS", "ENFORCED", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status cannot claim ENFORCED/CLEAN/PASS")
    if enforcement_status not in AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid aeg_state_write_denial_enforcement_status: {enforcement_status}")
    if enforcement_status != AEG_STATE_WRITE_DENIAL_ENFORCEMENT_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED:
        errors.append(
            "INVALID_EVIDENCE: aeg_state_write_denial_enforcement_status must remain "
            "SCAFFOLD_ONLY_NOT_ENFORCED"
        )

    if packet.get("aeg_state_write_denial_source") != AEG_STATE_WRITE_DENIAL_SOURCE_AEGIS_RUNTIME_METADATA:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_source must be aegis runtime scaffold metadata")
    if packet.get("aeg_state_write_denial_source") == "executor_self_report":
        errors.append("INVALID_EVIDENCE: executor self-report cannot prove aeg state write denial")
    if packet.get("aeg_state_write_denial_reason") != AEG_STATE_WRITE_DENIAL_REASON_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_reason must describe scaffold-only metadata denial")

    reported = packet.get("executor_reported_aeg_state_write_denial")
    if isinstance(reported, dict) and reported.get("judgment_basis") is True:
        errors.append("INVALID_EVIDENCE: executor_reported_aeg_state_write_denial cannot become judgment basis")
    if packet.get("judgment_basis") == "executor_reported_aeg_state_write_denial":
        errors.append("INVALID_EVIDENCE: executor_reported_aeg_state_write_denial cannot become judgment basis")

    metadata_hash = packet.get("aeg_state_write_denial_metadata_hash")
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_aeg_state_write_denial_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: aeg_state_write_denial_metadata_hash mismatch")


def _validate_pre_live_executor_gate_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "live_executor_authority_requested",
        "live_executor_authority_granted",
        "requires_tamper_evident_ledger",
        "tamper_evident_ledger_present",
        "requires_aeg_state_write_denial",
        "aeg_state_write_denial_present",
        "requires_external_enforcement",
        "external_enforcement_present",
        "evidence_store_executor_isolated_required",
        "evidence_store_executor_isolated_present",
    )
    string_fields = (
        "pre_live_executor_gate_version",
        "pre_live_executor_gate_mode",
        "pre_live_executor_gate_status",
        "live_executor_authority_hold_reason",
        "pre_live_executor_gate_result",
        "pre_live_executor_gate_reason",
        "pre_live_executor_gate_metadata_hash",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    if packet.get("pre_live_executor_gate_version") != PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0:
        errors.append(
            "INVALID_EVIDENCE: pre_live_executor_gate_version must be "
            f"{PRE_LIVE_EXECUTOR_GATE_SCAFFOLD_V0}"
        )
    if packet.get("pre_live_executor_gate_mode") != PRE_LIVE_EXECUTOR_GATE_MODE_METADATA_SCAFFOLD:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_mode must remain metadata scaffold")

    gate_status = packet.get("pre_live_executor_gate_status")
    if gate_status in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_status cannot claim PASS/CLEAN/ALLOW")
    if gate_status not in PRE_LIVE_EXECUTOR_GATE_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid pre_live_executor_gate_status: {gate_status}")
    if gate_status != PRE_LIVE_EXECUTOR_GATE_STATUS_ON_HOLD:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_status must remain PRE_LIVE_EXECUTOR_ON_HOLD")

    if packet.get("live_executor_authority_requested") is not False:
        errors.append("INVALID_EVIDENCE: live_executor_authority_requested must remain false")
    if packet.get("live_executor_authority_granted") is not False:
        errors.append("INVALID_EVIDENCE: live_executor_authority_granted must remain false")
        errors.append("INVALID_EVIDENCE: live executor authority cannot be granted by pre-live gate scaffold")
    if packet.get("live_executor_authority_hold_reason") != LIVE_EXECUTOR_AUTHORITY_HOLD_REASON_PRE_LIVE_GATE:
        errors.append("INVALID_EVIDENCE: live_executor_authority_hold_reason must preserve pre-live gate hold")

    if packet.get("requires_tamper_evident_ledger") is not True:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require tamper-evident ledger scaffold")
    if packet.get("tamper_evident_ledger_present") is not True:
        errors.append("INVALID_EVIDENCE: tamper-evident ledger scaffold must be present before live executor")
    if packet.get("requires_tamper_evident_ledger") is True:
        if packet.get("ledger_integrity_version") != LEDGER_INTEGRITY_SCAFFOLD_V0:
            errors.append("INVALID_EVIDENCE: required tamper-evident ledger scaffold is missing")
        if packet.get("ledger_tamper_evident_enabled") is not True:
            errors.append("INVALID_EVIDENCE: required tamper-evident ledger scaffold is not enabled")
        if packet.get("ledger_tamper_proof_claimed") is not False:
            errors.append("INVALID_EVIDENCE: tamper-evident ledger scaffold cannot satisfy tamper-proof")

    if packet.get("requires_aeg_state_write_denial") is not True:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require aeg state write denial scaffold")
    if packet.get("aeg_state_write_denial_present") is not True:
        errors.append("INVALID_EVIDENCE: aeg state write denial scaffold must be present before live executor")
    if packet.get("requires_aeg_state_write_denial") is True:
        if packet.get("aeg_state_write_denial_version") != AEG_STATE_WRITE_DENIAL_SCAFFOLD_V0:
            errors.append("INVALID_EVIDENCE: required aeg state write denial scaffold is missing")
        if packet.get("capability_write_aeg_state_granted") is not False:
            errors.append("INVALID_EVIDENCE: aeg state write denial prerequisite cannot grant write authority")
        if packet.get("capability_write_aeg_state_denied") is not True:
            errors.append("INVALID_EVIDENCE: aeg state write denial prerequisite must deny explicitly")

    if packet.get("requires_external_enforcement") is not True:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require external enforcement before live executor")
    if packet.get("external_enforcement_present") is not False:
        errors.append("INVALID_EVIDENCE: external_enforcement_present must remain false in scaffold v0")
    if packet.get("evidence_store_executor_isolated_required") is not True:
        errors.append("INVALID_EVIDENCE: pre-live executor gate must require executor-isolated evidence store")
    if packet.get("evidence_store_executor_isolated_present") is not False:
        errors.append("INVALID_EVIDENCE: evidence_store_executor_isolated_present must remain false in scaffold v0")
    if packet.get("evidence_store_executor_isolated_present") != packet.get("evidence_store_is_executor_isolated"):
        errors.append("INVALID_EVIDENCE: pre-live gate must mirror evidence_store_is_executor_isolated=false")

    gate_result = packet.get("pre_live_executor_gate_result")
    if gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_result cannot claim PASS/CLEAN/ALLOW")
    if gate_result not in PRE_LIVE_EXECUTOR_GATE_RESULTS:
        errors.append(f"INVALID_EVIDENCE: invalid pre_live_executor_gate_result: {gate_result}")
    if gate_result not in (
        PRE_LIVE_EXECUTOR_GATE_RESULT_HOLD_CURRENT_STATE,
        PRE_LIVE_EXECUTOR_GATE_RESULT_NEEDS_ENFORCEMENT,
    ):
        errors.append(
            "INVALID_EVIDENCE: pre_live_executor_gate_result must remain HOLD_CURRENT_STATE or "
            "NEEDS_ENFORCEMENT_BEFORE_LIVE_EXECUTOR"
        )
    if (
        packet.get("external_enforcement_present") is False
        and gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS
    ):
        errors.append("INVALID_EVIDENCE: external_enforcement_present=false cannot produce PASS/CLEAN/ALLOW")
    if (
        packet.get("evidence_store_executor_isolated_present") is False
        and gate_result in PRE_LIVE_EXECUTOR_GATE_PASSLIKE_RESULTS
    ):
        errors.append("INVALID_EVIDENCE: evidence_store_executor_isolated_present=false cannot produce PASS/CLEAN/ALLOW")
    if packet.get("pre_live_executor_gate_reason") != PRE_LIVE_EXECUTOR_GATE_REASON_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_reason must describe scaffold-only hold")

    metadata_hash = packet.get("pre_live_executor_gate_metadata_hash")
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_pre_live_executor_gate_metadata_hash(packet):
        errors.append("INVALID_EVIDENCE: pre_live_executor_gate_metadata_hash mismatch")


def _validate_ledger_integrity_metadata(packet: dict[str, Any], errors: list[str]) -> None:
    bool_fields = (
        "ledger_tamper_evident_enabled",
        "ledger_tamper_proof_claimed",
    )
    string_fields = (
        "ledger_integrity_version",
        "ledger_integrity_mode",
        "ledger_integrity_status",
        "previous_ledger_hash",
        "current_evidence_hash",
        "current_manifest_hash",
        "current_ledger_entry_hash",
        "ledger_chain_hash",
        "ledger_integrity_metadata_hash",
        "ledger_integrity_check_status",
        "ledger_integrity_check_reason",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)

    sequence = packet.get("ledger_sequence_number")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        errors.append("INVALID_EVIDENCE: ledger_sequence_number must be integer")
    elif sequence < 1:
        errors.append("INVALID_EVIDENCE: ledger_sequence_number must be positive")

    if packet.get("ledger_integrity_version") != LEDGER_INTEGRITY_SCAFFOLD_V0:
        errors.append(f"INVALID_EVIDENCE: ledger_integrity_version must be {LEDGER_INTEGRITY_SCAFFOLD_V0}")
    if packet.get("ledger_integrity_mode") != LEDGER_INTEGRITY_MODE_TAMPER_EVIDENT_SCAFFOLD:
        errors.append("INVALID_EVIDENCE: ledger_integrity_mode must remain tamper_evident_scaffold")
    if packet.get("ledger_tamper_evident_enabled") is not True:
        errors.append("INVALID_EVIDENCE: ledger_tamper_evident_enabled must be true in scaffold v0")
    if packet.get("ledger_tamper_proof_claimed") is not False:
        errors.append("INVALID_EVIDENCE: tamper-evident ledger scaffold cannot claim tamper-proof")

    integrity_status = packet.get("ledger_integrity_status")
    if integrity_status in ("CLEAN", "PASS", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: ledger_integrity_status cannot claim CLEAN/PASS")
    if integrity_status not in LEDGER_INTEGRITY_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid ledger_integrity_status: {integrity_status}")
    if integrity_status != LEDGER_INTEGRITY_STATUS_TAMPER_EVIDENT_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: ledger_integrity_status must remain TAMPER_EVIDENT_SCAFFOLD_ONLY in scaffold v0")

    check_status = packet.get("ledger_integrity_check_status")
    if check_status in ("CLEAN", "PASS", EVIDENCE_STORE_CLEAN):
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_status cannot claim CLEAN/PASS")
    if check_status not in LEDGER_INTEGRITY_CHECK_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid ledger_integrity_check_status: {check_status}")
    if check_status != LEDGER_INTEGRITY_CHECK_STATUS_NOT_CHECKED:
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_status must remain NOT_CHECKED in scaffold v0")
    if packet.get("ledger_integrity_check_reason") != LEDGER_INTEGRITY_CHECK_REASON_SCAFFOLD_ONLY:
        errors.append("INVALID_EVIDENCE: ledger_integrity_check_reason must describe scaffold-only tamper evidence")

    previous_hash = packet.get("previous_ledger_hash")
    if previous_hash in ("", None):
        errors.append("INVALID_EVIDENCE: previous_ledger_hash must be explicit genesis/not_available or sha256")
    elif previous_hash not in (LEDGER_PREVIOUS_HASH_GENESIS, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE) and not is_sha256_hex(
        previous_hash
    ):
        errors.append("INVALID_EVIDENCE: previous_ledger_hash must be explicit genesis/not_available or sha256")
    if sequence == 1 and previous_hash not in (LEDGER_PREVIOUS_HASH_GENESIS, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE):
        errors.append("INVALID_EVIDENCE: first ledger entry must use explicit genesis/not_available previous hash")
    if isinstance(sequence, int) and not isinstance(sequence, bool) and sequence > 1:
        if previous_hash == LEDGER_PREVIOUS_HASH_GENESIS:
            errors.append("INVALID_EVIDENCE: non-genesis ledger entry cannot reuse genesis previous hash")
        if previous_hash == LEDGER_PREVIOUS_HASH_NOT_AVAILABLE:
            errors.append("INVALID_EVIDENCE: non-genesis ledger entry cannot use unavailable previous hash")

    for field in (
        "current_evidence_hash",
        "current_manifest_hash",
        "current_ledger_entry_hash",
        "ledger_chain_hash",
        "ledger_integrity_metadata_hash",
    ):
        value = packet.get(field)
        if not isinstance(value, str) or not _is_sha256_hex(value):
            errors.append(f"INVALID_EVIDENCE: {field} must be sha256 hex")

    evidence_hash = packet.get("current_evidence_hash")
    if isinstance(evidence_hash, str) and _is_sha256_hex(evidence_hash):
        expected_evidence_hash = expected_current_evidence_hash(packet)
        if evidence_hash != expected_evidence_hash:
            errors.append("INVALID_EVIDENCE: current_evidence_hash mismatch")

    chain_hash = packet.get("ledger_chain_hash")
    if isinstance(chain_hash, str) and _is_sha256_hex(chain_hash):
        expected_chain_hash = expected_ledger_chain_hash(packet)
        if chain_hash != expected_chain_hash:
            errors.append("INVALID_EVIDENCE: ledger_chain_hash mismatch")

    metadata_hash = packet.get("ledger_integrity_metadata_hash")
    if isinstance(metadata_hash, str) and _is_sha256_hex(metadata_hash):
        expected_metadata_hash = expected_ledger_integrity_metadata_hash(packet)
        if metadata_hash != expected_metadata_hash:
            errors.append("INVALID_EVIDENCE: ledger_integrity_metadata_hash mismatch")

    if packet.get("binding_status") == BOUND and packet.get("ledger_tamper_proof_claimed") is True:
        errors.append("INVALID_EVIDENCE: EVIDENCE_BINDING != LEDGER_TAMPER_PROOF")


def _dangerous_executor_capability_fields(packet: dict[str, Any]) -> list[str]:
    return [
        field
        for field in EXECUTOR_CAPABILITY_BOOL_FIELDS
        if field != "capability_shell" and packet.get(field) is True
    ]


def _expected_action_risk(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return NOT_CHECKED
    for action in actions:
        risk = action.get("risk") or action.get("action_risk")
        if risk == HIGH:
            return HIGH
        if _action_kind(action) in ACTION_HIGH_RISK_KINDS:
            return HIGH
    return NOT_CHECKED


def _action_kind(action: dict[str, Any]) -> str:
    for field in ("action_type", "action_kind", "kind", "category", "operation", "name"):
        value = action.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip().lower().replace("-", "_").replace(" ", "_")
    return ""


def _validate_proposal_contract_fields(packet: dict[str, Any], errors: list[str]) -> None:
    for field in PROPOSAL_CONTRACT_FIELDS:
        if field not in packet:
            errors.append(f"missing required proposal contract field: {field}")

    bool_fields = (
        "proposal_requires_user_gate",
        "proposal_reported_only",
        "proposal_present",
    )
    string_fields = (
        "proposal_id",
        "proposal_version",
        "proposal_kind",
        "proposal_summary",
        "proposal_trust_boundary",
        "proposal_source",
        "proposal_output_hash_candidate",
        "proposal_redaction_status",
        "proposal_status",
        "proposal_hold_reason",
    )
    list_fields = (
        "proposal_steps",
        "proposal_risk_notes",
    )
    for field in bool_fields:
        _expect(packet, field, bool, errors)
    for field in string_fields:
        _expect(packet, field, str, errors)
    for field in list_fields:
        _expect(packet, field, list, errors)

    if packet.get("proposal_version") != CITIZEN_ONE_PROPOSAL_CONTRACT_V0:
        errors.append(f"INVALID_EVIDENCE: proposal_version must be {CITIZEN_ONE_PROPOSAL_CONTRACT_V0}")
    if packet.get("proposal_trust_boundary") != REPORTED_ONLY:
        errors.append("INVALID_EVIDENCE: proposal_trust_boundary must be reported_only")
    if packet.get("proposal_reported_only") is not True:
        errors.append("INVALID_EVIDENCE: proposal must be marked reported_only")
    if packet.get("proposal_redaction_status") not in PROPOSAL_REDACTION_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid proposal_redaction_status: {packet.get('proposal_redaction_status')}")
    if packet.get("proposal_redaction_status") != PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED:
        errors.append("INVALID_EVIDENCE: proposal_redaction_status must declare no raw prompt/response storage")
    if packet.get("proposal_status") not in PROPOSAL_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid proposal_status: {packet.get('proposal_status')}")
    expected_user_gate = packet.get("status") == NEEDS_USER_GATE or packet.get("risk_level") == HIGH
    if packet.get("proposal_requires_user_gate") != expected_user_gate:
        errors.append("INVALID_EVIDENCE: proposal_requires_user_gate must preserve law/user-gate status")
    if packet.get("proposal_present") is True:
        _validate_deterministic_stub_proposal_fields(packet, errors)
    elif packet.get("proposal_present") is False:
        _validate_provider_hold_proposal_fields(packet, errors)


def _validate_provider_hold_proposal_fields(packet: dict[str, Any], errors: list[str]) -> None:
    if packet.get("proposal_id") != "":
        errors.append("INVALID_EVIDENCE: proposal_id must be empty when proposal is not generated")
    if packet.get("proposal_kind") != PROPOSAL_KIND_NOT_GENERATED:
        errors.append("INVALID_EVIDENCE: proposal_kind must be not_generated when provider is not configured")
    if packet.get("proposal_summary") != "":
        errors.append("INVALID_EVIDENCE: proposal_summary must be empty when proposal is not generated")
    if packet.get("proposal_steps") != []:
        errors.append("INVALID_EVIDENCE: proposal_steps must be empty when proposal is not generated")
    if packet.get("proposal_risk_notes") != []:
        errors.append("INVALID_EVIDENCE: proposal_risk_notes must be empty when proposal is not generated")
    if packet.get("proposal_source") != PROPOSAL_SOURCE_NONE:
        errors.append("INVALID_EVIDENCE: proposal_source must be none when provider is not configured")
    if packet.get("proposal_output_hash_candidate") != "":
        errors.append("INVALID_EVIDENCE: proposal_output_hash_candidate must be empty when proposal is not generated")
    if packet.get("proposal_status") != PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED:
        errors.append("INVALID_EVIDENCE: proposal_status must hold as provider_not_configured")
    if packet.get("proposal_hold_reason") != PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED:
        errors.append("INVALID_EVIDENCE: proposal_hold_reason must be provider_not_configured")


def _validate_deterministic_stub_proposal_fields(packet: dict[str, Any], errors: list[str]) -> None:
    if packet.get("proposal_id") != DETERMINISTIC_STUB_PROPOSAL_ID:
        errors.append("INVALID_EVIDENCE: deterministic proposal stub id mismatch")
    if packet.get("proposal_kind") != PROPOSAL_KIND_DETERMINISTIC_STUB:
        errors.append("INVALID_EVIDENCE: proposal_kind must be deterministic_stub when proposal stub is recorded")
    if packet.get("proposal_summary") != DETERMINISTIC_STUB_PROPOSAL_SUMMARY:
        errors.append("INVALID_EVIDENCE: deterministic proposal stub summary mismatch")
    if packet.get("proposal_steps") != list(DETERMINISTIC_STUB_PROPOSAL_STEPS):
        errors.append("INVALID_EVIDENCE: deterministic proposal stub steps mismatch")
    if packet.get("proposal_risk_notes") != list(DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES):
        errors.append("INVALID_EVIDENCE: deterministic proposal stub risk notes mismatch")
    if packet.get("proposal_source") != PROPOSAL_SOURCE_DETERMINISTIC_STUB:
        errors.append("INVALID_EVIDENCE: proposal_source must be deterministic_stub when proposal stub is recorded")
    if packet.get("proposal_status") != PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED:
        errors.append("INVALID_EVIDENCE: proposal_status must be deterministic_stub_recorded")
    if packet.get("proposal_hold_reason") != PROPOSAL_HOLD_REASON_NONE:
        errors.append("INVALID_EVIDENCE: deterministic proposal stub hold reason must be empty")

    output_hash = packet.get("proposal_output_hash_candidate")
    if not isinstance(output_hash, str) or not _is_sha256_hex(output_hash):
        errors.append("INVALID_EVIDENCE: deterministic proposal stub output hash candidate must be sha256 hex")
    elif output_hash != _expected_deterministic_stub_output_hash(packet):
        errors.append("INVALID_EVIDENCE: deterministic proposal stub output hash candidate mismatch")


def _expected_deterministic_stub_output_hash(packet: dict[str, Any]) -> str:
    hash_payload = {
        "proposal_id": DETERMINISTIC_STUB_PROPOSAL_ID,
        "proposal_version": CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
        "proposal_kind": PROPOSAL_KIND_DETERMINISTIC_STUB,
        "proposal_summary": DETERMINISTIC_STUB_PROPOSAL_SUMMARY,
        "proposal_steps": list(DETERMINISTIC_STUB_PROPOSAL_STEPS),
        "proposal_risk_notes": list(DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES),
        "proposal_requires_user_gate": packet.get("proposal_requires_user_gate"),
        "proposal_trust_boundary": REPORTED_ONLY,
        "proposal_reported_only": True,
        "proposal_source": PROPOSAL_SOURCE_DETERMINISTIC_STUB,
        "proposal_redaction_status": PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "proposal_status": PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
        "proposal_present": True,
        "proposal_hold_reason": PROPOSAL_HOLD_REASON_NONE,
    }
    canonical = json.dumps(hash_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _expected_provider_request_metadata_hash(packet: dict[str, Any]) -> str:
    return _sha256_json(
        {
            "provider_request_requested": packet.get("provider_request_requested"),
            "provider_request_status": packet.get("provider_request_status"),
            "provider_request_id": packet.get("provider_request_id"),
            "provider_request_redaction_status": packet.get("provider_request_redaction_status"),
            "provider_request_raw_stored": packet.get("provider_request_raw_stored"),
        }
    )


def _expected_provider_response_metadata_hash(packet: dict[str, Any]) -> str:
    return _sha256_json(
        {
            "provider_response_present": packet.get("provider_response_present"),
            "provider_response_status": packet.get("provider_response_status"),
            "provider_response_reported_only": packet.get("provider_response_reported_only"),
            "provider_response_trust_boundary": packet.get("provider_response_trust_boundary"),
            "provider_response_redaction_status": packet.get("provider_response_redaction_status"),
            "provider_response_raw_stored": packet.get("provider_response_raw_stored"),
            "provider_error_class": packet.get("provider_error_class"),
            "provider_error_safe_summary": packet.get("provider_error_safe_summary"),
        }
    )


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_forbidden_raw_prompt_response_fields(packet: dict[str, Any], errors: list[str]) -> None:
    errors.extend(validate_no_forbidden_raw_prompt_response_keys(packet, label="evidence"))


def validate_no_forbidden_raw_prompt_response_keys(payload: Any, label: str) -> list[str]:
    errors: list[str] = []
    forbidden = set(FORBIDDEN_RAW_PROMPT_RESPONSE_KEYS)
    for path in _forbidden_key_paths(payload, forbidden):
        errors.append(f"INVALID_EVIDENCE: forbidden raw/secret storage key in {label}: {path}")
    return errors


def _forbidden_key_paths(value: Any, forbidden: set[str], prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                paths.append(key_path)
            paths.extend(_forbidden_key_paths(child, forbidden, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_key_paths(child, forbidden, child_path))
    return paths


def validate_evidence_binding_v0(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in BINDING_REQUIRED_FIELDS:
        if field not in packet:
            errors.append(f"INVALID_EVIDENCE: missing evidence binding field: {field}")

    string_fields = (
        "repo_root",
        "branch",
        "head_sha",
        "tree_sha",
        "changed_files_source",
        "risk_level",
        "status",
        "run_id",
    )
    for field in string_fields:
        value = packet.get(field)
        if field in packet and (not isinstance(value, str) or not value.strip()):
            errors.append(f"INVALID_EVIDENCE: evidence binding field must be non-empty string: {field}")

    if "changed_files" in packet and not isinstance(packet.get("changed_files"), list):
        errors.append("INVALID_EVIDENCE: evidence binding field changed_files must be list")

    return errors


def validate_evidence_binding_v1(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in BINDING_V1_REQUIRED_FIELDS:
        if field not in packet:
            errors.append(f"INVALID_EVIDENCE: missing evidence binding v1 field: {field}")

    if errors:
        return errors

    if packet.get("binding_version") != EVIDENCE_BINDING_V1:
        errors.append(f"INVALID_EVIDENCE: binding_version must be {EVIDENCE_BINDING_V1}")
    if packet.get("binding_status") not in BINDING_STATUSES:
        errors.append(f"INVALID_EVIDENCE: invalid binding_status: {packet.get('binding_status')}")

    string_fields = (
        "binding_version",
        "binding_status",
        "bound_run_id",
        "bound_repo_root",
        "bound_branch",
        "bound_head_sha",
        "bound_tree_sha",
        "bound_changed_files_hash",
        "bound_pre_run_changed_files_hash",
        "bound_post_run_changed_files_hash",
        "bound_computed_mutation_delta_hash",
        "bound_snapshot_trust_boundary_hash",
        "bound_action_boundary_metadata_hash",
        "bound_capability_isolation_metadata_hash",
        "bound_tool_surface_metadata_hash",
        "bound_executor_capability_exposure_metadata_hash",
        "bound_evidence_store_trust_metadata_hash",
        "bound_aeg_state_write_denial_metadata_hash",
        "bound_pre_live_executor_gate_metadata_hash",
        "bound_ledger_integrity_metadata_hash",
        "bound_manifest_hash",
        "bound_manifest_path",
        "bound_at",
    )
    for field in string_fields:
        value = packet.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"INVALID_EVIDENCE: evidence binding v1 field must be non-empty string: {field}")

    binding_reasons = packet.get("binding_reasons")
    if not isinstance(binding_reasons, list):
        errors.append("INVALID_EVIDENCE: binding_reasons must be list")
    elif not all(isinstance(item, str) for item in binding_reasons):
        errors.append("INVALID_EVIDENCE: binding_reasons must contain only strings")

    if packet.get("binding_status") != BOUND:
        errors.append("INVALID_EVIDENCE: binding_status must be BOUND for judgment basis")
    if packet.get("status") == "PASS":
        errors.append("INVALID_EVIDENCE: binding_status cannot promote evidence to PASS")
    if packet.get("status") == CLEAN_CORE and packet.get("binding_status") != BOUND:
        errors.append("INVALID_EVIDENCE: CLEAN_CORE requires binding_status BOUND")
    if packet.get("reported_only") is True:
        errors.append("INVALID_EVIDENCE: reported_only evidence is not judgment basis")
    if packet.get("judgment_basis") == "reported_only":
        errors.append("INVALID_EVIDENCE: reported_only cannot be judgment basis")

    for field in (
        "bound_changed_files_hash",
        "bound_pre_run_changed_files_hash",
        "bound_post_run_changed_files_hash",
        "bound_computed_mutation_delta_hash",
        "bound_snapshot_trust_boundary_hash",
        "bound_action_boundary_metadata_hash",
        "bound_capability_isolation_metadata_hash",
        "bound_tool_surface_metadata_hash",
        "bound_executor_capability_exposure_metadata_hash",
        "bound_evidence_store_trust_metadata_hash",
        "bound_aeg_state_write_denial_metadata_hash",
        "bound_pre_live_executor_gate_metadata_hash",
        "bound_ledger_integrity_metadata_hash",
        "bound_manifest_hash",
    ):
        value = packet.get(field)
        if isinstance(value, str) and not _is_sha256_hex(value):
            errors.append(f"INVALID_EVIDENCE: {field} must be sha256 hex")

    if packet.get("bound_run_id") != packet.get("run_id"):
        errors.append("INVALID_EVIDENCE: bound_run_id mismatch")
    if packet.get("bound_repo_root") != packet.get("repo_root"):
        errors.append("INVALID_EVIDENCE: bound_repo_root mismatch")
    if packet.get("bound_branch") != packet.get("branch"):
        errors.append("INVALID_EVIDENCE: bound_branch mismatch")
    if packet.get("bound_head_sha") != packet.get("head_sha"):
        errors.append("INVALID_EVIDENCE: bound_head_sha mismatch")
    if packet.get("bound_tree_sha") != packet.get("tree_sha"):
        errors.append("INVALID_EVIDENCE: bound_tree_sha mismatch")

    return errors


def validate_completion_contract_v0(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    task_text = packet.get("task_text")
    if not isinstance(task_text, str) or not task_text.strip():
        errors.append("INVALID_EVIDENCE: completion contract requires task_text")

    checks = packet.get("checks")
    if not isinstance(checks, dict):
        return errors + ["INVALID_EVIDENCE: completion contract requires checks"]

    executor = checks.get("executor")
    if not isinstance(executor, dict):
        return errors + ["INVALID_EVIDENCE: missing completion contract executor result"]

    completion_contract = executor.get("completion_contract")
    if not isinstance(completion_contract, dict):
        return errors + ["INVALID_EVIDENCE: missing completion_contract_v0"]

    if completion_contract.get("version") != COMPLETION_CONTRACT_V0:
        errors.append(f"INVALID_EVIDENCE: completion contract version must be {COMPLETION_CONTRACT_V0}")

    if executor.get("executor") != CONTRACT_FIRST_NOOP:
        errors.append(f"INVALID_EVIDENCE: executor mode must be {CONTRACT_FIRST_NOOP}")
    if completion_contract.get("executor_mode") != CONTRACT_FIRST_NOOP:
        errors.append(f"INVALID_EVIDENCE: completion contract executor_mode must be {CONTRACT_FIRST_NOOP}")

    if executor.get("task_text") != task_text:
        errors.append("INVALID_EVIDENCE: completion contract task_text is not bound to evidence task_text")
    if completion_contract.get("task_text_present") is not True:
        errors.append("INVALID_EVIDENCE: completion contract must declare task_text_present=true")

    declared_result = executor.get("declared_result") or completion_contract.get("declared_result")
    if not isinstance(declared_result, str) or not declared_result.strip():
        errors.append("INVALID_EVIDENCE: completion contract requires declared_result shell")

    for field in ("file_mutation", "provider_calls", "network_calls"):
        if executor.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: executor {field} must be false")
        if completion_contract.get(field) is not False:
            errors.append(f"INVALID_EVIDENCE: completion contract {field} must be false")

    if executor.get("actions") != []:
        errors.append("INVALID_EVIDENCE: no-op executor actions must be empty")
    if completion_contract.get("actions") != []:
        errors.append("INVALID_EVIDENCE: no-op completion contract actions must be empty")
    if executor.get("action_count") != 0:
        errors.append("INVALID_EVIDENCE: no-op executor action_count must be 0")
    if completion_contract.get("action_count") != 0:
        errors.append("INVALID_EVIDENCE: no-op completion contract action_count must be 0")
    if executor.get("expected_action_count") != 0:
        errors.append("INVALID_EVIDENCE: no-op executor expected_action_count must be 0")
    if completion_contract.get("expected_action_count") != 0:
        errors.append("INVALID_EVIDENCE: no-op completion contract expected_action_count must be 0")

    completion_reported = completion_contract.get("completion_reported")
    completion_satisfied = completion_contract.get("completion_satisfied")
    if completion_reported is not True:
        errors.append("INVALID_EVIDENCE: completion must be reported by the no-op shell")
    if completion_satisfied is not False:
        errors.append("INVALID_EVIDENCE: no-op completion cannot be marked satisfied")
    if completion_reported == completion_satisfied:
        errors.append("INVALID_EVIDENCE: completion reported must not equal completion satisfied")

    return errors


def validate_user_gate_reason_card_v1(packet: dict[str, Any]) -> list[str]:
    if packet.get("risk_level") != HIGH and packet.get("status") != NEEDS_USER_GATE:
        return []

    errors: list[str] = []
    card = packet.get("user_gate_reason_card")
    if not isinstance(card, dict):
        return ["INVALID_EVIDENCE: HIGH risk evidence requires user_gate_reason_card"]

    for field in USER_GATE_REASON_CARD_FIELDS:
        if field not in card:
            errors.append(f"INVALID_EVIDENCE: user_gate_reason_card missing field: {field}")

    if errors:
        return errors

    if card.get("risk_level") != packet.get("risk_level"):
        errors.append("INVALID_EVIDENCE: user_gate_reason_card risk_level mismatch")
    if card.get("status") != packet.get("status"):
        errors.append("INVALID_EVIDENCE: user_gate_reason_card status mismatch")
    if card.get("intent_risk") != packet.get("intent_risk"):
        errors.append("INVALID_EVIDENCE: user_gate_reason_card intent_risk mismatch")
    if card.get("impact_risk") != packet.get("impact_risk"):
        errors.append("INVALID_EVIDENCE: user_gate_reason_card impact_risk mismatch")
    if card.get("protected_paths_touched") != packet.get("protected_paths_touched"):
        errors.append("INVALID_EVIDENCE: user_gate_reason_card protected_paths_touched mismatch")
    if card.get("safe_default") != SAFE_DEFAULT:
        errors.append("INVALID_EVIDENCE: user_gate_reason_card safe_default mismatch")
    if card.get("irreversible_action_blocked") is not True:
        errors.append("INVALID_EVIDENCE: user_gate_reason_card must block irreversible action")
    why = card.get("why_gate_is_required")
    if not isinstance(why, str) or not why.strip():
        errors.append("INVALID_EVIDENCE: user_gate_reason_card why_gate_is_required must be non-empty")

    return errors


def _expect(packet: dict[str, Any], field: str, expected: type, errors: list[str]) -> None:
    if field in packet and not isinstance(packet[field], expected):
        errors.append(f"{field} must be {expected.__name__}")


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)
