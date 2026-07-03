"""Phase 11-B-0 actual ``store.py`` write mediation evidence.

This module records the narrow runtime wiring added in Phase 11-B-0:
executor-attributed ``.aeg`` direct/traversal write attempts are routed through
the guard/mediator path and blocked, while deterministic Aegis runtime writes
remain allowed. It does not create a live executor, provider/model/network
path, shell authority, general write tool, or external filesystem enforcement.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping, Sequence

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
    SAFE_DEFAULT,
    STORE_WRITE_BOUNDARY_STRENGTH_IN_PROCESS_TAMPER_EVIDENT_ONLY,
    STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
    STORE_WRITE_EXECUTOR_CODE_EXECUTION_MODEL_STRUCTURED_ACTIONS_REQUIRED,
    STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED,
    STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_NO_ATTEMPT,
    STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED,
    STORE_WRITE_MEDIATION_FIELDS,
    STORE_WRITE_MEDIATION_REASON_EXECUTOR_AEG_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT,
    STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED,
    STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_MEDIATION_SCOPE_AEG_EXECUTOR_ATTRIBUTED_ONLY,
    STORE_WRITE_MEDIATION_V0,
    STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
    STORE_WRITE_CONTEXT_RESULT_BLOCKED,
    STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
    STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
    STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
    STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
    STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
    STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED,
    STORE_WRITE_SINK_APPEND_LEDGER,
    STORE_WRITE_SINK_WRITE_JSON,
    STORE_WRITE_OS_SANDBOX_NOT_IMPLEMENTED,
    STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
    STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
)

STORE_WRITE_MEDIATION_VERIFICATION_ACCEPTED = "VERIFY_REPLAY_ACCEPTED"
STORE_WRITE_MEDIATION_VERIFICATION_REJECTED = "VERIFY_REPLAY_REJECTED"
FORBIDDEN_STORE_WRITE_OVERCLAIM_LABELS = (
    "TRUSTED_CONTEXT_SECURITY_BOUNDARY",
    "EXECUTOR_AEG_WRITE_FULLY_BLOCKED",
    "RAW_BYPASS_IMPOSSIBLE",
    "AEG_TAMPER_PROOF",
)


def build_store_write_mediation_metadata(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build digest-bound metadata from actual ``store.py`` mediation events."""

    normalized_events = [deepcopy(dict(event)) for event in events]
    blocked_events = [
        event for event in normalized_events if event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED
    ]
    blocked_write_json_events = [
        event for event in blocked_events if event.get("sink_name") == STORE_WRITE_SINK_WRITE_JSON
    ]
    blocked_ledger_events = [
        event for event in blocked_events if event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
    ]
    trusted_allowed_events = [
        event
        for event in normalized_events
        if event.get("write_provenance_type") == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        and event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED
    ]
    trusted_write_json_events = [
        event for event in trusted_allowed_events if event.get("sink_name") == STORE_WRITE_SINK_WRITE_JSON
    ]
    trusted_ledger_events = [
        event for event in trusted_allowed_events if event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
    ]
    fallback_events = [event for event in normalized_events if event.get("fallback_to_unwired") is True]
    blocked_created_count = sum(1 for event in blocked_write_json_events if event.get("target_file_created") is True)
    blocked_ledger_appended_count = sum(
        _non_negative_int(event.get("ledger_entries_appended_count")) for event in blocked_ledger_events
    )
    guarded_sinks = sorted(
        {
            str(event.get("sink_name"))
            for event in normalized_events
            if event.get("sink_guarded") is True
            and event.get("store_write_boundary") == STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED
            and event.get("sink_name") in (STORE_WRITE_SINK_WRITE_JSON, STORE_WRITE_SINK_APPEND_LEDGER)
        }
    )
    executor_direct_sink_write_result = (
        STORE_WRITE_MEDIATION_RESULT_BLOCKED
        if blocked_write_json_events
        else STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT
    )
    executor_direct_ledger_append_result = (
        STORE_WRITE_MEDIATION_RESULT_BLOCKED
        if blocked_ledger_events
        else STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT
    )
    result, reason = _summary_result_and_reason(
        blocked_events=blocked_events,
        trusted_allowed_events=trusted_allowed_events,
        fallback_events=fallback_events,
    )
    record = {
        "store_write_mediation_version": STORE_WRITE_MEDIATION_V0,
        "store_write_mediation_enabled": True,
        "store_write_mediation_scope": STORE_WRITE_MEDIATION_SCOPE_AEG_EXECUTOR_ATTRIBUTED_ONLY,
        "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
        "store_write_boundary_strength": STORE_WRITE_BOUNDARY_STRENGTH_IN_PROCESS_TAMPER_EVIDENT_ONLY,
        "trusted_context_security_boundary": False,
        "requires_structured_executor": True,
        "arbitrary_in_process_code_breaks_boundary": True,
        "process_isolation_status": STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED,
        "os_sandbox_status": STORE_WRITE_OS_SANDBOX_NOT_IMPLEMENTED,
        "executor_code_execution_model": STORE_WRITE_EXECUTOR_CODE_EXECUTION_MODEL_STRUCTURED_ACTIONS_REQUIRED,
        "tamper_proof_claimed": False,
        "physical_prevention_claimed": False,
        "raw_bypass_impossible": False,
        "arbitrary_in_process_code_safe": False,
        "live_executor_ready": False,
        "write_authority_safe": False,
        "guarded_sinks": guarded_sinks,
        "write_json_sink_guarded": STORE_WRITE_SINK_WRITE_JSON in guarded_sinks,
        "ledger_append_sink_guarded": STORE_WRITE_SINK_APPEND_LEDGER in guarded_sinks,
        "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
        "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
        "call_stack_inference_used_as_judgment_basis": STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
        "missing_context_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED,
        "omitted_declaration_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED,
        "executor_self_report_trusted_result": STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
        "store_write_mediation_binding_present": True,
        "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
        "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
        "write_provenance_type": "mixed_runtime_owned_capability",
        "executor_attributed_write_blocked": bool(blocked_events),
        "executor_direct_sink_write_result": executor_direct_sink_write_result,
        "executor_direct_sink_write_created_files_count": blocked_created_count,
        "executor_direct_ledger_append_result": executor_direct_ledger_append_result,
        "executor_direct_ledger_entries_appended_count": blocked_ledger_appended_count,
        "trusted_runtime_write_allowed": bool(trusted_write_json_events),
        "trusted_runtime_ledger_append_allowed": bool(trusted_ledger_events),
        "executor_self_report_ignored": not any(event.get("executor_self_report_used") is True for event in normalized_events),
        "executor_omitted_declaration_rejected": any(
            event.get("executor_omitted_declaration") is True
            and event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED
            for event in normalized_events
        ),
        "blocked_write_target_count": len(blocked_write_json_events),
        "blocked_write_created_files_count": blocked_created_count,
        "store_write_attempt_count": len(normalized_events),
        "write_mediation_result": result,
        "write_mediation_reason": reason,
        "rollback_used": bool(fallback_events),
        "fallback_to_unwired": bool(fallback_events),
        "fallback_evidence_recorded": bool(fallback_events),
        "known_gap_aeg_direct_traversal_status": (
            STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED
            if blocked_events
            else STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_NO_ATTEMPT
        ),
        "known_gap_non_aeg_status": STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11b_live_executor_status": PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
        "store_write_mediation_events": normalized_events,
    }
    record["store_write_mediation_metadata_hash"] = expected_store_write_mediation_metadata_hash(record)
    return record


