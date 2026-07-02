"""Phase 10-E4 mediated outside-repo write path denial helper.

The helper models an in-process mediated write request for targets that
canonicalize outside the repository boundary, calls the E2 deny-only mediator
skeleton, and returns a repo-boundary denial result without writing. It is not
OS, filesystem, or external enforcement and raw/direct writes remain bypassable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from src.contracts import (
    DENIED_BY_MEDIATOR,
    DENIED_BY_REPO_BOUNDARY_POLICY,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATED_WRITE_DENIED,
    NOT_FILESYSTEM_ENFORCED,
    OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    REPO_BOUNDARY_WRITE_DENIED,
    WRITE_CLASS_OUTSIDE_REPO_WRITE,
)
from src.evidence.deny_only_mediator import (
    WriteMediationDecision,
    WriteMediationRequest,
    decide_write_request,
)


@dataclass(frozen=True)
class RepoBoundaryPathResolution:
    """Canonical repo-boundary path view used by the Phase 10-E4 policy."""

    repo_root: str
    submitted_target: str
    absolute_target: str
    canonical_target: str
    target_under_repo: bool
    target_outside_repo: bool

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediatedOutsideRepoWriteResult:
    """Denied mediated outside-repo write result.

    This is a mediator/repo-boundary policy denial only. It is intentionally
    not a claim that raw/direct filesystem writes are blocked.
    """

    decision_id: str
    request: WriteMediationRequest
    mediator_decision: WriteMediationDecision
    path_resolution: RepoBoundaryPathResolution
    decision_status: str = MEDIATED_WRITE_DENIED
    decision_reason: str = OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH
    mediator_status: str = DENIED_BY_MEDIATOR
    path_policy_status: str = REPO_BOUNDARY_WRITE_DENIED
    repo_boundary_policy_status: str = DENIED_BY_REPO_BOUNDARY_POLICY
    enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    external_enforcement_status: str = EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED
    raw_direct_write_status: str = RAW_DIRECT_WRITE_STILL_BYPASSABLE
    write_performed: bool = False
    target_outside_repo: bool = True
    filesystem_interception_present: bool = False
    permission_hardening_present: bool = False
    mediated_outside_repo_denial_present: bool = True
    live_executor_authority_granted: bool = False

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["request"] = self.request.to_record()
        record["mediator_decision"] = self.mediator_decision.to_record()
        record["path_resolution"] = self.path_resolution.to_record()
        return record


def request_mediated_outside_repo_write_text(
    *,
    repo_root: str | Path,
    submitted_target: str | Path,
    payload: str,
    actor: str,
    operation: str = "write",
    request_id: str | None = None,
) -> MediatedOutsideRepoWriteResult:
    """Request a mediated text write outside the repo and return denial.

    ``payload`` is accepted to model the requested write, but this helper never
    writes it. Phase 10-E4 only implements mediated outside-repo denial through
    the repo-boundary path policy.
    """

    path_resolution = resolve_repo_boundary_path(
        repo_root=repo_root,
        submitted_target=submitted_target,
    )
    if not path_resolution.target_outside_repo:
        raise ValueError("Phase 10-E4 only implements mediated outside-repo write denial")

    request = WriteMediationRequest(
        request_id=request_id
        or _request_id_for_path(
            actor=actor,
            operation=operation,
            submitted_target=path_resolution.submitted_target,
            canonical_target=path_resolution.canonical_target,
        ),
        actor=actor,
        operation=operation,
        write_class=WRITE_CLASS_OUTSIDE_REPO_WRITE,
        submitted_target=path_resolution.submitted_target,
        canonical_target=path_resolution.canonical_target,
        declared_scope="phase10_e4_outside_repo_write_denial_v0",
        repo_boundary="outside_repo",
        aeg_boundary="not_evaluated_for_aeg_denial",
        action_summary="mediated outside-repo write request denied before file mutation",
        metadata={
            "payload_size_bytes": str(len(payload.encode("utf-8"))),
            "path_policy": REPO_BOUNDARY_WRITE_DENIED,
            "repo_boundary_policy": DENIED_BY_REPO_BOUNDARY_POLICY,
            "raw_direct_write_status": RAW_DIRECT_WRITE_STILL_BYPASSABLE,
        },
    )
    mediator_decision = decide_write_request(request)
    return MediatedOutsideRepoWriteResult(
        decision_id=_decision_id_for_denied_path(request, mediator_decision, path_resolution),
        request=request,
        mediator_decision=mediator_decision,
        path_resolution=path_resolution,
        target_outside_repo=path_resolution.target_outside_repo,
    )


def resolve_repo_boundary_path(
    *,
    repo_root: str | Path,
    submitted_target: str | Path,
) -> RepoBoundaryPathResolution:
    repo_root_path = Path(repo_root).resolve(strict=False)
    submitted_path = Path(submitted_target)
    absolute_target = submitted_path if submitted_path.is_absolute() else repo_root_path / submitted_path
    canonical_target = absolute_target.resolve(strict=False)
    target_under_repo = _is_relative_to_or_same(canonical_target, repo_root_path)
    return RepoBoundaryPathResolution(
        repo_root=str(repo_root_path),
        submitted_target=str(submitted_target),
        absolute_target=str(absolute_target),
        canonical_target=str(canonical_target),
        target_under_repo=target_under_repo,
        target_outside_repo=not target_under_repo,
    )


def _request_id_for_path(
    *,
    actor: str,
    operation: str,
    submitted_target: str,
    canonical_target: str,
) -> str:
    digest = _sha256_json(
        {
            "actor": actor,
            "operation": operation,
            "submitted_target": submitted_target,
            "canonical_target": canonical_target,
        }
    )
    return f"phase10-e4-mediated-outside-repo-write:{digest}"


def _decision_id_for_denied_path(
    request: WriteMediationRequest,
    mediator_decision: WriteMediationDecision,
    path_resolution: RepoBoundaryPathResolution,
) -> str:
    digest = _sha256_json(
        {
            "request": request.to_record(),
            "mediator_decision": mediator_decision.to_record(),
            "path_resolution": path_resolution.to_record(),
            "decision_status": MEDIATED_WRITE_DENIED,
            "decision_reason": OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH,
            "path_policy_status": REPO_BOUNDARY_WRITE_DENIED,
            "repo_boundary_policy_status": DENIED_BY_REPO_BOUNDARY_POLICY,
            "enforcement_status": NOT_FILESYSTEM_ENFORCED,
            "external_enforcement_status": EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
            "raw_direct_write_status": RAW_DIRECT_WRITE_STILL_BYPASSABLE,
        }
    )
    return f"mediated-outside-repo-write-denial:{digest}"


def _is_relative_to_or_same(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "MediatedOutsideRepoWriteResult",
    "RepoBoundaryPathResolution",
    "request_mediated_outside_repo_write_text",
    "resolve_repo_boundary_path",
]
