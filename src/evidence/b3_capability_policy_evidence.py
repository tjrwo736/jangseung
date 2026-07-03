"""B3-3 deterministic evidence binding for the B3-2 capability policy.

This module only builds and verifies deterministic policy validation evidence.
It does not execute tools, mediate runtime writes, call providers, use the
network, spawn processes, or change executor authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    SAFE_DEFAULT,
)
from src.evidence.b3_capability_policy_contract import (
    B3_CAPABILITY_POLICY_CONTRACT_V0,
    CAPABILITY_FIELDS,
    GRANT_SOURCE_UNKNOWN,
    PASSLIKE_CLAIMS,
    UNVERIFIED_CHECK_STATUSES,
    validate_capability_policy_contract,
)

B3_CAPABILITY_POLICY_EVIDENCE_KIND = "b3_capability_policy_validation_evidence"
B3_CAPABILITY_POLICY_EVIDENCE_VERSION = "b3_capability_policy_evidence_v0"

VERIFY_REPLAY_ACCEPTED = "VERIFY_REPLAY_ACCEPTED"
VERIFY_REPLAY_REJECTED = "VERIFY_REPLAY_REJECTED"

AUTHORITY_SNAPSHOT = {
    "runtime_write_path": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "safe_default": SAFE_DEFAULT,
}

CAPABILITY_SUMMARY_FIELDS = (
    "capability_name",
    "granted",
    "grant_source",
    "policy_status",
    "check_status",
    "evidence_required",
    "evidence_ref",
    "claim_status",
    "overclaim_risk",
)

NON_CLAIM_CAVEATS = (
    "policy validation evidence is not a capability grant",
    "no raw shell authority grant",
    "no write_file tool",
    "no run_command tool",
    "no process_spawn tool",
    "no network authority grant",
    "no provider/model call authority grant",
    "no remote write authority grant",
    "no repo outside write authority grant",
    "no OS/filesystem enforcement",
    "no sandbox/container",
    "no physical impossibility proof",
    "no executor isolation",
    "no runtime tool gating",
    "no live executor",
    "no runtime write authority grant",
    "no Phase 11-A start",
    "no B3 closure",
    "no B1 hard blocker fully green",
    "no Live Executor Entry Gate approval",
)

SOURCE_CONTRACT_NOTE = {
    "module": "src.evidence.b3_capability_policy_contract",
    "contract_version": B3_CAPABILITY_POLICY_CONTRACT_V0,
    "validation_function": "validate_capability_policy_contract",
    "scope": "policy_validation_evidence_only",
}

_RECORD_FIELDS = frozenset(
    {
        "record_kind",
        "record_version",
        "claim_type",
        "capability_policy_digest",
        "policy_validation_outcome",
        "capability_fields_summary",
        "rejected_overclaim_candidates",
        "authority_snapshot",
        "boundary_preservation",
        "non_claim_caveats",
        "source_contract_module_version_note",
        "deterministic_evidence_digest",
    }
)

_OVERCLAIM_FLAG_REJECTIONS = {
    "physical_impossibility_claimed": "physical impossibility claim rejected",
    "outside_denial_claimed": "outside denial claim rejected",
    "externally_enforced_denial_claimed": "external denial claim rejected",
    "composition_safe_claimed": "composition closure claim rejected",
    "bypass_impossible_claimed": "bypass impossibility claim rejected",
    "structured_tool_safe_claimed": "structured tool safety claim rejected",
    "live_executor_ready_claimed": "live executor ready claim rejected",
    "phase11a_started_claimed": "Phase 11-A started claim rejected",
    "b3_closure_claimed": "B3 closure claim rejected",
    "runtime_enforcement_claimed": "runtime enforcement claim rejected",
    "tool_execution_gating_claimed": "tool execution gating claim rejected",
    "runtime_write_path_wired_claimed": "runtime write path wiring claim rejected",
}


def build_capability_policy_evidence_record(
    capability_policy_contract: Mapping[str, Any],
    validation_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic B3-3 evidence record for a B3-2 validation result."""

    if validation_result is None:
        validation_result = validate_capability_policy_contract(dict(capability_policy_contract))

    record = {
        "record_kind": B3_CAPABILITY_POLICY_EVIDENCE_KIND,
        "record_version": B3_CAPABILITY_POLICY_EVIDENCE_VERSION,
        "claim_type": "policy_validation_evidence_not_capability_grant",
        "capability_policy_digest": capability_policy_digest(capability_policy_contract),
        "policy_validation_outcome": _validation_outcome(validation_result),
        "capability_fields_summary": capability_fields_summary(capability_policy_contract),
        "rejected_overclaim_candidates": _rejected_overclaim_candidates(
            capability_policy_contract,
            validation_result,
        ),
        "authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "boundary_preservation": {
            "b3_1_preserved": capability_policy_contract.get("b3_1_preserved"),
            "b3_4_path_scope_fixture_started": capability_policy_contract.get(
                "b3_4_path_scope_fixture_started"
            ),
        },
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
        "source_contract_module_version_note": dict(SOURCE_CONTRACT_NOTE),
    }
    record["deterministic_evidence_digest"] = capability_policy_evidence_digest(record)
    return record


