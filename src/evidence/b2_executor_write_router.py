"""B2-1 pre-live executor-like write routing through B1 guard components.

The router accepts a structured write request model, resolves the submitted
target through the existing B1-B guard, binds the B1-C evidence record, and
returns a routed denial record for protected ``.aeg`` targets. It does not
perform file mutation, connect a live executor, or add external enforcement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_NOT_PROTECTED_TARGET,
    B2_AEG_PROTECTED_TARGET_ROUTED,
    B2_EXECUTOR_WRITE_ROUTER,
    B2_NO_MUTATION_OBSERVATION_BOUND,
    B2_NOT_PROTECTED_TARGET_OUT_OF_SCOPE,
    B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST,
    B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE,
    B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE,
    B2_ROUTED_DENIAL,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATOR_DECISION_DENY,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    NOT_WIRED_TO_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_CLASS_AEG_STATE_WRITE,
)
from src.evidence.b1_aeg_integrity_evidence_binding import (
    B1AegGuardEvidenceRecord,
    B1AegGuardNoMutationObservation,
    build_b1_aeg_guard_evidence_record,
    build_b1_aeg_guard_no_mutation_observation,
)
from src.evidence.b1_aeg_integrity_guard import (
    B1AegIntegrityGuardDecision,
    decide_b1_aeg_integrity_guard,
)
from src.evidence.deny_only_mediator import (
    WriteMediationDecision,
    WriteMediationRequest,
    decide_write_request,
)

B2_EXECUTOR_WRITE_ROUTING_VERSION = "B2_1_EXECUTOR_WRITE_ROUTING_THROUGH_MEDIATOR_GUARD_PATH_V0"


@dataclass(frozen=True)
class PreLiveExecutorWriteRequest:
    """Structured model for a pre-live executor-like write request."""

    request_id: str
    submitted_path: str
    intended_operation: str
    payload_digest: str
    payload_metadata: Mapping[str, str] = field(default_factory=dict)
    request_model: str = B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST
    request_source: str = B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE
    live_executor_request: bool = False
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    live_executor_authority_granted: bool = False
    runtime_write_path_status: str = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
    raw_direct_write_requested: bool = False
    write_performed: bool = False

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["payload_metadata"] = dict(self.payload_metadata)
        return record


@dataclass(frozen=True)
class B2ExecutorWriteRoutingResult:
    """Routed result for a pre-live executor-like write request."""

    route_id: str
    route_digest: str
    component: str
    version: str
    request: PreLiveExecutorWriteRequest
    routing_status: str
    routing_decision: str
    route_target: str
    guard_decision: B1AegIntegrityGuardDecision
    mediator_request: WriteMediationRequest | None
    mediator_decision: WriteMediationDecision | None
    no_mutation_observation: B1AegGuardNoMutationObservation
    guard_evidence_record: B1AegGuardEvidenceRecord | None
    b1_guard_reused: bool
    b1_evidence_binding_reused: bool
    b1_known_gap_baseline_status: str
    raw_direct_path_status: str
    no_mutation_status: str
    runtime_write_path_status: str
    live_executor_authority_status: str
    phase11a_status: str
    os_enforcement_status: str
    filesystem_enforcement_status: str
    live_executor_authority_granted: bool
    runtime_write_authority_granted: bool
    raw_direct_write_success_claimed: bool
    write_performed: bool
    filesystem_mutation_performed: bool
    executor_write_path_wired: bool

    def to_record(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "route_digest": self.route_digest,
            **_routing_payload(self),
        }


def build_pre_live_executor_write_request(
    *,
    submitted_path: str | Path,
    intended_operation: str,
    payload: str | bytes | None = None,
    payload_metadata: Mapping[str, str] | None = None,
    request_id: str | None = None,
) -> PreLiveExecutorWriteRequest:
    """Build a request record without storing raw payload content."""

    metadata = dict(payload_metadata or {})
    payload_digest = _payload_digest(payload=payload, payload_metadata=metadata)
    return PreLiveExecutorWriteRequest(
        request_id=request_id
        or _request_id(
            submitted_path=str(submitted_path),
            intended_operation=intended_operation,
            payload_digest=payload_digest,
            payload_metadata=metadata,
        ),
        submitted_path=str(submitted_path),
        intended_operation=intended_operation,
        payload_digest=payload_digest,
        payload_metadata=metadata,
    )


def route_pre_live_executor_write_request(
    *,
    repo_root: str | Path,
    request: PreLiveExecutorWriteRequest,
) -> B2ExecutorWriteRoutingResult:
    """Route a pre-live executor-like write request through B1/B2 components."""

    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=request.submitted_path,
    )
    no_mutation_observation = build_b1_aeg_guard_no_mutation_observation(
        guard_decision=guard_decision,
    )

    if guard_decision.protected_target:
        mediator_request = _build_mediator_request(request=request, guard_decision=guard_decision)
        mediator_decision = decide_write_request(mediator_request)
        guard_evidence_record = build_b1_aeg_guard_evidence_record(
            guard_decision=guard_decision,
            no_mutation_observation=no_mutation_observation,
        )
        routing_status = B2_AEG_PROTECTED_TARGET_ROUTED
        routing_decision = B2_ROUTED_DENIAL
        route_target = B2_ROUTE_GUARD_MEDIATOR_COMPATIBLE
    else:
        mediator_request = None
        mediator_decision = None
        guard_evidence_record = None
        routing_status = B2_NOT_PROTECTED_TARGET_OUT_OF_SCOPE
        routing_decision = B1_AEG_NOT_PROTECTED_TARGET
        route_target = B1_AEG_NOT_PROTECTED_TARGET

    result_args = {
        "component": B2_EXECUTOR_WRITE_ROUTER,
        "version": B2_EXECUTOR_WRITE_ROUTING_VERSION,
        "request": request,
        "routing_status": routing_status,
        "routing_decision": routing_decision,
        "route_target": route_target,
        "guard_decision": guard_decision,
        "mediator_request": mediator_request,
        "mediator_decision": mediator_decision,
        "no_mutation_observation": no_mutation_observation,
        "guard_evidence_record": guard_evidence_record,
        "b1_guard_reused": True,
        "b1_evidence_binding_reused": guard_evidence_record is not None,
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
    route_digest = _sha256_json(_routing_payload_from_args(result_args))
    return B2ExecutorWriteRoutingResult(
        route_id=f"b2-executor-write-route:{route_digest}",
        route_digest=route_digest,
        **result_args,
    )


def _build_mediator_request(
    *,
    request: PreLiveExecutorWriteRequest,
    guard_decision: B1AegIntegrityGuardDecision,
) -> WriteMediationRequest:
    return WriteMediationRequest(
        request_id=f"b2-mediator:{request.request_id}",
        actor=request.request_source,
        operation=request.intended_operation,
        write_class=WRITE_CLASS_AEG_STATE_WRITE,
        submitted_target=guard_decision.submitted_path,
        canonical_target=guard_decision.resolved_path,
        declared_scope="b2_1_executor_write_routing_through_mediator_guard_path_v0",
        repo_boundary="repo_root_resolved_by_b1_guard",
        aeg_boundary=guard_decision.protected_target_status,
        action_summary="pre-live executor-like write request routed before file mutation",
        metadata={
            "payload_digest": request.payload_digest,
            "guard_decision_id": guard_decision.decision_id,
            "guard_target_class": guard_decision.target_class,
            "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
            "mediator_write_path_status": NOT_WIRED_TO_WRITE_PATH,
            "raw_direct_path_status": RAW_DIRECT_WRITE_STILL_BYPASSABLE,
            "expected_mediator_decision": MEDIATOR_DECISION_DENY,
        },
    )


def _routing_payload(record: B2ExecutorWriteRoutingResult) -> dict[str, Any]:
    return _routing_payload_from_args(
        {
            "component": record.component,
            "version": record.version,
            "request": record.request,
            "routing_status": record.routing_status,
            "routing_decision": record.routing_decision,
            "route_target": record.route_target,
            "guard_decision": record.guard_decision,
            "mediator_request": record.mediator_request,
            "mediator_decision": record.mediator_decision,
            "no_mutation_observation": record.no_mutation_observation,
            "guard_evidence_record": record.guard_evidence_record,
            "b1_guard_reused": record.b1_guard_reused,
            "b1_evidence_binding_reused": record.b1_evidence_binding_reused,
            "b1_known_gap_baseline_status": record.b1_known_gap_baseline_status,
            "raw_direct_path_status": record.raw_direct_path_status,
            "no_mutation_status": record.no_mutation_status,
            "runtime_write_path_status": record.runtime_write_path_status,
            "live_executor_authority_status": record.live_executor_authority_status,
            "phase11a_status": record.phase11a_status,
            "os_enforcement_status": record.os_enforcement_status,
            "filesystem_enforcement_status": record.filesystem_enforcement_status,
            "live_executor_authority_granted": record.live_executor_authority_granted,
            "runtime_write_authority_granted": record.runtime_write_authority_granted,
            "raw_direct_write_success_claimed": record.raw_direct_write_success_claimed,
            "write_performed": record.write_performed,
            "filesystem_mutation_performed": record.filesystem_mutation_performed,
            "executor_write_path_wired": record.executor_write_path_wired,
        }
    )


def _routing_payload_from_args(args: Mapping[str, Any]) -> dict[str, Any]:
    request = args["request"]
    guard_decision = args["guard_decision"]
    mediator_request = args["mediator_request"]
    mediator_decision = args["mediator_decision"]
    no_mutation_observation = args["no_mutation_observation"]
    guard_evidence_record = args["guard_evidence_record"]
    return {
        "component": args["component"],
        "version": args["version"],
        "request": request.to_record(),
        "routing_status": args["routing_status"],
        "routing_decision": args["routing_decision"],
        "route_target": args["route_target"],
        "guard_decision": guard_decision.to_record(),
        "mediator_request": mediator_request.to_record() if mediator_request else None,
        "mediator_decision": mediator_decision.to_record() if mediator_decision else None,
        "no_mutation_observation": no_mutation_observation.to_record(),
        "guard_evidence_record": guard_evidence_record.to_record() if guard_evidence_record else None,
        "b1_guard_reused": args["b1_guard_reused"],
        "b1_evidence_binding_reused": args["b1_evidence_binding_reused"],
        "b1_known_gap_baseline_status": args["b1_known_gap_baseline_status"],
        "raw_direct_path_status": args["raw_direct_path_status"],
        "no_mutation_status": args["no_mutation_status"],
        "runtime_write_path_status": args["runtime_write_path_status"],
        "live_executor_authority_status": args["live_executor_authority_status"],
        "phase11a_status": args["phase11a_status"],
        "os_enforcement_status": args["os_enforcement_status"],
        "filesystem_enforcement_status": args["filesystem_enforcement_status"],
        "live_executor_authority_granted": args["live_executor_authority_granted"],
        "runtime_write_authority_granted": args["runtime_write_authority_granted"],
        "raw_direct_write_success_claimed": args["raw_direct_write_success_claimed"],
        "write_performed": args["write_performed"],
        "filesystem_mutation_performed": args["filesystem_mutation_performed"],
        "executor_write_path_wired": args["executor_write_path_wired"],
    }


def _request_id(
    *,
    submitted_path: str,
    intended_operation: str,
    payload_digest: str,
    payload_metadata: Mapping[str, str],
) -> str:
    digest = _sha256_json(
        {
            "submitted_path": submitted_path,
            "intended_operation": intended_operation,
            "payload_digest": payload_digest,
            "payload_metadata": dict(payload_metadata),
            "request_source": B2_REQUEST_SOURCE_PRE_LIVE_EXECUTOR_LIKE,
        }
    )
    return f"b2-pre-live-write-request:{digest}"


def _payload_digest(*, payload: str | bytes | None, payload_metadata: Mapping[str, str]) -> str:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
        payload_kind = "text"
    elif isinstance(payload, bytes):
        payload_bytes = payload
        payload_kind = "bytes"
    else:
        payload_bytes = json.dumps(
            {"payload_metadata": dict(payload_metadata)},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        payload_kind = "metadata_only"
    return _sha256_json(
        {
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "payload_kind": payload_kind,
            "payload_metadata": dict(payload_metadata),
        }
    )


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "B2_EXECUTOR_WRITE_ROUTING_VERSION",
    "B2ExecutorWriteRoutingResult",
    "PreLiveExecutorWriteRequest",
    "build_pre_live_executor_write_request",
    "route_pre_live_executor_write_request",
]
