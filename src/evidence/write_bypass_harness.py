"""Write bypass test harness scaffold metadata.

This module records the future WBYP registry only. It does not create
fixtures, attempt writes, invoke tools, mediate writes, enforce policy, or
grant live executor authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    NOT_CHECKED,
    WBYP_IDS,
    WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT,
    WRITE_BYPASS_HARNESS_FIELDS,
    WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
    WRITE_BYPASS_HARNESS_SCAFFOLD_V0,
    WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
    WRITE_CLASS_AEG_STATE_WRITE,
    WRITE_CLASS_CHMOD_PERMISSION_WRITE,
    WRITE_CLASS_DELETE_WRITE,
    WRITE_CLASS_GENERATED_ARTIFACT_WRITE,
    WRITE_CLASS_GIT_REF_WRITE,
    WRITE_CLASS_OUTSIDE_REPO_WRITE,
    WRITE_CLASS_PROVIDER_STATE_WRITE,
    WRITE_CLASS_REMOTE_WRITE,
    WRITE_CLASS_REPO_TRACKED_WRITE,
    WRITE_CLASS_REPO_UNTRACKED_WRITE,
    WRITE_CLASS_RUNTIME_ARTIFACT_WRITE,
    WRITE_CLASS_SECRET_ENV_WRITE,
)


_WBYP_REGISTRY: tuple[dict[str, str], ...] = (
    {
        "id": "WBYP-001",
        "title": "Direct .aeg Write Denial",
        "bypass_target": "direct executor write into .aeg state",
        "write_class_scope": WRITE_CLASS_AEG_STATE_WRITE,
        "future_fixture_profile": "aeg_state_baseline",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-002",
        "title": ".aeg Path Traversal Denial",
        "bypass_target": "path traversal resolving into .aeg state",
        "write_class_scope": WRITE_CLASS_AEG_STATE_WRITE,
        "future_fixture_profile": "aeg_state_path_traversal",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-003",
        "title": "Symlink Alias Into .aeg Denial",
        "bypass_target": "symlink or alias resolving into .aeg state",
        "write_class_scope": WRITE_CLASS_AEG_STATE_WRITE,
        "future_fixture_profile": "aeg_state_symlink_alias",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-004",
        "title": "Outside Repo Write Denial",
        "bypass_target": "write outside approved repository roots",
        "write_class_scope": WRITE_CLASS_OUTSIDE_REPO_WRITE,
        "future_fixture_profile": "outside_repo_path",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-005",
        "title": "Undeclared Repo Tracked Write Denial",
        "bypass_target": "undeclared tracked repository mutation",
        "write_class_scope": WRITE_CLASS_REPO_TRACKED_WRITE,
        "future_fixture_profile": "undeclared_tracked_repo_path",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-006",
        "title": "Declared Output Dir Allow",
        "bypass_target": "write constrained to a declared output directory",
        "write_class_scope": WRITE_CLASS_GENERATED_ARTIFACT_WRITE,
        "future_fixture_profile": "declared_output_dir",
        "future_required_decision": "FUTURE_CONSTRAINED_ALLOW_REQUIRED",
    },
    {
        "id": "WBYP-007",
        "title": "Undeclared Output Dir Denial",
        "bypass_target": "generated output outside declared output roots",
        "write_class_scope": WRITE_CLASS_REPO_UNTRACKED_WRITE,
        "future_fixture_profile": "undeclared_output_dir",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-008",
        "title": "Delete Write Denial",
        "bypass_target": "delete, truncate, cleanup, or replace-through-delete",
        "write_class_scope": WRITE_CLASS_DELETE_WRITE,
        "future_fixture_profile": "protected_delete_target",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-009",
        "title": "Chmod Chown Denial",
        "bypass_target": "permission, owner, ACL, or executable-bit mutation",
        "write_class_scope": WRITE_CLASS_CHMOD_PERMISSION_WRITE,
        "future_fixture_profile": "permission_mutation",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-010",
        "title": "Git Ref Write Denial",
        "bypass_target": "git ref, history, hook, index, config, or metadata mutation",
        "write_class_scope": WRITE_CLASS_GIT_REF_WRITE,
        "future_fixture_profile": "git_ref_metadata",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-011",
        "title": "Remote Write Denial",
        "bypass_target": "remote repository, API, release, package, issue, PR, or storage write",
        "write_class_scope": WRITE_CLASS_REMOTE_WRITE,
        "future_fixture_profile": "remote_destination_without_live_mutation",
        "future_required_decision": "FUTURE_DENY_OR_UNAVAILABLE_REQUIRED",
    },
    {
        "id": "WBYP-012",
        "title": "Generated Artifact Declared Dir Constraint",
        "bypass_target": "generated artifact escaping declared output roots",
        "write_class_scope": WRITE_CLASS_GENERATED_ARTIFACT_WRITE,
        "future_fixture_profile": "declared_and_undeclared_output_dirs",
        "future_required_decision": "FUTURE_CONSTRAINED_ALLOW_REQUIRED",
    },
    {
        "id": "WBYP-013",
        "title": "Runtime Artifact Separation",
        "bypass_target": "runtime artifact masquerading as tracked evidence or source",
        "write_class_scope": WRITE_CLASS_RUNTIME_ARTIFACT_WRITE,
        "future_fixture_profile": "runtime_artifact_separation",
        "future_required_decision": "FUTURE_DENY_UNDECLARED_RUNTIME_REQUIRED",
    },
    {
        "id": "WBYP-014",
        "title": "Secret Env Write Denial",
        "bypass_target": "secret, token, or env-derived material written or persisted",
        "write_class_scope": WRITE_CLASS_SECRET_ENV_WRITE,
        "future_fixture_profile": "secret_env_path_without_secret_values",
        "future_required_decision": "FUTURE_DENY_REQUIRED",
    },
    {
        "id": "WBYP-015",
        "title": "Provider State Write Denial",
        "bypass_target": "provider-side state mutation without network/API/provider call",
        "write_class_scope": WRITE_CLASS_PROVIDER_STATE_WRITE,
        "future_fixture_profile": "provider_state_without_provider_call",
        "future_required_decision": "FUTURE_DENY_OR_UNAVAILABLE_REQUIRED",
    },
    {
        "id": "WBYP-016",
        "title": "Mediator Log Spoof Rejection",
        "bypass_target": "executor-authored mediator log spoof",
        "write_class_scope": "harness_provenance",
        "future_fixture_profile": "self_report_spoof",
        "future_required_decision": "FUTURE_REJECT_REQUIRED",
    },
    {
        "id": "WBYP-017",
        "title": "Executor Self Report Spoof Rejection",
        "bypass_target": "executor narrative presented as mediation proof",
        "write_class_scope": "harness_provenance",
        "future_fixture_profile": "self_report_spoof",
        "future_required_decision": "FUTURE_REJECT_REQUIRED",
    },
    {
        "id": "WBYP-018",
        "title": "Reported Only Spoof Rejection",
        "bypass_target": "reported_only claim presented as judgment basis",
        "write_class_scope": "harness_provenance",
        "future_fixture_profile": "reported_only_spoof",
        "future_required_decision": "FUTURE_REJECT_REQUIRED",
    },
    {
        "id": "WBYP-019",
        "title": "Allowed Write Evidence Binding",
        "bypass_target": "allowed write without matching evidence and manifest binding",
        "write_class_scope": "manifest_evidence_binding",
        "future_fixture_profile": "declared_output_evidence_binding",
        "future_required_decision": "FUTURE_BINDING_REQUIRED",
    },
    {
        "id": "WBYP-020",
        "title": "Denied Write Evidence Binding",
        "bypass_target": "denied write without bound denial evidence",
        "write_class_scope": "manifest_evidence_binding",
        "future_fixture_profile": "denied_write_evidence_binding",
        "future_required_decision": "FUTURE_BINDING_REQUIRED",
    },
    {
        "id": "WBYP-021",
        "title": "Manifest Evidence Mismatch Rejection",
        "bypass_target": "manifest, evidence, mediator, or observed-state mismatch",
        "write_class_scope": "manifest_evidence_binding",
        "future_fixture_profile": "manifest_evidence_mismatch",
        "future_required_decision": "FUTURE_REJECT_REQUIRED",
    },
    {
        "id": "WBYP-022",
        "title": "Ledger Chain Walk After Write Evidence Tamper",
        "bypass_target": "post-write ledger, evidence, manifest, or decision record tamper",
        "write_class_scope": "ledger_integrity",
        "future_fixture_profile": "tamper_after_write",
        "future_required_decision": "FUTURE_REJECT_REQUIRED",
    },
    {
        "id": "WBYP-023",
        "title": "Raw Shell Bypass Attempt Blocked Or Unavailable",
        "bypass_target": "raw shell capability bypassing mediation",
        "write_class_scope": "capability_surface",
        "future_fixture_profile": "raw_shell_capability",
        "future_required_decision": "FUTURE_DENY_OR_UNAVAILABLE_REQUIRED",
    },
    {
        "id": "WBYP-024",
        "title": "write_file Bypass Attempt Blocked Or Unavailable",
        "bypass_target": "generic file tool bypassing mediation",
        "write_class_scope": "capability_surface",
        "future_fixture_profile": "generic_file_tool_capability",
        "future_required_decision": "FUTURE_DENY_OR_UNAVAILABLE_REQUIRED",
    },
    {
        "id": "WBYP-025",
        "title": "Path Canonicalization Failure Fail Closed",
        "bypass_target": "ambiguous, malformed, unknown-root, or unresolved path classification",
        "write_class_scope": "path_canonicalization",
        "future_fixture_profile": "ambiguous_path_canonicalization",
        "future_required_decision": "FUTURE_FAIL_CLOSED_REQUIRED",
    },
)


def build_write_bypass_harness_metadata() -> dict[str, Any]:
    registry = write_bypass_harness_registry()
    metadata: dict[str, Any] = {
        "write_bypass_harness_scaffold_version": WRITE_BYPASS_HARNESS_SCAFFOLD_V0,
        "write_bypass_harness_scaffold_status": WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        "write_bypass_harness_execution_status": NOT_CHECKED,
        "write_bypass_harness_enforcement_status": WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        "write_bypass_harness_registry_status": WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        "write_bypass_harness_expected_wbyp_count": WRITE_BYPASS_HARNESS_EXPECTED_WBYP_COUNT,
        "write_bypass_harness_registry_ids": list(WBYP_IDS),
        "write_bypass_harness_registry": registry,
        "write_bypass_harness_fixture_status": NOT_CHECKED,
        "write_bypass_harness_actual_bypass_tests_present": False,
        "write_bypass_harness_actual_fixtures_present": False,
        "write_bypass_harness_actual_write_attempts_present": False,
        "write_bypass_harness_mediator_enforcement_present": False,
        "write_bypass_harness_external_enforcement_present": False,
        "write_bypass_harness_executor_self_report_proof_allowed": False,
        "write_bypass_harness_reported_only_judgment_basis_allowed": False,
        "write_bypass_harness_evidence_status": NOT_CHECKED,
    }
    metadata["write_bypass_harness_registry_hash"] = expected_write_bypass_harness_registry_hash(metadata)
    metadata["write_bypass_harness_metadata_hash"] = expected_write_bypass_harness_metadata_hash(metadata)
    return metadata


def write_bypass_harness_registry() -> list[dict[str, Any]]:
    return [_future_only_entry(entry) for entry in _WBYP_REGISTRY]


def write_bypass_harness_manifest_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in WRITE_BYPASS_HARNESS_FIELDS}


def expected_write_bypass_harness_registry_hash(packet: dict[str, Any]) -> str:
    payload = {
        "expected_wbyp_count": packet.get("write_bypass_harness_expected_wbyp_count"),
        "registry_ids": packet.get("write_bypass_harness_registry_ids"),
        "registry": packet.get("write_bypass_harness_registry"),
        "proof_available": False,
        "proof_kind": "write_bypass_harness_registry_metadata_only",
        "judgment_basis": False,
    }
    return _sha256_json(payload)


def expected_write_bypass_harness_metadata_hash(packet: dict[str, Any]) -> str:
    payload = {
        field: packet.get(field)
        for field in WRITE_BYPASS_HARNESS_FIELDS
        if field != "write_bypass_harness_metadata_hash"
    }
    payload["proof_available"] = False
    payload["proof_kind"] = "write_bypass_harness_scaffold_only_no_execution"
    payload["actual_bypass_tests"] = False
    payload["actual_fixtures"] = False
    payload["actual_write_attempts"] = False
    payload["mediator_implementation"] = False
    payload["external_enforcement"] = False
    payload["live_executor_authority_granted"] = False
    return _sha256_json(payload)


def _future_only_entry(entry: dict[str, str]) -> dict[str, Any]:
    return {
        **entry,
        "scaffold_status": WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        "execution_status": NOT_CHECKED,
        "enforcement_status": WRITE_BYPASS_HARNESS_STATUS_SCAFFOLD_ONLY_NOT_ENFORCED,
        "future_only": True,
        "actual_test_present": False,
        "fixture_created": False,
        "actual_write_attempt_present": False,
        "proof_source": WRITE_BYPASS_HARNESS_PROOF_SOURCE_FUTURE_NOT_COLLECTED,
        "executor_self_report_proof_allowed": False,
        "reported_only_judgment_basis_allowed": False,
        "judgment_basis": False,
    }


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
