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
    run_parser.add_argument("task", help="task text to classify and gate")
    subparsers.add_parser("verify", help="verify latest evidence with deterministic replay")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(Path.cwd())
    if args.command == "doctor":
        return _cmd_doctor(Path.cwd())
    if args.command == "run":
        return _cmd_run(Path.cwd(), args.task, citizen_one_requested=args.citizen_one)
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


def _cmd_run(cwd: Path, task_text: str, citizen_one_requested: bool = False) -> int:
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


def _short_hash(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value[:12]


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
