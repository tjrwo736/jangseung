"""Phase 11-B-3-2 deterministic restricted propose-only stub executor.

The stub accepts only named fixture input and returns structured action
candidate data. It does not build ActionDecisionPacket instances, call tools,
run commands, call providers, mutate files, access the store module, or grant
authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.structured_actions import (
    NOOP,
    PROPOSE_PATCH,
    REQUEST_EXPLANATION,
    REQUEST_RISK_CLASSIFICATION,
)

RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR_VERSION = (
    "phase11b_3_2_restricted_propose_only_stub_executor_v0"
)

FIXTURE_INPUT_FIELD = "fixture_id"
NOOP_FIXTURE_ID = "restricted_stub_noop_v0"
REQUEST_EXPLANATION_FIXTURE_ID = "restricted_stub_request_explanation_v0"
REQUEST_RISK_CLASSIFICATION_FIXTURE_ID = (
    "restricted_stub_request_risk_classification_v0"
)
PROPOSE_PATCH_FIXTURE_ID = "restricted_stub_propose_patch_v0"
README_TYPO_PROPOSE_PATCH_FIXTURE_ID = (
    "restricted_stub_readme_typo_propose_patch_v0"
)

ALLOWED_STUB_ACTION_CANDIDATES = (
    NOOP,
    REQUEST_EXPLANATION,
    REQUEST_RISK_CLASSIFICATION,
    PROPOSE_PATCH,
)
ALLOWED_STUB_FIXTURE_IDS = (
    NOOP_FIXTURE_ID,
    REQUEST_EXPLANATION_FIXTURE_ID,
    REQUEST_RISK_CLASSIFICATION_FIXTURE_ID,
    PROPOSE_PATCH_FIXTURE_ID,
    README_TYPO_PROPOSE_PATCH_FIXTURE_ID,
)

_FIXTURE_OUTPUTS: dict[str, dict[str, Any]] = {
    NOOP_FIXTURE_ID: {
        "action_type": NOOP,
        "action_id": "restricted-stub-noop-001",
        "declared_intent": "Deterministic restricted stub no-op candidate.",
        "declared_risk": "LOW",
        "capability_requirements": ["noop"],
        "target_scope": {"repo_relative": True, "paths": []},
        "payload": {},
    },
    REQUEST_EXPLANATION_FIXTURE_ID: {
        "action_type": REQUEST_EXPLANATION,
        "action_id": "restricted-stub-request-explanation-001",
        "declared_intent": "Request deterministic explanation data.",
        "declared_risk": "LOW",
        "capability_requirements": ["explanation"],
        "target_scope": {"repo_relative": True, "paths": []},
        "payload": {
            "question": "Explain the proposal boundary without executing actions.",
        },
    },
    REQUEST_RISK_CLASSIFICATION_FIXTURE_ID: {
        "action_type": REQUEST_RISK_CLASSIFICATION,
        "action_id": "restricted-stub-request-risk-classification-001",
        "declared_intent": "Request deterministic risk classification data.",
        "declared_risk": "LOW",
        "capability_requirements": ["risk_classification"],
        "target_scope": {"repo_relative": True, "paths": []},
        "payload": {
            "subject": "Restricted propose-only proposal metadata.",
            "classification_request": "Classify risk without granting authority.",
        },
    },
    PROPOSE_PATCH_FIXTURE_ID: {
        "action_type": PROPOSE_PATCH,
        "action_id": "restricted-stub-propose-patch-001",
        "declared_intent": "Propose an inert documentation patch as data.",
        "declared_risk": "LOW",
        "capability_requirements": ["propose_patch"],
        "target_scope": {
            "repo_relative": True,
            "paths": ["docs/example_proposal.md"],
        },
        "payload": {
            "target_files": ["docs/example_proposal.md"],
            "patch_summary": "Add a review-only proposal note.",
            "patch_plan": [
                "Review the proposed documentation-only change.",
                "Apply only through a future separately authorized path.",
            ],
            "patch_diff": (
                "diff --git a/docs/example_proposal.md "
                "b/docs/example_proposal.md\n"
                "--- /dev/null\n"
                "+++ b/docs/example_proposal.md\n"
                "@@\n"
                "+Review-only proposal text.\n"
            ),
        },
    },
    README_TYPO_PROPOSE_PATCH_FIXTURE_ID: {
        "action_type": PROPOSE_PATCH,
        "action_id": "restricted-stub-readme-typo-propose-patch-001",
        "declared_intent": "Propose an inert README typo fix as data.",
        "declared_risk": "LOW",
        "capability_requirements": ["propose_patch"],
        "target_scope": {
            "repo_relative": True,
            "paths": ["README.md"],
        },
        "payload": {
            "target_files": ["README.md"],
            "patch_summary": "Fix a README typo as review-only proposal data.",
            "patch_plan": [
                "Review the README typo proposal.",
                "Apply only through a future separately authorized path.",
            ],
            "patch_diff": (
                "diff --git a/README.md b/README.md\n"
                "--- a/README.md\n"
                "+++ b/README.md\n"
                "@@\n"
                "-Aegis demo typoo line.\n"
                "+Aegis demo typo line.\n"
            ),
        },
    },
}


def build_restricted_stub_fixture_input(fixture_id: str) -> dict[str, str]:
    """Return deterministic fixture input for the restricted stub."""

    if fixture_id not in _FIXTURE_OUTPUTS:
        raise ValueError(f"unknown restricted stub fixture id: {fixture_id}")
    return {FIXTURE_INPUT_FIELD: fixture_id}


def produce_restricted_propose_only_stub_output(
    fixture_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Return raw structured action candidate data for one named fixture."""

    fixture_id = _fixture_id_from_input(fixture_input)
    return _clone_json_data(_FIXTURE_OUTPUTS[fixture_id])