def verify_capability_policy_evidence_record(
    evidence_record: Mapping[str, Any],
    capability_policy_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay B3-2 validation and verify the deterministic B3-3 evidence record."""

    reasons: list[str] = []
    replay_validation = validate_capability_policy_contract(dict(capability_policy_contract))
    expected_record = build_capability_policy_evidence_record(
        capability_policy_contract,
        replay_validation,
    )

    if not isinstance(evidence_record, Mapping):
        reasons.append("evidence record must be a mapping")
        evidence_record = {}

    unexpected_fields = sorted(set(evidence_record) - _RECORD_FIELDS)
    for field in unexpected_fields:
        reasons.append(f"unexpected evidence record field: {field}")

    _compare_field(reasons, evidence_record, expected_record, "record_kind")
    _compare_field(reasons, evidence_record, expected_record, "record_version")
    _compare_field(reasons, evidence_record, expected_record, "claim_type")
    _compare_field(reasons, evidence_record, expected_record, "capability_policy_digest")
    _compare_field(reasons, evidence_record, expected_record, "policy_validation_outcome")
    _compare_field(reasons, evidence_record, expected_record, "capability_fields_summary")
    _compare_field(reasons, evidence_record, expected_record, "rejected_overclaim_candidates")
    _compare_field(reasons, evidence_record, expected_record, "authority_snapshot")
    _compare_field(reasons, evidence_record, expected_record, "boundary_preservation")
    _compare_field(reasons, evidence_record, expected_record, "non_claim_caveats")
    _compare_field(reasons, evidence_record, expected_record, "source_contract_module_version_note")

    supplied_evidence_digest = evidence_record.get("deterministic_evidence_digest")
    recomputed_evidence_digest = capability_policy_evidence_digest(evidence_record)
    if supplied_evidence_digest != recomputed_evidence_digest:
        reasons.append("deterministic evidence digest mismatch")
    if supplied_evidence_digest != expected_record["deterministic_evidence_digest"]:
        reasons.append("expected evidence digest mismatch")

    if evidence_record.get("authority_snapshot") != AUTHORITY_SNAPSHOT:
        reasons.append("authority snapshot mismatch")

    if not replay_validation.get("valid"):
        for reason in replay_validation.get("reasons", []):
            reasons.append(f"policy replay rejected: {reason}")

    reasons.extend(_direct_capability_overclaim_rejections(capability_policy_contract))
    reasons.extend(_recursive_overclaim_rejections(capability_policy_contract))
    reasons.extend(_recursive_overclaim_rejections(evidence_record))
    reasons = _unique(reasons)

    accepted = not reasons
    return {
        "accepted": accepted,
        "status": VERIFY_REPLAY_ACCEPTED if accepted else VERIFY_REPLAY_REJECTED,
        "rejection_reasons": reasons,
        "replay_validation_outcome": _validation_outcome(replay_validation),
        "verification_scope": "deterministic_policy_evidence_replay_only",
        "is_runtime_enforcement": False,
        "is_tool_execution_gate": False,
        "safe_default": SAFE_DEFAULT,
    }


def capability_policy_digest(capability_policy_contract: Mapping[str, Any]) -> str:
    """Return the deterministic digest for the normalized capability policy input."""

    return _sha256_json(_normalized_policy_contract(capability_policy_contract))


def capability_policy_evidence_digest(evidence_record: Mapping[str, Any]) -> str:
    """Return the deterministic digest for an evidence record payload."""

    payload = dict(evidence_record)
    payload.pop("deterministic_evidence_digest", None)
    return _sha256_json(payload)


def capability_fields_summary(capability_policy_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize capability policy fields that must replay exactly."""

    capability_map, extras = _capability_map(capability_policy_contract.get("capabilities"))
    summary: dict[str, Any] = {}
    for capability_name in CAPABILITY_FIELDS:
        policy = capability_map.get(capability_name)
        if policy is None:
            summary[capability_name] = None
        else:
            summary[capability_name] = {
                field: policy.get(field)
                for field in CAPABILITY_SUMMARY_FIELDS
            }
    if extras:
        summary["__extra_capability_names__"] = extras
    return summary


def _validation_outcome(validation_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "valid": validation_result.get("valid"),
        "status": validation_result.get("status"),
        "reasons": list(validation_result.get("reasons", [])),
        "overclaim_candidates": sorted(validation_result.get("overclaim_candidates", [])),
        "is_runtime_enforcement": validation_result.get("is_runtime_enforcement"),
        "is_tool_execution_gate": validation_result.get("is_tool_execution_gate"),
        "safe_default": validation_result.get("safe_default"),
    }


def _rejected_overclaim_candidates(
    capability_policy_contract: Mapping[str, Any],
    validation_result: Mapping[str, Any],
) -> list[str]:
    candidates = set(validation_result.get("overclaim_candidates", []))
    candidates.update(_direct_capability_overclaim_rejections(capability_policy_contract))
    candidates.update(_recursive_overclaim_rejections(capability_policy_contract))
    return sorted(candidates)


def _normalized_policy_contract(capability_policy_contract: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(capability_policy_contract))
    capability_map, extras = _capability_map(normalized.get("capabilities"))
    normalized["capabilities"] = {
        capability_name: capability_map[capability_name]
        for capability_name in sorted(capability_map)
    }
    if extras:
        normalized["capability_summary_extras"] = extras
    return normalized


def _capability_map(value: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if isinstance(value, Mapping):
        items = list(value.values())
    elif isinstance(value, list):
        items = value
    else:
        return {}, []

    capability_map: dict[str, dict[str, Any]] = {}
    extras: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            extras.append(f"non_mapping_{index}")
            continue
        policy = dict(item)
        capability_name = policy.get("capability_name")
        if isinstance(capability_name, str):
            capability_map[capability_name] = policy
            if capability_name not in CAPABILITY_FIELDS:
                extras.append(capability_name)
        else:
            extras.append(f"missing_name_{index}")
    return capability_map, sorted(extras)


def _direct_capability_overclaim_rejections(capability_policy_contract: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    capability_map, _ = _capability_map(capability_policy_contract.get("capabilities"))
    for capability_name, policy in sorted(capability_map.items()):
        granted = policy.get("granted")
        grant_source = policy.get("grant_source")
        check_status = policy.get("check_status")
        claim_status = policy.get("claim_status")
        evidence_ref = policy.get("evidence_ref")

        if granted is True and not evidence_ref:
            reasons.append(f"{capability_name} granted=true missing evidence rejected")
        if granted is True and grant_source in (GRANT_SOURCE_UNKNOWN, None, ""):
            reasons.append(f"{capability_name} granted=true unknown source rejected")
        if grant_source == REPORTED_ONLY and _passlike(claim_status):
            reasons.append(f"{capability_name} reported_only PASS-like claim rejected")
        if check_status in UNVERIFIED_CHECK_STATUSES and _passlike(claim_status):
            reasons.append(f"{capability_name} unchecked PASS-like claim rejected")
        if granted is True and grant_source == REPORTED_ONLY:
            reasons.append(f"{capability_name} reported_only grant claim rejected")
        if granted is True and check_status in UNVERIFIED_CHECK_STATUSES:
            reasons.append(f"{capability_name} unchecked grant claim rejected")
    return reasons


def _recursive_overclaim_rejections(value: Any) -> list[str]:
    reasons: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _OVERCLAIM_FLAG_REJECTIONS and child is True:
                reasons.append(_OVERCLAIM_FLAG_REJECTIONS[key])
            if key in ("runtime_enforcement", "tool_execution_gating") and child is True:
                reasons.append("runtime enforcement or tool gating claim rejected")
            reasons.extend(_recursive_overclaim_rejections(child))
    elif isinstance(value, list):
        for child in value:
            reasons.extend(_recursive_overclaim_rejections(child))
    return reasons


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _compare_field(
    reasons: list[str],
    supplied: Mapping[str, Any],
    expected: Mapping[str, Any],
    field: str,
) -> None:
    if supplied.get(field) != expected.get(field):
        reasons.append(f"{field} mismatch")


def _passlike(value: Any) -> bool:
    return isinstance(value, str) and value.upper() in PASSLIKE_CLAIMS


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "AUTHORITY_SNAPSHOT",
    "B3_CAPABILITY_POLICY_EVIDENCE_KIND",
    "B3_CAPABILITY_POLICY_EVIDENCE_VERSION",
    "NON_CLAIM_CAVEATS",
    "VERIFY_REPLAY_ACCEPTED",
    "VERIFY_REPLAY_REJECTED",
    "build_capability_policy_evidence_record",
    "capability_fields_summary",
    "capability_policy_digest",
    "capability_policy_evidence_digest",
    "verify_capability_policy_evidence_record",
]
