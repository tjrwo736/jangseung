"""Fixture-only B2-3 executor-like write ingress harness.

This module models a synthetic executor-like write intent, converts it to the
B2-1 pre-live router request, and returns the routed result. It is fixture
support for tests and boundary documentation; it is not imported by production
CLI/runtime paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.contracts import (
    B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
)
from src.evidence import b2_executor_write_router
from src.evidence.b2_executor_write_router import (
    B2ExecutorWriteRoutingResult,
    PreLiveExecutorWriteRequest,
)

B2_EXECUTOR_LIKE_INGRESS_HARNESS_VERSION = "B2_3_EXECUTOR_LIKE_WRITE_INGRESS_HARNESS_V0"
B2_EXECUTOR_LIKE_INGRESS_HARNESS_COMPONENT = "B2_3_EXECUTOR_LIKE_WRITE_INGRESS_HARNESS"
B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE = "fixture-only executor-like ingress"
B2_NOT_PRODUCTION_RUNTIME_INGRESS = "not production runtime ingress"
B2_NO_LIVE_EXECUTOR_AUTHORITY = "no live authority"
B2_REMAINS_OPEN_NOT_FULLY_ROUTED = "B2_REMAINS_OPEN_NOT_FULLY_ROUTED"
B3_NOT_STARTED = "B3_NOT_STARTED"


@dataclass(frozen=True)
class FixtureExecutorLikeIngressRequest:
    """Synthetic ingress record for a fixture-only executor-like write intent."""

    ingress_id: str
    source: str
    submitted_path: str
    intended_operation: str
    payload_digest: str
    payload_metadata: Mapping[str, str] = field(default_factory=dict)
    live_executor_request: bool = False
    production_runtime_ingress: bool = False
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    live_executor_authority_granted: bool = False
    live_authority_note: str = B2_NO_LIVE_EXECUTOR_AUTHORITY
    runtime_write_path_status: str = NOT_WIRED_TO_EXECUTOR_WRITE_PATH
    production_runtime_ingress_status: str = B2_NOT_PRODUCTION_RUNTIME_INGRESS
    router_request_model: str = B2_PRE_LIVE_EXECUTOR_LIKE_REQUEST

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["payload_metadata"] = dict(self.payload_metadata)
        return record


@dataclass(frozen=True)
class B2ExecutorLikeIngressHarnessResult:
    """Observed B2-3 fixture ingress routing result."""

    harness_id: str
    harness_digest: str
    component: str
    version: str
    ingress: FixtureExecutorLikeIngressRequest
    router_request: PreLiveExecutorWriteRequest
    router_result: B2ExecutorWriteRoutingResult
    router_called: bool
    fixture_only: bool
    production_runtime_wiring_added: bool
    production_adapter_added: bool
    live_executor_invoked: bool
    external_runtime_invoked: bool
    command_runner_invoked: bool
    broad_write_capability_granted: bool
    raw_capability_granted: bool
    runtime_write_authority_granted: bool
    no_mutation_observed: bool
    runtime_write_path_status: str
    live_executor_authority_status: str
    phase11a_status: str
    b2_status: str
    b3_status: str

    def to_record(self) -> dict[str, Any]:
        return {
            "harness_id": self.harness_id,
            "harness_digest": self.harness_digest,
            **_harness_payload(self),
        }


def build_fixture_executor_like_ingress_request(
    *,
    submitted_path: str | Path,
    intended_operation: str,
    payload: str | bytes | None = None,
    payload_metadata: Mapping[str, str] | None = None,
    ingress_id: str | None = None,
) -> FixtureExecutorLikeIngressRequest:
    """Build a fixture-only ingress request without retaining raw payload."""

    metadata = dict(payload_metadata or {})
    payload_digest = _payload_digest(payload=payload, payload_metadata=metadata)
    return FixtureExecutorLikeIngressRequest(
        ingress_id=ingress_id
        or _ingress_id(
            submitted_path=str(submitted_path),
            intended_operation=intended_operation,
            payload_digest=payload_digest,
            payload_metadata=metadata,
        ),
        source=B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
        submitted_path=str(submitted_path),
        intended_operation=intended_operation,
        payload_digest=payload_digest,
        payload_metadata=metadata,
    )


def route_fixture_executor_like_ingress_through_router(
    *,
    repo_root: str | Path,
    ingress: FixtureExecutorLikeIngressRequest,
) -> B2ExecutorLikeIngressHarnessResult:
    """Convert fixture ingress into the B2-1 router request and route it."""

    router_request = b2_executor_write_router.build_pre_live_executor_write_request(
        submitted_path=ingress.submitted_path,
        intended_operation=ingress.intended_operation,
        payload=None,
        payload_metadata={
            **dict(ingress.payload_metadata),
            "fixture_ingress_id": ingress.ingress_id,
            "fixture_ingress_source": ingress.source,
            "fixture_payload_digest": ingress.payload_digest,
            "fixture_authority": ingress.live_authority_note,
            "runtime_write_path_status": ingress.runtime_write_path_status,
        },
        request_id=f"b2-3-router-request:{ingress.ingress_id}",
    )
    router_result = b2_executor_write_router.route_pre_live_executor_write_request(
        repo_root=repo_root,
        request=router_request,
    )
    result_args = {
        "component": B2_EXECUTOR_LIKE_INGRESS_HARNESS_COMPONENT,
        "version": B2_EXECUTOR_LIKE_INGRESS_HARNESS_VERSION,
        "ingress": ingress,
        "router_request": router_request,
        "router_result": router_result,
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
        "no_mutation_observed": router_result.no_mutation_observation.no_mutation_observed,
        "runtime_write_path_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        "live_executor_authority_status": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11a_status": PHASE11A_NOT_STARTED,
        "b2_status": B2_REMAINS_OPEN_NOT_FULLY_ROUTED,
        "b3_status": B3_NOT_STARTED,
    }
    harness_digest = _sha256_json(_harness_payload_from_args(result_args))
    return B2ExecutorLikeIngressHarnessResult(
        harness_id=f"b2-3-executor-like-ingress-harness:{harness_digest}",
        harness_digest=harness_digest,
        **result_args,
    )


def _harness_payload(record: B2ExecutorLikeIngressHarnessResult) -> dict[str, Any]:
    return _harness_payload_from_args(
        {
            "component": record.component,
            "version": record.version,
            "ingress": record.ingress,
            "router_request": record.router_request,
            "router_result": record.router_result,
            "router_called": record.router_called,
            "fixture_only": record.fixture_only,
            "production_runtime_wiring_added": record.production_runtime_wiring_added,
            "production_adapter_added": record.production_adapter_added,
            "live_executor_invoked": record.live_executor_invoked,
            "external_runtime_invoked": record.external_runtime_invoked,
            "command_runner_invoked": record.command_runner_invoked,
            "broad_write_capability_granted": record.broad_write_capability_granted,
            "raw_capability_granted": record.raw_capability_granted,
            "runtime_write_authority_granted": record.runtime_write_authority_granted,
            "no_mutation_observed": record.no_mutation_observed,
            "runtime_write_path_status": record.runtime_write_path_status,
            "live_executor_authority_status": record.live_executor_authority_status,
            "phase11a_status": record.phase11a_status,
            "b2_status": record.b2_status,
            "b3_status": record.b3_status,
        }
    )


def _harness_payload_from_args(args: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "component": args["component"],
        "version": args["version"],
        "ingress": args["ingress"].to_record(),
        "router_request": args["router_request"].to_record(),
        "router_result": args["router_result"].to_record(),
        "router_called": args["router_called"],
        "fixture_only": args["fixture_only"],
        "production_runtime_wiring_added": args["production_runtime_wiring_added"],
        "production_adapter_added": args["production_adapter_added"],
        "live_executor_invoked": args["live_executor_invoked"],
        "external_runtime_invoked": args["external_runtime_invoked"],
        "command_runner_invoked": args["command_runner_invoked"],
        "broad_write_capability_granted": args["broad_write_capability_granted"],
        "raw_capability_granted": args["raw_capability_granted"],
        "runtime_write_authority_granted": args["runtime_write_authority_granted"],
        "no_mutation_observed": args["no_mutation_observed"],
        "runtime_write_path_status": args["runtime_write_path_status"],
        "live_executor_authority_status": args["live_executor_authority_status"],
        "phase11a_status": args["phase11a_status"],
        "b2_status": args["b2_status"],
        "b3_status": args["b3_status"],
    }


def _ingress_id(
    *,
    submitted_path: str,
    intended_operation: str,
    payload_digest: str,
    payload_metadata: Mapping[str, str],
) -> str:
    digest = _sha256_json(
        {
            "source": B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE,
            "submitted_path": submitted_path,
            "intended_operation": intended_operation,
            "payload_digest": payload_digest,
            "payload_metadata": dict(payload_metadata),
        }
    )
    return f"b2-3-fixture-executor-like-ingress:{digest}"


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
    "B2_EXECUTOR_LIKE_INGRESS_HARNESS_COMPONENT",
    "B2_EXECUTOR_LIKE_INGRESS_HARNESS_VERSION",
    "B2_FIXTURE_ONLY_EXECUTOR_LIKE_INGRESS_SOURCE",
    "B2_NO_LIVE_EXECUTOR_AUTHORITY",
    "B2_NOT_PRODUCTION_RUNTIME_INGRESS",
    "B2_REMAINS_OPEN_NOT_FULLY_ROUTED",
    "B3_NOT_STARTED",
    "B2ExecutorLikeIngressHarnessResult",
    "FixtureExecutorLikeIngressRequest",
    "build_fixture_executor_like_ingress_request",
    "route_fixture_executor_like_ingress_through_router",
]
