"""Phase 11-B-3-6 store-adjacent runtime seal evidence.

This module is metadata and verification only. It records and verifies, under
the structured executor assumption, that store-adjacent candidate data is
admitted only from a runtime-built ``ActionDecisionPacket`` path while store.py
sink writes remain covered by the existing sink guard. It does not call
providers, execute actions, mutate files, apply patches, or grant write
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from src.contracts import (
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    SAFE_DEFAULT,
    STORE_ADJACENT_PACKET_ORIGIN_BASIS_RUNTIME_BUILD_PATH,
    STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL,
    STORE_ADJACENT_RUNTIME_SEAL_FIELDS,
    STORE_ADJACENT_RUNTIME_SEAL_LIMITS,
    STORE_ADJACENT_RUNTIME_SEAL_V0,
    STORE_ADJACENT_SEALING_FAILURE_FALLBACK_NONE,
    STORE_ADJACENT_SEALING_FAILURE_FALLBACK_RECORDED,
)
from src.evidence.action_decision_routing import (
    DENIED_CAPABILITY_STORE_PATH_REJECTED,
    DIRECT_PACKET_SUBMISSION_STORE_PATH_REJECTED,
    PACKET_EVIDENCE_STORE_PATH_REJECTED,
    RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
    REPORTED_ONLY_STORE_PATH_REJECTED,
    SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    UNVALIDATED_ACTION_STORE_PATH_REJECTED,
    evaluate_store_adjacent_candidate_gate,
)
from src.evidence.executor_output_ingress import (
    ActionDecisionPacket,
    RUNTIME_INGRESS_ADAPTER,
    ingest_executor_output,
)
from src.evidence.structured_action_capabilities import CAPABILITY_GATE_ALLOWED
from src.evidence.structured_actions import NOOP

STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED = (
    "STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED"
)
STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED = (
    "STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED"
)

_FORCED_STORE_ADJACENT_RUNTIME_PATH = (
    "raw_executor_output",
    "executor_output_ingress",
    "parse_normalize",
    "validate_structured_action",
    "evaluate_action_capabilities",
    "runtime_built_action_decision_packet",
    "action_decision_packet_evidence_verify",
    "metadata_only_store_adjacent_candidate_guard",
    "store_adjacent_decision",
    "stop",
)

_EXPECTED_REJECTION_STATUSES = {
    "direct_packet_submission": DIRECT_PACKET_SUBMISSION_STORE_PATH_REJECTED,
    "executor_built_packet": PACKET_EVIDENCE_STORE_PATH_REJECTED,
    "created_by_text_ownership": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "packet_id_text_ownership": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "capability_gate_result_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "execution_allowed_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "mutation_allowed_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "write_authority_granted_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "store_routing_allowed_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "store_path_reachable_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "live_executor_ready_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "authority_promotion_self_report": SELF_REPORTED_AUTHORITY_STORE_PATH_REJECTED,
    "raw_store_adjacent_path": RAW_EXECUTOR_OUTPUT_STORE_PATH_REJECTED,
    "unvalidated_store_adjacent_path": UNVALIDATED_ACTION_STORE_PATH_REJECTED,
    "denied_store_adjacent_path": DENIED_CAPABILITY_STORE_PATH_REJECTED,
    "reported_only_store_adjacent_path": REPORTED_ONLY_STORE_PATH_REJECTED,
}


def build_store_adjacent_runtime_seal_metadata(
    *,
    raw_store_sink_bypass_rejected: bool,
    direct_write_json_bypass_created_files_count: int,
    direct_ledger_bypass_appended_count: int,
    trusted_runtime_write_preserved: bool,
    trusted_runtime_ledger_preserved: bool,
    fallback_to_unwired: bool,
) -> dict[str, Any]:
    """Build digest-bound metadata for the store-adjacent runtime seal."""

    rejection_fixtures = _build_rejection_fixture_records()
    rejection_by_name = {
        str(record.get("fixture_name")): record for record in rejection_fixtures
    }
    accepted_gate = evaluate_store_adjacent_candidate_gate(
        ingest_executor_output(_valid_noop_action("runtime-seal-accepted-metadata"))
    )
    fallback_status = (
        STORE_ADJACENT_SEALING_FAILURE_FALLBACK_RECORDED
        if fallback_to_unwired
        else STORE_ADJACENT_SEALING_FAILURE_FALLBACK_NONE
    )

    record: dict[str, Any] = {
        "phase11b_3_6_store_adjacent_runtime_seal_version": (
            STORE_ADJACENT_RUNTIME_SEAL_V0
        ),
        "phase11b_3_6_store_adjacent_runtime_seal_label": (
            STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL
        ),
        "phase11b_3_6_store_adjacent_runtime_seal_limits": (
            STORE_ADJACENT_RUNTIME_SEAL_LIMITS
        ),
        "store_adjacent_runtime_seal_enabled": True,
        "runtime_build_packet_only_enforced": True,
        "packet_origin_basis": STORE_ADJACENT_PACKET_ORIGIN_BASIS_RUNTIME_BUILD_PATH,
        "forced_store_adjacent_runtime_path": _FORCED_STORE_ADJACENT_RUNTIME_PATH,
        "direct_packet_submission_rejected": _fixture_rejected(
            rejection_by_name,
            "direct_packet_submission",
        ),
        "executor_built_packet_rejected": _fixture_rejected(
            rejection_by_name,
            "executor_built_packet",
        ),
        "created_by_text_ownership_rejected": _fixture_rejected(
            rejection_by_name,
            "created_by_text_ownership",
        ),
        "packet_id_text_ownership_rejected": _fixture_rejected(
            rejection_by_name,
            "packet_id_text_ownership",
        ),
        "capability_gate_result_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "capability_gate_result_self_report",
        ),
        "execution_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "execution_allowed_self_report",
        ),
        "mutation_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "mutation_allowed_self_report",
        ),
        "write_authority_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "write_authority_granted_self_report",
        ),
        "store_routing_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "store_routing_allowed_self_report",
        ),
        "store_path_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "store_path_reachable_self_report",
        ),
        "live_executor_self_report_rejected": _fixture_rejected(
            rejection_by_name,
            "live_executor_ready_self_report",
        ),
        "authority_promotion_rejected": _fixture_rejected(
            rejection_by_name,
            "authority_promotion_self_report",
        ),
        "raw_store_adjacent_path_rejected": _fixture_rejected(
            rejection_by_name,
            "raw_store_adjacent_path",
        ),
        "unvalidated_store_adjacent_path_rejected": _fixture_rejected(
            rejection_by_name,
            "unvalidated_store_adjacent_path",
        ),
        "denied_store_adjacent_path_rejected": _fixture_rejected(
            rejection_by_name,
            "denied_store_adjacent_path",
        ),
        "reported_only_store_adjacent_path_rejected": _fixture_rejected(
            rejection_by_name,
            "reported_only_store_adjacent_path",
        ),
        "accepted_store_adjacent_candidate_metadata_only": (
            accepted_gate.candidate_accepted
            and accepted_gate.gate_status == STORE_ADJACENT_CANDIDATE_ACCEPTED
            and accepted_gate.store_adjacent_candidate_gate_metadata_only is True
        ),
        "accepted_store_adjacent_candidate_store_routing_allowed": (
            accepted_gate.store_routing_allowed
        ),
        "accepted_store_adjacent_candidate_store_path_reachable": (
            accepted_gate.store_path_reachable
        ),
        "accepted_store_adjacent_candidate_execution_allowed": (
            accepted_gate.execution_allowed
        ),
        "accepted_store_adjacent_candidate_mutation_allowed": (
            accepted_gate.mutation_allowed
        ),
        "accepted_store_adjacent_candidate_write_authority_granted": (
            accepted_gate.write_authority_granted
        ),
        "raw_store_sink_bypass_rejected": raw_store_sink_bypass_rejected,
        "direct_write_json_bypass_created_files_count": (
            direct_write_json_bypass_created_files_count
        ),
        "direct_ledger_bypass_appended_count": direct_ledger_bypass_appended_count,
        "trusted_runtime_write_preserved": trusted_runtime_write_preserved,
        "trusted_runtime_ledger_preserved": trusted_runtime_ledger_preserved,
        "sealing_failure_fallback_status": fallback_status,
        "sealing_failed": False,
        "sealing_pass_claimed": False,
        "fallback_success_claimed": False,
        "store_adjacent_runtime_seal_rejection_fixtures": rejection_fixtures,
        "store_adjacent_runtime_seal_fixture_count": len(rejection_fixtures),
    }
    record["store_adjacent_runtime_seal_metadata_hash"] = (
        expected_store_adjacent_runtime_seal_metadata_hash(record)
    )
    return record


def expected_store_adjacent_runtime_seal_metadata_hash(
    payload: Mapping[str, Any],
) -> str:
    material = {
        field: payload.get(field)
        for field in STORE_ADJACENT_RUNTIME_SEAL_FIELDS
        if field != "store_adjacent_runtime_seal_metadata_hash"
    }
    return _sha256_json(material)


def verify_store_adjacent_runtime_seal_metadata(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify store-adjacent runtime seal metadata and reject overclaims."""

    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        payload = {}
        reasons.append("store-adjacent runtime seal evidence must be a mapping")

    for field in STORE_ADJACENT_RUNTIME_SEAL_FIELDS:
        if field not in payload:
            reasons.append(f"missing store-adjacent runtime seal field: {field}")

    _expect(
        reasons,
        payload,
        "phase11b_3_6_store_adjacent_runtime_seal_version",
        STORE_ADJACENT_RUNTIME_SEAL_V0,
    )
    _expect(
        reasons,
        payload,
        "phase11b_3_6_store_adjacent_runtime_seal_label",
        STORE_ADJACENT_RUNTIME_SEAL_COMPLETE_LABEL,
    )
    _expect(
        reasons,
        payload,
        "phase11b_3_6_store_adjacent_runtime_seal_limits",
        STORE_ADJACENT_RUNTIME_SEAL_LIMITS,
    )
    _expect(reasons, payload, "store_adjacent_runtime_seal_enabled", True)
    _expect(reasons, payload, "runtime_build_packet_only_enforced", True)
    _expect(
        reasons,
        payload,
        "packet_origin_basis",
        STORE_ADJACENT_PACKET_ORIGIN_BASIS_RUNTIME_BUILD_PATH,
    )
    _expect(
        reasons,
        payload,
        "forced_store_adjacent_runtime_path",
        _FORCED_STORE_ADJACENT_RUNTIME_PATH,
    )

    required_true_fields = (
        "direct_packet_submission_rejected",
        "executor_built_packet_rejected",
        "created_by_text_ownership_rejected",
        "packet_id_text_ownership_rejected",
        "capability_gate_result_self_report_rejected",
        "execution_self_report_rejected",
        "mutation_self_report_rejected",
        "write_authority_self_report_rejected",
        "store_routing_self_report_rejected",
        "store_path_self_report_rejected",
        "live_executor_self_report_rejected",
        "authority_promotion_rejected",
        "raw_store_adjacent_path_rejected",
        "unvalidated_store_adjacent_path_rejected",
        "denied_store_adjacent_path_rejected",
        "reported_only_store_adjacent_path_rejected",
        "accepted_store_adjacent_candidate_metadata_only",
        "trusted_runtime_write_preserved",
        "trusted_runtime_ledger_preserved",
    )
    required_false_fields = (
        "accepted_store_adjacent_candidate_store_routing_allowed",
        "accepted_store_adjacent_candidate_store_path_reachable",
        "accepted_store_adjacent_candidate_execution_allowed",
        "accepted_store_adjacent_candidate_mutation_allowed",
        "accepted_store_adjacent_candidate_write_authority_granted",
        "sealing_failed",
        "sealing_pass_claimed",
        "fallback_success_claimed",
    )
    boolean_fields = (
        "store_adjacent_runtime_seal_enabled",
        "runtime_build_packet_only_enforced",
        "raw_store_sink_bypass_rejected",
        *required_true_fields,
        *required_false_fields,
    )
    for field in boolean_fields:
        if not isinstance(payload.get(field), bool):
            reasons.append(f"{field} must be boolean")
    for field in required_true_fields:
        if payload.get(field) is not True:
            reasons.append(f"{field} must be true")
    for field in required_false_fields:
        if payload.get(field) is not False:
            reasons.append(f"{field}=true rejected")

    for field in (
        "direct_write_json_bypass_created_files_count",
        "direct_ledger_bypass_appended_count",
        "store_adjacent_runtime_seal_fixture_count",
    ):
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            reasons.append(f"{field} must be a non-negative integer")

    if payload.get("direct_write_json_bypass_created_files_count") != 0:
        reasons.append("direct write_json bypass created files count must be 0")
    if payload.get("direct_ledger_bypass_appended_count") != 0:
        reasons.append("direct ledger bypass appended count must be 0")

    fallback_status = payload.get("sealing_failure_fallback_status")
    if fallback_status not in (
        STORE_ADJACENT_SEALING_FAILURE_FALLBACK_NONE,
        STORE_ADJACENT_SEALING_FAILURE_FALLBACK_RECORDED,
    ):
        reasons.append("sealing_failure_fallback_status mismatch")
    fallback_to_unwired = payload.get("fallback_to_unwired")
    if fallback_to_unwired is True:
        if fallback_status == STORE_ADJACENT_SEALING_FAILURE_FALLBACK_NONE:
            reasons.append("fallback used but sealing fallback status claims none")
        if payload.get("fallback_success_claimed") is True:
            reasons.append("fallback used but success claimed")
    elif fallback_status != STORE_ADJACENT_SEALING_FAILURE_FALLBACK_NONE:
        reasons.append("fallback status recorded without fallback evidence")
    if payload.get("sealing_failed") is True and payload.get("sealing_pass_claimed") is True:
        reasons.append("sealing failed but pass claimed")

    if payload.get("live_executor_authority") not in (
        None,
        LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    ):
        reasons.append("live executor authority promotion rejected")
    if payload.get("safe_default") not in (None, SAFE_DEFAULT):
        reasons.append("safe_default must remain hold_current_state")

    fixtures = payload.get("store_adjacent_runtime_seal_rejection_fixtures")
    if not isinstance(fixtures, list):
        reasons.append("store_adjacent_runtime_seal_rejection_fixtures must be a list")
        fixtures = []
    elif not all(isinstance(fixture, Mapping) for fixture in fixtures):
        reasons.append(
            "store_adjacent_runtime_seal_rejection_fixtures must contain only objects"
        )
        fixtures = [fixture for fixture in fixtures if isinstance(fixture, Mapping)]

    if payload.get("store_adjacent_runtime_seal_fixture_count") != len(fixtures):
        reasons.append("store_adjacent_runtime_seal_fixture_count mismatch")
    reasons.extend(_fixture_rejection_reasons(fixtures))

    metadata_hash = payload.get("store_adjacent_runtime_seal_metadata_hash")
    expected_hash = expected_store_adjacent_runtime_seal_metadata_hash(payload)
    if not isinstance(metadata_hash, str) or not _is_sha256_hex(metadata_hash):
        reasons.append("store_adjacent_runtime_seal_metadata_hash must be sha256 hex")
    elif metadata_hash != expected_hash:
        reasons.append("store_adjacent_runtime_seal_metadata_hash mismatch")

    accepted = not reasons
    return {
        "accepted": accepted,
        "status": (
            STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED
            if accepted
            else STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED
        ),
        "rejection_reasons": _unique(reasons),
        "verification_scope": "phase11b_3_6_store_adjacent_runtime_seal",
        "safe_default": SAFE_DEFAULT,
    }