def store_write_mediation_manifest_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in STORE_WRITE_MEDIATION_FIELDS}


def expected_store_write_mediation_metadata_hash(payload: Mapping[str, Any]) -> str:
    material = {
        field: payload.get(field)
        for field in STORE_WRITE_MEDIATION_FIELDS
        if field != "store_write_mediation_metadata_hash"
    }
    return _sha256_json(material)


def verify_store_write_mediation_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        payload = {}
        reasons.append("store write mediation evidence must be a mapping")

    for field in STORE_WRITE_MEDIATION_FIELDS:
        if field not in payload:
            reasons.append(f"missing store write mediation field: {field}")

    _expect(reasons, payload, "store_write_mediation_version", STORE_WRITE_MEDIATION_V0)
    _expect(reasons, payload, "store_write_mediation_enabled", True)
    _expect(
        reasons,
        payload,
        "store_write_mediation_scope",
        STORE_WRITE_MEDIATION_SCOPE_AEG_EXECUTOR_ATTRIBUTED_ONLY,
    )
    _expect(reasons, payload, "store_write_boundary", STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED)
    _expect(
        reasons,
        payload,
        "store_write_boundary_strength",
        STORE_WRITE_BOUNDARY_STRENGTH_IN_PROCESS_TAMPER_EVIDENT_ONLY,
    )
    _expect(reasons, payload, "trusted_context_security_boundary", False)
    _expect(reasons, payload, "requires_structured_executor", True)
    _expect(reasons, payload, "arbitrary_in_process_code_breaks_boundary", True)
    _expect(reasons, payload, "process_isolation_status", STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED)
    _expect(reasons, payload, "os_sandbox_status", STORE_WRITE_OS_SANDBOX_NOT_IMPLEMENTED)
    _expect(
        reasons,
        payload,
        "executor_code_execution_model",
        STORE_WRITE_EXECUTOR_CODE_EXECUTION_MODEL_STRUCTURED_ACTIONS_REQUIRED,
    )
    _expect(reasons, payload, "tamper_proof_claimed", False)
    _expect(reasons, payload, "physical_prevention_claimed", False)
    _expect(reasons, payload, "raw_bypass_impossible", False)
    _expect(reasons, payload, "arbitrary_in_process_code_safe", False)
    _expect(reasons, payload, "live_executor_ready", False)
    _expect(reasons, payload, "write_authority_safe", False)
    _expect(reasons, payload, "write_json_sink_guarded", True)
    _expect(reasons, payload, "ledger_append_sink_guarded", True)
    _expect(reasons, payload, "trusted_context_required", STORE_WRITE_TRUSTED_CONTEXT_REQUIRED)
    _expect(
        reasons,
        payload,
        "trusted_context_basis",
        STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
    )
    _expect(
        reasons,
        payload,
        "call_stack_inference_used_as_judgment_basis",
        STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
    )
    _expect(reasons, payload, "missing_context_result", STORE_WRITE_CONTEXT_RESULT_BLOCKED)
    _expect(reasons, payload, "omitted_declaration_result", STORE_WRITE_CONTEXT_RESULT_BLOCKED)
    _expect(
        reasons,
        payload,
        "executor_self_report_trusted_result",
        STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
    )
    _expect(reasons, payload, "store_write_mediation_binding_present", True)
    _expect(
        reasons,
        payload,
        "write_provenance_source",
        STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
    )
    _expect(
        reasons,
        payload,
        "write_provenance_basis",
        STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
    )
    _expect(reasons, payload, "trusted_runtime_write_allowed", True)
    _expect(reasons, payload, "trusted_runtime_ledger_append_allowed", True)
    _expect(reasons, payload, "executor_self_report_ignored", True)
    _expect(reasons, payload, "known_gap_non_aeg_status", STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED)
    _expect(reasons, payload, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
    _expect(reasons, payload, "phase11b_live_executor_status", PHASE11B_LIVE_EXECUTOR_NOT_STARTED)

    for field in (
        "store_write_mediation_enabled",
        "store_write_mediation_binding_present",
        "write_json_sink_guarded",
        "ledger_append_sink_guarded",
        "trusted_context_required",
        "trusted_context_security_boundary",
        "requires_structured_executor",
        "arbitrary_in_process_code_breaks_boundary",
        "tamper_proof_claimed",
        "physical_prevention_claimed",
        "raw_bypass_impossible",
        "arbitrary_in_process_code_safe",
        "live_executor_ready",
        "write_authority_safe",
        "call_stack_inference_used_as_judgment_basis",
        "executor_attributed_write_blocked",
        "trusted_runtime_write_allowed",
        "trusted_runtime_ledger_append_allowed",
        "executor_self_report_ignored",
        "executor_omitted_declaration_rejected",
        "rollback_used",
        "fallback_to_unwired",
        "fallback_evidence_recorded",
    ):
        if not isinstance(payload.get(field), bool):
            reasons.append(f"{field} must be boolean")

    if (
        payload.get("trusted_context_security_boundary") is True
        and payload.get("process_isolation_status") == STORE_WRITE_PROCESS_ISOLATION_NOT_IMPLEMENTED
    ):
        reasons.append(
            "trusted_context_security_boundary=true rejected while process_isolation_status is NOT_IMPLEMENTED"
        )
    if payload.get("tamper_proof_claimed") is True:
        reasons.append("tamper_proof_claimed=true rejected for in-process trusted-context guard")
    if payload.get("physical_prevention_claimed") is True:
        reasons.append("physical_prevention_claimed=true rejected for in-process trusted-context guard")
    if payload.get("raw_bypass_impossible") is True:
        reasons.append("raw_bypass_impossible=true rejected for in-process trusted-context guard")
    if payload.get("arbitrary_in_process_code_safe") is True:
        reasons.append("arbitrary_in_process_code_safe=true rejected for in-process trusted-context guard")
    if payload.get("live_executor_ready") is True:
        reasons.append("live_executor_ready=true rejected; live executor authority remains on hold")
    if payload.get("write_authority_safe") is True:
        reasons.append("write_authority_safe=true rejected; structured executor gate is not complete")
    for claim_path, claim_label in _forbidden_store_write_overclaim_paths(payload):
        reasons.append(f"{claim_label} claim rejected at {claim_path}")

    guarded_sinks = payload.get("guarded_sinks")
    if guarded_sinks != [STORE_WRITE_SINK_APPEND_LEDGER, STORE_WRITE_SINK_WRITE_JSON]:
        reasons.append("guarded_sinks must exactly cover _append_ledger_unmediated and _write_json")

    blocked_count = payload.get("blocked_write_target_count")
    created_count = payload.get("blocked_write_created_files_count")
    direct_created_count = payload.get("executor_direct_sink_write_created_files_count")
    direct_ledger_appended_count = payload.get("executor_direct_ledger_entries_appended_count")
    attempt_count = payload.get("store_write_attempt_count")
    for field, value in (
        ("blocked_write_target_count", blocked_count),
        ("blocked_write_created_files_count", created_count),
        ("executor_direct_sink_write_created_files_count", direct_created_count),
        ("executor_direct_ledger_entries_appended_count", direct_ledger_appended_count),
        ("store_write_attempt_count", attempt_count),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            reasons.append(f"{field} must be a non-negative integer")

    events = payload.get("store_write_mediation_events")
    if not isinstance(events, list):
        reasons.append("store_write_mediation_events must be a list")
        events = []
    elif not all(isinstance(event, Mapping) for event in events):
        reasons.append("store_write_mediation_events must contain only objects")
        events = [event for event in events if isinstance(event, Mapping)]

    normalized_events = [dict(event) for event in events]
    blocked_events = [
        event for event in normalized_events if event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED
    ]
    blocked_write_json_events = [
        event for event in blocked_events if event.get("sink_name") == STORE_WRITE_SINK_WRITE_JSON
    ]
    blocked_ledger_events = [
        event for event in blocked_events if event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
    ]
    trusted_events = [
        event
        for event in normalized_events
        if event.get("write_provenance_type") == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        and event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED
    ]
    trusted_write_json_events = [
        event for event in trusted_events if event.get("sink_name") == STORE_WRITE_SINK_WRITE_JSON
    ]
    trusted_ledger_events = [
        event for event in trusted_events if event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
    ]
    fallback_events = [event for event in normalized_events if event.get("fallback_to_unwired") is True]
    created_from_events = sum(1 for event in blocked_write_json_events if event.get("target_file_created") is True)
    ledger_appended_from_events = sum(
        _non_negative_int(event.get("ledger_entries_appended_count")) for event in blocked_ledger_events
    )
    guarded_sinks_from_events = sorted(
        {
            str(event.get("sink_name"))
            for event in normalized_events
            if event.get("sink_guarded") is True
            and event.get("store_write_boundary") == STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED
            and event.get("sink_name") in (STORE_WRITE_SINK_WRITE_JSON, STORE_WRITE_SINK_APPEND_LEDGER)
        }
    )

    if payload.get("guarded_sinks") != guarded_sinks_from_events:
        reasons.append("guarded_sinks overclaim rejected")
    if STORE_WRITE_SINK_WRITE_JSON not in guarded_sinks_from_events:
        reasons.append("SINK_LEVEL_GUARDED claim rejected: _write_json sink event missing")
    if STORE_WRITE_SINK_APPEND_LEDGER not in guarded_sinks_from_events:
        reasons.append("SINK_LEVEL_GUARDED claim rejected: _append_ledger_unmediated sink event missing")

    if isinstance(blocked_count, int) and not isinstance(blocked_count, bool) and blocked_count != len(blocked_write_json_events):
        reasons.append("blocked_write_target_count mismatch")
    if isinstance(created_count, int) and not isinstance(created_count, bool) and created_count != created_from_events:
        reasons.append("blocked_write_created_files_count mismatch")
    if (
        isinstance(direct_created_count, int)
        and not isinstance(direct_created_count, bool)
        and direct_created_count != created_from_events
    ):
        reasons.append("executor_direct_sink_write_created_files_count mismatch")
    if (
        isinstance(direct_ledger_appended_count, int)
        and not isinstance(direct_ledger_appended_count, bool)
        and direct_ledger_appended_count != ledger_appended_from_events
    ):
        reasons.append("executor_direct_ledger_entries_appended_count mismatch")
    if isinstance(attempt_count, int) and not isinstance(attempt_count, bool) and attempt_count != len(normalized_events):
        reasons.append("store_write_attempt_count mismatch")
    if payload.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED and created_count != 0:
        reasons.append("blocked_write_created_files_count > 0 cannot support BLOCKED claim")
    if payload.get("executor_direct_sink_write_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED and direct_created_count != 0:
        reasons.append("executor direct sink BLOCKED claim rejected because target file exists")
    if payload.get("executor_direct_ledger_append_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED and direct_ledger_appended_count != 0:
        reasons.append("executor direct ledger BLOCKED claim rejected because forged entry appended")
    if blocked_write_json_events:
        _expect(reasons, payload, "executor_direct_sink_write_result", STORE_WRITE_MEDIATION_RESULT_BLOCKED)
    else:
        _expect(
            reasons,
            payload,
            "executor_direct_sink_write_result",
            STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT,
        )
    if blocked_ledger_events:
        _expect(reasons, payload, "executor_direct_ledger_append_result", STORE_WRITE_MEDIATION_RESULT_BLOCKED)
    else:
        _expect(
            reasons,
            payload,
            "executor_direct_ledger_append_result",
            STORE_WRITE_MEDIATION_RESULT_NO_EXECUTOR_ATTEMPT,
        )
    if blocked_events and payload.get("executor_attributed_write_blocked") is not True:
        reasons.append("executor_attributed_write_blocked mismatch")
    if blocked_events and payload.get("known_gap_aeg_direct_traversal_status") != STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED:
        reasons.append("known-gap .aeg direct/traversal status was not BLOCKED")
    if not blocked_events and payload.get("known_gap_aeg_direct_traversal_status") not in (
        STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_NO_ATTEMPT,
        STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED,
    ):
        reasons.append("known-gap .aeg direct/traversal status mismatch")
    if not trusted_write_json_events:
        reasons.append("trusted runtime write was not allowed")
    if not trusted_ledger_events:
        reasons.append("trusted runtime ledger append was not allowed")
    if payload.get("rollback_used") is not bool(fallback_events):
        reasons.append("rollback_used mismatch")
    if payload.get("fallback_to_unwired") is not bool(fallback_events):
        reasons.append("fallback_to_unwired mismatch")
    if payload.get("fallback_evidence_recorded") is not bool(fallback_events):
        reasons.append("fallback evidence recorded mismatch")
    omitted_rejected_from_events = any(
        event.get("executor_omitted_declaration") is True
        and event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED
        for event in normalized_events
    )
    if payload.get("executor_omitted_declaration_rejected") is not omitted_rejected_from_events:
        reasons.append("executor_omitted_declaration_rejected mismatch")

    reasons.extend(_event_rejection_reasons(normalized_events))

    metadata_hash = payload.get("store_write_mediation_metadata_hash")
    expected_hash = expected_store_write_mediation_metadata_hash(payload)
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        reasons.append("store_write_mediation_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_hash:
        reasons.append("store_write_mediation_metadata_hash mismatch")

    accepted = not reasons
    return {
        "accepted": accepted,
        "status": (
            STORE_WRITE_MEDIATION_VERIFICATION_ACCEPTED
            if accepted
            else STORE_WRITE_MEDIATION_VERIFICATION_REJECTED
        ),
        "rejection_reasons": _unique(reasons),
        "verification_scope": "phase11b0_store_write_mediation_actual_runtime_replay",
        "safe_default": SAFE_DEFAULT,
    }


def _summary_result_and_reason(
    *,
    blocked_events: Sequence[Mapping[str, Any]],
    trusted_allowed_events: Sequence[Mapping[str, Any]],
    fallback_events: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    if fallback_events:
        return (
            STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED,
            "fallback_to_unwired_recorded_for_trusted_runtime_write",
        )
    if blocked_events:
        return STORE_WRITE_MEDIATION_RESULT_BLOCKED, STORE_WRITE_MEDIATION_REASON_EXECUTOR_AEG_BLOCKED
    if trusted_allowed_events:
        return (
            STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED,
            STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_ALLOWED,
        )
    return "NO_STORE_WRITE_ATTEMPT", "no_store_write_attempt_recorded"


def _non_negative_int(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def _event_rejection_reasons(events: Sequence[Mapping[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for index, event in enumerate(events):
        label = f"store_write_mediation_events[{index}]"
        _expect(reasons, event, "store_write_boundary", STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED, label)
        _expect(reasons, event, "write_provenance_source", STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT, label)
        _expect(reasons, event, "write_provenance_basis", STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY, label)
        _expect(reasons, event, "live_executor_authority", LIVE_EXECUTOR_AUTHORITY_ON_HOLD, label)
        _expect(reasons, event, "phase11b_live_executor_status", PHASE11B_LIVE_EXECUTOR_NOT_STARTED, label)
        _expect(reasons, event, "trusted_context_required", STORE_WRITE_TRUSTED_CONTEXT_REQUIRED, label)
        _expect(
            reasons,
            event,
            "trusted_context_basis",
            STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
            label,
        )
        _expect(
            reasons,
            event,
            "call_stack_inference_used_as_judgment_basis",
            STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
            label,
        )
        if event.get("sink_name") not in (STORE_WRITE_SINK_WRITE_JSON, STORE_WRITE_SINK_APPEND_LEDGER):
            reasons.append(f"{label} sink_name must identify a guarded store.py sink")
        if event.get("sink_guarded") is not True:
            reasons.append(f"{label} sink_guarded must be true")
        if event.get("caller_name_match_used_as_judgment_basis") is True:
            reasons.append(f"{label} caller-name match trusted provenance rejected")
        if event.get("executor_self_report_used") is True:
            reasons.append(f"{label} executor self-report trusted provenance rejected")
        if event.get("trusted_runtime_claim_allowed") is True:
            reasons.append(f"{label} trusted runtime self-report claim rejected")
        if event.get("executor_self_report_trusted_result") == "ACCEPTED":
            reasons.append(f"{label} executor self-report trusted provenance accepted")
        if event.get("missing_context_result") == "ALLOWED":
            reasons.append(f"{label} missing context accepted as trusted")
        if event.get("omitted_declaration_result") in ("ACCEPTED", "TRUSTED", "ALLOWED"):
            reasons.append(f"{label} omitted declaration accepted as trusted")
        if event.get("executor_claimed_provenance") == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME:
            if event.get("write_provenance_type") != STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED:
                reasons.append(f"{label} executor self-report trusted provenance accepted")
        if event.get("write_provenance_type") == STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED:
            if event.get("write_mediation_result") == STORE_WRITE_MEDIATION_RESULT_BLOCKED:
                if event.get("write_performed") is not False:
                    reasons.append(f"{label} blocked executor write recorded a write")
                if event.get("target_file_created") is not False:
                    reasons.append(f"{label} blocked executor write created a target file")
                if event.get("target_exists_after") is True and event.get("sink_name") == STORE_WRITE_SINK_WRITE_JSON:
                    reasons.append(f"{label} blocked executor write target exists after BLOCKED")
                if (
                    event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
                    and _non_negative_int(event.get("ledger_entries_appended_count")) != 0
                ):
                    reasons.append(f"{label} blocked executor ledger append created a forged entry")
                if event.get("guard_router_invoked") is not True:
                    reasons.append(f"{label} executor-attributed block lacks guard/router invocation")
                if event.get("fallback_to_unwired") is True:
                    reasons.append(f"{label} executor-attributed block must not fallback to unwired write")
            elif event.get("write_mediation_result") != STORE_WRITE_MEDIATION_RESULT_OUT_OF_SCOPE_UNCHANGED:
                reasons.append(f"{label} executor-attributed write was not blocked or marked out of scope")
        if event.get("write_provenance_type") == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME:
            if event.get("write_mediation_result") != STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED:
                reasons.append(f"{label} trusted runtime write was not allowed")
            if event.get("write_performed") is not True:
                reasons.append(f"{label} trusted runtime write did not record performed write")
            if event.get("trusted_context_valid") is not True:
                reasons.append(f"{label} trusted runtime write lacks valid runtime-owned trusted context")
            if event.get("trusted_capability_runtime_owned") is not True:
                reasons.append(f"{label} trusted runtime write lacks runtime-owned capability")
            if event.get("target_exists_after") is not True:
                reasons.append(f"{label} trusted runtime write preserved claim rejected because target is missing")
            if (
                event.get("sink_name") == STORE_WRITE_SINK_APPEND_LEDGER
                and _non_negative_int(event.get("ledger_entries_appended_count")) <= 0
            ):
                reasons.append(f"{label} trusted runtime ledger append preserved claim rejected because append failed")
    return reasons


def _expect(
    reasons: list[str],
    record: Mapping[str, Any],
    field: str,
    expected: Any,
    label: str = "store_write_mediation",
) -> None:
    if record.get(field) != expected:
        reasons.append(f"{label} {field} mismatch")


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _forbidden_store_write_overclaim_paths(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(_forbidden_store_write_overclaim_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_store_write_overclaim_paths(child, child_path))
    elif isinstance(value, str) and value in FORBIDDEN_STORE_WRITE_OVERCLAIM_LABELS:
        paths.append((prefix or "<root>", value))
    return paths


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "STORE_WRITE_MEDIATION_VERIFICATION_ACCEPTED",
    "STORE_WRITE_MEDIATION_VERIFICATION_REJECTED",
    "build_store_write_mediation_metadata",
    "expected_store_write_mediation_metadata_hash",
    "store_write_mediation_manifest_fields",
    "verify_store_write_mediation_metadata",
]