def build_restricted_propose_only_stub_executor_evidence() -> dict[str, Any]:
    """Return deterministic evidence for the restricted stub contract."""

    return {
        "restricted_propose_only_stub_executor_version": (
            RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR_VERSION
        ),
        "deterministic_fixture_input_only": True,
        "deterministic_structured_output_only": True,
        "output_is_raw_structured_action_candidate_data": True,
        "output_is_action_decision_packet": False,
        "completed_action_decision_packet_submission_allowed": False,
        "tool_calls_allowed": False,
        "code_execution_allowed": False,
        "provider_model_network_allowed": False,
        "shell_process_allowed": False,
        "filesystem_mutation_allowed": False,
        "store_direct_access_allowed": False,
        "dynamic_import_allowed": False,
        "eval_exec_allowed": False,
        "runtime_introspection_allowed": False,
        "executor_authority_claim_allowed": False,
        "allowed_action_candidates": ALLOWED_STUB_ACTION_CANDIDATES,
        "allowed_fixture_ids": ALLOWED_STUB_FIXTURE_IDS,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def _fixture_id_from_input(fixture_input: Mapping[str, Any]) -> str:
    if not isinstance(fixture_input, Mapping):
        raise TypeError("restricted stub fixture input must be a mapping")
    if tuple(fixture_input.keys()) != (FIXTURE_INPUT_FIELD,):
        raise ValueError("restricted stub accepts only deterministic fixture_id input")

    fixture_id = fixture_input.get(FIXTURE_INPUT_FIELD)
    if fixture_id not in _FIXTURE_OUTPUTS:
        raise ValueError(f"unknown restricted stub fixture id: {fixture_id}")
    return str(fixture_id)


def _clone_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_data(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_clone_json_data(nested) for nested in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported fixture data type: {type(value).__name__}")


__all__ = [
    "ALLOWED_STUB_ACTION_CANDIDATES",
    "ALLOWED_STUB_FIXTURE_IDS",
    "FIXTURE_INPUT_FIELD",
    "NOOP_FIXTURE_ID",
    "PROPOSE_PATCH_FIXTURE_ID",
    "README_TYPO_PROPOSE_PATCH_FIXTURE_ID",
    "REQUEST_EXPLANATION_FIXTURE_ID",
    "REQUEST_RISK_CLASSIFICATION_FIXTURE_ID",
    "RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR_VERSION",
    "build_restricted_propose_only_stub_executor_evidence",
    "build_restricted_stub_fixture_input",
    "produce_restricted_propose_only_stub_output",
]
