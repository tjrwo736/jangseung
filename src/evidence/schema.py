"""Evidence packet schema checks for v0.1."""

from __future__ import annotations

from typing import Any

from src.contracts import (
    AEG_VERSION,
    BINDING_STATUSES,
    BOUND,
    CHANGED_FILES_SOURCES,
    CLEAN_CORE,
    COMPLETION_CONTRACT_V0,
    CONTRACT_FIRST_NOOP,
    EVIDENCE_BINDING_V1,
    GIT_STATUS_PORCELAIN_V1,
    HIGH,
    IMPACT_RISKS,
    NEEDS_USER_GATE,
    MUTATION_BOUNDARY_STATUSES,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_DELTA_SOURCE_COMPUTED,
    MUTATION_DELTA_SOURCE_UNTRUSTED,
    RISK_LEVELS,
    SAFE_DEFAULT,
    SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
    STATUSES,
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
