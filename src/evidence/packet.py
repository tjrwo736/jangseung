"""Build bound evidence packets."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.classify import Classification
from src.contracts import AEG_VERSION, SAFE_DEFAULT, STATE_DIR
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
    run_id: str | None = None,
) -> dict[str, Any]:
    repo = git.repo_root(cwd)
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
        },
        "status": law_result.status,
        "status_reasons": list(law_result.status_reasons),
        "safe_default": SAFE_DEFAULT,
    }
    if law_result.user_gate_reason_card is not None:
        packet["user_gate_reason_card"] = dict(law_result.user_gate_reason_card)
    return packet
