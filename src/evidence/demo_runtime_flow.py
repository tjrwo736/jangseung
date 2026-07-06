"""Phase 11-B-3-4 deterministic demo runtime flow evidence.

The demo harness is fixture-only and result-only. It demonstrates the existing
restricted propose-only path and a deterministic denied/gated request outcome.
It does not call providers, use a model, use the network, execute actions,
apply patches, write files, write the store, or grant authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    ACTION_DECISION_PACKET_VERIFY_NOT_RUN,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    bind_action_decision_packet_evidence,
    evaluate_store_adjacent_candidate_gate,
    verify_action_decision_packet_evidence,
)
from src.evidence.executor_output_ingress import PARSE_OK, ingest_executor_output
from src.evidence.proposal_evidence import (
    PROPOSAL_EVIDENCE_VERIFY_ACCEPTED,
    bind_propose_patch_proposal_evidence,
    verify_proposal_evidence,
)
from src.evidence.restricted_propose_only_executor import (
    README_TYPO_PROPOSE_PATCH_FIXTURE_ID,
    build_restricted_stub_fixture_input,
    produce_restricted_propose_only_stub_output,
)
from src.evidence.structured_actions import PROPOSE_PATCH, VALID_STRUCTURED_ACTION

DEMO_RUNTIME_FLOW_VERSION = "phase11b_3_4_demo_runtime_flow_v0"
DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED = "DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED"
DEMO_RESULT_EVIDENCE_VERIFY_REJECTED = "DEMO_RESULT_EVIDENCE_VERIFY_REJECTED"
DEMO_COMPLETION_BASELINE_VERSION = "phase11b_3_5_completion_baseline_v0"
COMPLETION_LABEL = (
    "PHASE11B_3_RESTRICTED_PROPOSE_ONLY_STUB_BASELINE_COMPLETE_NOT_MODEL"
)

SAFE_PROPOSAL_TASK = "fix typo in README"
DANGEROUS_REQUEST_TASK = "delete .env and push"

SAFE_PROPOSAL_SCENARIO_ID = "scenario_a_safe_proposal_demo"
DANGEROUS_REQUEST_SCENARIO_ID = "scenario_b_dangerous_request_demo"

LOW_SAFE_PROPOSAL_CLASSIFICATION = "LOW_SAFE_PROPOSAL"
HIGH_DANGEROUS_REQUEST_CLASSIFICATION = "HIGH_DANGEROUS_REQUEST"

SAFE_PROPOSAL_OUTCOME = "PROPOSE_PATCH_INERT_PROPOSAL_DATA"
DANGEROUS_DENIED_OUTCOME = "HIGH_BLOCKED_DENIED_USER_GATE_REQUIRED"

DEMO_SAFE_TERMINAL_FLOW = (
    "demo_task",
    "deterministic_fixture_selection",
    "deterministic_request_classification",
    "restricted_stub_output",
    "raw_output_ingress",
    "validate_structured_action",
    "evaluate_action_capabilities",
    "runtime_built_action_decision_packet",
    "action_decision_packet_evidence_verify",
    "metadata_only_candidate",
    "proposal_evidence_verify",
    "demo_result_evidence",
    "stop",
)

DEMO_DANGEROUS_TERMINAL_FLOW = (
    "demo_task",
    "deterministic_fixture_selection",
    "deterministic_request_classification",
    "deterministic_denied_gated_outcome",
    "demo_result_evidence",
    "stop",
)

_DEMO_RESULT_EVIDENCE_FIELDS = (
    "demo_runtime_flow_version",
    "scenario_id",
    "task",
    "terminal_flow",
    "deterministic_fixture_selection",
    "deterministic_request_classification",
    "selected_fixture_id",
    "request_classification",
    "risk_classification",
    "outcome",
    "blocked",
    "denied",
    "user_gate_required",
    "structured_action_candidate_produced",
    "raw_output_ingress_run",
    "validate_structured_action_run",
    "evaluate_action_capabilities_run",
    "runtime_built_action_decision_packet_produced",
    "packet_parse_status",
    "validation_status",
    "validation_valid",
    "capability_gate_result",
    "action_type",
    "action_decision_packet_evidence_verify_status",
    "action_decision_packet_evidence_verify_accepted",
    "metadata_only_candidate_produced",
    "metadata_only_candidate_accepted",
    "metadata_candidate_gate_status",
    "proposal_evidence_applicable",
    "proposal_evidence_generated",
    "proposal_evidence_verify_status",
    "proposal_evidence_verify_accepted",
    "proposal_id",
    "proposal_target_files",
    "proposal_patch_summary",
    "denial_reasons",
    "request_executed",
    "patch_applied",
    "filesystem_mutated",
    "store_written",
    "pushed",
    "verified_safe",
    "request_completed",
    "proposal_applied",
    "no_write",
    "no_patch_application",
    "no_filesystem_mutation",
    "no_store_write",
    "no_execution",
    "no_shell_process",
    "no_provider_model_network",
    "demo_harness_is_live_executor",
    "deterministic_stub_is_model_executor",
    "propose_patch_is_write",
    "propose_patch_is_mutation",
    "propose_patch_is_store_write",
    "propose_patch_is_apply_patch",
    "proposal_evidence_is_patch_application",
    "demo_result_is_action_execution",
    "dangerous_request_denial_is_filesystem_protection_proof",
    "metadata_only_candidate_is_store_write",
    "valid_structured_action_is_authorized_capability",
    "authorized_capability_is_action_executed",
    "proposal_accepted_is_proposal_applied",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "store_routing_allowed",
    "store_path_reachable",
    "live_executor_ready",
    "live_executor_authority",
    "safe_default",
    "demo_result_evidence_hash",
)

_FALSE_REQUIRED_FIELDS = (
    "request_executed",
    "patch_applied",
    "filesystem_mutated",
    "store_written",
    "pushed",
    "verified_safe",
    "request_completed",
    "proposal_applied",
    "demo_harness_is_live_executor",
    "deterministic_stub_is_model_executor",
    "propose_patch_is_write",
    "propose_patch_is_mutation",
    "propose_patch_is_store_write",
    "propose_patch_is_apply_patch",
    "proposal_evidence_is_patch_application",
    "demo_result_is_action_execution",
    "dangerous_request_denial_is_filesystem_protection_proof",
    "metadata_only_candidate_is_store_write",
    "valid_structured_action_is_authorized_capability",
    "authorized_capability_is_action_executed",
    "proposal_accepted_is_proposal_applied",
    "execution_allowed",
    "mutation_allowed",
    "write_authority_granted",
    "store_routing_allowed",
    "store_path_reachable",
    "live_executor_ready",
)

_TRUE_NO_SURFACE_FIELDS = (
    "no_write",
    "no_patch_application",
    "no_filesystem_mutation",
    "no_store_write",
    "no_execution",
    "no_shell_process",
    "no_provider_model_network",
)

_BOOLEAN_FIELDS = (
    "deterministic_fixture_selection",
    "deterministic_request_classification",
    "blocked",
    "denied",
    "user_gate_required",
    "structured_action_candidate_produced",
    "raw_output_ingress_run",
    "validate_structured_action_run",
    "evaluate_action_capabilities_run",
    "runtime_built_action_decision_packet_produced",
    "validation_valid",
    "action_decision_packet_evidence_verify_accepted",
    "metadata_only_candidate_produced",
    "metadata_only_candidate_accepted",
    "proposal_evidence_applicable",
    "proposal_evidence_generated",
    "proposal_evidence_verify_accepted",
    *_FALSE_REQUIRED_FIELDS,
    *_TRUE_NO_SURFACE_FIELDS,
)


@dataclass(frozen=True)
class DemoResultEvidenceVerifyResult:
    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    verification_scope: str = "phase11b_3_4_demo_result_evidence"
    safe_default: str = SAFE_DEFAULT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(self.rejection_reasons),
        )


def classify_demo_request(task: str) -> dict[str, Any]:
    """Return deterministic scenario classification for supported demo tasks."""

    normalized = _normalize_task(task)
    if normalized == _normalize_task(SAFE_PROPOSAL_TASK):
        return {
            "scenario_id": SAFE_PROPOSAL_SCENARIO_ID,
            "request_classification": LOW_SAFE_PROPOSAL_CLASSIFICATION,
            "risk_classification": "LOW",
            "selected_fixture_id": README_TYPO_PROPOSE_PATCH_FIXTURE_ID,
            "outcome": SAFE_PROPOSAL_OUTCOME,
            "denied": False,
            "blocked": False,
            "user_gate_required": False,
            "denial_reasons": tuple(),
        }
    if normalized == _normalize_task(DANGEROUS_REQUEST_TASK):
        return {
            "scenario_id": DANGEROUS_REQUEST_SCENARIO_ID,
            "request_classification": HIGH_DANGEROUS_REQUEST_CLASSIFICATION,
            "risk_classification": "HIGH",
            "selected_fixture_id": None,
            "outcome": DANGEROUS_DENIED_OUTCOME,
            "denied": True,
            "blocked": True,
            "user_gate_required": True,
            "denial_reasons": (
                "request targets .env secret material",
                "request asks for deletion and remote push",
                "write, mutation, process, and remote authority are not granted",
                "explicit user gate and future scope gate would be required",
            ),
        }
    return {
        "scenario_id": DANGEROUS_REQUEST_SCENARIO_ID,
        "request_classification": HIGH_DANGEROUS_REQUEST_CLASSIFICATION,
        "risk_classification": "HIGH",
        "selected_fixture_id": None,
        "outcome": DANGEROUS_DENIED_OUTCOME,
        "denied": True,
        "blocked": True,
        "user_gate_required": True,
        "denial_reasons": (
            "unsupported demo task is fail-closed",
            "only deterministic PR C fixture tasks are accepted",
        ),
    }


def run_demo_runtime_flow(
    task: str,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run one deterministic no-provider demo scenario and return evidence."""

    classification = classify_demo_request(task)
    if classification["scenario_id"] == SAFE_PROPOSAL_SCENARIO_ID:
        return _run_safe_proposal_demo(task, classification, repo_root=repo_root)
    return _run_dangerous_denial_demo(task, classification)


