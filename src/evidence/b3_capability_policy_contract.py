"""B3-2 capability non-grant policy contract.

This module defines import-safe policy objects and validation helpers only. It
does not execute tools, mediate writes, call providers, use the network, or
enforce runtime capability boundaries.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    SAFE_DEFAULT,
)

B3_CAPABILITY_POLICY_CONTRACT_V0 = "b3_capability_policy_contract_v0"

NOT_GRANTED_BY_POLICY = "NOT_GRANTED_BY_POLICY"
VALID_CONTRACT = "VALID_CONTRACT"
INVALID_CONTRACT = "INVALID_CONTRACT"

GRANT_SOURCE_POLICY_DEFAULT = "policy_default_non_grant"
GRANT_SOURCE_EVIDENCE = "evidence_bound_future"
GRANT_SOURCE_UNKNOWN = "unknown"

CHECK_STATUS_CHECKED = "CHECKED"
CHECK_STATUS_MISSING = "MISSING"
CHECK_STATUS_UNKNOWN = "UNKNOWN"

PASSLIKE_CLAIMS = frozenset({"PASS", "CLEAN", "ALLOW", "ALLOWED", "GRANTED"})
UNVERIFIED_CHECK_STATUSES = frozenset({NOT_CHECKED, CHECK_STATUS_MISSING, CHECK_STATUS_UNKNOWN, None})

CAPABILITY_FIELDS = (
    "raw_shell_authority",
    "write_file_authority",
    "run_command_authority",
    "process_spawn_authority",
    "network_authority",
    "provider_model_call_authority",
    "remote_write_authority",
    "repo_outside_write_authority",
    "aeg_state_write_authority",
    "aeg_state_read_authority",
    "env_read_authority",
    "secret_read_authority",
)

CAPABILITY_POLICY_OBJECT_FIELDS = (
    "capability_name",
    "granted",
    "grant_source",
    "check_status",
    "scope_note",
    "evidence_required",
    "overclaim_risk",
    "non_claim_caveat",
)

CONTRACT_NON_ENFORCEMENT_FLAGS = (
    "runtime_enforcement",
    "tool_execution_gating",
    "os_filesystem_hardening",
    "sandbox_boundary",
    "command_runner_added",
)

OVERCLAIM_FLAG_FIELDS = (
    "physical_impossibility_claimed",
    "outside_denial_claimed",
    "composition_safe_claimed",
    "structured_tool_safe_claimed",
    "live_executor_ready_claimed",
    "phase11a_started_claimed",
)

DEFAULT_SCOPE_NOTES = {
    "raw_shell_authority": "No raw shell grant is present in the B3-2 policy contract.",
    "write_file_authority": "No generic file write grant is present in the B3-2 policy contract.",
    "run_command_authority": "No command runner grant is present in the B3-2 policy contract.",
    "process_spawn_authority": "No process spawn grant is present in the B3-2 policy contract.",
    "network_authority": "No network grant is present in the B3-2 policy contract.",
    "provider_model_call_authority": "No provider or model call grant is present in the B3-2 policy contract.",
    "remote_write_authority": "No remote write grant is present in the B3-2 policy contract.",
    "repo_outside_write_authority": "No outside-repo write grant is present in the B3-2 policy contract.",
    "aeg_state_write_authority": "No executor-authored .aeg state write grant is present in the B3-2 policy contract.",
    "aeg_state_read_authority": "No executor .aeg state read grant is present in the B3-2 policy contract.",
    "env_read_authority": "No environment read grant is present in the B3-2 policy contract.",
    "secret_read_authority": "No secret read grant is present in the B3-2 policy contract.",
}

NON_CLAIM_CAVEAT = (
    "Policy non-grant is not a runtime denial proof, not a path-safety proof, "
    "and not a composition-closure claim."
)


def build_default_capability_policy(capability_name: str) -> dict[str, Any]:
    if capability_name not in CAPABILITY_FIELDS:
        raise ValueError(f"unknown capability: {capability_name}")

    return {
        "capability_name": capability_name,
        "granted": False,
        "grant_source": GRANT_SOURCE_POLICY_DEFAULT,
        "policy_status": NOT_GRANTED_BY_POLICY,
        "check_status": NOT_CHECKED,
        "scope_note": DEFAULT_SCOPE_NOTES[capability_name],
        "evidence_required": False,
        "evidence_ref": None,
        "overclaim_risk": False,
        "non_claim_caveat": NON_CLAIM_CAVEAT,
        "claim_status": None,
    }


def build_default_capability_policy_contract() -> dict[str, Any]:
    return {
        "contract_version": B3_CAPABILITY_POLICY_CONTRACT_V0,
        "capabilities": {
            capability_name: build_default_capability_policy(capability_name)
            for capability_name in CAPABILITY_FIELDS
        },
        "default_policy_status": NOT_GRANTED_BY_POLICY,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        "phase11a_status": PHASE11A_NOT_STARTED,
        "safe_default": SAFE_DEFAULT,
        "b3_1_preserved": True,
        "b3_4_path_scope_fixture_started": False,
        "non_enforcement": {flag: False for flag in CONTRACT_NON_ENFORCEMENT_FLAGS},
        "overclaim_flags": {flag: False for flag in OVERCLAIM_FLAG_FIELDS},
    }


def validate_capability_policy_contract(contract: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    overclaim_candidates: list[str] = []

    if contract.get("contract_version") != B3_CAPABILITY_POLICY_CONTRACT_V0:
        reasons.append("contract_version mismatch")

    if contract.get("default_policy_status") != NOT_GRANTED_BY_POLICY:
        reasons.append("default policy status must be NOT_GRANTED_BY_POLICY")

    if contract.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("live executor authority must remain on hold")
    if contract.get("runtime_write_path") != NOT_WIRED_TO_EXECUTOR_WRITE_PATH:
        reasons.append("runtime write path must remain unwired")
    if contract.get("phase11a_status") != PHASE11A_NOT_STARTED:
        reasons.append("Phase 11-A must remain not started")

    if contract.get("b3_1_preserved") is not True:
        reasons.append("B3-1 inventory and non-grant baseline must be preserved")
    if contract.get("b3_4_path_scope_fixture_started") is True:
        reasons.append("B3-4 path and scope fixture work is out of scope for B3-2")

    _validate_non_enforcement(contract, reasons)
    _validate_overclaim_flags(contract, reasons)
    _validate_capabilities(contract, reasons, overclaim_candidates)

    return {
        "valid": not reasons,
        "status": VALID_CONTRACT if not reasons else INVALID_CONTRACT,
        "reasons": reasons,
        "overclaim_candidates": overclaim_candidates,
        "is_runtime_enforcement": False,
        "is_tool_execution_gate": False,
        "safe_default": SAFE_DEFAULT,
    }


def clone_default_capability_policy_contract() -> dict[str, Any]:
    return deepcopy(build_default_capability_policy_contract())


def _validate_non_enforcement(contract: dict[str, Any], reasons: list[str]) -> None:
    flags = contract.get("non_enforcement")
    if not isinstance(flags, dict):
        reasons.append("non-enforcement flags are missing")
        return

    for flag in CONTRACT_NON_ENFORCEMENT_FLAGS:
        if flags.get(flag) is not False:
            reasons.append(f"{flag} must be false for B3-2 contract-only scope")


def _validate_overclaim_flags(contract: dict[str, Any], reasons: list[str]) -> None:
    flags = contract.get("overclaim_flags")
    if not isinstance(flags, dict):
        reasons.append("overclaim flags are missing")
        return

    rejection_messages = {
        "physical_impossibility_claimed": "physical impossibility claims are rejected",
        "outside_denial_claimed": "outside denial claims are rejected",
        "composition_safe_claimed": "composition closure claims are rejected",
        "structured_tool_safe_claimed": "structured tool safety claims are rejected",
        "live_executor_ready_claimed": "live executor ready claims are rejected",
        "phase11a_started_claimed": "Phase 11-A started claims are rejected",
    }
    for flag, message in rejection_messages.items():
        if flags.get(flag) is True:
            reasons.append(message)


def _validate_capabilities(
    contract: dict[str, Any],
    reasons: list[str],
    overclaim_candidates: list[str],
) -> None:
    capabilities = _capability_items(contract.get("capabilities"))
    if capabilities is None:
        reasons.append("capabilities must be a mapping or list")
        return

    present_names = {policy.get("capability_name") for policy in capabilities}
    for capability_name in CAPABILITY_FIELDS:
        if capability_name not in present_names:
            reasons.append(f"missing capability policy: {capability_name}")

    for policy in capabilities:
        _validate_capability_policy(policy, reasons, overclaim_candidates)


def _validate_capability_policy(
    policy: dict[str, Any],
    reasons: list[str],
    overclaim_candidates: list[str],
) -> None:
    capability_name = policy.get("capability_name")
    if capability_name not in CAPABILITY_FIELDS:
        reasons.append(f"unknown capability policy: {capability_name}")
        return

    for field in CAPABILITY_POLICY_OBJECT_FIELDS:
        if field not in policy:
            reasons.append(f"{capability_name} missing field: {field}")

    granted = policy.get("granted")
    grant_source = policy.get("grant_source")
    check_status = policy.get("check_status")
    claim_status = policy.get("claim_status")
    evidence_ref = policy.get("evidence_ref")

    if granted is not False and granted is not True:
        reasons.append(f"{capability_name} granted must be boolean")

    if granted is False and policy.get("policy_status") != NOT_GRANTED_BY_POLICY:
        reasons.append(f"{capability_name} default non-grant status is missing")

    if granted is True and not evidence_ref:
        reasons.append(f"{capability_name} granted=true requires evidence_ref")
    if granted is True and grant_source in (GRANT_SOURCE_UNKNOWN, None, ""):
        reasons.append(f"{capability_name} granted=true cannot use unknown grant source")
    if granted is True and grant_source == REPORTED_ONLY:
        reasons.append(f"{capability_name} reported-only source cannot support granted=true")

    if grant_source == REPORTED_ONLY and granted is True and check_status != CHECK_STATUS_CHECKED:
        overclaim_candidates.append(f"{capability_name}:grant_true_reported_only_unchecked")

    if _passlike(claim_status):
        if grant_source == REPORTED_ONLY:
            reasons.append(f"{capability_name} reported-only source cannot support PASS-like claim")
        if check_status in UNVERIFIED_CHECK_STATUSES:
            reasons.append(f"{capability_name} unchecked status cannot support PASS-like claim")

    if granted is True and check_status in UNVERIFIED_CHECK_STATUSES:
        overclaim_candidates.append(f"{capability_name}:grant_true_unchecked")

    if policy.get("overclaim_risk") is True:
        overclaim_candidates.append(f"{capability_name}:declared_overclaim_risk")


def _capability_items(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, dict):
        items = list(value.values())
    elif isinstance(value, list):
        items = value
    else:
        return None

    if not all(isinstance(item, dict) for item in items):
        return None
    return items


def _passlike(value: Any) -> bool:
    return isinstance(value, str) and value.upper() in PASSLIKE_CLAIMS
