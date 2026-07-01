"""No-op executor for Day-1 contract-first runtime."""

from __future__ import annotations

from typing import Any

from src.classify import Classification
from src.contracts import (
    CLEAN_CORE,
    COMPLETION_CONTRACT_V0,
    CONTRACT_FIRST_NOOP,
    NEEDS_USER_GATE,
    NOT_CHECKED,
)
from src.law import LawResult


def execute_contract(task_text: str, classification: Classification, law_result: LawResult) -> dict[str, Any]:
    if law_result.status == NEEDS_USER_GATE:
        declared_result = "Stopped before execution; explicit user gate is required."
        completion_claim = "BLOCKED_BY_GATE"
    elif law_result.status == CLEAN_CORE:
        declared_result = "No-op contract completed; no repository files were changed."
        completion_claim = "CLEAN_CORE_NO_MUTATION"
    elif law_result.status == NOT_CHECKED:
        declared_result = "No-op contract recorded evidence, but completion is not checked."
        completion_claim = "NOT_CHECKED"
    else:
        declared_result = "No-op contract held current state."
        completion_claim = "HOLD_CURRENT_STATE"

    completion_contract = {
        "version": COMPLETION_CONTRACT_V0,
        "task_text_present": bool(task_text.strip()),
        "executor_mode": CONTRACT_FIRST_NOOP,
        "declared_result": declared_result,
        "file_mutation": False,
        "provider_calls": False,
        "network_calls": False,
        "actions": [],
        "action_count": 0,
        "expected_action_count": 0,
        "completion_reported": True,
        "completion_satisfied": False,
    }

    return {
        "executor": CONTRACT_FIRST_NOOP,
        "task_text": task_text,
        "model_backed": False,
        "provider_calls": False,
        "network_calls": False,
        "file_mutation": False,
        "actions": [],
        "action_count": 0,
        "expected_action_count": 0,
        "declared_status": law_result.status,
        "declared_result": declared_result,
        "completion_claim": completion_claim,
        "completion_contract": completion_contract,
        "risk_level": classification.risk_level,
    }
