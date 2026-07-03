"""Phase 11-A-2 known-gap blocked transition evidence.

This module converts the prior known-gap expected-red baseline into blocked
transition evidence only when Phase 11-A-1 pre-live routing evidence verifies.
It is replay-only evidence. It does not call save_run, activate enforcement,
grant runtime write authority, spawn processes, call providers, use the network,
or implement a live executor.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    SAFE_DEFAULT,
)
from src.evidence.phase11a_rollback_kill_path import (
    VERIFY_REPLAY_ACCEPTED as ROLLBACK_VERIFY_REPLAY_ACCEPTED,
    verify_phase11a_rollback_kill_path_evidence,
)
from src.evidence.phase11a_save_run_write_routing import (
    GUARD_DECISION_DENIED,
    PHASE11A_SAVE_RUN_WRITE_ROUTING_KIND,
    SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,
    SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE,
    VERIFY_REPLAY_ACCEPTED as SAVE_RUN_VERIFY_REPLAY_ACCEPTED,
    WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT,
    WRITE_ATTRIBUTION_EXECUTOR_ATTRIBUTED,
    WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER,
    phase11a_save_run_routing_evidence_digest,
    verify_phase11a_save_run_write_routing_evidence,
)

PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND = "phase11a_known_gap_blocked_transition_evidence"
PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION = "phase11a_known_gap_blocked_transition_v0"

PHASE11A_STEP = "11-A-2"
TRANSITION_SOURCE_PHASE = "11-A-1"
PHASE11B_STATUS_NOT_STARTED = "NOT_STARTED"

KNOWN_GAP_EXPECTED_RED_BASELINE = "KNOWN_GAP_EXPECTED_RED_BASELINE"
KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE = "KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE"
KNOWN_GAP_TRANSITION_NOT_APPLICABLE = "KNOWN_GAP_TRANSITION_NOT_APPLICABLE"
KNOWN_GAP_TRANSITION_REJECTED = "KNOWN_GAP_TRANSITION_REJECTED"
KNOWN_GAP_TRANSITION_VERIFY_REJECTED = "KNOWN_GAP_TRANSITION_VERIFY_REJECTED"
ALLOWED_KNOWN_GAP_TRANSITION_STATUSES = (
    KNOWN_GAP_EXPECTED_RED_BASELINE,
    KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE,
    KNOWN_GAP_TRANSITION_NOT_APPLICABLE,
    KNOWN_GAP_TRANSITION_REJECTED,
    KNOWN_GAP_TRANSITION_VERIFY_REJECTED,
)

TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE = "phase11a1_verified_prelive_save_run_route"

RUNTIME_WRITE_PATH_STATUS_NOT_WIRED = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
LIVE_EXECUTOR_AUTHORITY_STATUS_ON_HOLD = LIVE_EXECUTOR_AUTHORITY_ON_HOLD

VERIFY_REPLAY_ACCEPTED = "VERIFY_REPLAY_ACCEPTED"
VERIFY_REPLAY_REJECTED = "VERIFY_REPLAY_REJECTED"

ALLOWED_BLOCKED_TRANSITION_ROUTE_STATUSES = (SAVE_RUN_ROUTE_ACCEPTED_PRELIVE,)

AUTHORITY_SNAPSHOT = {
    "runtime_write_path_status": RUNTIME_WRITE_PATH_STATUS_NOT_WIRED,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_STATUS_ON_HOLD,
    "phase11a_step": PHASE11A_STEP,
    "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
    "safe_default": SAFE_DEFAULT,
}

NON_CLAIM_CAVEATS = (
    "11-A-2 records known-gap blocked transition evidence only",
    "blocked transition is derived from verified 11-A-1 pre-live route evidence",
    "no actual runtime write is performed",
    "no actual enforcement is activated",
    "no live executor authority is granted",
    "no runtime write authority is granted",
    "no provider model network authority is granted",
    "no raw shell write_file run_command or process_spawn authority is granted",
    "Phase 11-B remains not started",
    "11-A-0 fallback evidence remains preserved",
    "11-A-1 deterministic attribution remains preserved",
)

_EVIDENCE_FIELDS = frozenset(
    {
        "record_kind",
        "record_version",
        "claim_type",
        "phase11a_step",
        "prior_known_gap_status",
        "prior_known_gap_contract_status",
        "known_gap_transition_status",
        "transition_basis",
        "transition_source_phase",
        "save_run_route_evidence_kind",
        "save_run_route_evidence_digest",
        "save_run_route_evidence_verified",
        "save_run_route_verify_status",
        "deterministic_attribution_verified",
        "self_reported_attribution_rejected",
        "trusted_runtime_self_claim_rejected",
        "request_source_spoof_rejected",
        "mediator_actor_mismatch_rejected",
        "route_target_verified",
        "guard_decision_verified",
        "route_status_verified",
        "fallback_preserved",
        "runtime_write_path_status",
        "live_executor_authority",
        "phase11b_status",
        "safe_default",
        "actual_runtime_write_performed",
        "actual_enforcement_activated",
        "live_executor_implemented",
        "tool_authority_granted",
        "provider_model_network_authority_granted",
        "authority_snapshot",
        "source_route_verify",
        "transition_rejection_reasons",
        "non_claim_caveats",
        "deterministic_evidence_digest",
    }
)

_OVERCLAIM_KEYS = {
    "runtime_write_authority_granted": "runtime write authority grant claim rejected",
    "live_executor_authority_granted": "live executor authority grant claim rejected",
    "phase11b_started": "Phase 11-B start claim rejected",
    "actual_enforcement_active": "actual enforcement activation claim rejected",
    "actual_runtime_write_performed": "actual runtime write claim rejected",
    "save_run_write_path_wired": "save_run write path wiring claim rejected",
    "executor_write_path_wired": "runtime write path wiring claim rejected",
    "provider_authority_granted": "provider authority grant claim rejected",
    "model_authority_granted": "model authority grant claim rejected",
    "network_authority_granted": "network authority grant claim rejected",
    "raw_shell_authority_granted": "raw shell authority grant claim rejected",
    "command_runner_authority_granted": "command runner authority grant claim rejected",
    "write_file_authority_granted": "write_file authority grant claim rejected",
    "process_spawn_authority_granted": "process_spawn authority grant claim rejected",
}


def build_phase11a_known_gap_blocked_transition_evidence(
    *,
    prior_known_gap_status: str,
    save_run_route_evidence: Mapping[str, Any],
    save_run_route_verify: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic 11-A-2 known-gap transition evidence."""

    route_verify = _route_verify(save_run_route_evidence, save_run_route_verify)
    rejection_reasons = _transition_rejection_reasons(
        prior_known_gap_status=prior_known_gap_status,
        save_run_route_evidence=save_run_route_evidence,
        save_run_route_verify=route_verify,
    )
    accepted = not rejection_reasons
    route_evidence = deepcopy(dict(save_run_route_evidence))
    record = {
        "record_kind": PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND,
        "record_version": PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION,
        "claim_type": "known_gap_blocked_transition_evidence_not_runtime_enforcement",
        "phase11a_step": PHASE11A_STEP,
        "prior_known_gap_status": prior_known_gap_status,
        "prior_known_gap_contract_status": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
        "known_gap_transition_status": (
            KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE if accepted else KNOWN_GAP_TRANSITION_REJECTED
        ),
        "transition_basis": TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE,
        "transition_source_phase": TRANSITION_SOURCE_PHASE,
        "save_run_route_evidence_kind": route_evidence.get("record_kind"),
        "save_run_route_evidence_digest": phase11a_save_run_routing_evidence_digest(route_evidence),
        "save_run_route_evidence_verified": _route_verify_accepted(route_verify),
        "save_run_route_verify_status": route_verify.get("status"),
        "deterministic_attribution_verified": _deterministic_attribution_verified(route_evidence),
        "self_reported_attribution_rejected": _self_reported_attribution_rejected(route_evidence),
        "trusted_runtime_self_claim_rejected": _trusted_runtime_self_claim_rejected(route_evidence),
        "request_source_spoof_rejected": _request_source_spoof_rejected(route_evidence),
        "mediator_actor_mismatch_rejected": _mediator_actor_mismatch_rejected(route_evidence),
        "route_target_verified": (
            route_evidence.get("save_run_route_target") == SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE
        ),
        "guard_decision_verified": route_evidence.get("guard_decision_status") == GUARD_DECISION_DENIED,
        "route_status_verified": (
            route_evidence.get("save_run_route_status") in ALLOWED_BLOCKED_TRANSITION_ROUTE_STATUSES
        ),
        "fallback_preserved": _fallback_preserved(route_evidence),
        "runtime_write_path_status": RUNTIME_WRITE_PATH_STATUS_NOT_WIRED,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_STATUS_ON_HOLD,
        "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
        "safe_default": SAFE_DEFAULT,
        "actual_runtime_write_performed": False,
        "actual_enforcement_activated": False,
        "live_executor_implemented": False,
        "tool_authority_granted": False,
        "provider_model_network_authority_granted": False,
        "authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "source_route_verify": _route_verify_summary(route_verify),
        "transition_rejection_reasons": rejection_reasons,
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
    }
    record["deterministic_evidence_digest"] = phase11a_known_gap_transition_evidence_digest(record)
    return record


def verify_phase11a_known_gap_blocked_transition_evidence(
    evidence_record: Mapping[str, Any],
    *,
    save_run_route_evidence: Mapping[str, Any],
    save_run_route_verify: Mapping[str, Any] | None = None,
    expected_prior_known_gap_status: str = KNOWN_GAP_EXPECTED_RED_BASELINE,
) -> dict[str, Any]:
    """Verify schema, digest binding, transition basis, and authority caveats."""

    reasons: list[str] = []
    if not isinstance(evidence_record, Mapping):
        reasons.append("evidence record must be a mapping")
        evidence_record = {}

    unexpected_fields = sorted(set(evidence_record) - _EVIDENCE_FIELDS)
    for field in unexpected_fields:
        reasons.append(f"unexpected evidence record field: {field}")

    missing_fields = sorted(_EVIDENCE_FIELDS - set(evidence_record))
    for field in missing_fields:
        reasons.append(f"missing evidence record field: {field}")

    route_verify = _route_verify(save_run_route_evidence, save_run_route_verify)
    expected_record = build_phase11a_known_gap_blocked_transition_evidence(
        prior_known_gap_status=expected_prior_known_gap_status,
        save_run_route_evidence=save_run_route_evidence,
        save_run_route_verify=route_verify,
    )

    for field in sorted(_EVIDENCE_FIELDS - {"deterministic_evidence_digest"}):
        if evidence_record.get(field) != expected_record.get(field):
            reasons.append(f"{field} mismatch")

    if evidence_record.get("prior_known_gap_status") != KNOWN_GAP_EXPECTED_RED_BASELINE:
        reasons.append("prior known-gap status mismatch")
    if evidence_record.get("known_gap_transition_status") not in ALLOWED_KNOWN_GAP_TRANSITION_STATUSES:
        reasons.append("known-gap transition status vocabulary mismatch")
    if evidence_record.get("known_gap_transition_status") != KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE:
        reasons.append("known-gap transition was not accepted")
    if evidence_record.get("transition_basis") != TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE:
        reasons.append("transition basis mismatch")
    if evidence_record.get("transition_source_phase") != TRANSITION_SOURCE_PHASE:
        reasons.append("transition source phase mismatch")

    _expect_field(reasons, evidence_record, "record_kind", PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND)
    _expect_field(reasons, evidence_record, "record_version", PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION)
    _expect_field(
        reasons,
        evidence_record,
        "claim_type",
        "known_gap_blocked_transition_evidence_not_runtime_enforcement",
    )
    _expect_field(reasons, evidence_record, "phase11a_step", PHASE11A_STEP)
    _expect_field(
        reasons,
        evidence_record,
        "prior_known_gap_contract_status",
        B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    )
    _expect_field(reasons, evidence_record, "runtime_write_path_status", RUNTIME_WRITE_PATH_STATUS_NOT_WIRED)
    _expect_field(reasons, evidence_record, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_STATUS_ON_HOLD)
    _expect_field(reasons, evidence_record, "phase11b_status", PHASE11B_STATUS_NOT_STARTED)
    _expect_field(reasons, evidence_record, "safe_default", SAFE_DEFAULT)
    _expect_field(reasons, evidence_record, "authority_snapshot", AUTHORITY_SNAPSHOT)
    _expect_field(reasons, evidence_record, "actual_runtime_write_performed", False)
    _expect_field(reasons, evidence_record, "actual_enforcement_activated", False)
    _expect_field(reasons, evidence_record, "live_executor_implemented", False)
    _expect_field(reasons, evidence_record, "tool_authority_granted", False)
    _expect_field(reasons, evidence_record, "provider_model_network_authority_granted", False)

    if evidence_record.get("save_run_route_evidence_verified") is not True:
        reasons.append("save_run route evidence verify rejected")
    if evidence_record.get("deterministic_attribution_verified") is not True:
        reasons.append("deterministic attribution missing or mismatch")
    if evidence_record.get("self_reported_attribution_rejected") is not True:
        reasons.append("self-reported attribution accepted state rejected")
    if evidence_record.get("trusted_runtime_self_claim_rejected") is not True:
        reasons.append("trusted runtime self-claim accepted state rejected")
    if evidence_record.get("request_source_spoof_rejected") is not True:
        reasons.append("request_source spoof accepted state rejected")
    if evidence_record.get("mediator_actor_mismatch_rejected") is not True:
        reasons.append("mediator actor mismatch accepted state rejected")
    if evidence_record.get("route_target_verified") is not True:
        reasons.append("route target mismatch")
    if evidence_record.get("guard_decision_verified") is not True:
        reasons.append("guard decision mismatch")
    if evidence_record.get("route_status_verified") is not True:
        reasons.append("route status mismatch")
    if evidence_record.get("fallback_preserved") is not True:
        reasons.append("fallback evidence invalid")

    reasons.extend(_transition_rejection_reasons(
        prior_known_gap_status=expected_prior_known_gap_status,
        save_run_route_evidence=save_run_route_evidence,
        save_run_route_verify=route_verify,
    ))
    reasons.extend(_recursive_overclaim_rejections(evidence_record))

    supplied_digest = evidence_record.get("deterministic_evidence_digest")
    recomputed_digest = phase11a_known_gap_transition_evidence_digest(evidence_record)
    if supplied_digest != recomputed_digest:
        reasons.append("deterministic evidence digest mismatch")
    if supplied_digest != expected_record.get("deterministic_evidence_digest"):
        reasons.append("expected evidence digest mismatch")

    reasons = _unique(reasons)
    accepted = not reasons
    return {
        "accepted": accepted,
        "status": VERIFY_REPLAY_ACCEPTED if accepted else VERIFY_REPLAY_REJECTED,
        "known_gap_transition_verify_status": (
            KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE if accepted else KNOWN_GAP_TRANSITION_VERIFY_REJECTED
        ),
        "rejection_reasons": reasons,
        "verification_scope": "phase11a_known_gap_blocked_transition_replay_only",
        "is_runtime_wiring": False,
        "is_runtime_enforcement": False,
        "safe_default": SAFE_DEFAULT,
    }