def _build_rejection_fixture_records() -> list[dict[str, Any]]:
    runtime_packet = ingest_executor_output(_valid_noop_action("runtime-packet-source"))
    direct_packet = {
        "packet_id": runtime_packet.packet_id,
        "raw_output_hash": runtime_packet.raw_output_hash,
        "parse_status": runtime_packet.parse_status,
        "parse_error": runtime_packet.parse_error,
        "normalized_action": _jsonable(runtime_packet.normalized_action),
        "decision_basis": tuple(runtime_packet.decision_basis),
        "adapter_version": runtime_packet.adapter_version,
        "created_by": runtime_packet.created_by,
    }
    executor_built_packet = ActionDecisionPacket(
        packet_id=runtime_packet.packet_id,
        raw_output_hash=runtime_packet.raw_output_hash,
        parse_status=runtime_packet.parse_status,
        parse_error=runtime_packet.parse_error,
        normalized_action=runtime_packet.normalized_action,
        validation_result=runtime_packet.validation_result,
        capability_result=runtime_packet.capability_result,
        decision_basis=runtime_packet.decision_basis,
        ignored_reported_only_fields=runtime_packet.ignored_reported_only_fields,
        created_by=RUNTIME_INGRESS_ADAPTER,
    )
    fixtures: tuple[tuple[str, Any], ...] = (
        ("direct_packet_submission", direct_packet),
        ("executor_built_packet", executor_built_packet),
        (
            "created_by_text_ownership",
            _self_report_packet("created_by", RUNTIME_INGRESS_ADAPTER),
        ),
        (
            "packet_id_text_ownership",
            _self_report_packet("packet_id", "action-decision-packet-forged"),
        ),
        (
            "capability_gate_result_self_report",
            _self_report_packet("capability_gate_result", CAPABILITY_GATE_ALLOWED),
        ),
        ("execution_allowed_self_report", _self_report_packet("execution_allowed", True)),
        ("mutation_allowed_self_report", _self_report_packet("mutation_allowed", True)),
        (
            "write_authority_granted_self_report",
            _self_report_packet("write_authority_granted", True),
        ),
        (
            "store_routing_allowed_self_report",
            _self_report_packet("store_routing_allowed", True),
        ),
        (
            "store_path_reachable_self_report",
            _self_report_packet("store_path_reachable", True),
        ),
        (
            "live_executor_ready_self_report",
            _self_report_packet("live_executor_ready", True),
        ),
        (
            "authority_promotion_self_report",
            _self_report_packet("live_executor_authority", "PROMOTED"),
        ),
        ("raw_store_adjacent_path", _valid_noop_action("raw-store-adjacent")),
        (
            "unvalidated_store_adjacent_path",
            ingest_executor_output(
                {
                    "action_type": NOOP,
                    "action_id": "runtime-seal-unvalidated",
                }
            ),
        ),
        (
            "denied_store_adjacent_path",
            ingest_executor_output(
                _valid_noop_action(
                    "runtime-seal-denied",
                    capability_requirements=("network",),
                )
            ),
        ),
        (
            "reported_only_store_adjacent_path",
            ingest_executor_output(
                _valid_noop_action(
                    "runtime-seal-reported-only",
                    payload={
                        "authority": "write_file",
                        "approved_by_executor": True,
                    },
                )
            ),
        ),
    )

    records: list[dict[str, Any]] = []
    for fixture_name, candidate in fixtures:
        gate = evaluate_store_adjacent_candidate_gate(candidate)
        records.append(
            {
                "fixture_name": fixture_name,
                "expected_gate_status": _EXPECTED_REJECTION_STATUSES[fixture_name],
                "actual_gate_status": gate.gate_status,
                "candidate_accepted": gate.candidate_accepted,
                "store_adjacent_candidate": gate.store_adjacent_candidate,
                "store_adjacent_candidate_gate_metadata_only": (
                    gate.store_adjacent_candidate_gate_metadata_only
                ),
                "store_routing_allowed": gate.store_routing_allowed,
                "store_path_reachable": gate.store_path_reachable,
                "execution_allowed": gate.execution_allowed,
                "mutation_allowed": gate.mutation_allowed,
                "write_authority_granted": gate.write_authority_granted,
                "live_executor_ready": gate.live_executor_ready,
                "live_executor_authority": gate.live_executor_authority,
                "safe_default": gate.safe_default,
            }
        )
    return records