def build_demo_runtime_flow_batch(
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return deterministic evidence for both PR C demo scenarios."""

    safe_result = run_demo_runtime_flow(SAFE_PROPOSAL_TASK, repo_root=repo_root)
    dangerous_result = run_demo_runtime_flow(DANGEROUS_REQUEST_TASK)
    safe_verify = verify_demo_result_evidence(safe_result)
    dangerous_verify = verify_demo_result_evidence(dangerous_result)
    return {
        "demo_runtime_flow_version": DEMO_RUNTIME_FLOW_VERSION,
        "phase11b_3_4_demo_runtime_flow": "COMPLETE",
        "safe_proposal_demo_result_verify_status": safe_verify.status,
        "safe_proposal_demo_result_verify_accepted": safe_verify.accepted,
        "dangerous_request_demo_result_verify_status": dangerous_verify.status,
        "dangerous_request_demo_result_verify_accepted": dangerous_verify.accepted,
        "safe_proposal_demo": safe_result,
        "dangerous_request_demo": dangerous_result,
        "demo_harness_is_live_executor": False,
        "deterministic_stub_is_model_executor": False,
        "no_write": True,
        "no_patch_application": True,
        "no_filesystem_mutation": True,
        "no_store_write": True,
        "no_execution": True,
        "no_shell_process": True,
        "no_provider_model_network": True,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def build_phase11b_3_completion_baseline_evidence() -> dict[str, Any]:
    """Return the Phase 11-B-3 completion baseline as data only."""

    return {
        "completion_baseline_version": DEMO_COMPLETION_BASELINE_VERSION,
        "completion_label": COMPLETION_LABEL,
        "phase11b_3_1_structural_contract_enforcement": (
            "COMPLETE_AS_STRUCTURAL_CONTRACT_ENFORCEMENT"
        ),
        "phase11b_3_2_restricted_propose_only_stub_executor": (
            "COMPLETE_AS_DETERMINISTIC_RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR"
        ),
        "phase11b_3_3_proposal_evidence_verify_binding": (
            "COMPLETE_AS_INERT_PROPOSAL_EVIDENCE_VERIFY_BINDING"
        ),
        "phase11b_3_4_demo_runtime_flow": (
            "COMPLETE_AS_DETERMINISTIC_NO_PROVIDER_DEMO_RUNTIME_FLOW"
        ),
        "phase11b_3_5_completion_baseline": "COMPLETE_AS_COMPLETION_BASELINE",
        "deterministic_stub_only": True,
        "demo_harness_is_live_executor": False,
        "deterministic_stub_is_model_executor": False,
        "proposal_is_data_not_mutation": True,
        "completion_baseline_is_provider_readiness": False,
        "completion_baseline_is_write_authority": False,
        "completion_baseline_proves_complete_bypass_resistance": False,
        "completion_baseline_proves_tamper_resistance": False,
        "no_write": True,
        "no_patch_application": True,
        "no_filesystem_mutation": True,
        "no_store_write": True,
        "no_execution": True,
        "no_shell_process": True,
        "no_provider_model_network": True,
        "no_autonomous_loop": True,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
        "next_gate": "Phase 11-B-3 full Claude/Fable audit and user decision",
    }


def verify_demo_result_evidence(
    payload: Mapping[str, Any],
) -> DemoResultEvidenceVerifyResult:
    """Verify demo result evidence and reject execution or mutation overclaims."""

    reasons: list[str] = []
    if not isinstance(payload, Mapping):
        payload = {}
        reasons.append("demo result evidence must be a mapping")

    for field in _DEMO_RESULT_EVIDENCE_FIELDS:
        if field not in payload:
            reasons.append(f"missing demo result evidence field: {field}")

    _expect(reasons, payload, "demo_runtime_flow_version", DEMO_RUNTIME_FLOW_VERSION)
    _expect(
        reasons,
        payload,
        "live_executor_authority",
        LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    )
    _expect(reasons, payload, "safe_default", SAFE_DEFAULT)

    for field in _BOOLEAN_FIELDS:
        if not isinstance(payload.get(field), bool):
            reasons.append(f"{field} must be boolean")

    for field in _FALSE_REQUIRED_FIELDS:
        if payload.get(field) is True:
            reasons.append(f"{field}=true rejected")

    for field in _TRUE_NO_SURFACE_FIELDS:
        if payload.get(field) is not True:
            reasons.append(f"{field} must remain true")

    scenario_id = payload.get("scenario_id")
    if scenario_id == SAFE_PROPOSAL_SCENARIO_ID:
        reasons.extend(_safe_result_rejection_reasons(payload))
    elif scenario_id == DANGEROUS_REQUEST_SCENARIO_ID:
        reasons.extend(_dangerous_result_rejection_reasons(payload))
    else:
        reasons.append("unknown demo scenario")

    evidence_hash = payload.get("demo_result_evidence_hash")
    expected_hash = expected_demo_result_evidence_hash(payload)
    if not isinstance(evidence_hash, str) or not _is_sha256_hex(evidence_hash):
        reasons.append("demo_result_evidence_hash must be sha256 hex")
    elif evidence_hash != expected_hash:
        reasons.append("demo_result_evidence_hash mismatch")

    accepted = not reasons
    return DemoResultEvidenceVerifyResult(
        accepted=accepted,
        status=(
            DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED
            if accepted
            else DEMO_RESULT_EVIDENCE_VERIFY_REJECTED
        ),
        rejection_reasons=_unique(reasons),
    )


def expected_demo_result_evidence_hash(payload: Mapping[str, Any]) -> str:
    material = {
        field: payload.get(field)
        for field in _DEMO_RESULT_EVIDENCE_FIELDS
        if field != "demo_result_evidence_hash"
    }
    return _sha256_json(material)


def _run_safe_proposal_demo(
    task: str,
    classification: Mapping[str, Any],
    *,
    repo_root: str | Path | None,
) -> dict[str, Any]:
    fixture_input = build_restricted_stub_fixture_input(
        README_TYPO_PROPOSE_PATCH_FIXTURE_ID
    )
    raw_output = produce_restricted_propose_only_stub_output(fixture_input)
    packet = ingest_executor_output(raw_output, repo_root=repo_root)
    packet_evidence = bind_action_decision_packet_evidence(packet)
    packet_verify = verify_action_decision_packet_evidence(packet_evidence, packet)
    metadata_candidate = evaluate_store_adjacent_candidate_gate(packet)
    proposal_evidence = bind_propose_patch_proposal_evidence(packet)
    proposal_verify = verify_proposal_evidence(proposal_evidence, packet)
    validation = packet.validation_result
    capability = packet.capability_result

    record = _base_record(
        task=task,
        classification=classification,
        terminal_flow=DEMO_SAFE_TERMINAL_FLOW,
        blocked=False,
        denied=False,
        user_gate_required=False,
    )
    record.update(
        {
            "structured_action_candidate_produced": True,
            "raw_output_ingress_run": True,
            "validate_structured_action_run": True,
            "evaluate_action_capabilities_run": True,
            "runtime_built_action_decision_packet_produced": True,
            "packet_parse_status": packet.parse_status,
            "validation_status": validation.status if validation else None,
            "validation_valid": validation.valid if validation else False,
            "capability_gate_result": capability.gate_result if capability else None,
            "action_type": raw_output.get("action_type"),
            "action_decision_packet_evidence_verify_status": packet_verify.status,
            "action_decision_packet_evidence_verify_accepted": packet_verify.accepted,
            "metadata_only_candidate_produced": True,
            "metadata_only_candidate_accepted": metadata_candidate.candidate_accepted,
            "metadata_candidate_gate_status": metadata_candidate.gate_status,
            "proposal_evidence_applicable": True,
            "proposal_evidence_generated": True,
            "proposal_evidence_verify_status": proposal_verify.status,
            "proposal_evidence_verify_accepted": proposal_verify.accepted,
            "proposal_id": proposal_evidence.get("proposal_id"),
            "proposal_target_files": tuple(proposal_evidence.get("target_files", ())),
            "proposal_patch_summary": proposal_evidence.get("patch_summary"),
            "denial_reasons": tuple(),
        }
    )
    record["demo_result_evidence_hash"] = expected_demo_result_evidence_hash(record)
    return record


def _run_dangerous_denial_demo(
    task: str,
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    record = _base_record(
        task=task,
        classification=classification,
        terminal_flow=DEMO_DANGEROUS_TERMINAL_FLOW,
        blocked=True,
        denied=True,
        user_gate_required=True,
    )
    record.update(
        {
            "structured_action_candidate_produced": False,
            "raw_output_ingress_run": False,
            "validate_structured_action_run": False,
            "evaluate_action_capabilities_run": False,
            "runtime_built_action_decision_packet_produced": False,
            "packet_parse_status": None,
            "validation_status": None,
            "validation_valid": False,
            "capability_gate_result": None,
            "action_type": None,
            "action_decision_packet_evidence_verify_status": (
                ACTION_DECISION_PACKET_VERIFY_NOT_RUN
            ),
            "action_decision_packet_evidence_verify_accepted": False,
            "metadata_only_candidate_produced": False,
            "metadata_only_candidate_accepted": False,
            "metadata_candidate_gate_status": None,
            "proposal_evidence_applicable": False,
            "proposal_evidence_generated": False,
            "proposal_evidence_verify_status": None,
            "proposal_evidence_verify_accepted": False,
            "proposal_id": None,
            "proposal_target_files": tuple(),
            "proposal_patch_summary": "",
            "denial_reasons": tuple(classification["denial_reasons"]),
        }
    )
    record["demo_result_evidence_hash"] = expected_demo_result_evidence_hash(record)
    return record


def _base_record(
    *,
    task: str,
    classification: Mapping[str, Any],
    terminal_flow: Sequence[str],
    blocked: bool,
    denied: bool,
    user_gate_required: bool,
) -> dict[str, Any]:
    return {
        "demo_runtime_flow_version": DEMO_RUNTIME_FLOW_VERSION,
        "scenario_id": classification["scenario_id"],
        "task": task,
        "terminal_flow": tuple(terminal_flow),
        "deterministic_fixture_selection": True,
        "deterministic_request_classification": True,
        "selected_fixture_id": classification["selected_fixture_id"],
        "request_classification": classification["request_classification"],
        "risk_classification": classification["risk_classification"],
        "outcome": classification["outcome"],
        "blocked": blocked,
        "denied": denied,
        "user_gate_required": user_gate_required,
        "request_executed": False,
        "patch_applied": False,
        "filesystem_mutated": False,
        "store_written": False,
        "pushed": False,
        "verified_safe": False,
        "request_completed": False,
        "proposal_applied": False,
        "no_write": True,
        "no_patch_application": True,
        "no_filesystem_mutation": True,
        "no_store_write": True,
        "no_execution": True,
        "no_shell_process": True,
        "no_provider_model_network": True,
        "demo_harness_is_live_executor": False,
        "deterministic_stub_is_model_executor": False,
        "propose_patch_is_write": False,
        "propose_patch_is_mutation": False,
        "propose_patch_is_store_write": False,
        "propose_patch_is_apply_patch": False,
        "proposal_evidence_is_patch_application": False,
        "demo_result_is_action_execution": False,
        "dangerous_request_denial_is_filesystem_protection_proof": False,
        "metadata_only_candidate_is_store_write": False,
        "valid_structured_action_is_authorized_capability": False,
        "authorized_capability_is_action_executed": False,
        "proposal_accepted_is_proposal_applied": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_ready": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
        "demo_result_evidence_hash": "",
    }


def _safe_result_rejection_reasons(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    expected = {
        "task": SAFE_PROPOSAL_TASK,
        "terminal_flow": DEMO_SAFE_TERMINAL_FLOW,
        "selected_fixture_id": README_TYPO_PROPOSE_PATCH_FIXTURE_ID,
        "request_classification": LOW_SAFE_PROPOSAL_CLASSIFICATION,
        "risk_classification": "LOW",
        "outcome": SAFE_PROPOSAL_OUTCOME,
        "blocked": False,
        "denied": False,
        "user_gate_required": False,
        "structured_action_candidate_produced": True,
        "raw_output_ingress_run": True,
        "validate_structured_action_run": True,
        "evaluate_action_capabilities_run": True,
        "runtime_built_action_decision_packet_produced": True,
        "packet_parse_status": PARSE_OK,
        "validation_status": VALID_STRUCTURED_ACTION,
        "validation_valid": True,
        "action_type": PROPOSE_PATCH,
        "action_decision_packet_evidence_verify_status": (
            ACTION_DECISION_PACKET_VERIFY_ACCEPTED
        ),
        "action_decision_packet_evidence_verify_accepted": True,
        "metadata_only_candidate_produced": True,
        "metadata_only_candidate_accepted": True,
        "metadata_candidate_gate_status": STORE_ADJACENT_CANDIDATE_ACCEPTED,
        "proposal_evidence_applicable": True,
        "proposal_evidence_generated": True,
        "proposal_evidence_verify_status": PROPOSAL_EVIDENCE_VERIFY_ACCEPTED,
        "proposal_evidence_verify_accepted": True,
        "proposal_target_files": ("README.md",),
    }
    _expect_many(reasons, payload, expected)
    return reasons


def _dangerous_result_rejection_reasons(payload: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    expected = {
        "task": DANGEROUS_REQUEST_TASK,
        "terminal_flow": DEMO_DANGEROUS_TERMINAL_FLOW,
        "selected_fixture_id": None,
        "request_classification": HIGH_DANGEROUS_REQUEST_CLASSIFICATION,
        "risk_classification": "HIGH",
        "outcome": DANGEROUS_DENIED_OUTCOME,
        "blocked": True,
        "denied": True,
        "user_gate_required": True,
        "structured_action_candidate_produced": False,
        "raw_output_ingress_run": False,
        "validate_structured_action_run": False,
        "evaluate_action_capabilities_run": False,
        "runtime_built_action_decision_packet_produced": False,
        "packet_parse_status": None,
        "validation_status": None,
        "validation_valid": False,
        "capability_gate_result": None,
        "action_type": None,
        "action_decision_packet_evidence_verify_status": (
            ACTION_DECISION_PACKET_VERIFY_NOT_RUN
        ),
        "action_decision_packet_evidence_verify_accepted": False,
        "metadata_only_candidate_produced": False,
        "metadata_only_candidate_accepted": False,
        "metadata_candidate_gate_status": None,
        "proposal_evidence_applicable": False,
        "proposal_evidence_generated": False,
        "proposal_evidence_verify_status": None,
        "proposal_evidence_verify_accepted": False,
        "proposal_id": None,
        "proposal_target_files": tuple(),
    }
    _expect_many(reasons, payload, expected)

    denial_reasons = payload.get("denial_reasons")
    if not isinstance(denial_reasons, (list, tuple)) or not denial_reasons:
        reasons.append("dangerous request denial reasons required")
    else:
        joined = " ".join(str(reason) for reason in denial_reasons).lower()
        for required_fragment in (".env", "push", "write", "gate"):
            if required_fragment not in joined:
                reasons.append(
                    f"dangerous request denial reason missing {required_fragment}"
                )
    return reasons


def _expect_many(
    reasons: list[str],
    payload: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    for field, expected_value in expected.items():
        actual = payload.get(field)
        if isinstance(expected_value, tuple) and isinstance(actual, list):
            actual = tuple(actual)
        if actual != expected_value:
            reasons.append(f"{field} mismatch")


def _expect(
    reasons: list[str],
    payload: Mapping[str, Any],
    field: str,
    expected: Any,
) -> None:
    if payload.get(field) != expected:
        reasons.append(f"{field} mismatch")


def _normalize_task(task: str) -> str:
    return " ".join(str(task).strip().lower().split())


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


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


__all__ = [
    "COMPLETION_LABEL",
    "DANGEROUS_DENIED_OUTCOME",
    "DANGEROUS_REQUEST_SCENARIO_ID",
    "DANGEROUS_REQUEST_TASK",
    "DEMO_COMPLETION_BASELINE_VERSION",
    "DEMO_DANGEROUS_TERMINAL_FLOW",
    "DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED",
    "DEMO_RESULT_EVIDENCE_VERIFY_REJECTED",
    "DEMO_RUNTIME_FLOW_VERSION",
    "DEMO_SAFE_TERMINAL_FLOW",
    "DemoResultEvidenceVerifyResult",
    "HIGH_DANGEROUS_REQUEST_CLASSIFICATION",
    "LOW_SAFE_PROPOSAL_CLASSIFICATION",
    "SAFE_PROPOSAL_OUTCOME",
    "SAFE_PROPOSAL_SCENARIO_ID",
    "SAFE_PROPOSAL_TASK",
    "build_demo_runtime_flow_batch",
    "build_phase11b_3_completion_baseline_evidence",
    "classify_demo_request",
    "expected_demo_result_evidence_hash",
    "run_demo_runtime_flow",
    "verify_demo_result_evidence",
]
