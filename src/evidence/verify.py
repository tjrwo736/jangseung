"""Deterministic verification replay for latest evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.classify import classify_task
from src.contracts import (
    BOUND,
    CLEAN_CORE,
    HIGH,
    LOW,
    NEEDS_USER_GATE,
    NOT_CHECKED_IMPACT_RISKS,
    RUN_MANIFEST_V1,
)
from src.evidence.binding import (
    changed_files_hash,
    expected_artifact_path,
    manifest_hash,
    repo_relative_path,
    sha256_text,
)
from src.evidence.schema import (
    validate_completion_contract_v0,
    validate_evidence_binding_v0,
    validate_evidence_binding_v1,
    validate_evidence_packet,
    validate_user_gate_reason_card_v1,
)
from src.law import apply_law
from src.state import git
from src.state.store import load_latest_evidence, state_root


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checks: list[str]
    errors: list[str]
    evidence: dict[str, Any] | None


def verify_latest(cwd: str | Path) -> VerifyResult:
    checks: list[str] = []
    errors: list[str] = []

    try:
        repo = git.repo_root(cwd)
    except git.GitError as exc:
        return VerifyResult(False, checks, [f"git repo root unavailable: {exc}"], None)

    try:
        evidence, evidence_path, ledger_entry = load_latest_evidence(repo)
    except Exception as exc:  # JSON parse errors should be human-readable.
        return VerifyResult(False, checks, [f"latest evidence could not be loaded: {exc}"], None)

    if not ledger_entry:
        return VerifyResult(False, checks, ["latest run/evidence not found"], None)
    checks.append("latest ledger entry found")

    if evidence_path is None or evidence is None:
        return VerifyResult(False, checks, [f"latest evidence file not found for run: {ledger_entry.get('run_id')}"], None)
    checks.append(f"latest evidence loaded: {evidence_path}")

    schema_errors = validate_evidence_packet(evidence)
    if schema_errors:
        errors.extend(schema_errors)
    else:
        checks.append("evidence schema valid")

    binding_errors = validate_evidence_binding_v0(evidence)
    if binding_errors:
        errors.extend(binding_errors)
    else:
        checks.append("evidence binding v0 valid")

    binding_v1_errors = validate_evidence_binding_v1(evidence)
    if binding_v1_errors:
        errors.extend(binding_v1_errors)
    else:
        checks.append("evidence binding v1 valid")

    manifest, manifest_checks, manifest_errors = _verify_manifest_binding(repo, evidence, evidence_path, ledger_entry)
    checks.extend(manifest_checks)
    errors.extend(manifest_errors)

    completion_errors = validate_completion_contract_v0(evidence)
    if completion_errors:
        errors.extend(completion_errors)
    else:
        checks.append("completion contract v0 valid")

    gate_card_errors = validate_user_gate_reason_card_v1(evidence)
    if gate_card_errors:
        errors.extend(gate_card_errors)
    elif evidence.get("risk_level") == HIGH:
        checks.append("HIGH user gate reason card valid")

    evidence_repo_root = evidence.get("repo_root")
    if isinstance(evidence_repo_root, str) and evidence_repo_root.strip():
        if Path(evidence_repo_root).resolve() == repo:
            checks.append("repo_root is bound to current repository")
        else:
            errors.append(f"INVALID_EVIDENCE: repo_root mismatch: evidence={evidence_repo_root} replay={repo}")

    bound_head_sha = evidence.get("bound_head_sha") or evidence.get("head_sha", "")
    if evidence and git.object_exists(repo, str(bound_head_sha), "commit"):
        checks.append("bound_head_sha is readable")
    else:
        errors.append("NOT_CHECKED: bound_head_sha is not readable in current repository")

    bound_tree_sha = evidence.get("bound_tree_sha") or evidence.get("tree_sha", "")
    if evidence and git.object_exists(repo, str(bound_tree_sha), "tree"):
        checks.append("bound_tree_sha is readable")
    else:
        errors.append("NOT_CHECKED: bound_tree_sha is not readable in current repository")

    if evidence:
        status = evidence.get("status")
        replay_changed_files = evidence.get("changed_files", [])
        replay_changed_files_source = evidence.get("changed_files_source")
        if manifest:
            replay_changed_files = manifest.get("changed_files", [])
            replay_changed_files_source = manifest.get("changed_files_source")
        saved_changed_files = _string_list(replay_changed_files)
        task_text = evidence.get("task_text", "")
        if not isinstance(task_text, str):
            task_text = ""
        replay = classify_task(
            task_text,
            changed_files=list(saved_changed_files),
            changed_files_source=replay_changed_files_source,
            no_mutation=False,
        )
        replay_law = apply_law(replay)
        if evidence.get("intent_risk") == replay.intent_risk:
            checks.append(f"intent_risk replay matched: {replay.intent_risk}")
        else:
            errors.append(f"INVALID_EVIDENCE: intent_risk mismatch: evidence={evidence.get('intent_risk')} replay={replay.intent_risk}")

        if evidence.get("risk_level") == replay.risk_level:
            checks.append(f"risk_level replay matched: {replay.risk_level}")
        else:
            errors.append(f"INVALID_EVIDENCE: risk_level mismatch: evidence={evidence.get('risk_level')} replay={replay.risk_level}")

        if evidence.get("impact_risk") == replay.impact_risk:
            checks.append(f"impact_risk replay matched: {replay.impact_risk}")
        else:
            errors.append(f"INVALID_EVIDENCE: impact_risk mismatch: evidence={evidence.get('impact_risk')} replay={replay.impact_risk}")

        if evidence.get("impact_reasons", []) == replay.impact_reasons:
            checks.append("impact_reasons replay matched")
        else:
            errors.append(f"INVALID_EVIDENCE: impact_reasons mismatch: evidence={evidence.get('impact_reasons')} replay={replay.impact_reasons}")

        if evidence.get("changed_files_source") == replay.changed_files_source:
            checks.append(f"changed_files_source replay matched: {replay.changed_files_source}")
        else:
            errors.append(
                "INVALID_EVIDENCE: changed_files_source mismatch: "
                f"evidence={evidence.get('changed_files_source')} replay={replay.changed_files_source}"
            )

        if evidence.get("protected_paths_touched", []) == replay.protected_paths_touched:
            checks.append("protected_paths_touched replay matched")
        else:
            errors.append(
                "INVALID_EVIDENCE: protected_paths_touched mismatch: "
                f"evidence={evidence.get('protected_paths_touched')} replay={replay.protected_paths_touched}"
            )

        if evidence.get("risk_escalation_applied") == replay.risk_escalation_applied:
            checks.append(f"risk_escalation_applied replay matched: {replay.risk_escalation_applied}")
        else:
            errors.append(
                "INVALID_EVIDENCE: risk_escalation_applied mismatch: "
                f"evidence={evidence.get('risk_escalation_applied')} replay={replay.risk_escalation_applied}"
            )

        if evidence.get("final_risk_rule") == replay.final_risk_rule:
            checks.append(f"final_risk_rule replay matched: {replay.final_risk_rule}")
        else:
            errors.append(f"INVALID_EVIDENCE: final_risk_rule mismatch: evidence={evidence.get('final_risk_rule')} replay={replay.final_risk_rule}")

        saved_protected_paths = evidence.get("protected_paths_touched", [])
        if not isinstance(saved_protected_paths, list):
            saved_protected_paths = []
        if (replay.protected_paths_touched or saved_protected_paths) and evidence.get("risk_level") == LOW:
            errors.append("INVALID_EVIDENCE: protected path touched but saved risk_level is LOW")

        if replay.impact_risk in NOT_CHECKED_IMPACT_RISKS and status == CLEAN_CORE:
            errors.append("INVALID_EVIDENCE: NOT_CHECKED impact cannot be CLEAN_CORE")

        if replay.risk_level == HIGH and status != NEEDS_USER_GATE:
            errors.append("HIGH risk evidence must remain NEEDS_USER_GATE")
        elif replay.risk_level == HIGH:
            checks.append("HIGH risk remained NEEDS_USER_GATE")

        if replay.risk_level == LOW and status == NEEDS_USER_GATE:
            errors.append("LOW risk was over-gated as NEEDS_USER_GATE")
        elif replay.risk_level == LOW and status == CLEAN_CORE:
            checks.append("LOW risk remained CLEAN_CORE")

        if status == "PASS":
            errors.append("NOT_CHECKED/PASS invariant violated: PASS status is forbidden")
        else:
            checks.append("NOT_CHECKED was not promoted to PASS")

        if status != replay_law.status:
            errors.append(f"INVALID_EVIDENCE: law status mismatch: evidence={status} replay={replay_law.status}")
        else:
            checks.append(f"law status replay matched: {replay_law.status}")

        root = state_root(repo).resolve()
        run_id = str(evidence.get("run_id", ""))
        run_path = root / "runs" / run_id / "run.json"
        resolved_evidence = evidence_path.resolve()
        if _is_under(root, run_path) and _is_under(root, resolved_evidence):
            checks.append("runtime artifacts are under .aeg/")
        else:
            errors.append("runtime artifact path escaped .aeg/")

        if evidence.get("checks", {}).get("runtime_artifacts_under_state") is True:
            checks.append("evidence declares runtime artifacts under state")
        else:
            errors.append("evidence did not declare runtime artifacts under state")

    return VerifyResult(not errors, checks, errors, evidence)


def _verify_manifest_binding(
    repo: Path,
    evidence: dict[str, Any],
    evidence_path: Path,
    ledger_entry: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    checks: list[str] = []
    errors: list[str] = []

    run_id = evidence.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return None, checks, ["INVALID_EVIDENCE: manifest binding requires evidence run_id"]

    expected_manifest_rel = expected_artifact_path(run_id, "manifest.json")
    expected_evidence_rel = expected_artifact_path(run_id, "evidence.json")
    expected_run_rel = expected_artifact_path(run_id, "run.json")

    bound_manifest_path = evidence.get("bound_manifest_path")
    if not isinstance(bound_manifest_path, str) or not bound_manifest_path.strip():
        return None, checks, ["INVALID_EVIDENCE: missing bound_manifest_path"]
    if Path(bound_manifest_path).is_absolute():
        errors.append("INVALID_EVIDENCE: bound_manifest_path must be repository-relative")
        return None, checks, errors
    if bound_manifest_path != expected_manifest_rel:
        errors.append(
            "INVALID_EVIDENCE: bound_manifest_path mismatch: "
            f"evidence={bound_manifest_path} expected={expected_manifest_rel}"
        )

    manifest_path = (repo / bound_manifest_path).resolve()
    root = state_root(repo).resolve()
    if not _is_under(root, manifest_path):
        errors.append(f"INVALID_EVIDENCE: manifest path escaped .aeg/: {bound_manifest_path}")
        return None, checks, errors
    if not manifest_path.exists():
        errors.append(f"INVALID_EVIDENCE: manifest missing: {bound_manifest_path}")
        return None, checks, errors

    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"INVALID_EVIDENCE: manifest could not be parsed: {exc}")
        return None, checks, errors
    if not isinstance(loaded, dict):
        errors.append("INVALID_EVIDENCE: manifest must be object")
        return None, checks, errors
    manifest = loaded

    actual_manifest_hash = manifest_hash(manifest)
    if evidence.get("bound_manifest_hash") == actual_manifest_hash:
        checks.append(f"manifest hash matched: {actual_manifest_hash[:12]}")
    else:
        errors.append(
            "INVALID_EVIDENCE: manifest hash mismatch: "
            f"evidence={evidence.get('bound_manifest_hash')} actual={actual_manifest_hash}"
        )

    if manifest.get("manifest_version") == RUN_MANIFEST_V1:
        checks.append("manifest version valid")
    else:
        errors.append(f"INVALID_EVIDENCE: manifest_version must be {RUN_MANIFEST_V1}")

    actual_evidence_rel = repo_relative_path(repo, evidence_path)
    if actual_evidence_rel == expected_evidence_rel:
        checks.append("evidence path matches expected run path")
    else:
        errors.append(
            "INVALID_EVIDENCE: loaded evidence path mismatch: "
            f"actual={actual_evidence_rel} expected={expected_evidence_rel}"
        )

    if ledger_entry:
        _check_equal(checks, errors, "ledger run_id", ledger_entry.get("run_id"), run_id)
        if ledger_entry.get("evidence_path") is not None:
            _check_equal(checks, errors, "ledger evidence_path", ledger_entry.get("evidence_path"), expected_evidence_rel)
        if ledger_entry.get("run_path") is not None:
            _check_equal(checks, errors, "ledger run_path", ledger_entry.get("run_path"), expected_run_rel)
        if ledger_entry.get("manifest_path") is not None:
            _check_equal(checks, errors, "ledger manifest_path", ledger_entry.get("manifest_path"), expected_manifest_rel)
        if ledger_entry.get("manifest_hash") is not None:
            _check_equal(checks, errors, "ledger manifest_hash", ledger_entry.get("manifest_hash"), actual_manifest_hash)

    _check_equal(checks, errors, "manifest run_id", manifest.get("run_id"), run_id)
    _check_equal(checks, errors, "manifest repo_root", manifest.get("repo_root"), evidence.get("repo_root"))
    _check_equal(checks, errors, "manifest branch", manifest.get("branch"), evidence.get("branch"))
    _check_equal(checks, errors, "manifest head_sha", manifest.get("head_sha"), evidence.get("head_sha"))
    _check_equal(checks, errors, "manifest tree_sha", manifest.get("tree_sha"), evidence.get("tree_sha"))
    _check_equal(
        checks,
        errors,
        "manifest changed_files_source",
        manifest.get("changed_files_source"),
        evidence.get("changed_files_source"),
    )
    _check_equal(checks, errors, "manifest risk_level", manifest.get("risk_level"), evidence.get("risk_level"))
    _check_equal(checks, errors, "manifest status", manifest.get("status"), evidence.get("status"))
    _check_equal(checks, errors, "manifest safe_default", manifest.get("safe_default"), evidence.get("safe_default"))
    _check_equal(checks, errors, "bound_run_id", evidence.get("bound_run_id"), run_id)
    _check_equal(checks, errors, "bound_repo_root", evidence.get("bound_repo_root"), manifest.get("repo_root"))
    _check_equal(checks, errors, "bound_branch", evidence.get("bound_branch"), manifest.get("branch"))
    _check_equal(checks, errors, "bound_head_sha", evidence.get("bound_head_sha"), manifest.get("head_sha"))
    _check_equal(checks, errors, "bound_tree_sha", evidence.get("bound_tree_sha"), manifest.get("tree_sha"))

    _check_equal(checks, errors, "manifest evidence_path", manifest.get("evidence_path"), expected_evidence_rel)
    _check_equal(checks, errors, "manifest run_path", manifest.get("run_path"), expected_run_rel)

    evidence_changed_files = evidence.get("changed_files")
    manifest_changed_files = manifest.get("changed_files")
    if not _is_string_list(evidence_changed_files):
        errors.append("INVALID_EVIDENCE: evidence changed_files must be list of strings")
        evidence_changed_files = []
    if not _is_string_list(manifest_changed_files):
        errors.append("INVALID_EVIDENCE: manifest changed_files must be list of strings")
        manifest_changed_files = []
    if evidence_changed_files == manifest_changed_files:
        checks.append("manifest changed_files matched evidence")
    else:
        errors.append(
            "INVALID_EVIDENCE: changed_files mismatch: "
            f"evidence={evidence_changed_files} manifest={manifest_changed_files}"
        )

    evidence_changed_files_hash = changed_files_hash(evidence_changed_files)
    manifest_changed_files_hash = changed_files_hash(manifest_changed_files)
    _check_equal(
        checks,
        errors,
        "manifest changed_files_hash",
        manifest.get("changed_files_hash"),
        manifest_changed_files_hash,
    )
    _check_equal(
        checks,
        errors,
        "bound_changed_files_hash",
        evidence.get("bound_changed_files_hash"),
        evidence_changed_files_hash,
    )
    _check_equal(checks, errors, "changed_files hash", evidence_changed_files_hash, manifest_changed_files_hash)

    task_text = evidence.get("task_text")
    if isinstance(task_text, str):
        _check_equal(checks, errors, "manifest task_text_hash", manifest.get("task_text_hash"), sha256_text(task_text))
    else:
        errors.append("INVALID_EVIDENCE: task_text must be string for manifest binding")

    if evidence.get("binding_status") != BOUND:
        errors.append("INVALID_EVIDENCE: binding_status is not BOUND")
    else:
        checks.append("binding_status is BOUND")

    return manifest, checks, errors


def _check_equal(checks: list[str], errors: list[str], label: str, actual: Any, expected: Any) -> None:
    if actual == expected:
        checks.append(f"{label} matched")
    else:
        errors.append(f"INVALID_EVIDENCE: {label} mismatch: actual={actual} expected={expected}")


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _string_list(value: Any) -> list[str]:
    if not _is_string_list(value):
        return []
    return list(value)


def _is_under(root: Path, path: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents
