"""Phase 11-A-4 deterministic completion baseline evidence.

This module closes Phase 11-A as replay evidence only. It recomputes source
verifies for Phase 11-A-0, 11-A-1, 11-A-2, and 11-A-3, then records a
deterministic completion baseline. It does not call save_run, write runtime
state, activate enforcement, implement a live executor, call providers, use the
network, spawn processes, grant runtime authority, or start Phase 11-B.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    SAFE_DEFAULT,
)
from src.evidence.phase11a_known_gap_blocked_transition import (
    KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE,
    SAVE_RUN_ROUTE_VERIFY_SOURCE_RECOMPUTED_INTERNAL_REPLAY,
    VERIFY_REPLAY_ACCEPTED as KNOWN_GAP_VERIFY_REPLAY_ACCEPTED,
    phase11a_known_gap_transition_evidence_digest,
    verify_phase11a_known_gap_blocked_transition_evidence,
)
from src.evidence.phase11a_rollback_kill_path import (
    VERIFY_REPLAY_ACCEPTED as ROLLBACK_VERIFY_REPLAY_ACCEPTED,
    phase11a_rollback_evidence_digest,
    verify_phase11a_rollback_kill_path_evidence,
)
from src.evidence.phase11a_save_run_write_routing import (
    VERIFY_REPLAY_ACCEPTED as SAVE_RUN_VERIFY_REPLAY_ACCEPTED,
    WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT,
    WRITE_ATTRIBUTION_EXECUTOR_ATTRIBUTED,
    WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER,
    phase11a_save_run_routing_evidence_digest,
    verify_phase11a_save_run_write_routing_evidence,
)
from src.evidence.phase11a_write_route_evidence_binding import (
    EVIDENCE_BINDING_ACCEPTED,
    PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_KIND,
    SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY,
    phase11a_write_route_evidence_binding_digest,
    verify_phase11a_write_route_evidence_binding,
)

PHASE11A_COMPLETION_BASELINE_KIND = "phase11a_completion_baseline"
PHASE11A_COMPLETION_BASELINE_VERSION = "phase11a_completion_baseline_v0"

PHASE11A_STEP = "11-A-4"
PHASE11B_STATUS_NOT_STARTED = "NOT_STARTED"

PHASE11A_COMPLETION_BASELINE_ACCEPTED = "PHASE11A_COMPLETION_BASELINE_ACCEPTED"
PHASE11A_COMPLETION_BASELINE_REJECTED = "PHASE11A_COMPLETION_BASELINE_REJECTED"
SOURCE_EVIDENCE_VERIFY_REJECTED = "SOURCE_EVIDENCE_VERIFY_REJECTED"
SOURCE_EVIDENCE_DIGEST_MISMATCH = "SOURCE_EVIDENCE_DIGEST_MISMATCH"
COMPLETION_CHAIN_BINDING_ACCEPTED = "COMPLETION_CHAIN_BINDING_ACCEPTED"
COMPLETION_CHAIN_BINDING_REJECTED = "COMPLETION_CHAIN_BINDING_REJECTED"

COMPLETION_BASIS_PHASE11A_INTERNAL_RECOMPUTE_CLOSURE = (
    "phase11a_0_1_2_3_internal_recompute_closure"
)

AUTHORITY_SNAPSHOT = {
    "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    "phase11a_step": PHASE11A_STEP,
    "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
    "safe_default": SAFE_DEFAULT,
}

NON_CLAIM_CAVEATS = (
    "11-A-4 records Phase 11-A completion baseline evidence only",
    "11-A-4 is not Phase 11-B",
    "11-A-4 is not live executor implementation",
    "11-A-4 is not actual runtime write wiring",
    "11-A-4 is not actual runtime enforcement",
    "source verifies are recomputed internally",
    "caller-supplied verify objects are not acceptance authority",
    "no actual runtime write is performed",
    "no actual enforcement is activated",
    "no live executor authority is granted",
    "no runtime write authority is granted",
    "no tool provider model or network authority is granted",
    "no raw shell write_file run_command or process_spawn authority is granted",
    "no OS filesystem sandbox or container hardening is claimed",
    "Phase 11-B remains not started",
    "safe default remains hold_current_state",
)

_EVIDENCE_FIELDS = frozenset(
    {
        "record_kind",
        "record_version",
        "claim_type",
        "phase11a_step",
        "completion_status",
        "completion_basis",
        "completion_chain_binding_result",
        "source_phase11a0_digest",
        "source_phase11a1_digest",
        "source_phase11a2_digest",
        "source_phase11a3_digest",
        "phase11a0_verify_status",
        "phase11a1_verify_status",
        "phase11a2_verify_status",
        "phase11a3_verify_status",
        "phase11a3_binding_status",
        "source_verify_recomputed",
        "source_verify_source",
        "supplied_verify_trusted",
        "supplied_verify_mismatch_rejected",
        "completion_chain_binding_valid",
        "phase11a3_deterministic_binding_verified",
        "phase11a2_internal_route_verify_preserved",
        "deterministic_attribution_preserved",
        "spoof_rejection_preserved",
        "known_gap_blocked_transition_preserved",
        "fallback_preserved",
        "candidate_success_rejected_as_rollback_evidence",
        "runtime_write_path_status",
        "live_executor_authority",
        "phase11b_status",
        "safe_default",
        "actual_runtime_write_performed",
        "actual_enforcement_activated",
        "live_executor_implemented",
        "runtime_write_authority_granted",
        "tool_authority_granted",
        "provider_model_network_authority_granted",
        "os_filesystem_sandbox_container_hardening_claimed",
        "current_authority_snapshot",
        "source_verify_summary",
        "source_verify_rejection_reasons",
        "source_phase11a3_bound_phase11a0_digest",
        "source_phase11a3_bound_phase11a1_digest",
        "source_phase11a3_bound_phase11a2_digest",
        "completion_rejection_reasons",
        "non_claim_caveats",
        "deterministic_evidence_digest",
    }
)

_OVERCLAIM_KEYS = {
    "runtime_write_authority_granted": "runtime write authority grant claim rejected",
    "live_executor_authority_granted": "live executor authority grant claim rejected",
    "phase11b_started": "Phase 11-B start claim rejected",
    "actual_runtime_write_performed": "actual runtime write claim rejected",
    "write_performed": "actual runtime write claim rejected",
    "actual_enforcement_activated": "actual enforcement claim rejected",
    "actual_enforcement_active": "actual enforcement claim rejected",
    "live_executor_implemented": "live executor claim rejected",
    "tool_authority_granted": "tool authority grant claim rejected",
    "provider_model_network_authority_granted": "provider model network authority grant claim rejected",
    "provider_authority_granted": "provider model network authority grant claim rejected",
    "model_authority_granted": "provider model network authority grant claim rejected",
    "network_authority_granted": "provider model network authority grant claim rejected",
    "raw_shell_authority_granted": "raw shell authority grant claim rejected",
    "command_runner_authority_granted": "command runner authority grant claim rejected",
    "write_file_authority_granted": "write_file authority grant claim rejected",
    "process_spawn_authority_granted": "process_spawn authority grant claim rejected",
    "os_filesystem_sandbox_container_hardening_claimed": (
        "OS/filesystem/sandbox/container hardening claim rejected"
    ),
    "os_hardening_claimed": "OS/filesystem/sandbox/container hardening claim rejected",
    "filesystem_hardening_claimed": "OS/filesystem/sandbox/container hardening claim rejected",
    "sandbox_hardening_claimed": "OS/filesystem/sandbox/container hardening claim rejected",
    "container_hardening_claimed": "OS/filesystem/sandbox/container hardening claim rejected",
}


def build_phase11a_completion_baseline(
    *,
    phase11a0_evidence: Mapping[str, Any],
    phase11a1_evidence: Mapping[str, Any],
    phase11a2_evidence: Mapping[str, Any],
    phase11a3_binding_evidence: Mapping[str, Any],
    supplied_phase11a0_verify: Mapping[str, Any] | None = None,
    supplied_phase11a1_verify: Mapping[str, Any] | None = None,
    supplied_phase11a2_verify: Mapping[str, Any] | None = None,
    supplied_phase11a3_verify: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic Phase 11-A completion baseline record."""

    source0 = _mapping_or_empty(phase11a0_evidence)
    source1 = _mapping_or_empty(phase11a1_evidence)
    source2 = _mapping_or_empty(phase11a2_evidence)
    source3 = _mapping_or_empty(phase11a3_binding_evidence)

    phase11a0_digest = phase11a_rollback_evidence_digest(source0)
    phase11a1_digest = phase11a_save_run_routing_evidence_digest(source1)
    phase11a2_digest = phase11a_known_gap_transition_evidence_digest(source2)
    phase11a3_digest = phase11a_write_route_evidence_binding_digest(source3)

    phase11a0_verify = verify_phase11a_rollback_kill_path_evidence(source0)
    phase11a1_verify = verify_phase11a_save_run_write_routing_evidence(source1)
    phase11a2_verify = verify_phase11a_known_gap_blocked_transition_evidence(
        source2,
        save_run_route_evidence=source1,
    )
    phase11a3_verify = verify_phase11a_write_route_evidence_binding(
        source3,
        phase11a0_evidence=source0,
        phase11a1_evidence=source1,
        phase11a2_evidence=source2,
    )

    source_verify_summary = {
        "phase11a0": _verify_summary(phase11a0_verify),
        "phase11a1": _verify_summary(phase11a1_verify),
        "phase11a2": _verify_summary(phase11a2_verify),
        "phase11a3": _verify_summary(phase11a3_verify),
    }
    source_verify_rejection_reasons = {
        "phase11a0": list(phase11a0_verify.get("rejection_reasons", [])),
        "phase11a1": list(phase11a1_verify.get("rejection_reasons", [])),
        "phase11a2": list(phase11a2_verify.get("rejection_reasons", [])),
        "phase11a3": list(phase11a3_verify.get("rejection_reasons", [])),
    }

    completion_chain_binding_valid = _completion_chain_binding_valid(
        source3=source3,
        phase11a0_digest=phase11a0_digest,
        phase11a1_digest=phase11a1_digest,
        phase11a2_digest=phase11a2_digest,
        phase11a3_verify=phase11a3_verify,
    )
    phase11a3_deterministic_binding_verified = (
        source3.get("binding_record_kind") == PHASE11A_WRITE_ROUTE_EVIDENCE_BINDING_KIND
        and source3.get("source_verify_source") == SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY
        and source3.get("source_verify_recomputed") is True
        and source3.get("supplied_verify_trusted") is False
        and source3.get("cross_digest_binding_valid") is True
        and _verify_accepted(phase11a3_verify, EVIDENCE_BINDING_ACCEPTED)
    )
    phase11a2_internal_route_verify_preserved = _phase11a2_internal_route_verify_preserved(source2)
    deterministic_attribution_preserved = _deterministic_attribution_preserved(source1, source2, source3)
    spoof_rejection_preserved = _spoof_rejection_preserved(source2, source3)
    known_gap_blocked_transition_preserved = _known_gap_blocked_transition_preserved(source2, source3)
    fallback_preserved = _fallback_preserved(
        source0=source0,
        source1=source1,
        source2=source2,
        source3=source3,
        phase11a0_verify=phase11a0_verify,
    )
    candidate_success_rejected_as_rollback_evidence = not _candidate_success_accepted_as_rollback(
        source0,
        source1,
    )
    supplied_verify_mismatch_rejected = _supplied_verify_mismatch_rejected(
        supplied_phase11a0_verify=supplied_phase11a0_verify,
        supplied_phase11a1_verify=supplied_phase11a1_verify,
        supplied_phase11a2_verify=supplied_phase11a2_verify,
        supplied_phase11a3_verify=supplied_phase11a3_verify,
        phase11a0_verify=phase11a0_verify,
        phase11a1_verify=phase11a1_verify,
        phase11a2_verify=phase11a2_verify,
        phase11a3_verify=phase11a3_verify,
    )

    rejection_reasons = _completion_rejection_reasons(
        source0=source0,
        source1=source1,
        source2=source2,
        source3=source3,
        phase11a0_verify=phase11a0_verify,
        phase11a1_verify=phase11a1_verify,
        phase11a2_verify=phase11a2_verify,
        phase11a3_verify=phase11a3_verify,
        completion_chain_binding_valid=completion_chain_binding_valid,
        phase11a3_deterministic_binding_verified=phase11a3_deterministic_binding_verified,
        phase11a2_internal_route_verify_preserved=phase11a2_internal_route_verify_preserved,
        deterministic_attribution_preserved=deterministic_attribution_preserved,
        spoof_rejection_preserved=spoof_rejection_preserved,
        known_gap_blocked_transition_preserved=known_gap_blocked_transition_preserved,
        fallback_preserved=fallback_preserved,
        candidate_success_rejected_as_rollback_evidence=(
            candidate_success_rejected_as_rollback_evidence
        ),
        supplied_verify_mismatch_rejected=supplied_verify_mismatch_rejected,
    )
    completion_status = _completion_status(rejection_reasons)

    record = {
        "record_kind": PHASE11A_COMPLETION_BASELINE_KIND,
        "record_version": PHASE11A_COMPLETION_BASELINE_VERSION,
        "claim_type": "phase11a_completion_baseline_closure_evidence_not_live_enforcement",
        "phase11a_step": PHASE11A_STEP,
        "completion_status": completion_status,
        "completion_basis": COMPLETION_BASIS_PHASE11A_INTERNAL_RECOMPUTE_CLOSURE,
        "completion_chain_binding_result": (
            COMPLETION_CHAIN_BINDING_ACCEPTED
            if completion_chain_binding_valid
            else COMPLETION_CHAIN_BINDING_REJECTED
        ),
        "source_phase11a0_digest": phase11a0_digest,
        "source_phase11a1_digest": phase11a1_digest,
        "source_phase11a2_digest": phase11a2_digest,
        "source_phase11a3_digest": phase11a3_digest,
        "phase11a0_verify_status": phase11a0_verify.get("status"),
        "phase11a1_verify_status": phase11a1_verify.get("status"),
        "phase11a2_verify_status": phase11a2_verify.get("status"),
        "phase11a3_verify_status": phase11a3_verify.get("status"),
        "phase11a3_binding_status": source3.get("binding_status"),
        "source_verify_recomputed": True,
        "source_verify_source": SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY,
        "supplied_verify_trusted": False,
        "supplied_verify_mismatch_rejected": supplied_verify_mismatch_rejected,
        "completion_chain_binding_valid": completion_chain_binding_valid,
        "phase11a3_deterministic_binding_verified": phase11a3_deterministic_binding_verified,
        "phase11a2_internal_route_verify_preserved": phase11a2_internal_route_verify_preserved,
        "deterministic_attribution_preserved": deterministic_attribution_preserved,
        "spoof_rejection_preserved": spoof_rejection_preserved,
        "known_gap_blocked_transition_preserved": known_gap_blocked_transition_preserved,
        "fallback_preserved": fallback_preserved,
        "candidate_success_rejected_as_rollback_evidence": (
            candidate_success_rejected_as_rollback_evidence
        ),
        "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11b_status": PHASE11B_STATUS_NOT_STARTED,
        "safe_default": SAFE_DEFAULT,
        "actual_runtime_write_performed": False,
        "actual_enforcement_activated": False,
        "live_executor_implemented": False,
        "runtime_write_authority_granted": False,
        "tool_authority_granted": False,
        "provider_model_network_authority_granted": False,
        "os_filesystem_sandbox_container_hardening_claimed": False,
        "current_authority_snapshot": dict(AUTHORITY_SNAPSHOT),
        "source_verify_summary": source_verify_summary,
        "source_verify_rejection_reasons": source_verify_rejection_reasons,
        "source_phase11a3_bound_phase11a0_digest": source3.get("source_phase11a0_digest"),
        "source_phase11a3_bound_phase11a1_digest": source3.get("source_phase11a1_digest"),
        "source_phase11a3_bound_phase11a2_digest": source3.get("source_phase11a2_digest"),
        "completion_rejection_reasons": rejection_reasons,
        "non_claim_caveats": list(NON_CLAIM_CAVEATS),
    }
    record["deterministic_evidence_digest"] = phase11a_completion_baseline_digest(record)
    return record


def verify_phase11a_completion_baseline(
    baseline_record: Mapping[str, Any],
    *,
    phase11a0_evidence: Mapping[str, Any],
    phase11a1_evidence: Mapping[str, Any],
    phase11a2_evidence: Mapping[str, Any],
    phase11a3_binding_evidence: Mapping[str, Any],
    supplied_phase11a0_verify: Mapping[str, Any] | None = None,
    supplied_phase11a1_verify: Mapping[str, Any] | None = None,
    supplied_phase11a2_verify: Mapping[str, Any] | None = None,
    supplied_phase11a3_verify: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay-verify the Phase 11-A completion baseline against source evidence."""

    reasons: list[str] = []
    if not isinstance(baseline_record, Mapping):
        baseline_record = {}
        reasons.append("baseline record must be a mapping")

    unexpected_fields = sorted(set(baseline_record) - _EVIDENCE_FIELDS)
    for field in unexpected_fields:
        reasons.append(f"unexpected baseline record field: {field}")

    missing_fields = sorted(_EVIDENCE_FIELDS - set(baseline_record))
    for field in missing_fields:
        reasons.append(f"missing baseline record field: {field}")

    expected_record = build_phase11a_completion_baseline(
        phase11a0_evidence=phase11a0_evidence,
        phase11a1_evidence=phase11a1_evidence,
        phase11a2_evidence=phase11a2_evidence,
        phase11a3_binding_evidence=phase11a3_binding_evidence,
        supplied_phase11a0_verify=supplied_phase11a0_verify,
        supplied_phase11a1_verify=supplied_phase11a1_verify,
        supplied_phase11a2_verify=supplied_phase11a2_verify,
        supplied_phase11a3_verify=supplied_phase11a3_verify,
    )

    for field in sorted(_EVIDENCE_FIELDS - {"deterministic_evidence_digest"}):
        if baseline_record.get(field) != expected_record.get(field):
            reasons.append(f"{field} mismatch")

    _expect_field(reasons, baseline_record, "record_kind", PHASE11A_COMPLETION_BASELINE_KIND)
    _expect_field(reasons, baseline_record, "record_version", PHASE11A_COMPLETION_BASELINE_VERSION)
    _expect_field(
        reasons,
        baseline_record,
        "claim_type",
        "phase11a_completion_baseline_closure_evidence_not_live_enforcement",
    )
    _expect_field(reasons, baseline_record, "phase11a_step", PHASE11A_STEP)
    _expect_field(
        reasons,
        baseline_record,
        "completion_basis",
        COMPLETION_BASIS_PHASE11A_INTERNAL_RECOMPUTE_CLOSURE,
    )
    _expect_field(reasons, baseline_record, "source_verify_recomputed", True)
    _expect_field(
        reasons,
        baseline_record,
        "source_verify_source",
        SOURCE_VERIFY_RECOMPUTED_INTERNAL_REPLAY,
    )
    _expect_field(reasons, baseline_record, "supplied_verify_trusted", False)
    _expect_field(reasons, baseline_record, "runtime_write_path_status", NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
    _expect_field(reasons, baseline_record, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
    _expect_field(reasons, baseline_record, "phase11b_status", PHASE11B_STATUS_NOT_STARTED)
    _expect_field(reasons, baseline_record, "safe_default", SAFE_DEFAULT)
    _expect_field(reasons, baseline_record, "actual_runtime_write_performed", False)
    _expect_field(reasons, baseline_record, "actual_enforcement_activated", False)
    _expect_field(reasons, baseline_record, "live_executor_implemented", False)
    _expect_field(reasons, baseline_record, "runtime_write_authority_granted", False)
    _expect_field(reasons, baseline_record, "tool_authority_granted", False)
    _expect_field(reasons, baseline_record, "provider_model_network_authority_granted", False)
    _expect_field(reasons, baseline_record, "os_filesystem_sandbox_container_hardening_claimed", False)
    _expect_field(reasons, baseline_record, "current_authority_snapshot", AUTHORITY_SNAPSHOT)

    source0 = _mapping_or_empty(phase11a0_evidence)
    source1 = _mapping_or_empty(phase11a1_evidence)
    source2 = _mapping_or_empty(phase11a2_evidence)
    source3 = _mapping_or_empty(phase11a3_binding_evidence)
    expected_digest0 = phase11a_rollback_evidence_digest(source0)
    expected_digest1 = phase11a_save_run_routing_evidence_digest(source1)
    expected_digest2 = phase11a_known_gap_transition_evidence_digest(source2)
    expected_digest3 = phase11a_write_route_evidence_binding_digest(source3)

    if baseline_record.get("source_phase11a0_digest") != expected_digest0:
        reasons.append("source 11-A-0 evidence digest mismatch")
    if baseline_record.get("source_phase11a1_digest") != expected_digest1:
        reasons.append("source 11-A-1 evidence digest mismatch")
    if baseline_record.get("source_phase11a2_digest") != expected_digest2:
        reasons.append("source 11-A-2 evidence digest mismatch")
    if baseline_record.get("source_phase11a3_digest") != expected_digest3:
        reasons.append("source 11-A-3 evidence digest mismatch")

    reasons.extend(expected_record.get("completion_rejection_reasons", []))
    reasons.extend(_recursive_overclaim_rejections(baseline_record))

    supplied_digest = baseline_record.get("deterministic_evidence_digest")
    recomputed_digest = phase11a_completion_baseline_digest(baseline_record)
    if supplied_digest != recomputed_digest:
        reasons.append("deterministic evidence digest mismatch")
    if supplied_digest != expected_record.get("deterministic_evidence_digest"):
        reasons.append("expected evidence digest mismatch")

    reasons = _unique(reasons)
    accepted = not reasons
    status = PHASE11A_COMPLETION_BASELINE_ACCEPTED if accepted else _completion_status(reasons)
    return {
        "accepted": accepted,
        "status": status,
        "completion_verify_status": status,
        "rejection_reasons": reasons,
        "verification_scope": "phase11a_completion_baseline_replay_only",
        "source_verify_recomputed": True,
        "supplied_verify_trusted": False,
        "completion_chain_binding_valid": (
            accepted and baseline_record.get("completion_chain_binding_valid") is True
        ),
        "is_runtime_wiring": False,
        "is_runtime_enforcement": False,
        "safe_default": SAFE_DEFAULT,
    }


def phase11a_completion_baseline_digest(evidence_record: Mapping[str, Any]) -> str:
    """Return the deterministic digest for the Phase 11-A-4 baseline payload."""

    payload = deepcopy(dict(evidence_record))
    payload.pop("deterministic_evidence_digest", None)
    return _sha256_json(payload)


def _completion_rejection_reasons(
    *,
    source0: Mapping[str, Any],
    source1: Mapping[str, Any],
    source2: Mapping[str, Any],
    source3: Mapping[str, Any],
    phase11a0_verify: Mapping[str, Any],
    phase11a1_verify: Mapping[str, Any],
    phase11a2_verify: Mapping[str, Any],
    phase11a3_verify: Mapping[str, Any],
    completion_chain_binding_valid: bool,
    phase11a3_deterministic_binding_verified: bool,
    phase11a2_internal_route_verify_preserved: bool,
    deterministic_attribution_preserved: bool,
    spoof_rejection_preserved: Mapping[str, bool],
    known_gap_blocked_transition_preserved: bool,
    fallback_preserved: bool,
    candidate_success_rejected_as_rollback_evidence: bool,
    supplied_verify_mismatch_rejected: bool,
) -> list[str]:
    reasons: list[str] = []
    if not _verify_accepted(phase11a0_verify, ROLLBACK_VERIFY_REPLAY_ACCEPTED):
        reasons.append("source 11-A-0 evidence verify rejected")
    if not _verify_accepted(phase11a1_verify, SAVE_RUN_VERIFY_REPLAY_ACCEPTED):
        reasons.append("source 11-A-1 evidence verify rejected")
    if not _verify_accepted(phase11a2_verify, KNOWN_GAP_VERIFY_REPLAY_ACCEPTED):
        reasons.append("source 11-A-2 evidence verify rejected")
    if not _verify_accepted(phase11a3_verify, EVIDENCE_BINDING_ACCEPTED):
        reasons.append("source 11-A-3 evidence verify rejected")
    if not completion_chain_binding_valid:
        reasons.append("completion chain binding mismatch")
    if not phase11a3_deterministic_binding_verified:
        reasons.append("11-A-3 deterministic binding broken")
    if not phase11a2_internal_route_verify_preserved:
        reasons.append("11-A-2 internal route verify preservation mismatch")
    if not deterministic_attribution_preserved:
        reasons.append("deterministic attribution missing or mismatch")
    if spoof_rejection_preserved.get("self_reported_attribution_rejected") is not True:
        reasons.append("self-reported attribution accepted state rejected")
    if spoof_rejection_preserved.get("trusted_runtime_self_claim_rejected") is not True:
        reasons.append("trusted runtime self-claim accepted state rejected")
    if spoof_rejection_preserved.get("request_source_spoof_rejected") is not True:
        reasons.append("request_source spoof accepted state rejected")
    if spoof_rejection_preserved.get("mediator_actor_mismatch_rejected") is not True:
        reasons.append("mediator actor mismatch accepted state rejected")
    if not known_gap_blocked_transition_preserved:
        reasons.append("known-gap blocked transition missing or mismatch")
    if not fallback_preserved:
        reasons.append("fallback preservation mismatch")
    if not candidate_success_rejected_as_rollback_evidence:
        reasons.append("candidate success accepted as 11-A-0 rollback evidence rejected")
    if not supplied_verify_mismatch_rejected:
        reasons.append("supplied verify mismatch rejected")
    if source1.get("runtime_write_path_status") != NOT_WIRED_TO_EXECUTOR_WRITE_PATH:
        reasons.append("runtime write authority grant claim rejected")
    if source2.get("runtime_write_path_status") != NOT_WIRED_TO_EXECUTOR_WRITE_PATH:
        reasons.append("runtime write authority grant claim rejected")
    if source3.get("runtime_write_path_status") != NOT_WIRED_TO_EXECUTOR_WRITE_PATH:
        reasons.append("runtime write authority grant claim rejected")
    if source1.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("live executor authority grant claim rejected")
    if source2.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("live executor authority grant claim rejected")
    if source3.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
        reasons.append("live executor authority grant claim rejected")
    if source1.get("phase11b_status") != PHASE11B_STATUS_NOT_STARTED:
        reasons.append("Phase 11-B start claim rejected")
    if source2.get("phase11b_status") != PHASE11B_STATUS_NOT_STARTED:
        reasons.append("Phase 11-B start claim rejected")
    if source3.get("phase11b_status") != PHASE11B_STATUS_NOT_STARTED:
        reasons.append("Phase 11-B start claim rejected")

    for source in (source0, source1, source2, source3):
        reasons.extend(_recursive_overclaim_rejections(source))
    return _unique(reasons)


def _completion_status(reasons: list[str]) -> str:
    if not reasons:
        return PHASE11A_COMPLETION_BASELINE_ACCEPTED
    if any(
        reason.startswith("source 11-A-") and "evidence digest mismatch" in reason
        for reason in reasons
    ):
        return SOURCE_EVIDENCE_DIGEST_MISMATCH
    if any("evidence verify rejected" in reason for reason in reasons):
        return SOURCE_EVIDENCE_VERIFY_REJECTED
    if any("binding" in reason for reason in reasons):
        return COMPLETION_CHAIN_BINDING_REJECTED
    return PHASE11A_COMPLETION_BASELINE_REJECTED


def _completion_chain_binding_valid(
    *,
    source3: Mapping[str, Any],
    phase11a0_digest: str,
    phase11a1_digest: str,
    phase11a2_digest: str,
    phase11a3_verify: Mapping[str, Any],
) -> bool:
    return (
        _verify_accepted(phase11a3_verify, EVIDENCE_BINDING_ACCEPTED)
        and source3.get("binding_status") == EVIDENCE_BINDING_ACCEPTED
        and source3.get("source_phase11a0_digest") == phase11a0_digest
        and source3.get("source_phase11a1_digest") == phase11a1_digest
        and source3.get("source_phase11a2_digest") == phase11a2_digest
        and source3.get("phase11a0_verify_status") == ROLLBACK_VERIFY_REPLAY_ACCEPTED
        and source3.get("phase11a1_verify_status") == SAVE_RUN_VERIFY_REPLAY_ACCEPTED
        and source3.get("phase11a2_verify_status") == KNOWN_GAP_VERIFY_REPLAY_ACCEPTED
    )


def _phase11a2_internal_route_verify_preserved(source2: Mapping[str, Any]) -> bool:
    return (
        source2.get("known_gap_transition_status") == KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE
        and source2.get("save_run_route_verify_source")
        == SAVE_RUN_ROUTE_VERIFY_SOURCE_RECOMPUTED_INTERNAL_REPLAY
        and source2.get("supplied_route_verify_trusted") is False
        and source2.get("route_verify_recomputed") is True
    )


def _deterministic_attribution_preserved(
    source1: Mapping[str, Any],
    source2: Mapping[str, Any],
    source3: Mapping[str, Any],
) -> bool:
    return (
        source1.get("write_attribution_type") == WRITE_ATTRIBUTION_EXECUTOR_ATTRIBUTED
        and source1.get("write_attribution_basis")
        == WRITE_ATTRIBUTION_BASIS_DETERMINISTIC_ADAPTER_CONTEXT
        and source1.get("write_attribution_source")
        == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
        and source1.get("write_attribution_is_self_reported") is False
        and source1.get("trusted_runtime_claim_allowed") is False
        and source1.get("executor_self_claim_used") is False
        and _request_source_preserved(source1)
        and _mediator_actor_preserved(source1)
        and source2.get("deterministic_attribution_verified") is True
        and source3.get("deterministic_attribution_preserved") is True
    )


def _spoof_rejection_preserved(
    source2: Mapping[str, Any],
    source3: Mapping[str, Any],
) -> dict[str, bool]:
    binding_preserved = source3.get("deterministic_attribution_preserved") is True
    return {
        "self_reported_attribution_rejected": (
            source2.get("self_reported_attribution_rejected") is True
            and binding_preserved
        ),
        "trusted_runtime_self_claim_rejected": (
            source2.get("trusted_runtime_self_claim_rejected") is True
            and binding_preserved
        ),
        "request_source_spoof_rejected": (
            source2.get("request_source_spoof_rejected") is True and binding_preserved
        ),
        "mediator_actor_mismatch_rejected": (
            source2.get("mediator_actor_mismatch_rejected") is True and binding_preserved
        ),
    }


def _known_gap_blocked_transition_preserved(
    source2: Mapping[str, Any],
    source3: Mapping[str, Any],
) -> bool:
    return (
        source2.get("known_gap_transition_status") == KNOWN_GAP_BLOCKED_BY_PRELIVE_ROUTE
        and source3.get("known_gap_blocked_transition_preserved") is True
    )


def _fallback_preserved(
    *,
    source0: Mapping[str, Any],
    source1: Mapping[str, Any],
    source2: Mapping[str, Any],
    source3: Mapping[str, Any],
    phase11a0_verify: Mapping[str, Any],
) -> bool:
    fallback_evidence = source1.get("fallback_evidence")
    fallback_verify = source1.get("fallback_verify")
    return (
        _verify_accepted(phase11a0_verify, ROLLBACK_VERIFY_REPLAY_ACCEPTED)
        and isinstance(fallback_evidence, Mapping)
        and phase11a_rollback_evidence_digest(fallback_evidence)
        == phase11a_rollback_evidence_digest(source0)
        and isinstance(fallback_verify, Mapping)
        and fallback_verify.get("accepted") is True
        and fallback_verify.get("status") == ROLLBACK_VERIFY_REPLAY_ACCEPTED
        and source2.get("fallback_preserved") is True
        and source3.get("fallback_preserved") is True
    )


def _candidate_success_accepted_as_rollback(
    source0: Mapping[str, Any],
    source1: Mapping[str, Any],
) -> bool:
    return _candidate_success_claimed(source0) or _candidate_success_claimed(
        _mapping_or_empty(source1.get("fallback_evidence"))
    )


def _candidate_success_claimed(value: Mapping[str, Any]) -> bool:
    candidate = value.get("candidate_wired_path_result")
    if not isinstance(candidate, Mapping):
        return False
    status = candidate.get("status")
    return candidate.get("success") is True or status in {"returned_success", "success", "succeeded"}


def _request_source_preserved(source1: Mapping[str, Any]) -> bool:
    request = source1.get("request")
    return (
        isinstance(request, Mapping)
        and request.get("request_source") == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
    )


def _mediator_actor_preserved(source1: Mapping[str, Any]) -> bool:
    mediator_request = source1.get("mediator_request")
    return (
        isinstance(mediator_request, Mapping)
        and mediator_request.get("actor") == WRITE_ATTRIBUTION_SOURCE_PHASE11A_SAVE_RUN_PRE_LIVE_ADAPTER
    )


def _supplied_verify_mismatch_rejected(
    *,
    supplied_phase11a0_verify: Mapping[str, Any] | None,
    supplied_phase11a1_verify: Mapping[str, Any] | None,
    supplied_phase11a2_verify: Mapping[str, Any] | None,
    supplied_phase11a3_verify: Mapping[str, Any] | None,
    phase11a0_verify: Mapping[str, Any],
    phase11a1_verify: Mapping[str, Any],
    phase11a2_verify: Mapping[str, Any],
    phase11a3_verify: Mapping[str, Any],
) -> bool:
    supplied_pairs = (
        (supplied_phase11a0_verify, phase11a0_verify),
        (supplied_phase11a1_verify, phase11a1_verify),
        (supplied_phase11a2_verify, phase11a2_verify),
        (supplied_phase11a3_verify, phase11a3_verify),
    )
    for supplied, recomputed in supplied_pairs:
        if supplied is not None and _verify_summary(supplied) != _verify_summary(recomputed):
            return False
    return True


def _verify_accepted(verify_result: Mapping[str, Any], expected_status: str) -> bool:
    return verify_result.get("accepted") is True and verify_result.get("status") == expected_status


def _verify_summary(verify_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "accepted": verify_result.get("accepted"),
        "status": verify_result.get("status"),
        "verification_scope": verify_result.get("verification_scope"),
        "safe_default": verify_result.get("safe_default"),
    }


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


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
    elif isinstance(value, (list, tuple)):
        for child in value:
            reasons.extend(_recursive_overclaim_rejections(child))
    return reasons


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
    "COMPLETION_BASIS_PHASE11A_INTERNAL_RECOMPUTE_CLOSURE",
    "COMPLETION_CHAIN_BINDING_ACCEPTED",
    "COMPLETION_CHAIN_BINDING_REJECTED",
    "PHASE11A_COMPLETION_BASELINE_ACCEPTED",
    "PHASE11A_COMPLETION_BASELINE_KIND",
    "PHASE11A_COMPLETION_BASELINE_REJECTED",
    "PHASE11A_COMPLETION_BASELINE_VERSION",
    "PHASE11A_STEP",
    "PHASE11B_STATUS_NOT_STARTED",
    "SOURCE_EVIDENCE_DIGEST_MISMATCH",
    "SOURCE_EVIDENCE_VERIFY_REJECTED",
    "build_phase11a_completion_baseline",
    "phase11a_completion_baseline_digest",
    "verify_phase11a_completion_baseline",
]
