"""B2-4 evidence binding and verify replay for B2-3 routing results.

This module binds the fixture-only B2-3 executor-like ingress harness result to
a deterministic B2-level evidence record. Verify replay rejects mismatch,
tamper, and overclaim fields. It does not prove an external oracle, wire the
executor write path, grant runtime write authority, or start Phase 11-A/B3.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B2_AEG_PROTECTED_TARGET_ROUTED,
    B2_EXECUTOR_WRITE_ROUTER,
    B2_NO_MUTATION_OBSERVATION_BOUND,
    B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST,
    B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    B2_ROUTED_DENIAL,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_TAMPER_PROOF,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence.b1_aeg_integrity_verify import verify_b1_aeg_guard_evidence_record
from src.evidence.b2_executor_like_ingress_harness import (
    B2_EXECUTOR_LIKE_INGRESS_HARNESS_COMPONENT,
    B2_EXECUTOR_LIKE_INGRESS_HARNESS_VERSION,
    B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
    B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
    B3_NOT_STARTED,
)
from src.evidence.b2_executor_write_router import B2_EXECUTOR_WRITE_ROUTING_VERSION

B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION = (
    "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REPLAY_V0"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT = "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE"
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD = "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD"
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST = "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST"
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT = (
    "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED = (
    "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION = (
    "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND = (
    "B2_4_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_ONLY_SCOPE = (
    "B2_4_VERIFY_REPLAY_MISMATCH_REJECTION_ONLY"
)
B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_NOT_EXTERNAL_ORACLE = (
    "B2_4_VERIFY_REPLAY_NOT_EXTERNAL_ORACLE"
)
B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED = (
    "B2_4_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED"
)
B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED = "B2_4_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED"
B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED = (
    "B2_4_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED"
)
B2_ROUTING_FIELD_MISMATCH_REJECTED = "B2_4_ROUTING_FIELD_MISMATCH_REJECTED"
B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED = "B2_4_ROUTING_NO_MUTATION_MISMATCH_REJECTED"
B2_ROUTING_B1_REPLAY_REJECTED = "B2_4_ROUTING_B1_REPLAY_REJECTED"
B2_ROUTING_OVERCLAIM_REJECTED = "B2_4_ROUTING_OVERCLAIM_REJECTED"

_HARNESS_PAYLOAD_FIELDS = (
    "component",
    "version",
    "ingress",
    "router_request",
    "router_result",
    "router_called",
    "fixture_only",
    "production_runtime_wiring_added",
    "production_adapter_added",
    "live_executor_invoked",
    "external_runtime_invoked",
    "command_runner_invoked",
    "broad_write_capability_granted",
    "raw_capability_granted",
    "runtime_write_authority_granted",
    "no_mutation_observed",
    "runtime_write_path_status",
    "live_executor_authority_status",
    "phase11a_status",
    "b2_status",
    "b3_status",
)

_ROUTE_PAYLOAD_FIELDS = (
    "component",
    "version",
    "request",
    "routing_status",
    "routing_decision",
    "route_target",
    "guard_decision",
    "mediator_request",
    "mediator_decision",
    "no_mutation_observation",
    "guard_evidence_record",
    "b1_guard_reused",
    "b1_evidence_binding_reused",
    "b1_known_gap_baseline_status",
    "raw_direct_path_status",
    "no_mutation_status",
    "runtime_write_path_status",
    "live_executor_authority_status",
    "phase11a_status",
    "os_enforcement_status",
    "filesystem_enforcement_status",
    "live_executor_authority_granted",
    "runtime_write_authority_granted",
    "raw_direct_write_success_claimed",
    "write_performed",
    "filesystem_mutation_performed",
    "executor_write_path_wired",
)

_EVIDENCE_PAYLOAD_FIELDS = (
    "binding_version",
    "component",
    "record_type",
    "binding_status",
    "digest_status",
    "source",
    "fixture_only",
    "ingress_id",
    "harness_id",
    "harness_digest",
    "harness_record_digest",
    "route_id",
    "route_digest",
    "submitted_path",
    "resolved_target",
    "routing_status",
    "routing_decision",
    "route_target",
    "target_class",
    "denial_reason",
    "no_mutation_observed",
    "no_mutation_status",
    "guard_evidence_record_digest",
    "b1_known_gap_baseline_status",
    "raw_direct_path_status",
    "runtime_write_path_status",
    "live_executor_authority_status",
    "phase11a_status",
    "b2_status",
    "b3_status",
    "executor_write_path_wired",
    "runtime_write_authority_granted",
    "live_executor_authority_granted",
    "production_runtime_wiring_added",
    "live_executor_invoked",
    "harness_result",
)

_EXPECTED_EVIDENCE_FIELDS = {
    "binding_version": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION,
    "component": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT,
    "record_type": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD,
    "binding_status": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND,
    "digest_status": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST,
    "source": B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
    "fixture_only": True,
    "routing_status": B2_AEG_PROTECTED_TARGET_ROUTED,
    "routing_decision": B2_ROUTED_DENIAL,
    "route_target": B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    "no_mutation_observed": True,
    "no_mutation_status": B2_NO_MUTATION_OBSERVATION_BOUND,
    "b1_known_gap_baseline_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    "raw_direct_path_status": WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "b2_status": B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
    "b3_status": B3_NOT_STARTED,
    "executor_write_path_wired": False,
    "runtime_write_authority_granted": False,
    "live_executor_authority_granted": False,
    "production_runtime_wiring_added": False,
    "live_executor_invoked": False,
}

_EXPECTED_HARNESS_FIELDS = {
    "component": B2_EXECUTOR_LIKE_INGRESS_HARNESS_COMPONENT,
    "version": B2_EXECUTOR_LIKE_INGRESS_HARNESS_VERSION,
    "router_called": True,
    "fixture_only": True,
    "production_runtime_wiring_added": False,
    "production_adapter_added": False,
    "live_executor_invoked": False,
    "external_runtime_invoked": False,
    "command_runner_invoked": False,
    "broad_write_capability_granted": False,
    "raw_capability_granted": False,
    "runtime_write_authority_granted": False,
    "no_mutation_observed": True,
    "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "b2_status": B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
    "b3_status": B3_NOT_STARTED,
}

_EXPECTED_ROUTE_FIELDS = {
    "component": B2_EXECUTOR_WRITE_ROUTER,
    "version": B2_EXECUTOR_WRITE_ROUTING_VERSION,
    "routing_status": B2_AEG_PROTECTED_TARGET_ROUTED,
    "routing_decision": B2_ROUTED_DENIAL,
    "route_target": B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    "b1_guard_reused": True,
    "b1_evidence_binding_reused": True,
    "b1_known_gap_baseline_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    "raw_direct_path_status": WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    "no_mutation_status": B2_NO_MUTATION_OBSERVATION_BOUND,
    "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
    "os_enforcement_status": NOT_OS_ENFORCED,
    "filesystem_enforcement_status": NOT_FILESYSTEM_ENFORCED,
    "live_executor_authority_granted": False,
    "runtime_write_authority_granted": False,
    "raw_direct_write_success_claimed": False,
    "write_performed": False,
    "filesystem_mutation_performed": False,
    "executor_write_path_wired": False,
}

_EXPECTED_NO_MUTATION_FIELDS = {
    "write_performed": False,
    "filesystem_mutation_performed": False,
    "mutation_observed": False,
    "no_mutation_observed": True,
    "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_status": PHASE11A_NOT_STARTED,
}

_OVERCLAIM_LABELS = frozenset(
    (
        "B2_" + "COMPLETE",
        "B2_" + "WIRED",
        "WRITE_PATH_" + "WIRED",
        "EXECUTOR_WRITE_PATH_" + "WIRED",
        "LIVE_EXECUTOR_AUTHORITY_" + "GRANTED",
        "RUNTIME_WRITE_AUTHORITY_" + "GRANTED",
        "PHASE11A_" + "STARTED",
        "B3_" + "STARTED",
        "PRODUCTION_RUNTIME_WIRING_" + "ADDED",
    )
)
_OVERCLAIM_TRUE_FIELDS = frozenset(
    (
        "executor_write_path_wired",
        "runtime_write_authority_granted",
        "live_executor_authority_granted",
        "production_runtime_wiring_added",
        "production_adapter_added",
        "live_executor_invoked",
        "external_runtime_invoked",
        "command_runner_invoked",
        "broad_write_capability_granted",
        "raw_capability_granted",
        "write_performed",
        "filesystem_mutation_performed",
        "mutation_observed",
        "raw_direct_write_success_claimed",
        "b2_closure_claimed",
        "runtime_authority_claimed",
    )
)


@dataclass(frozen=True)
class B2ExecutorLikeRoutingEvidenceRecord:
    """Canonical B2 evidence record bound to a B2-3 harness result."""

    record_id: str
    evidence_record_digest: str
    binding_version: str
    component: str
    record_type: str
    binding_status: str
    digest_status: str
    source: str
    fixture_only: bool
    ingress_id: str
    harness_id: str
    harness_digest: str
    harness_record_digest: str
    route_id: str
    route_digest: str
    submitted_path: str
    resolved_target: str
    routing_status: str
    routing_decision: str
    route_target: str
    target_class: str
    denial_reason: str
    no_mutation_observed: bool
    no_mutation_status: str
    guard_evidence_record_digest: str
    b1_known_gap_baseline_status: str
    raw_direct_path_status: str
    runtime_write_path_status: str
    live_executor_authority_status: str
    phase11a_status: str
    b2_status: str
    b3_status: str
    executor_write_path_wired: bool
    runtime_write_authority_granted: bool
    live_executor_authority_granted: bool
    production_runtime_wiring_added: bool
    live_executor_invoked: bool
    harness_result: Mapping[str, Any]

    def to_record(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "evidence_record_digest": self.evidence_record_digest,
            **_evidence_payload(self),
        }


@dataclass(frozen=True)
class B2ExecutorLikeRoutingEvidenceVerifyResult:
    """Result of verify-only replay for B2-4 routing evidence."""

    component: str
    version: str
    status: str
    consistent: bool
    replay_status: str
    rejection_codes: tuple[str, ...]
    checks: tuple[str, ...]
    scope_status: str = B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_ONLY_SCOPE
    external_oracle_status: str = B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_NOT_EXTERNAL_ORACLE
    tamper_proof_status: str = NOT_TAMPER_PROOF
    external_anchor_status: str = NOT_EXTERNAL_ANCHORED
    runtime_write_path_status: str = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
    os_enforcement_status: str = NOT_OS_ENFORCED
    filesystem_enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    phase11a_status: str = PHASE11A_NOT_STARTED


def build_b2_executor_like_routing_evidence_record(
    *,
    harness_result: Mapping[str, Any] | Any,
) -> B2ExecutorLikeRoutingEvidenceRecord:
    """Bind a B2-3 fixture-only routed denial result to B2-level evidence."""

    harness = _coerce_record(harness_result)
    route = _require_mapping(harness.get("router_result"), "router_result")
    ingress = _require_mapping(harness.get("ingress"), "ingress")
    guard_decision = _require_mapping(route.get("guard_decision"), "guard_decision")
    guard_evidence = _require_mapping(route.get("guard_evidence_record"), "guard_evidence_record")
    observation = _require_mapping(route.get("no_mutation_observation"), "no_mutation_observation")

    payload = {
        "binding_version": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION,
        "component": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT,
        "record_type": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD,
        "binding_status": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND,
        "digest_status": B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST,
        "source": ingress.get("source"),
        "fixture_only": harness.get("fixture_only"),
        "ingress_id": ingress.get("ingress_id"),
        "harness_id": harness.get("harness_id"),
        "harness_digest": harness.get("harness_digest"),
        "harness_record_digest": _harness_record_digest(harness),
        "route_id": route.get("route_id"),
        "route_digest": route.get("route_digest"),
        "submitted_path": ingress.get("submitted_path"),
        "resolved_target": guard_decision.get("resolved_path"),
        "routing_status": route.get("routing_status"),
        "routing_decision": route.get("routing_decision"),
        "route_target": route.get("route_target"),
        "target_class": guard_decision.get("target_class"),
        "denial_reason": guard_decision.get("denial_reason"),
        "no_mutation_observed": observation.get("no_mutation_observed"),
        "no_mutation_status": route.get("no_mutation_status"),
        "guard_evidence_record_digest": guard_evidence.get("evidence_record_digest"),
        "b1_known_gap_baseline_status": route.get("b1_known_gap_baseline_status"),
        "raw_direct_path_status": route.get("raw_direct_path_status"),
        "runtime_write_path_status": route.get("runtime_write_path_status"),
        "live_executor_authority_status": route.get("live_executor_authority_status"),
        "phase11a_status": route.get("phase11a_status"),
        "b2_status": harness.get("b2_status"),
        "b3_status": harness.get("b3_status"),
        "executor_write_path_wired": route.get("executor_write_path_wired"),
        "runtime_write_authority_granted": route.get("runtime_write_authority_granted"),
        "live_executor_authority_granted": route.get("live_executor_authority_granted"),
        "production_runtime_wiring_added": harness.get("production_runtime_wiring_added"),
        "live_executor_invoked": harness.get("live_executor_invoked"),
        "harness_result": harness,
    }
    evidence_record_digest = _sha256_json(payload)
    return B2ExecutorLikeRoutingEvidenceRecord(
        record_id=f"b2-4-executor-like-routing-evidence:{evidence_record_digest}",
        evidence_record_digest=evidence_record_digest,
        **payload,
    )


def verify_b2_executor_like_routing_evidence_record(
    record: Mapping[str, Any] | Any,
) -> B2ExecutorLikeRoutingEvidenceVerifyResult:
    """Replay B2-4 evidence and reject mismatch, tamper, and overclaim fields."""

    evidence = _coerce_record(record)
    rejections: list[str] = []
    checks: list[str] = []

    harness = evidence.get("harness_result")
    if not isinstance(harness, Mapping):
        _reject(rejections, B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED)
        checks.append("harness_result missing or not a mapping")
        harness = {}

    _verify_evidence_record_digest(evidence, rejections, checks)
    _verify_harness_digest(harness, evidence, rejections, checks)
    _verify_route_digest(harness, rejections, checks)
    _verify_b1_replay(harness, rejections, checks)
    _verify_bound_fields(evidence, harness, rejections, checks)
    _verify_expected_scope_fields(evidence, harness, rejections, checks)
    _verify_no_mutation(harness, rejections, checks)
    _verify_overclaims(evidence, rejections, checks)

    rejection_codes = tuple(dict.fromkeys(rejections))
    consistent = not rejection_codes
    status = (
        B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT
        if consistent
        else B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED
    )
    if consistent:
        checks.append("B2-3 fixture-only routed denial replay matched")
        checks.append("B2-4 evidence binding remains mismatch-rejection only")
        checks.append("B2 remains open; B2-5 status note remains separate")
        checks.append("live executor authority remains on hold")
        checks.append("B3 remains not started")

    return B2ExecutorLikeRoutingEvidenceVerifyResult(
        component=B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION,
        version=B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION,
        status=status,
        consistent=consistent,
        replay_status=status,
        rejection_codes=rejection_codes,
        checks=tuple(checks),
    )


def b2_executor_like_routing_evidence_digest_from_mapping(record: Mapping[str, Any]) -> str:
    """Return the B2-4 canonical payload digest for a mapping record."""

    return _sha256_json(_evidence_payload(record))


def _verify_evidence_record_digest(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    expected_digest = b2_executor_like_routing_evidence_digest_from_mapping(evidence)
    expected_record_id = f"b2-4-executor-like-routing-evidence:{expected_digest}"
    if (
        evidence.get("evidence_record_digest") == expected_digest
        and evidence.get("record_id") == expected_record_id
    ):
        checks.append("B2-4 evidence record digest replay matched")
        return

    _reject(rejections, B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED)
    checks.append("B2-4 evidence record digest or record id mismatch rejected")


def _verify_harness_digest(
    harness: Mapping[str, Any],
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    expected_digest = _harness_payload_digest(harness)
    expected_record_digest = _harness_record_digest(harness)
    expected_harness_id = f"b2-3-executor-like-ingress-harness:{expected_digest}"
    if (
        harness.get("harness_digest") == expected_digest
        and harness.get("harness_id") == expected_harness_id
        and evidence.get("harness_digest") == expected_digest
        and evidence.get("harness_record_digest") == expected_record_digest
    ):
        checks.append("B2-3 harness digest replay matched")
        return

    _reject(rejections, B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED)
    checks.append("B2-3 harness digest mismatch rejected")


def _verify_route_digest(
    harness: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    route = harness.get("router_result")
    if not isinstance(route, Mapping):
        _reject(rejections, B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED)
        checks.append("router_result missing or not a mapping")
        return

    expected_digest = _sha256_json({field: route.get(field) for field in _ROUTE_PAYLOAD_FIELDS})
    expected_route_id = f"b2-executor-write-route:{expected_digest}"
    if route.get("route_digest") == expected_digest and route.get("route_id") == expected_route_id:
        checks.append("B2 routed result digest replay matched")
        return

    _reject(rejections, B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED)
    checks.append("B2 routed result digest mismatch rejected")


def _verify_b1_replay(
    harness: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    route = harness.get("router_result")
    guard_evidence = route.get("guard_evidence_record") if isinstance(route, Mapping) else None
    if not isinstance(guard_evidence, Mapping):
        _reject(rejections, B2_ROUTING_B1_REPLAY_REJECTED)
        checks.append("B1-C guard evidence record missing or not a mapping")
        return

    result = verify_b1_aeg_guard_evidence_record(guard_evidence)
    if result.consistent:
        checks.append("embedded B1-C/B1-D guard evidence replay matched")
        return

    _reject(rejections, B2_ROUTING_B1_REPLAY_REJECTED)
    checks.append("embedded B1-C/B1-D guard evidence replay rejected")


def _verify_bound_fields(
    evidence: Mapping[str, Any],
    harness: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    ingress = harness.get("ingress")
    route = harness.get("router_result")
    if not isinstance(ingress, Mapping) or not isinstance(route, Mapping):
        _reject(rejections, B2_ROUTING_FIELD_MISMATCH_REJECTED)
        checks.append("ingress or router_result missing for bound field replay")
        return

    guard_decision = route.get("guard_decision")
    observation = route.get("no_mutation_observation")
    guard_evidence = route.get("guard_evidence_record")
    mismatches: list[str] = []

    _compare(evidence, "source", ingress.get("source"), mismatches)
    _compare(evidence, "ingress_id", ingress.get("ingress_id"), mismatches)
    _compare(evidence, "harness_id", harness.get("harness_id"), mismatches)
    _compare(evidence, "harness_digest", harness.get("harness_digest"), mismatches)
    _compare(evidence, "route_id", route.get("route_id"), mismatches)
    _compare(evidence, "route_digest", route.get("route_digest"), mismatches)
    _compare(evidence, "submitted_path", ingress.get("submitted_path"), mismatches)

    if isinstance(guard_decision, Mapping):
        _compare(evidence, "resolved_target", guard_decision.get("resolved_path"), mismatches)
        _compare(evidence, "target_class", guard_decision.get("target_class"), mismatches)
        _compare(evidence, "denial_reason", guard_decision.get("denial_reason"), mismatches)
    else:
        mismatches.append("guard_decision missing")

    if isinstance(observation, Mapping):
        _compare(evidence, "no_mutation_observed", observation.get("no_mutation_observed"), mismatches)
    else:
        mismatches.append("no_mutation_observation missing")

    if isinstance(guard_evidence, Mapping):
        _compare(
            evidence,
            "guard_evidence_record_digest",
            guard_evidence.get("evidence_record_digest"),
            mismatches,
        )
    else:
        mismatches.append("guard_evidence_record missing")

    if mismatches:
        _reject(rejections, B2_ROUTING_FIELD_MISMATCH_REJECTED)
        checks.append("B2 routing evidence bound field mismatch rejected: " + ", ".join(mismatches))
    else:
        checks.append("B2 routing evidence bound fields replay matched")


def _verify_expected_scope_fields(
    evidence: Mapping[str, Any],
    harness: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    mismatches: list[str] = []

    for field, expected in _EXPECTED_EVIDENCE_FIELDS.items():
        if evidence.get(field) != expected:
            mismatches.append(f"evidence.{field}")

    for field, expected in _EXPECTED_HARNESS_FIELDS.items():
        if harness.get(field) != expected:
            mismatches.append(f"harness_result.{field}")

    ingress = harness.get("ingress")
    if isinstance(ingress, Mapping):
        if ingress.get("source") != B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE:
            mismatches.append("harness_result.ingress.source")
        if ingress.get("router_request_model") != B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST:
            mismatches.append("harness_result.ingress.router_request_model")
        if ingress.get("live_executor_request") is not False:
            mismatches.append("harness_result.ingress.live_executor_request")
        if ingress.get("production_runtime_ingress") is not False:
            mismatches.append("harness_result.ingress.production_runtime_ingress")
        if ingress.get("live_executor_authority_granted") is not False:
            mismatches.append("harness_result.ingress.live_executor_authority_granted")
    else:
        mismatches.append("harness_result.ingress")

    route = harness.get("router_result")
    if isinstance(route, Mapping):
        for field, expected in _EXPECTED_ROUTE_FIELDS.items():
            if route.get(field) != expected:
                mismatches.append(f"harness_result.router_result.{field}")

        request = route.get("request")
        if isinstance(request, Mapping):
            if request.get("request_model") != B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST:
                mismatches.append("harness_result.router_result.request.request_model")
            if request.get("live_executor_authority_granted") is not False:
                mismatches.append("harness_result.router_result.request.live_executor_authority_granted")
            if request.get("write_performed") is not False:
                mismatches.append("harness_result.router_result.request.write_performed")
        else:
            mismatches.append("harness_result.router_result.request")

        mediator_decision = route.get("mediator_decision")
        if isinstance(mediator_decision, Mapping):
            if mediator_decision.get("decision_status") != MEDIATOR_DECISION_DENY:
                mismatches.append("harness_result.router_result.mediator_decision.decision_status")
        else:
            mismatches.append("harness_result.router_result.mediator_decision")
    else:
        mismatches.append("harness_result.router_result")

    if mismatches:
        _reject(rejections, B2_ROUTING_FIELD_MISMATCH_REJECTED)
        checks.append("B2-4 fixture-only routing scope mismatch rejected: " + ", ".join(mismatches))
    else:
        checks.append("B2-4 fixture-only routing scope fields replay matched")


def _verify_no_mutation(
    harness: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    route = harness.get("router_result")
    observation = route.get("no_mutation_observation") if isinstance(route, Mapping) else None
    if not isinstance(route, Mapping) or not isinstance(observation, Mapping):
        _reject(rejections, B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED)
        checks.append("no-mutation routing records missing or not mappings")
        return

    mismatches: list[str] = []
    for field, expected in _EXPECTED_NO_MUTATION_FIELDS.items():
        if observation.get(field) != expected:
            mismatches.append(f"no_mutation_observation.{field}")

    for field in ("write_performed", "filesystem_mutation_performed", "raw_direct_write_success_claimed"):
        if route.get(field) is not False:
            mismatches.append(f"router_result.{field}")

    if harness.get("no_mutation_observed") is not True:
        mismatches.append("harness_result.no_mutation_observed")

    if mismatches:
        _reject(rejections, B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED)
        checks.append("B2 no-mutation observation mismatch rejected: " + ", ".join(mismatches))
    else:
        checks.append("B2 routed denial/no-mutation replay matched")


def _verify_overclaims(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    overclaims: list[str] = []

    for path, value in _walk_values(evidence):
        if isinstance(value, str) and value in _OVERCLAIM_LABELS:
            overclaims.append(path)
        if path.rsplit(".", 1)[-1] in _OVERCLAIM_TRUE_FIELDS and value is True:
            overclaims.append(path)

    if overclaims:
        _reject(rejections, B2_ROUTING_OVERCLAIM_REJECTED)
        checks.append("B2 routing overclaim rejected at " + ", ".join(sorted(overclaims)))
    else:
        checks.append("no B2 closure, write-path wiring, live authority, Phase 11-A, or B3 overclaim found")


def _evidence_payload(record: Mapping[str, Any] | B2ExecutorLikeRoutingEvidenceRecord) -> dict[str, Any]:
    if isinstance(record, B2ExecutorLikeRoutingEvidenceRecord):
        return {
            "binding_version": record.binding_version,
            "component": record.component,
            "record_type": record.record_type,
            "binding_status": record.binding_status,
            "digest_status": record.digest_status,
            "source": record.source,
            "fixture_only": record.fixture_only,
            "ingress_id": record.ingress_id,
            "harness_id": record.harness_id,
            "harness_digest": record.harness_digest,
            "harness_record_digest": record.harness_record_digest,
            "route_id": record.route_id,
            "route_digest": record.route_digest,
            "submitted_path": record.submitted_path,
            "resolved_target": record.resolved_target,
            "routing_status": record.routing_status,
            "routing_decision": record.routing_decision,
            "route_target": record.route_target,
            "target_class": record.target_class,
            "denial_reason": record.denial_reason,
            "no_mutation_observed": record.no_mutation_observed,
            "no_mutation_status": record.no_mutation_status,
            "guard_evidence_record_digest": record.guard_evidence_record_digest,
            "b1_known_gap_baseline_status": record.b1_known_gap_baseline_status,
            "raw_direct_path_status": record.raw_direct_path_status,
            "runtime_write_path_status": record.runtime_write_path_status,
            "live_executor_authority_status": record.live_executor_authority_status,
            "phase11a_status": record.phase11a_status,
            "b2_status": record.b2_status,
            "b3_status": record.b3_status,
            "executor_write_path_wired": record.executor_write_path_wired,
            "runtime_write_authority_granted": record.runtime_write_authority_granted,
            "live_executor_authority_granted": record.live_executor_authority_granted,
            "production_runtime_wiring_added": record.production_runtime_wiring_added,
            "live_executor_invoked": record.live_executor_invoked,
            "harness_result": dict(record.harness_result),
        }
    return {field: record.get(field) for field in _EVIDENCE_PAYLOAD_FIELDS}


def _harness_payload_digest(harness: Mapping[str, Any]) -> str:
    return _sha256_json({field: harness.get(field) for field in _HARNESS_PAYLOAD_FIELDS})


def _harness_record_digest(harness: Mapping[str, Any]) -> str:
    return _sha256_json(
        {
            "harness_id": harness.get("harness_id"),
            "harness_digest": harness.get("harness_digest"),
            **{field: harness.get(field) for field in _HARNESS_PAYLOAD_FIELDS},
        }
    )


def _coerce_record(record: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(record, Mapping):
        return dict(record)
    if hasattr(record, "to_record"):
        return dict(record.to_record())
    raise TypeError("record must be a mapping or expose to_record()")


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise ValueError(f"{field} must be a mapping")


def _compare(evidence: Mapping[str, Any], field: str, expected: Any, mismatches: list[str]) -> None:
    if evidence.get(field) != expected:
        mismatches.append(field)


def _walk_values(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(payload, Mapping):
        values: list[tuple[str, Any]] = []
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            values.extend(_walk_values(value, path))
        return values
    if isinstance(payload, list):
        values = []
        for index, value in enumerate(payload):
            values.extend(_walk_values(value, f"{prefix}[{index}]"))
        return values
    return [(prefix, payload)]


def _reject(rejections: list[str], code: str) -> None:
    if code not in rejections:
        rejections.append(code)


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_BINDING_BOUND",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_COMPONENT",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_DIGEST",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_NOT_EXTERNAL_ORACLE",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_RECORD",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_CONSISTENT",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_REPLAY_REJECTED",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_ONLY_SCOPE",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERIFY_REJECTION",
    "B2_EXECUTOR_LIKE_ROUTING_EVIDENCE_VERSION",
    "B2_ROUTING_B1_REPLAY_REJECTED",
    "B2_ROUTING_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED",
    "B2_ROUTING_FIELD_MISMATCH_REJECTED",
    "B2_ROUTING_HARNESS_DIGEST_MISMATCH_REJECTED",
    "B2_ROUTING_NO_MUTATION_MISMATCH_REJECTED",
    "B2_ROUTING_OVERCLAIM_REJECTED",
    "B2_ROUTING_ROUTE_DIGEST_MISMATCH_REJECTED",
    "B2ExecutorLikeRoutingEvidenceRecord",
    "B2ExecutorLikeRoutingEvidenceVerifyResult",
    "b2_executor_like_routing_evidence_digest_from_mapping",
    "build_b2_executor_like_routing_evidence_record",
    "verify_b2_executor_like_routing_evidence_record",
]
