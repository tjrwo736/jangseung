"""Build bound evidence packets."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.classify import Classification
from src.citizen_one import build_citizen_one_evidence
from src.contracts import AEG_VERSION, NEEDS_USER_GATE, SAFE_DEFAULT, STATE_DIR
from src.evidence.aeg_state_write_denial import build_aeg_state_write_denial_metadata
from src.evidence.action_boundary import build_action_boundary_metadata
from src.evidence.capability_exposure import build_capability_exposure_metadata
from src.evidence.capability_isolation import build_capability_isolation_metadata
from src.evidence.evidence_store import build_evidence_store_trust_metadata
from src.evidence.pre_live_executor_gate import build_pre_live_executor_gate_metadata
from src.evidence.tool_surface import build_tool_surface_metadata
from src.law import LawResult
from src.state import git


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{uuid4().hex[:8]}"


def build_evidence_packet(
    cwd: str | Path,
    task_text: str,
    classification: Classification,
    law_result: LawResult,
    executor_result: dict[str, Any],
    mutation_boundary: dict[str, Any] | None = None,
    citizen_one_requested: bool = False,
    proposal_stub_requested: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    repo = git.repo_root(cwd)
    boundary = mutation_boundary or {}
    citizen_one = build_citizen_one_evidence(
        citizen_one_requested,
        proposal_requires_user_gate=law_result.status == NEEDS_USER_GATE,
        proposal_stub_requested=proposal_stub_requested,
    )
    action_boundary = build_action_boundary_metadata(executor_result)
    capability_isolation = build_capability_isolation_metadata(executor_result)
    tool_surface = build_tool_surface_metadata(executor_result)
    capability_exposure = build_capability_exposure_metadata(executor_result)
    evidence_store_trust = build_evidence_store_trust_metadata()
    aeg_state_write_denial = build_aeg_state_write_denial_metadata()
    pre_live_executor_gate = build_pre_live_executor_gate_metadata()
    packet: dict[str, Any] = {
        "aeg_version": AEG_VERSION,
        "run_id": run_id or new_run_id(),
        "task_text": task_text,
        "repo_root": str(repo),
        "branch": git.branch_name(repo),
        "head_sha": git.head_sha(repo),
        "tree_sha": git.tree_sha(repo),
        "is_dirty": git.is_dirty(repo),
        "changed_files": list(classification.changed_files),
        "changed_files_source": classification.changed_files_source,
        "intent_risk": classification.intent_risk,
        "impact_risk": classification.impact_risk,
        "risk_level": classification.risk_level,
        "classification_reasons": list(classification.classification_reasons),
        "impact_reasons": list(classification.impact_reasons),
        "protected_paths_touched": list(classification.protected_paths_touched),
        "risk_escalation_applied": classification.risk_escalation_applied,
        "final_risk_rule": classification.final_risk_rule,
        "impact_checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": {
            "executor": executor_result,
            "completion_contract_v0_required": True,
            "evidence_binding_v0_required": True,
            "runtime_state_root": STATE_DIR,
            "runtime_artifacts_under_state": True,
            "not_checked_is_not_pass": True,
            "deterministic_law_replay_required": True,
            "citizen_one_control_plane_v0_required": True,
            "citizen_one_reported_only_is_not_judgment_basis": True,
            "citizen_one_proposal_contract_v0_required": citizen_one_requested,
            "proposal_reported_only_is_not_judgment_basis": citizen_one_requested,
            "deterministic_proposal_stub_opt_in": citizen_one_requested and proposal_stub_requested,
            "prompt_response_redaction_metadata_v0_required": True,
            "raw_prompt_response_storage_forbidden": True,
            "provider_runtime_opt_in_guard_metadata_v0_required": True,
            "provider_selection_metadata_v0_required": True,
            "provider_secret_env_safe_metadata_v0_required": True,
            "provider_network_opt_in_guard_metadata_v0_required": True,
            "provider_request_response_safe_metadata_v0_required": True,
            "provider_runtime_request_execution_forbidden": True,
            "raw_provider_runtime_storage_forbidden": True,
            "action_boundary_scaffold_v0_required": True,
            "action_interception_enabled": False,
            "action_boundary_clean_claim_forbidden": True,
            "mutation_boundary_clean_does_not_imply_action_boundary_clean": True,
            "git_diff_clean_does_not_imply_action_clean": True,
            "no_matched_dangerous_command_is_not_action_boundary_clean": True,
            "executor_reported_actions_is_reported_only": True,
            "reported_only_is_not_judgment_basis": True,
            "command_enumeration_only_grants_no_authority": True,
            "capability_isolation_scaffold_v0_required": True,
            "capability_isolation_enabled": False,
            "capability_boundary_clean_claim_forbidden": True,
            "capability_not_implemented_is_not_clean": True,
            "capability_not_observed_is_not_clean": True,
            "missing_isolation_proof_is_not_clean": True,
            "unavailable_capability_proof_is_not_checked": True,
            "executor_reported_capabilities_is_reported_only": True,
            "capability_reported_only_is_not_judgment_basis": True,
            "no_live_executor_authority_before_capability_isolation": True,
            "tool_surface_authority_grant_scaffold_v0_required": True,
            "tool_surface_enabled": False,
            "tool_surface_clean_claim_forbidden": True,
            "tool_surface_not_implemented_is_not_clean": True,
            "no_requested_tool_is_not_clean": True,
            "no_granted_tool_is_not_external_proof": True,
            "tool_authority_grant_count_expected_zero": True,
            "tool_authority_flags_default_false": True,
            "executor_reported_tool_usage_is_reported_only": True,
            "tool_usage_reported_only_is_not_judgment_basis": True,
            "command_denylist_alone_grants_no_tool_authority": True,
            "no_live_executor_authority_before_tool_surface": True,
            "executor_capability_exposure_scaffold_v0_required": True,
            "executor_capability_exposure_current_noop_only": True,
            "executor_capability_fields_default_false": True,
            "current_noop_executor_has_no_shell_network_provider_action": True,
            "no_raw_shell_is_not_no_dangerous_capability": True,
            "structured_tool_call_is_not_safe_capability": True,
            "executor_capability_exposure_reported_only_is_not_judgment_basis": True,
            "evidence_store_trust_boundary_metadata_required": True,
            "aeg_folder_local_state_is_not_executor_isolated": True,
            "evidence_binding_is_not_evidence_store_tamper_proof": True,
            "evidence_store_integrity_not_checked_is_not_clean": True,
            "executor_can_write_evidence_store_not_checked_is_not_clean": True,
            "aeg_state_write_denial_scaffold_v0_required": True,
            "capability_write_aeg_state_granted_default_false": True,
            "capability_write_aeg_state_denied_explicit": True,
            "aeg_state_write_denial_enforcement_not_claimed": True,
            "aeg_state_write_denial_metadata_is_not_external_proof": True,
            "executor_self_report_is_not_aeg_state_denial_proof": True,
            "raw_shell_write_aeg_state_bypass_forbidden": True,
            "write_file_write_aeg_state_bypass_forbidden": True,
            "repo_outside_write_aeg_state_bypass_forbidden": True,
            "executor_controlled_recorder_write_aeg_state_bypass_forbidden": True,
            "no_live_executor_authority_before_aeg_state_write_denial_enforcement": True,
            "ledger_integrity_scaffold_v0_required": True,
            "ledger_tamper_evident_is_not_tamper_proof": True,
            "ledger_tamper_proof_claim_forbidden": True,
            "ledger_integrity_clean_claim_forbidden": True,
            "ledger_integrity_check_not_checked_is_not_pass": True,
            "pre_live_executor_gate_scaffold_v0_required": True,
            "pre_live_executor_gate_candidate_e_requires_ledger": True,
            "pre_live_executor_gate_candidate_e_requires_aeg_state_write_denial": True,
            "live_executor_authority_granted_default_false": True,
            "pre_live_executor_gate_pass_clean_allow_forbidden": True,
            "external_enforcement_absent_keeps_live_executor_on_hold": True,
            "evidence_store_executor_isolation_absent_keeps_live_executor_on_hold": True,
        },
        "status": law_result.status,
        "status_reasons": list(law_result.status_reasons),
        "safe_default": SAFE_DEFAULT,
    }
    packet.update(citizen_one)
    packet.update(action_boundary)
    packet.update(capability_isolation)
    packet.update(tool_surface)
    packet.update(capability_exposure)
    packet.update(evidence_store_trust)
    packet.update(aeg_state_write_denial)
    packet.update(pre_live_executor_gate)
    packet.update(
        {
            "pre_run_changed_files": list(boundary.get("pre_run_changed_files", [])),
            "post_run_changed_files": list(boundary.get("post_run_changed_files", [])),
            "pre_snapshot_source": boundary.get("pre_snapshot_source", ""),
            "post_snapshot_source": boundary.get("post_snapshot_source", ""),
            "snapshot_collector": boundary.get("snapshot_collector", ""),
            "snapshot_trust_boundary": dict(boundary.get("snapshot_trust_boundary", {})),
            "executor_reported_changed_files": list(boundary.get("executor_reported_changed_files", [])),
            "executor_reported_changed_files_source": boundary.get("executor_reported_changed_files_source", ""),
            "executor_reported_mutation_delta": list(boundary.get("executor_reported_mutation_delta", [])),
            "executor_reported_mutation_delta_source": boundary.get("executor_reported_mutation_delta_source", ""),
            "computed_mutation_delta": list(boundary.get("computed_mutation_delta", [])),
            "mutation_delta_source": boundary.get("mutation_delta_source", ""),
            "pre_existing_dirty_tree": list(boundary.get("pre_existing_dirty_tree", [])),
            "executor_created_mutation": list(boundary.get("executor_created_mutation", [])),
            "protected_path_mutation_detected": boundary.get("protected_path_mutation_detected") is True,
            "mutation_boundary_status": boundary.get("mutation_boundary_status", ""),
        }
    )
    if law_result.user_gate_reason_card is not None:
        packet["user_gate_reason_card"] = dict(law_result.user_gate_reason_card)
    return packet