def _fixture_rejection_reasons(fixtures: Sequence[Mapping[str, Any]]) -> list[str]:
    reasons: list[str] = []
    by_name = {str(fixture.get("fixture_name")): fixture for fixture in fixtures}
    if set(by_name) != set(_EXPECTED_REJECTION_STATUSES):
        reasons.append("store-adjacent runtime seal rejection fixture coverage mismatch")
    for fixture_name, expected_status in _EXPECTED_REJECTION_STATUSES.items():
        fixture = by_name.get(fixture_name)
        if fixture is None:
            reasons.append(f"missing store-adjacent runtime seal fixture: {fixture_name}")
            continue
        label = f"store_adjacent_runtime_seal_rejection_fixtures[{fixture_name}]"
        if fixture.get("expected_gate_status") != expected_status:
            reasons.append(f"{label} expected_gate_status mismatch")
        if fixture.get("actual_gate_status") != expected_status:
            reasons.append(f"{label} actual_gate_status mismatch")
        if fixture.get("candidate_accepted") is not False:
            reasons.append(f"{label} candidate_accepted must be false")
        if fixture.get("store_adjacent_candidate") is not False:
            reasons.append(f"{label} store_adjacent_candidate must be false")
        for field in (
            "store_routing_allowed",
            "store_path_reachable",
            "execution_allowed",
            "mutation_allowed",
            "write_authority_granted",
            "live_executor_ready",
        ):
            if fixture.get(field) is not False:
                reasons.append(f"{label} {field}=true rejected")
        if fixture.get("live_executor_authority") != LIVE_EXECUTOR_AUTHORITY_ON_HOLD:
            reasons.append(f"{label} live executor authority promotion rejected")
        if fixture.get("safe_default") != SAFE_DEFAULT:
            reasons.append(f"{label} safe_default mismatch")
    return reasons


