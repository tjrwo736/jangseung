"""Command-line interface for the Day-1 Aegis runtime spine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.agents import execute_contract
from src.classify import classify_task
from src.contracts import NOT_CHECKED_SOURCE, SAFE_DEFAULT
from src.evidence import build_evidence_packet, verify_latest
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
    run_parser.add_argument("task", help="task text to classify and gate")
    subparsers.add_parser("verify", help="verify latest evidence with deterministic replay")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(Path.cwd())
    if args.command == "doctor":
        return _cmd_doctor(Path.cwd())
    if args.command == "run":
        return _cmd_run(Path.cwd(), args.task)
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


def _cmd_run(cwd: Path, task_text: str) -> int:
    try:
        repo = git.repo_root(cwd)
        require_initialized(repo)
        changed_files, changed_files_source = _runtime_changed_files(repo)
        classification = classify_task(
            task_text,
            changed_files=changed_files,
            changed_files_source=changed_files_source,
            no_mutation=False,
        )
        law_result = apply_law(classification)
        executor_result = execute_contract(task_text, classification, law_result)
        evidence = build_evidence_packet(repo, task_text, classification, law_result, executor_result)
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
        ("risk_level", evidence["risk_level"]),
        ("status", evidence["status"]),
        ("binding_status", evidence.get("binding_status", "")),
        ("binding_version", evidence.get("binding_version", "")),
        ("manifest_hash", _short_hash(evidence.get("bound_manifest_hash", ""))),
        ("binding_reason_count", str(len(evidence.get("binding_reasons", [])))),
        ("evidence", paths["evidence_path"]),
    ]
    rows.extend(_user_gate_rows(evidence.get("user_gate_reason_card")))
    _print_card("Aegis run", evidence["status"], rows, evidence["classification_reasons"] + evidence["status_reasons"])
    return 0


def _runtime_changed_files(repo: Path) -> tuple[list[str], str]:
    try:
        return git.changed_files_with_source(repo)
    except git.GitError:
        return [], NOT_CHECKED_SOURCE


def _cmd_verify(cwd: Path) -> int:
    result = verify_latest(cwd)
    status = "PASS" if result.ok else "FAIL"
    rows = []
    if result.evidence:
        rows.extend(
            [
                ("run_id", result.evidence.get("run_id", "")),
                ("intent_risk", result.evidence.get("intent_risk", "")),
                ("impact_risk", result.evidence.get("impact_risk", "")),
                ("changed_files_source", result.evidence.get("changed_files_source", "")),
                ("risk_level", result.evidence.get("risk_level", "")),
                ("status", result.evidence.get("status", "")),
                ("binding_status", result.evidence.get("binding_status", "")),
                ("binding_version", result.evidence.get("binding_version", "")),
                ("manifest_hash", _short_hash(result.evidence.get("bound_manifest_hash", ""))),
                ("binding_reason_count", str(len(result.evidence.get("binding_reasons", [])))),
            ]
        )
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