def phase11a_known_gap_transition_evidence_digest(evidence_record: Mapping[str, Any]) -> str:
    """Return the deterministic digest for the 11-A-2 evidence payload."""

    payload = deepcopy(dict(evidence_record))
    payload.pop("deterministic_evidence_digest", None)
    return _sha256_json(payload)


def _transition_rejection_reasons(
    *,
    prior_known_gap_status: str,
    save_run_route_evidence: Mapping[str, Any],
    save_run_route_verify: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []
    route_evidence = save_run_route_evidence if isinstance(save_run_route_evidence, Mapping) else {}

    if prior_known_gap_status != KNOWN_GAP_EXPECTED_RED_BASELINE:
        reasons.append("prior known-gap status mismatch")
    if not _route_verify_accepted(save_run_route_verify):
        reasons.append("save_run route evidence verify rejected")
    if not _deterministic_attribution_verified(route_evidence):
        reasons.append("deterministic attribution missing or mismatch")
    if not _self_reported_attribution_rejected(route_evidence):
        reasons.append("self-reported attribution accepted state rejected")
    if not _trusted_runtime_self_claim_rejected(route_evidence):
        reasons.append("trusted runtime self-claim accepted state rejected")
    if not _request_source_spoof_rejected(route_evidence):
        reasons.append("request_source spoof accepted state rejected")
    if not _mediator_actor_mismatch_rejected(route_evidence):
        reasons.append("mediator actor mismatch accepted state rejected")
    if route_evidence.get("save_run_route_target") != SAVE_RUN_ROUTE_TARGET_GUARD_MEDIATOR_COMPATIBLE:
        reasons.append("route target mismatch")
    if route_evidence.get("guard_decision_status") != GUARD_DECISION_DENIED:
        reasons.append("guard decision mismatch")
    if route_evidence.get("save_run_route_status") not in ALLOWED_BLOCKED_TRANSITION_ROUTE_STATUSES:
        reasons.append("route status mismatch")
    if not _fallback_preserved(route_evidence):
        reasons.append("fallback evidence invalid")
    if _fallback_candidate_success_claimed(route_evidence):
        reasons.append("candidate success accepted as 11-A-0 rollback evidence rejected")
    if route_evidence.get("runtime_write_path_status") != RUNTIME_WRITE_PATH_STATUS_NOT_WIRED:
        reasons.append("runtime write path authority grant claim rejected")
    if route_evidence.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_STATUS_ON_HOLD:
        reasons.append("live executor authority grant claim rejected")
    if route_evidence.get("phase11b_status") != PHASE11B_STATUS_NOT_STARTED:
        reasons.append("Phase 11-B start claim rejected")
    if _recursive_key_true(route_evidence, "actual_enforcement_active"):
        reasons.append("actual enforcement activation claim rejected")
    if _recursive_key_true(route_evidence, "write_performed"):
        reasons.append("actual runtime write claim rejected")
    if _mediator_decision_mismatch(route_evidence):
        reasons.append("guard decision mismatch")
    reasons.extend(_recursive_overclaim_rejections(route_evidence))
    return _unique(reasons)


def _route_verify(
    save_run_route_evidence: Mapping[str, Any],
    save_run_route_verify: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if save_run_route_verify is not None:
        return deepcopy(dict(save_run_route_verify))
    return verify_phase11a_save_run_write_routing_evidence(save_run_route_evidence)


def _route_verify_accepted(route_verify: Mapping[str, Any]) -> bool:
    return (
        route_verify.get("accepted") is True
        and route_verify.get("status") == SAVE_RUN_VERIFY_REPLAY_ACCEPTED
    )


def _deterministic_attribution_verified(route_evidence: Mapping[str, Any]) -> bool:
    return (
        route_evidence.get("write_attribution_type") == WRITE_ATTRIBUTION_EXECUTOR_ATTRIBUTED
        and route_evidence.get("write_attribution_basis")
        == WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT
        and route_evidence.get("write_attribution_source")
        == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
    )


def _self_reported_attribution_rejected(route_evidence: Mapping[str, Any]) -> bool:
    return (
        route_evidence.get("write_attribution_is_self_reported") is False
        and route_evidence.get("executor_self_claim_used") is False
    )


def _trusted_runtime_self_claim_rejected(route_evidence: Mapping[str, Any]) -> bool:
    return (
        route_evidence.get("trusted_runtime_claim_allowed") is False
        and not _recursive_value_or_key_equals(route_evidence, "trusted_runtime_internal")
    )


def _request_source_spoof_rejected(route_evidence: Mapping[str, Any]) -> bool:
    request = route_evidence.get("request")
    return (
        isinstance(request, Mapping)
        and request.get("request_source") == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
    )


def _mediator_actor_mismatch_rejected(route_evidence: Mapping[str, Any]) -> bool:
    mediator_request = route_evidence.get("mediator_request")
    return (
        isinstance(mediator_request, Mapping)
        and mediator_request.get("actor") == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
    )


def _fallback_preserved(route_evidence: Mapping[str, Any]) -> bool:
    fallback_evidence = route_evidence.get("fallback_evidence")
    fallback_verify = route_evidence.get("fallback_verify")
    if not isinstance(fallback_evidence, Mapping) or not isinstance(fallback_verify, Mapping):
        return False
    replay = verify_phase11a_rollback_kill_path_evidence(fallback_evidence)
    return (
        replay.get("status") == ROLLBACK_VERIFY_REPLAY_ACCEPTED
        and fallback_verify.get("status") == ROLLBACK_VERIFY_REPLAY_ACCEPTED
        and fallback_verify.get("accepted") is True
    )


def _fallback_candidate_success_claimed(route_evidence: Mapping[str, Any]) -> bool:
    fallback_evidence = route_evidence.get("fallback_evidence")
    if not isinstance(fallback_evidence, Mapping):
        return False
    candidate = fallback_evidence.get("candidate_wired_path_result")
    if not isinstance(candidate, Mapping):
        return False
    status = candidate.get("status")
    return candidate.get("success") is True or status in {"returned_success", "success", "succeeded"}


def _mediator_decision_mismatch(route_evidence: Mapping[str, Any]) -> bool:
    mediator_decision = route_evidence.get("mediator_decision")
    if not isinstance(mediator_decision, Mapping):
        return True
    return (
        mediator_decision.get("decision_status") != MEDIATOR_DECISION_DENY
        or mediator_decision.get("write_path_status") != NOT_WIRED_TO_WRITE_PATH
        or mediator_decision.get("write_performed") is not False
    )


def _route_verify_summary(route_verify: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "accepted": route_verify.get("accepted"),
        "status": route_verify.get("status"),
        "verification_scope": route_verify.get("verification_scope"),
        "safe_default": route_verify.get("safe_default"),
    }


def _expect_field(reasons: list[str], record: Mapping[str, Any], field: str, expected: Any) -> None:
    if record.get(field) != expected:
        reasons.append(f"{field} mismatch")


def _recursive_overclaim_rejections(value: Any) -> list[str]:
    reasons: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _OVERCLAIM_KEYS and child is True:
                reasons.append(_OVERCLAIM_KEYS[key])
            reasons.extend(_recursive_overclaim_rejections(child))
    elif isinstance(value, list):
        for child in value:
            reasons.extend(_recursive_overclaim_rejections(child))
    return reasons


def _recursive_key_true(value: Any, key_name: str) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == key_name and child is True:
                return True
            if _recursive_key_true(child, key_name):
                return True
    elif isinstance(value, list):
        return any(_recursive_key_true(child, key_name) for child in value)
    return False


def _recursive_value_or_key_equals(value: Any, expected: str) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == expected or child == expected:
                return True
            if _recursive_value_or_key_equals(child, expected):
                return True
    elif isinstance(value, list):
        return any(_recursive_value_or_key_equals(child, expected) for child in value)
    return False


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_KNOWN_GAP_TRANSITION_STATUSES",
    "KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE",
    "KNOWN_GAP_EXPECTED_RED_BASELINE",
    "KNOWN_GAP_TRANSITION_NOT_APPLICABLE",
    "KNOWN_GAP_TRANSITION_REJECTED",
    "KNOWN_GAP_TRANSITION_VERIFY_REJECTED",
    "PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_KIND",
    "PHASE11A_KNOWN_GAP_BLOCKED_TRANSITION_VERSION",
    "PHASE11A_STEP",
    "PHASE11B_STATUS_NOT_STARTED",
    "RUNTIME_WRITE_PATH_STATUS_NOT_WIRED",
    "TRANSITION_BASIS_PRELIVE_SAVE_RUN_ROUTE",
    "TRANSITION_SOURCE_PHASE",
    "VERIFY_REPLAY_ACCEPTED",
    "VERIFY_REPLAY_REJECTED",
    "build_phase11a_known_gap_blocked_transition_evidence",
    "phase11a_known_gap_transition_evidence_digest",
    "verify_phase11a_known_gap_blocked_transition_evidence",
]