def _fixture_rejected(
    rejection_by_name: Mapping[str, Mapping[str, Any]],
    fixture_name: str,
) -> bool:
    fixture = rejection_by_name.get(fixture_name, {})
    return (
        fixture.get("actual_gate_status") == _EXPECTED_REJECTION_STATUSES[fixture_name]
        and fixture.get("candidate_accepted") is False
    )


def _self_report_packet(field: str, value: Any) -> ActionDecisionPacket:
    return ingest_executor_output(
        {
            "action": _valid_noop_action(f"runtime-seal-self-report-{field}"),
            field: value,
        }
    )


def _valid_noop_action(
    action_id: str,
    *,
    capability_requirements: Sequence[str] = ("noop",),
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "action_type": NOOP,
        "action_id": action_id,
        "declared_intent": "Store-adjacent runtime seal fixture data.",
        "declared_risk": "LOW",
        "capability_requirements": list(capability_requirements),
        "target_scope": {"repo_relative": True, "paths": []},
        "payload": dict(payload or {}),
    }


def _expect(
    reasons: list[str],
    record: Mapping[str, Any],
    field: str,
    expected: Any,
) -> None:
    actual = record.get(field)
    if isinstance(expected, tuple) and isinstance(actual, list):
        actual = tuple(actual)
    if actual != expected:
        reasons.append(f"{field} mismatch")


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _jsonable(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if _is_sequence(value):
        return [_jsonable(nested) for nested in value]
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


__all__ = [
    "STORE_ADJACENT_RUNTIME_SEAL_VERIFY_ACCEPTED",
    "STORE_ADJACENT_RUNTIME_SEAL_VERIFY_REJECTED",
    "build_store_adjacent_runtime_seal_metadata",
    "expected_store_adjacent_runtime_seal_metadata_hash",
    "verify_store_adjacent_runtime_seal_metadata",
]
