"""Command-line interface for the Day-1 Aegis runtime spine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from src.agents import execute_contract
from src.classify import classify_task
from src.contracts import (
    GIT_WORKING_TREE,
    MUTATION_BOUNDARY_DELTA_DETECTED,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    NOT_CHECKED_SOURCE,
    SAFE_DEFAULT,
)
from src.evidence import build_evidence_packet, verify_latest
from src.evidence.mutation_boundary import (
    build_mutation_boundary,
    capture_mutation_snapshot,
    mutation_delta_paths,
)
from src.law import apply_law
from src.state import git
from src.state.doctor import DoctorCheck, doctor_status, run_doctor
from src.state.store import ensure_initialized, require_initialized, save_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aeg", description="Aegis contract-first runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="initialize folder-local .aeg/ state")
    subparsers.add_parser("doctor", help="check local runtime prerequisites")
    run_parser = subparsers.add_parser("run", help="record a contract-first no-op run")
    run_parser.add_argument(
        "--citizen-one",
        action="store_true",
        help="opt in to the Citizen One control plane skeleton",
    )
    run_parser.add_argument(
        "--proposal-stub",
        action="store_true",
        help="record a deterministic local Citizen One proposal stub; requires --citizen-one",
    )
    run_parser.add_argument("task", help="task text to classify and gate")
    subparsers.add_parser("verify", help="verify latest evidence with deterministic replay")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(Path.cwd())
    if args.command == "doctor":
        return _cmd_doctor(Path.cwd())
    if args.command == "run":
        return _cmd_run(
            Path.cwd(),
            args.task,
            citizen_one_requested=args.citizen_one,
            proposal_stub_requested=args.proposal_stub,
        )
    if args.command == "verify":
        return _cmd_verify(Path.cwd())
    parser.error(f"unknown command: {args.command}")
    return 2


def _cmd_init(cwd: Path) -> int:
    try:
        repo = git.repo_root(cwd)
        result = ensure_initialized(repo)
    except Exception as exc:
        _print_card("Aegis init", "FAIL", [("error", str(exc))])
        return 1

    ignored = git.is_ignored(repo, ".aeg/")
    status = "PASS" if ignored else "WARN"
    rows = [
        ("repo_root", str(repo)),
        ("state_root", result["state_root"]),
        ("config", result["config_path"]),
        ("runs", result["runs_path"]),
        ("ledger", result["ledger_path"]),
        ("git_ignored", str(ignored)),
    ]
    if not ignored:
        rows.append(("warning", ".aeg/ is not ignored by git"))
    _print_card("Aegis init", status, rows)
    return 0 if ignored else 0


def _cmd_doctor(cwd: Path) -> int:
    checks = run_doctor(cwd)
    status = doctor_status(checks)
    _print_doctor_card(status, checks)
    return 1 if status == "FAIL" else 0


def _cmd_run(
    cwd: Path,
    task_text: str,
    citizen_one_requested: bool = False,
    proposal_stub_requested: bool = False,
) -> int:
    if proposal_stub_requested and not citizen_one_requested:
        _print_card("Aegis run", "FAIL", [("error", "--proposal-stub requires --citizen-one")])
        return 2

    try:
        repo = git.repo_root(cwd)
        require_initialized(repo)
        pre_snapshot = capture_mutation_snapshot(repo)
        changed_files, changed_files_source = _runtime_changed_files(pre_snapshot.changed_files)
        classification = classify_task(
            task_text,
            changed_files=changed_files,
            changed_files_source=changed_files_source,
            # The Day-1 executor is no-op and does not mutate files. The CLI still
            # scans the current working tree for pre-existing impact risk.
            # no_mutation=False means "do not skip impact scanning", not "the
            # executor mutated files". Future model-backed execution must split
            # pre_run_changed_files and post_run_changed_files.
            no_mutation=False,
        )
        law_result = apply_law(classification)
        executor_result = execute_contract(task_text, classification, law_result)
        post_snapshot = capture_mutation_snapshot(repo)
        mutation_boundary = build_mutation_boundary(pre_snapshot, post_snapshot, executor_result)
        classification = _classification_after_mutation_boundary(task_text, classification, mutation_boundary)
        law_result = apply_law(classification)
        evidence = build_evidence_packet(
            repo,
            task_text,
            classification,
            law_result,
            executor_result,
            mutation_boundary=mutation_boundary,
            citizen_one_requested=citizen_one_requested,
            proposal_stub_requested=proposal_stub_requested,
        )
        run_payload = {
            "run_id": evidence["run_id"],
            "task_text": task_text,
            "executor": executor_result,
            "status": evidence["status"],
            "risk_level": evidence["risk_level"],
            "evidence_file": "evidence.json",
        }
        paths = save_run(repo, evidence, run_payload)
    except Exception as exc:
        _print_card("Aegis run", "FAIL", [("error", str(exc))])
        return 1

    rows = [
        ("run_id", evidence["run_id"]),
        ("intent_risk", evidence["intent_risk"]),
        ("impact_risk", evidence["impact_risk"]),
        ("changed_files_source", evidence["changed_files_source"]),
        ("mutation_boundary_status", evidence["mutation_boundary_status"]),
        ("mutation_delta_source", evidence["mutation_delta_source"]),
        ("risk_level", evidence["risk_level"]),
        ("status", evidence["status"]),
        ("citizen_one_requested", str(evidence["citizen_one_requested"]).lower()),
        ("citizen_one_mode", evidence["citizen_one_mode"]),
        ("citizen_one_status", evidence["citizen_one_status"]),
        ("citizen_one_provider_status", evidence["citizen_one_provider_status"]),
        ("citizen_one_output_present", str(evidence["citizen_one_output_present"]).lower()),
        ("citizen_one_output_trust_boundary", evidence["citizen_one_output_trust_boundary"]),
        ("provider_network_used", str(evidence["provider_network_used"]).lower()),
        ("provider_secret_observed", str(evidence["provider_secret_observed"]).lower()),
        ("binding_status", evidence.get("binding_status", "")),
        ("binding_version", evidence.get("binding_version", "")),
        ("manifest_hash", _short_hash(evidence.get("bound_manifest_hash", ""))),
        ("binding_reason_count", str(len(evidence.get("binding_reasons", [])))),
        ("evidence", paths["evidence_path"]),
    ]
    rows.extend(_action_boundary_rows(evidence))
    rows.extend(_capability_isolation_rows(evidence))
    rows.extend(_tool_surface_rows(evidence))
    rows.extend(_executor_capability_exposure_rows(evidence))
    rows.extend(_evidence_store_trust_rows(evidence))
    rows.extend(_aeg_state_write_denial_rows(evidence))
    rows.extend(_mediated_write_boundary_rows(evidence))
    rows.extend(_pre_live_executor_gate_rows(evidence))
    rows.extend(_ledger_integrity_rows(evidence))
    rows.extend(_provider_adapter_rows(evidence))
    rows.extend(_proposal_rows(evidence))
    rows.extend(_user_gate_rows(evidence.get("user_gate_reason_card")))
    _print_card("Aegis run", evidence["status"], rows, evidence["classification_reasons"] + evidence["status_reasons"])
    return 0


def _runtime_changed_files(snapshot: list[dict[str, object]]) -> tuple[list[str], str]:
    return git.changed_files_from_snapshot(snapshot), git.changed_files_source_from_snapshot(snapshot)


def _classification_after_mutation_boundary(task_text: str, classification, mutation_boundary: dict[str, object]):
    boundary_status = mutation_boundary.get("mutation_boundary_status")
    if boundary_status == MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT:
        return classify_task(
            task_text,
            changed_files=[],
            changed_files_source=NOT_CHECKED_SOURCE,
            no_mutation=False,
        )
    if boundary_status != MUTATION_BOUNDARY_DELTA_DETECTED:
        return classification

    pre_paths = git.changed_files_from_snapshot(_snapshot_entries(mutation_boundary.get("pre_run_changed_files")))
    delta_paths = mutation_delta_paths(_snapshot_entries(mutation_boundary.get("computed_mutation_delta")))
    changed_files = sorted(dict.fromkeys([*pre_paths, *delta_paths]))
    return classify_task(
        task_text,
        changed_files=changed_files,
        changed_files_source=GIT_WORKING_TREE,
        no_mutation=False,
    )


def _snapshot_entries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _cmd_verify(cwd: Path) -> int:
    result = verify_latest(cwd)
    status = "REPLAY_CONSISTENT" if result.ok else "REPLAY_FAILED"
    rows = [
        ("verification_scope", "deterministic_replay_and_binding_validation"),
        ("independent_oracle", "false"),
    ]
    if result.evidence:
        rows.extend(
            [
                ("run_id", result.evidence.get("run_id", "")),
                ("intent_risk", result.evidence.get("intent_risk", "")),
                ("impact_risk", result.evidence.get("impact_risk", "")),
                ("changed_files_source", result.evidence.get("changed_files_source", "")),
                ("risk_level", result.evidence.get("risk_level", "")),
                ("evidence_status_value", result.evidence.get("status", "")),
                ("citizen_one_requested", str(result.evidence.get("citizen_one_requested", "")).lower()),
                ("citizen_one_mode", result.evidence.get("citizen_one_mode", "")),
                ("citizen_one_status", result.evidence.get("citizen_one_status", "")),
                ("citizen_one_provider_status", result.evidence.get("citizen_one_provider_status", "")),
                ("citizen_one_output_present", str(result.evidence.get("citizen_one_output_present", "")).lower()),
                ("provider_network_used", str(result.evidence.get("provider_network_used", "")).lower()),
                ("provider_secret_observed", str(result.evidence.get("provider_secret_observed", "")).lower()),
                ("binding_status", result.evidence.get("binding_status", "")),
                ("binding_version", result.evidence.get("binding_version", "")),
                ("manifest_hash", _short_hash(result.evidence.get("bound_manifest_hash", ""))),
                ("binding_reason_count", str(len(result.evidence.get("binding_reasons", [])))),
            ]
        )
        rows.extend(_action_boundary_rows(result.evidence))
        rows.extend(_capability_isolation_rows(result.evidence))
        rows.extend(_tool_surface_rows(result.evidence))
        rows.extend(_executor_capability_exposure_rows(result.evidence))
        rows.extend(_evidence_store_trust_rows(result.evidence))
        rows.extend(_aeg_state_write_denial_rows(result.evidence))
        rows.extend(_mediated_write_boundary_rows(result.evidence))
        rows.extend(_pre_live_executor_gate_rows(result.evidence))
        rows.extend(_ledger_integrity_rows(result.evidence))
        rows.extend(_provider_adapter_rows(result.evidence))
        rows.extend(_proposal_rows(result.evidence))
    rows.extend(("check", check) for check in result.checks)
    rows.extend(("error", error) for error in result.errors)
    _print_card("Aegis verify", status, rows)
    return 0 if result.ok else 1


def _user_gate_rows(card: object) -> list[tuple[str, str]]:
    if not isinstance(card, dict):
        return []
    protected_paths = card.get("protected_paths_touched", [])
    if isinstance(protected_paths, list):
        protected_paths_value = ",".join(str(path) for path in protected_paths) or "[]"
    else:
        protected_paths_value = str(protected_paths)
    return [
        ("user_gate.risk_level", str(card.get("risk_level", ""))),
        ("user_gate.status", str(card.get("status", ""))),
        ("user_gate.why", str(card.get("why_gate_is_required", ""))),
        ("user_gate.irreversible_action_blocked", str(card.get("irreversible_action_blocked", ""))),
        ("user_gate.intent_risk", str(card.get("intent_risk", ""))),
        ("user_gate.impact_risk", str(card.get("impact_risk", ""))),
        ("user_gate.protected_paths_touched", protected_paths_value),
        ("user_gate.safe_default", str(card.get("safe_default", ""))),
    ]


def _proposal_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    if "proposal_present" not in evidence:
        return []
    steps = evidence.get("proposal_steps", [])
    risk_notes = evidence.get("proposal_risk_notes", [])
    return [
        ("proposal_present", str(evidence.get("proposal_present", "")).lower()),
        ("proposal_status", str(evidence.get("proposal_status", ""))),
        ("proposal_hold_reason", str(evidence.get("proposal_hold_reason", ""))),
        ("proposal_reported_only", str(evidence.get("proposal_reported_only", "")).lower()),
        ("proposal_trust_boundary", str(evidence.get("proposal_trust_boundary", ""))),
        ("proposal_requires_user_gate", str(evidence.get("proposal_requires_user_gate", "")).lower()),
        ("proposal_source", str(evidence.get("proposal_source", ""))),
        ("proposal_redaction_status", str(evidence.get("proposal_redaction_status", ""))),
        ("proposal_output_hash_candidate", str(evidence.get("proposal_output_hash_candidate", ""))),
        ("proposal_step_count", str(len(steps) if isinstance(steps, list) else "")),
        ("proposal_risk_note_count", str(len(risk_notes) if isinstance(risk_notes, list) else "")),
    ]


def _action_boundary_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("action_boundary_version", str(evidence.get("action_boundary_version", ""))),
        ("action_interception_enabled", str(evidence.get("action_interception_enabled", "")).lower()),
        ("action_boundary_status", str(evidence.get("action_boundary_status", ""))),
        ("action_log_source", str(evidence.get("action_log_source", ""))),
        ("action_log_source_trust_boundary", str(evidence.get("action_log_source_trust_boundary", ""))),
        ("action_count", str(evidence.get("action_count", ""))),
        ("expected_action_count", str(evidence.get("expected_action_count", ""))),
        ("action_risk", str(evidence.get("action_risk", ""))),
        ("command_enumeration_only", str(evidence.get("command_enumeration_only", "")).lower()),
        ("no_matched_dangerous_command", str(evidence.get("no_matched_dangerous_command", "")).lower()),
        ("capability_isolation_enabled", str(evidence.get("capability_isolation_enabled", "")).lower()),
        ("raw_shell_authority_granted", str(evidence.get("raw_shell_authority_granted", "")).lower()),
        ("network_authority_granted", str(evidence.get("network_authority_granted", "")).lower()),
        ("provider_authority_granted", str(evidence.get("provider_authority_granted", "")).lower()),
        ("remote_write_authority_granted", str(evidence.get("remote_write_authority_granted", "")).lower()),
        ("computed_action_log_hash", _short_hash(evidence.get("computed_action_log_hash", ""))),
    ]


def _capability_isolation_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("capability_isolation_version", str(evidence.get("capability_isolation_version", ""))),
        ("capability_isolation_mode", str(evidence.get("capability_isolation_mode", ""))),
        ("capability_boundary_status", str(evidence.get("capability_boundary_status", ""))),
        ("capability_boundary_source", str(evidence.get("capability_boundary_source", ""))),
        ("capability_boundary_trust_boundary", str(evidence.get("capability_boundary_trust_boundary", ""))),
        (
            "process_execution_authority_granted",
            str(evidence.get("process_execution_authority_granted", "")).lower(),
        ),
        (
            "credential_env_access_authority_granted",
            str(evidence.get("credential_env_access_authority_granted", "")).lower(),
        ),
        (
            "deploy_release_publish_authority_granted",
            str(evidence.get("deploy_release_publish_authority_granted", "")).lower(),
        ),
        (
            "repo_outside_write_authority_granted",
            str(evidence.get("repo_outside_write_authority_granted", "")).lower(),
        ),
        (
            "package_dependency_mutation_authority_granted",
            str(evidence.get("package_dependency_mutation_authority_granted", "")).lower(),
        ),
        ("telemetry_authority_granted", str(evidence.get("telemetry_authority_granted", "")).lower()),
        ("capability_matrix_hash", _short_hash(evidence.get("capability_matrix_hash", ""))),
        ("capability_isolation_proof_hash", _short_hash(evidence.get("capability_isolation_proof_hash", ""))),
    ]


def _tool_surface_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("tool_surface_version", str(evidence.get("tool_surface_version", ""))),
        ("tool_surface_enabled", str(evidence.get("tool_surface_enabled", "")).lower()),
        ("tool_surface_status", str(evidence.get("tool_surface_status", ""))),
        ("tool_surface_source", str(evidence.get("tool_surface_source", ""))),
        ("tool_surface_trust_boundary", str(evidence.get("tool_surface_trust_boundary", ""))),
        ("requested_tool_capability_count", str(_list_count(evidence.get("requested_tool_capabilities")))),
        ("granted_tool_capability_count", str(_list_count(evidence.get("granted_tool_capabilities")))),
        ("denied_tool_capability_count", str(_list_count(evidence.get("denied_tool_capabilities")))),
        ("tool_authority_grant_count", str(evidence.get("tool_authority_grant_count", ""))),
        ("expected_tool_authority_grant_count", str(evidence.get("expected_tool_authority_grant_count", ""))),
        ("raw_shell_tool_authority_granted", str(evidence.get("raw_shell_tool_authority_granted", "")).lower()),
        (
            "process_execution_tool_authority_granted",
            str(evidence.get("process_execution_tool_authority_granted", "")).lower(),
        ),
        ("network_tool_authority_granted", str(evidence.get("network_tool_authority_granted", "")).lower()),
        ("provider_tool_authority_granted", str(evidence.get("provider_tool_authority_granted", "")).lower()),
        (
            "credential_env_tool_authority_granted",
            str(evidence.get("credential_env_tool_authority_granted", "")).lower(),
        ),
        ("remote_write_tool_authority_granted", str(evidence.get("remote_write_tool_authority_granted", "")).lower()),
        (
            "deploy_release_publish_tool_authority_granted",
            str(evidence.get("deploy_release_publish_tool_authority_granted", "")).lower(),
        ),
        (
            "repo_outside_write_tool_authority_granted",
            str(evidence.get("repo_outside_write_tool_authority_granted", "")).lower(),
        ),
        (
            "file_mutation_tool_authority_granted",
            str(evidence.get("file_mutation_tool_authority_granted", "")).lower(),
        ),
        ("telemetry_tool_authority_granted", str(evidence.get("telemetry_tool_authority_granted", "")).lower()),
        ("tool_authority_grant_hash", _short_hash(evidence.get("tool_authority_grant_hash", ""))),
        ("tool_surface_metadata_hash", _short_hash(evidence.get("tool_surface_metadata_hash", ""))),
    ]


def _executor_capability_exposure_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (
            "executor_capability_exposure_version",
            str(evidence.get("executor_capability_exposure_version", "")),
        ),
        ("executor_capability_exposure_scope", str(evidence.get("executor_capability_exposure_scope", ""))),
        ("executor_capability_transport", str(evidence.get("executor_capability_transport", ""))),
        ("current_executor_capability_status", str(evidence.get("current_executor_capability_status", ""))),
        ("capability_read_repo", str(evidence.get("capability_read_repo", "")).lower()),
        ("capability_write_repo", str(evidence.get("capability_write_repo", "")).lower()),
        ("capability_read_aeg_state", str(evidence.get("capability_read_aeg_state", "")).lower()),
        ("capability_write_aeg_state", str(evidence.get("capability_write_aeg_state", "")).lower()),
        ("capability_read_outside_repo", str(evidence.get("capability_read_outside_repo", "")).lower()),
        ("capability_write_outside_repo", str(evidence.get("capability_write_outside_repo", "")).lower()),
        ("capability_delete_outside_repo", str(evidence.get("capability_delete_outside_repo", "")).lower()),
        ("capability_network", str(evidence.get("capability_network", "")).lower()),
        ("capability_remote_write", str(evidence.get("capability_remote_write", "")).lower()),
        ("capability_provider_call", str(evidence.get("capability_provider_call", "")).lower()),
        ("capability_env_read", str(evidence.get("capability_env_read", "")).lower()),
        ("capability_secret_read", str(evidence.get("capability_secret_read", "")).lower()),
        ("capability_process_spawn", str(evidence.get("capability_process_spawn", "")).lower()),
        ("capability_shell", str(evidence.get("capability_shell", "")).lower()),
        (
            "executor_capability_action_count",
            str(evidence.get("executor_capability_action_count", "")),
        ),
        (
            "executor_capability_expected_action_count",
            str(evidence.get("executor_capability_expected_action_count", "")),
        ),
        (
            "executor_capability_exposure_hash",
            _short_hash(evidence.get("executor_capability_exposure_hash", "")),
        ),
        (
            "executor_capability_exposure_metadata_hash",
            _short_hash(evidence.get("executor_capability_exposure_metadata_hash", "")),
        ),
    ]


def _evidence_store_trust_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("evidence_store_trust_boundary", str(evidence.get("evidence_store_trust_boundary", ""))),
        ("evidence_store_writer", str(evidence.get("evidence_store_writer", ""))),
        (
            "executor_can_write_evidence_store",
            str(evidence.get("executor_can_write_evidence_store", "")),
        ),
        (
            "evidence_store_is_executor_isolated",
            str(evidence.get("evidence_store_is_executor_isolated", "")).lower(),
        ),
        ("evidence_store_write_source", str(evidence.get("evidence_store_write_source", ""))),
        ("evidence_store_integrity_status", str(evidence.get("evidence_store_integrity_status", ""))),
        (
            "evidence_store_trust_metadata_hash",
            _short_hash(evidence.get("evidence_store_trust_metadata_hash", "")),
        ),
    ]


def _aeg_state_write_denial_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("aeg_state_write_denial_version", str(evidence.get("aeg_state_write_denial_version", ""))),
        ("aeg_state_write_denial_mode", str(evidence.get("aeg_state_write_denial_mode", ""))),
        ("aeg_state_write_denial_status", str(evidence.get("aeg_state_write_denial_status", ""))),
        (
            "capability_write_aeg_state_requested",
            str(evidence.get("capability_write_aeg_state_requested", "")).lower(),
        ),
        (
            "capability_write_aeg_state_granted",
            str(evidence.get("capability_write_aeg_state_granted", "")).lower(),
        ),
        (
            "capability_write_aeg_state_denied",
            str(evidence.get("capability_write_aeg_state_denied", "")).lower(),
        ),
        ("raw_shell_can_write_aeg_state", str(evidence.get("raw_shell_can_write_aeg_state", "")).lower()),
        ("write_file_can_write_aeg_state", str(evidence.get("write_file_can_write_aeg_state", "")).lower()),
        (
            "repo_outside_write_can_write_aeg_state",
            str(evidence.get("repo_outside_write_can_write_aeg_state", "")).lower(),
        ),
        (
            "executor_controlled_recorder_can_write_aeg_state",
            str(evidence.get("executor_controlled_recorder_can_write_aeg_state", "")).lower(),
        ),
        (
            "aeg_state_write_denial_enforcement_status",
            str(evidence.get("aeg_state_write_denial_enforcement_status", "")),
        ),
        ("aeg_state_write_denial_source", str(evidence.get("aeg_state_write_denial_source", ""))),
        ("aeg_state_write_denial_reason", str(evidence.get("aeg_state_write_denial_reason", ""))),
        (
            "aeg_state_write_denial_metadata_hash",
            _short_hash(evidence.get("aeg_state_write_denial_metadata_hash", "")),
        ),
    ]


def _mediated_write_boundary_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (
            "mediated_write_boundary_scaffold_version",
            str(evidence.get("mediated_write_boundary_scaffold_version", "")),
        ),
        (
            "mediated_write_boundary_scaffold_status",
            str(evidence.get("mediated_write_boundary_scaffold_status", "")),
        ),
        (
            "mediated_write_boundary_enforcement_status",
            str(evidence.get("mediated_write_boundary_enforcement_status", "")),
        ),
        ("write_mediation_enabled", str(evidence.get("write_mediation_enabled", "")).lower()),
        ("write_mediation_enforced", str(evidence.get("write_mediation_enforced", "")).lower()),
        ("write_classes_declared_count", str(_list_count(evidence.get("write_classes_declared")))),
        ("write_classes_granted_count", str(_list_count(evidence.get("write_classes_granted")))),
        ("write_classes_denied_count", str(_list_count(evidence.get("write_classes_denied")))),
        ("write_mediation_decision_source", str(evidence.get("write_mediation_decision_source", ""))),
        ("write_mediation_evidence_status", str(evidence.get("write_mediation_evidence_status", ""))),
        (
            "executor_direct_aeg_write_allowed",
            str(evidence.get("executor_direct_aeg_write_allowed", "")).lower(),
        ),
        (
            "executor_direct_outside_repo_write_allowed",
            str(evidence.get("executor_direct_outside_repo_write_allowed", "")).lower(),
        ),
        (
            "executor_direct_delete_allowed",
            str(evidence.get("executor_direct_delete_allowed", "")).lower(),
        ),
        (
            "executor_direct_chmod_allowed",
            str(evidence.get("executor_direct_chmod_allowed", "")).lower(),
        ),
        (
            "executor_direct_git_ref_write_allowed",
            str(evidence.get("executor_direct_git_ref_write_allowed", "")).lower(),
        ),
        (
            "executor_direct_remote_write_allowed",
            str(evidence.get("executor_direct_remote_write_allowed", "")).lower(),
        ),
        ("write_mediation_decision_hash", _short_hash(evidence.get("write_mediation_decision_hash", ""))),
        (
            "mediated_write_boundary_metadata_hash",
            _short_hash(evidence.get("mediated_write_boundary_metadata_hash", "")),
        ),
    ]


def _pre_live_executor_gate_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("pre_live_executor_gate_version", str(evidence.get("pre_live_executor_gate_version", ""))),
        ("pre_live_executor_gate_mode", str(evidence.get("pre_live_executor_gate_mode", ""))),
        ("pre_live_executor_gate_status", str(evidence.get("pre_live_executor_gate_status", ""))),
        (
            "live_executor_authority_requested",
            str(evidence.get("live_executor_authority_requested", "")).lower(),
        ),
        (
            "live_executor_authority_granted",
            str(evidence.get("live_executor_authority_granted", "")).lower(),
        ),
        ("live_executor_authority_hold_reason", str(evidence.get("live_executor_authority_hold_reason", ""))),
        (
            "requires_tamper_evident_ledger",
            str(evidence.get("requires_tamper_evident_ledger", "")).lower(),
        ),
        (
            "tamper_evident_ledger_present",
            str(evidence.get("tamper_evident_ledger_present", "")).lower(),
        ),
        (
            "requires_aeg_state_write_denial",
            str(evidence.get("requires_aeg_state_write_denial", "")).lower(),
        ),
        (
            "aeg_state_write_denial_present",
            str(evidence.get("aeg_state_write_denial_present", "")).lower(),
        ),
        (
            "requires_external_enforcement",
            str(evidence.get("requires_external_enforcement", "")).lower(),
        ),
        ("external_enforcement_present", str(evidence.get("external_enforcement_present", "")).lower()),
        (
            "evidence_store_executor_isolated_required",
            str(evidence.get("evidence_store_executor_isolated_required", "")).lower(),
        ),
        (
            "evidence_store_executor_isolated_present",
            str(evidence.get("evidence_store_executor_isolated_present", "")).lower(),
        ),
        ("pre_live_executor_gate_result", str(evidence.get("pre_live_executor_gate_result", ""))),
        ("pre_live_executor_gate_reason", str(evidence.get("pre_live_executor_gate_reason", ""))),
        (
            "pre_live_executor_gate_metadata_hash",
            _short_hash(evidence.get("pre_live_executor_gate_metadata_hash", "")),
        ),
    ]


def _ledger_integrity_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("ledger_integrity_version", str(evidence.get("ledger_integrity_version", ""))),
        ("ledger_integrity_mode", str(evidence.get("ledger_integrity_mode", ""))),
        ("ledger_integrity_status", str(evidence.get("ledger_integrity_status", ""))),
        ("ledger_tamper_evident_enabled", str(evidence.get("ledger_tamper_evident_enabled", "")).lower()),
        ("ledger_tamper_proof_claimed", str(evidence.get("ledger_tamper_proof_claimed", "")).lower()),
        ("ledger_sequence_number", str(evidence.get("ledger_sequence_number", ""))),
        ("previous_ledger_hash", str(evidence.get("previous_ledger_hash", ""))),
        ("current_evidence_hash", _short_hash(evidence.get("current_evidence_hash", ""))),
        ("current_manifest_hash", _short_hash(evidence.get("current_manifest_hash", ""))),
        ("current_ledger_entry_hash", _short_hash(evidence.get("current_ledger_entry_hash", ""))),
        ("ledger_chain_hash", _short_hash(evidence.get("ledger_chain_hash", ""))),
        ("ledger_integrity_metadata_hash", _short_hash(evidence.get("ledger_integrity_metadata_hash", ""))),
        ("ledger_integrity_check_status", str(evidence.get("ledger_integrity_check_status", ""))),
        ("ledger_integrity_check_reason", str(evidence.get("ledger_integrity_check_reason", ""))),
    ]


def _provider_adapter_rows(evidence: dict[str, Any]) -> list[tuple[str, str]]:
    if evidence.get("citizen_one_requested") is not True:
        return []
    return [
        ("provider_runtime_state", str(evidence.get("provider_runtime_state", ""))),
        ("provider_runtime_status", str(evidence.get("provider_runtime_status", ""))),
        ("provider_runtime_hold_reason", str(evidence.get("provider_runtime_hold_reason", ""))),
        ("provider_runtime_error_class", str(evidence.get("provider_runtime_error_class", ""))),
        ("provider_runtime_error_safe_summary", str(evidence.get("provider_runtime_error_safe_summary", ""))),
        ("provider_selection_requested", str(evidence.get("provider_selection_requested", "")).lower()),
        ("provider_selected", str(evidence.get("provider_selected", "")).lower()),
        ("provider_selection_source", str(evidence.get("provider_selection_source", ""))),
        ("provider_selection_status", str(evidence.get("provider_selection_status", ""))),
        ("provider_secret_required", str(evidence.get("provider_secret_required", "")).lower()),
        ("provider_secret_value_recorded", str(evidence.get("provider_secret_value_recorded", "")).lower()),
        ("provider_secret_redaction_status", str(evidence.get("provider_secret_redaction_status", ""))),
        ("provider_env_loading_requested", str(evidence.get("provider_env_loading_requested", "")).lower()),
        ("provider_env_loading_status", str(evidence.get("provider_env_loading_status", ""))),
        ("provider_network_opt_in_requested", str(evidence.get("provider_network_opt_in_requested", "")).lower()),
        ("provider_network_opt_in_allowed", str(evidence.get("provider_network_opt_in_allowed", "")).lower()),
        ("provider_network_status", str(evidence.get("provider_network_status", ""))),
        ("provider_network_block_reason", str(evidence.get("provider_network_block_reason", ""))),
        ("provider_request_requested", str(evidence.get("provider_request_requested", "")).lower()),
        ("provider_request_status", str(evidence.get("provider_request_status", ""))),
        ("provider_request_metadata_hash", _short_hash(evidence.get("provider_request_metadata_hash", ""))),
        ("provider_request_raw_stored", str(evidence.get("provider_request_raw_stored", "")).lower()),
        ("provider_response_metadata_hash", _short_hash(evidence.get("provider_response_metadata_hash", ""))),
        ("provider_response_raw_stored", str(evidence.get("provider_response_raw_stored", "")).lower()),
        ("provider_error_class", str(evidence.get("provider_error_class", ""))),
        ("provider_error_safe_summary", str(evidence.get("provider_error_safe_summary", ""))),
        ("prompt_build_requested", str(evidence.get("prompt_build_requested", "")).lower()),
        ("prompt_build_status", str(evidence.get("prompt_build_status", ""))),
        ("prompt_source", str(evidence.get("prompt_source", ""))),
        ("prompt_redaction_status", str(evidence.get("prompt_redaction_status", ""))),
        ("prompt_hash_candidate", str(evidence.get("prompt_hash_candidate", ""))),
        ("prompt_storage_policy", str(evidence.get("prompt_storage_policy", ""))),
        ("prompt_secret_detected", str(evidence.get("prompt_secret_detected", "")).lower()),
        ("prompt_raw_stored", str(evidence.get("prompt_raw_stored", "")).lower()),
        ("response_present", str(evidence.get("response_present", "")).lower()),
        ("response_status", str(evidence.get("response_status", ""))),
        ("response_source", str(evidence.get("response_source", ""))),
        ("response_reported_only", str(evidence.get("response_reported_only", "")).lower()),
        ("response_trust_boundary", str(evidence.get("response_trust_boundary", ""))),
        ("response_redaction_status", str(evidence.get("response_redaction_status", ""))),
        ("response_hash_candidate", str(evidence.get("response_hash_candidate", ""))),
        ("response_raw_stored", str(evidence.get("response_raw_stored", "")).lower()),
        ("response_error_class", str(evidence.get("response_error_class", ""))),
        ("response_error_safe_summary", str(evidence.get("response_error_safe_summary", ""))),
        ("provider_request_id", str(evidence.get("provider_request_id", ""))),
        ("provider_mode", str(evidence.get("provider_mode", ""))),
        ("provider_name", str(evidence.get("provider_name", ""))),
        ("provider_model", str(evidence.get("provider_model", ""))),
        ("provider_prompt_source", str(evidence.get("provider_prompt_source", ""))),
        ("provider_prompt_hash_candidate", str(evidence.get("provider_prompt_hash_candidate", ""))),
        ("provider_request_redaction_status", str(evidence.get("provider_request_redaction_status", ""))),
        ("provider_network_opt_in", str(evidence.get("provider_network_opt_in", "")).lower()),
        ("provider_secret_source", str(evidence.get("provider_secret_source", ""))),
        ("provider_response_present", str(evidence.get("provider_response_present", "")).lower()),
        ("provider_response_status", str(evidence.get("provider_response_status", ""))),
        ("provider_response_source", str(evidence.get("provider_response_source", ""))),
        ("provider_response_reported_only", str(evidence.get("provider_response_reported_only", "")).lower()),
        ("provider_response_trust_boundary", str(evidence.get("provider_response_trust_boundary", ""))),
        ("provider_response_hash_candidate", str(evidence.get("provider_response_hash_candidate", ""))),
        ("provider_response_redaction_status", str(evidence.get("provider_response_redaction_status", ""))),
        ("provider_response_error_class", str(evidence.get("provider_response_error_class", ""))),
        ("provider_response_error_safe_summary", str(evidence.get("provider_response_error_safe_summary", ""))),
    ]


def _short_hash(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value[:12]


def _list_count(value: object) -> int | str:
    if not isinstance(value, list):
        return ""
    return len(value)


def _print_card(title: str, status: str, rows: list[tuple[str, str]], reasons: list[str] | None = None) -> None:
    print(title)
    print(f"status: {status}")
    for key, value in rows:
        print(f"{key}: {value}")
    if reasons:
        print("reasons:")
        for reason in reasons:
            print(f"- {reason}")


def _print_doctor_card(status: str, checks: list[DoctorCheck]) -> None:
    print("Aegis doctor")
    print(f"status: {status}")
    print(f"overall_status: {status}")
    print(f"repo_root: {_doctor_detail(checks, 'repo_root')}")
    print(f"state_path: {_doctor_detail(checks, 'state_path')}")
    print(f"safe_default: {SAFE_DEFAULT}")
    print("checks:")
    for check in checks:
        print(f"- [{check.status}] {check.name}")
        print(f"  message: {check.message}")
        if check.fix_hint:
            print(f"  fix_hint: {check.fix_hint}")
        if check.next_step:
            print(f"  next_step: {check.next_step}")
        for key, value in check.details:
            print(f"  {key}: {value}")


def _doctor_detail(checks: list[DoctorCheck], key: str) -> str:
    for check in checks:
        for detail_key, detail_value in check.details:
            if detail_key == key:
                return detail_value
    return "NOT_AVAILABLE"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
