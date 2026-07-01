"""Evidence packet schema checks for v0.1."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    AEG_VERSION,
    BINDING_STATUSES,
    BOUND,
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
    EVIDENCE_BINDING_V1,
    GIT_STATUS_PORCELAIN_V1,
    HIGH,
    IMPACT_RISKS,
    NEEDS_USER_GATE,
    MUTATION_BOUNDARY_STATUSES,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_DELTA_SOURCE_COMPUTED,
    MUTATION_DELTA_SOURCE_UNTRUSTED,
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

BINDING_V1_REQUIRED_FIELDS: tuple[str, ...] = (
    "binding_version",
    "binding_status",
    "binding_reasons",
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
    "bound_manifest_hash",
    "bound_manifest_path",
    "bound_at",
)

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


def _validate_forbidden_raw_prompt_response_fields(packet: dict[str, Any], errors: list[str]) -> None:
    forbidden = {
        "raw_prompt",
        "raw_response",
        "provider_request_body",
        "provider_response_body",
        "model_request_body",
        "model_response_body",
    }
    for field in forbidden:
        if field in packet:
            errors.append(f"INVALID_EVIDENCE: raw prompt/response storage field is forbidden: {field}")


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
