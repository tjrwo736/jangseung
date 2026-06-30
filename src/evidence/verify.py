"""Deterministic verification replay for latest evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.classify import classify_task
from src.contracts import CLEAN_CORE, HIGH, LOW, NEEDS_USER_GATE, NOT_CHECKED_IMPACT_RISKS
from src.evidence.schema import validate_evidence_packet
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

    if evidence and git.object_exists(repo, evidence.get("head_sha", ""), "commit"):
        checks.append("head_sha is readable")
    else:
        errors.append("head_sha is not readable")

    if evidence and git.object_exists(repo, evidence.get("tree_sha", ""), "tree"):
        checks.append("tree_sha is readable")
    else:
        errors.append("tree_sha is not readable")

    if evidence:
        status = evidence.get("status")
        saved_changed_files = evidence.get("changed_files", [])
        if not isinstance(saved_changed_files, list):
            saved_changed_files = []
        replay = classify_task(
            evidence.get("task_text", ""),
            changed_files=list(saved_changed_files),
            changed_files_source=evidence.get("changed_files_source"),
            no_mutation=False,
        )
        replay_law = apply_law(replay)
        if evidence.get("intent_risk") == replay.intent_risk:
            checks.append(f"intent_risk replay matched: {replay.intent_risk}")
        else:
            errors.append(f"intent_risk mismatch: evidence={evidence.get('intent_risk')} replay={replay.intent_risk}")

        if evidence.get("risk_level") == replay.risk_level:
            checks.append(f"risk_level replay matched: {replay.risk_level}")
        else:
            errors.append(f"risk_level mismatch: evidence={evidence.get('risk_level')} replay={replay.risk_level}")

        if evidence.get("impact_risk") == replay.impact_risk:
            checks.append(f"impact_risk replay matched: {replay.impact_risk}")
        else:
            errors.append(f"impact_risk mismatch: evidence={evidence.get('impact_risk')} replay={replay.impact_risk}")

        if evidence.get("impact_reasons", []) == replay.impact_reasons:
            checks.append("impact_reasons replay matched")
        else:
            errors.append(f"impact_reasons mismatch: evidence={evidence.get('impact_reasons')} replay={replay.impact_reasons}")

        if evidence.get("changed_files_source") == replay.changed_files_source:
            checks.append(f"changed_files_source replay matched: {replay.changed_files_source}")
        else:
            errors.append(
                "changed_files_source mismatch: "
                f"evidence={evidence.get('changed_files_source')} replay={replay.changed_files_source}"
            )

        if evidence.get("protected_paths_touched", []) == replay.protected_paths_touched:
            checks.append("protected_paths_touched replay matched")
        else:
            errors.append(
                "protected_paths_touched mismatch: "
                f"evidence={evidence.get('protected_paths_touched')} replay={replay.protected_paths_touched}"
            )

        if evidence.get("risk_escalation_applied") == replay.risk_escalation_applied:
            checks.append(f"risk_escalation_applied replay matched: {replay.risk_escalation_applied}")
        else:
            errors.append(
                "risk_escalation_applied mismatch: "
                f"evidence={evidence.get('risk_escalation_applied')} replay={replay.risk_escalation_applied}"
            )

        if evidence.get("final_risk_rule") == replay.final_risk_rule:
            checks.append(f"final_risk_rule replay matched: {replay.final_risk_rule}")
        else:
            errors.append(f"final_risk_rule mismatch: evidence={evidence.get('final_risk_rule')} replay={replay.final_risk_rule}")

        if replay.protected_paths_touched and evidence.get("risk_level") == LOW:
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
            errors.append(f"law status mismatch: evidence={status} replay={replay_law.status}")
        else:
            checks.append(f"law status replay matched: {replay_law.status}")

        root = state_root(repo).resolve()
        run_id = evidence.get("run_id", "")
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


def _is_under(root: Path, path: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents
