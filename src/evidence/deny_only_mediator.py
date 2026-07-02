"""Deny-only write mediator skeleton.

This module models a write mediation request and returns a skeleton-local deny
decision. It does not open files, resolve paths, call tools, harden
permissions, or connect to any write path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping

from src.contracts import (
    DENIED_BY_MEDIATOR_SKELETON,
    DENY_ONLY_MEDIATOR_SKELETON_PRESENT,
    ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATOR_DECISION_DENY,
    NOT_WIRED_TO_WRITE_PATH,
)


@dataclass(frozen=True)
class WriteMediationRequest:
    """Pure request model for a future mediated write attempt."""

    request_id: str
    actor: str
    operation: str
    write_class: str
    submitted_target: str
    canonical_target: str | None = None
    declared_scope: str | None = None
    repo_boundary: str | None = None
    aeg_boundary: str | None = None
    action_summary: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["metadata"] = dict(self.metadata)
        return record


@dataclass(frozen=True)
class WriteMediationDecision:
    """Pure decision model returned by the deny-only skeleton."""

    decision_id: str
    request_id: str
    decision_status: str = MEDIATOR_DECISION_DENY
    decision_reason: str = DENIED_BY_MEDIATOR_SKELETON
    mediator_status: str = DENY_ONLY_MEDIATOR_SKELETON_PRESENT
    write_path_status: str = NOT_WIRED_TO_WRITE_PATH
    enforcement_status: str = ENFORCEMENT_NOT_IMPLEMENTED
    skeleton_local_decision_only: bool = True
    write_performed: bool = False
    filesystem_interception_present: bool = False
    permission_hardening_present: bool = False

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


class DenyOnlyWriteMediator:
    """Pure deny-only mediator skeleton.

    The returned deny decision is local to this skeleton and is not evidence
    that a filesystem write path was mediated.
    """

    def decide(self, request: WriteMediationRequest) -> WriteMediationDecision:
        return WriteMediationDecision(
            decision_id=decision_id_for_request(request),
            request_id=request.request_id,
        )


def decide_write_request(request: WriteMediationRequest) -> WriteMediationDecision:
    return DenyOnlyWriteMediator().decide(request)


def decision_id_for_request(request: WriteMediationRequest) -> str:
    digest = _sha256_json(
        {
            "request": request.to_record(),
            "mediator_status": DENY_ONLY_MEDIATOR_SKELETON_PRESENT,
            "decision_status": MEDIATOR_DECISION_DENY,
            "decision_reason": DENIED_BY_MEDIATOR_SKELETON,
            "write_path_status": NOT_WIRED_TO_WRITE_PATH,
            "enforcement_status": ENFORCEMENT_NOT_IMPLEMENTED,
        }
    )
    return f"deny-only-mediator-skeleton:{digest}"


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "DenyOnlyWriteMediator",
    "WriteMediationDecision",
    "WriteMediationRequest",
    "decide_write_request",
    "decision_id_for_request",
]
