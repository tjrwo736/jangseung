"""Phase 11-B-1f symlink realpath escape fixture summary.

This module evaluates structured action data against repo-root realpath scope
checks. It does not create symlinks, execute actions, mutate files, call
providers, use the network, or grant live executor authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    SCOPE_LIMIT_REJECTED,
    evaluate_action_capabilities,
)
from src.evidence.structured_actions import (
    FORBIDDEN_PAYLOAD_FIELD_REJECTED,
    PROPOSE_PATCH,
    PR_81_DRAFT_RELEASE_NOT_PERFORMED,
    PR_81_MERGE_NOT_PERFORMED,
    PR_81_STATUS_HOLD_OPEN_DRAFT,
    REQUEST_REPO_READ,
    VALID_STRUCTURED_ACTION,
    validate_structured_action,
)

SYMLINK_REALPATH_FIXTURE_SET_VERSION = (
    "phase11b_1f_symlink_realpath_escape_fixture_closure_v0"
)

SYMLINK_SUPPORTED = "SYMLINK_SUPPORTED"
NOT_CHECKED_SYMLINK_UNSUPPORTED = "NOT_CHECKED_SYMLINK_UNSUPPORTED"
NOT_CHECKED_PLATFORM_PERMISSION_LIMIT = "NOT_CHECKED_PLATFORM_PERMISSION_LIMIT"

SYMLINK_REALPATH_FIXTURES_CHECKED = "SYMLINK_REALPATH_FIXTURES_CHECKED"
SYMLINK_REALPATH_FIXTURE_FAILURE = "SYMLINK_REALPATH_FIXTURE_FAILURE"
AEG_SCOPE_ESCAPE_REJECTED = "AEG_SCOPE_ESCAPE_REJECTED"
OUTSIDE_REPO_ESCAPE_REJECTED = "OUTSIDE_REPO_ESCAPE_REJECTED"
ENV_SECRET_ACCESS_REJECTED = "ENV_SECRET_ACCESS_REJECTED"
INERT_PROPOSE_PATCH_DATA_ONLY = "INERT_PROPOSE_PATCH_DATA_ONLY"
REALPATH_SCOPE_ESCAPE_REJECTED = "REALPATH_SCOPE_ESCAPE_REJECTED"
UNEXPECTED_REALPATH_ESCAPE_ALLOWED = "UNEXPECTED_REALPATH_ESCAPE_ALLOWED"

CATEGORY_SYMLINK_REALPATH_ESCAPE = "symlink_realpath_escape"
CATEGORY_INERT_DATA = "inert_data"

ALLOWED_GATE_RESULTS = frozenset({CAPABILITY_GATE_ALLOWED, CAPABILITY_GATE_LIMITED_ALLOWED})
NOT_CHECKED_SUPPORT_STATUSES = frozenset(
    {NOT_CHECKED_SYMLINK_UNSUPPORTED, NOT_CHECKED_PLATFORM_PERMISSION_LIMIT}
)
FORBIDDEN_PASS_STATUSES = frozenset(
    {
        "PASS",
        "PASS_WITHOUT_SYMLINK_REALPATH_TEST",
        "SYMLINK_SAFE_WITHOUT_REALPATH_TEST",
    }
)


@dataclass(frozen=True)
class SymlinkRealpathFixture:
    case_id: str
    category: str
    action: Mapping[str, Any]
    expected_fixture_status: str
    note: str = ""


@dataclass(frozen=True)
class SymlinkRealpathFixtureEvaluation:
    case_id: str
    category: str
    fixture_status: str
    schema_status: str
    gate_result: str
    rejected: bool
    allowed: bool
    expectation_met: bool
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    live_executor_ready: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD


@dataclass(frozen=True)
class SymlinkRealpathFixtureSummaryVerification:
    ok: bool
    errors: tuple[str, ...]


def propose_patch_for_paths(paths: list[str]) -> dict[str, Any]:
    action = _base_propose_patch()
    action["target_scope"]["paths"] = list(paths)
    action["payload"]["target_files"] = list(paths)
    return action


def repo_read_for_paths(paths: list[str]) -> dict[str, Any]:
    return {
        "action_type": REQUEST_REPO_READ,
        "action_id": "phase11b-1f-repo-read",
        "declared_intent": "Request bounded repository context.",
        "declared_risk": "LOW",
        "capability_requirements": ["read_repo"],
        "target_scope": {
            "repo_relative": True,
            "paths": list(paths),
        },
        "payload": {
            "paths": list(paths),
        },
    }


def inert_propose_patch_action(target_file: str = "src/normal.py") -> dict[str, Any]:
    action = propose_patch_for_paths([target_file])
    action["payload"]["patch_diff"] = (
        f"diff --git a/{target_file} b/{target_file}\n"
        f"--- a/{target_file}\n"
        f"+++ b/{target_file}\n"
        "@@ -1 +1 @@\n"
        "-old data\n"
        "+new data\n"
    )
    action["payload"]["patch_plan"] = [
        "Keep patch text as reviewable data only.",
        "Do not interpret patch text as write authority.",
    ]
    return action


def evaluate_symlink_realpath_fixture(
    fixture: SymlinkRealpathFixture,
    *,
    repo_root: str | Path,
) -> SymlinkRealpathFixtureEvaluation:
    validation = validate_structured_action(fixture.action, repo_root=repo_root)
    gate_result = evaluate_action_capabilities(
        fixture.action,
        validation,
        repo_root=repo_root,
    )
    allowed = gate_result.gate_result in ALLOWED_GATE_RESULTS
    rejected = not allowed

    if fixture.expected_fixture_status == INERT_PROPOSE_PATCH_DATA_ONLY:
        fixture_status = INERT_PROPOSE_PATCH_DATA_ONLY
        expectation_met = (
            allowed
            and validation.status == VALID_STRUCTURED_ACTION
            and gate_result.gate_result == CAPABILITY_GATE_LIMITED_ALLOWED
        )
    elif allowed:
        fixture_status = UNEXPECTED_REALPATH_ESCAPE_ALLOWED
        expectation_met = False
    else:
        fixture_status = _classified_rejection_status(
            [*validation.reasons, gate_result.gate_reason]
        )
        expectation_met = (
            fixture_status == fixture.expected_fixture_status
            and validation.status == FORBIDDEN_PAYLOAD_FIELD_REJECTED
            and gate_result.gate_result == SCOPE_LIMIT_REJECTED
        )

    return SymlinkRealpathFixtureEvaluation(
        case_id=fixture.case_id,
        category=fixture.category,
        fixture_status=fixture_status,
        schema_status=validation.status,
        gate_result=gate_result.gate_result,
        rejected=rejected,
        allowed=allowed,
        expectation_met=expectation_met,
        execution_allowed=gate_result.execution_allowed,
        mutation_allowed=gate_result.mutation_allowed,
        write_authority_granted=gate_result.write_authority_granted,
        live_executor_ready=gate_result.live_executor_ready,
        live_executor_authority=gate_result.live_executor_authority,
    )


def build_symlink_realpath_fixture_summary(
    evaluations: tuple[SymlinkRealpathFixtureEvaluation, ...] = (),
    *,
    symlink_support_status: str,
) -> dict[str, Any]:
    checked = symlink_support_status == SYMLINK_SUPPORTED
    escape_results = tuple(
        result for result in evaluations if result.category == CATEGORY_SYMLINK_REALPATH_ESCAPE
    )
    inert_results = tuple(result for result in evaluations if result.category == CATEGORY_INERT_DATA)
    all_expectations_met = checked and all(result.expectation_met for result in evaluations)

    if checked:
        fixture_status = (
            SYMLINK_REALPATH_FIXTURES_CHECKED
            if all_expectations_met
            else SYMLINK_REALPATH_FIXTURE_FAILURE
        )
    else:
        fixture_status = symlink_support_status

    return {
        "symlink_realpath_fixture_set_version": SYMLINK_REALPATH_FIXTURE_SET_VERSION,
        "symlink_realpath_fixture_status": fixture_status,
        "symlink_realpath_checked": checked,
        "symlink_realpath_support_status": symlink_support_status,
        "symlink_escape_rejected_count": _count_rejected(escape_results),
        "symlink_escape_allowed_count": _count_allowed(escape_results),
        "realpath_escape_rejected_count": _count_rejected(escape_results),
        "realpath_escape_allowed_count": _count_allowed(escape_results),
        "inert_propose_patch_data_only_count": sum(
            1 for result in inert_results if result.allowed and result.expectation_met
        ),
        "execution_allowed": any(result.execution_allowed for result in evaluations),
        "mutation_allowed": any(result.mutation_allowed for result in evaluations),
        "write_authority_granted": any(
            result.write_authority_granted for result in evaluations
        ),
        "live_executor_ready": any(result.live_executor_ready for result in evaluations),
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "pr_81_status": PR_81_STATUS_HOLD_OPEN_DRAFT,
        "pr_81_draft_release": PR_81_DRAFT_RELEASE_NOT_PERFORMED,
        "pr_81_merge": PR_81_MERGE_NOT_PERFORMED,
        "safe_default": SAFE_DEFAULT,
        "fixture_results": [_evaluation_record(result) for result in evaluations],
    }


def verify_symlink_realpath_fixture_summary(
    summary: Mapping[str, Any],
) -> SymlinkRealpathFixtureSummaryVerification:
    errors: list[str] = []
    status = summary.get("symlink_realpath_fixture_status")
    support_status = summary.get("symlink_realpath_support_status")
    pass_claimed = status in FORBIDDEN_PASS_STATUSES or str(status).startswith("PASS")

    if status in FORBIDDEN_PASS_STATUSES:
        errors.append(f"forbidden symlink pass status rejected: {status}")
    if support_status in NOT_CHECKED_SUPPORT_STATUSES and summary.get(
        "symlink_realpath_checked"
    ):
        errors.append("symlink support unavailable cannot be marked checked")
    if support_status in NOT_CHECKED_SUPPORT_STATUSES and pass_claimed:
        errors.append("symlink support unavailable cannot be promoted to PASS")
    if summary.get("symlink_realpath_checked") is not True and pass_claimed:
        errors.append("unchecked symlink realpath fixture cannot be promoted to PASS")
    if _positive_count(summary.get("symlink_escape_allowed_count")):
        errors.append("symlink escape allowed count must be zero")
    if _positive_count(summary.get("realpath_escape_allowed_count")):
        errors.append("realpath escape allowed count must be zero")

    for field in (
        "execution_allowed",
        "mutation_allowed",
        "write_authority_granted",
        "live_executor_ready",
        "write_authority_safe",
        "bypass_impossible",
        "tool_system_safe",
    ):
        if summary.get(field) is True:
            errors.append(f"{field}=true rejected")

    if summary.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        errors.append("live executor authority must remain on hold")

    return SymlinkRealpathFixtureSummaryVerification(ok=not errors, errors=tuple(errors))


def _base_propose_patch() -> dict[str, Any]:
    return {
        "action_type": PROPOSE_PATCH,
        "action_id": "phase11b-1f-propose-patch",
        "declared_intent": "Propose a reviewable patch.",
        "declared_risk": "LOW",
        "capability_requirements": ["propose_patch"],
        "target_scope": {
            "repo_relative": True,
            "paths": ["src/normal.py"],
        },
        "payload": {
            "target_files": ["src/normal.py"],
            "patch_summary": "Change is proposed as inert data only.",
            "patch_plan": ["Edit src/normal.py through future mediated review."],
        },
    }


def _classified_rejection_status(reasons: list[str]) -> str:
    reason_text = " ".join(reasons).lower()
    if "env/secret" in reason_text:
        return ENV_SECRET_ACCESS_REJECTED
    if ".aeg" in reason_text:
        return AEG_SCOPE_ESCAPE_REJECTED
    if "outside repo" in reason_text:
        return OUTSIDE_REPO_ESCAPE_REJECTED
    return REALPATH_SCOPE_ESCAPE_REJECTED


def _count_rejected(results: tuple[SymlinkRealpathFixtureEvaluation, ...]) -> int:
    return sum(1 for result in results if result.rejected)


def _count_allowed(results: tuple[SymlinkRealpathFixtureEvaluation, ...]) -> int:
    return sum(1 for result in results if result.allowed)


def _positive_count(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def _evaluation_record(result: SymlinkRealpathFixtureEvaluation) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "category": result.category,
        "fixture_status": result.fixture_status,
        "schema_status": result.schema_status,
        "gate_result": result.gate_result,
        "rejected": result.rejected,
        "allowed": result.allowed,
        "expectation_met": result.expectation_met,
        "execution_allowed": result.execution_allowed,
        "mutation_allowed": result.mutation_allowed,
        "write_authority_granted": result.write_authority_granted,
        "live_executor_ready": result.live_executor_ready,
        "live_executor_authority": result.live_executor_authority,
    }
