"""B1-B deny-only guard component for submitted ``.aeg`` paths.

This component canonicalizes a submitted path and returns a decision record. It
does not write files, change permissions, wire runtime execution, or grant
executor authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from src.contracts import (
    B1_AEG_DIRECT_TARGET_DENIED,
    B1_AEG_EVIDENCE_TARGET_DENIED,
    B1_AEG_INTEGRITY_DENY_ONLY_GUARD,
    B1_AEG_LEDGER_TARGET_DENIED,
    B1_AEG_MANIFEST_TARGET_DENIED,
    B1_AEG_NOT_PROTECTED_TARGET,
    B1_AEG_OUT_OF_SCOPE,
    B1_AEG_PROTECTED_TARGET,
    B1_AEG_SYMLINK_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    B1_AEG_VERIFY_BASIS_TARGET_DENIED,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    STATE_DIR,
)


@dataclass(frozen=True)
class B1AegIntegrityGuardDecision:
    component: str
    decision_id: str
    submitted_path: str
    absolute_path: str
    resolved_path: str
    protected_root: str
    protected_target: bool
    protected_target_status: str
    target_class: str
    denial_reason: str
    wiring_status: str
    os_enforcement_status: str
    filesystem_enforcement_status: str
    live_executor_authority_status: str
    phase11a_status: str
    write_performed: bool
    filesystem_mutation_performed: bool
    capability_grant_created: bool
    executor_write_path_wired: bool

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def decide_b1_aeg_integrity_guard(
    *,
    repo_root: str | Path,
    submitted_path: str | Path,
) -> B1AegIntegrityGuardDecision:
    """Classify a submitted path under the B1-B deny-only guard component."""

    repo_root_path = Path(repo_root).resolve(strict=False)
    protected_root = (repo_root_path / STATE_DIR).resolve(strict=False)
    submitted = Path(submitted_path)
    absolute_path = submitted if submitted.is_absolute() else repo_root_path / submitted
    resolved_path = absolute_path.resolve(strict=False)
    protected_target = _is_relative_to_or_same(resolved_path, protected_root)

    if protected_target:
        target_class = _classify_protected_target(
            resolved_path=resolved_path,
            protected_root=protected_root,
            submitted_path=submitted,
            absolute_path=absolute_path,
        )
        protected_target_status = B1_AEG_PROTECTED_TARGET
        denial_reason = DENIED_BY_B1_AEG_INTEGRITY_GUARD
    else:
        target_class = B1_AEG_NOT_PROTECTED_TARGET
        protected_target_status = B1_AEG_NOT_PROTECTED_TARGET
        denial_reason = B1_AEG_OUT_OF_SCOPE

    return B1AegIntegrityGuardDecision(
        component=B1_AEG_INTEGRITY_DENY_ONLY_GUARD,
        decision_id=_decision_id(
            submitted_path=str(submitted_path),
            resolved_path=str(resolved_path),
            protected_root=str(protected_root),
            protected_target=protected_target,
            target_class=target_class,
            denial_reason=denial_reason,
        ),
        submitted_path=str(submitted_path),
        absolute_path=str(absolute_path),
        resolved_path=str(resolved_path),
        protected_root=str(protected_root),
        protected_target=protected_target,
        protected_target_status=protected_target_status,
        target_class=target_class,
        denial_reason=denial_reason,
        wiring_status=NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
        os_enforcement_status=NOT_OS_ENFORCED,
        filesystem_enforcement_status=NOT_FILESYSTEM_ENFORCED,
        live_executor_authority_status=LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        phase11a_status=PHASE11A_NOT_STARTED,
        write_performed=False,
        filesystem_mutation_performed=False,
        capability_grant_created=False,
        executor_write_path_wired=False,
    )


def _classify_protected_target(
    *,
    resolved_path: Path,
    protected_root: Path,
    submitted_path: Path,
    absolute_path: Path,
) -> str:
    relative = resolved_path.relative_to(protected_root)
    if relative == Path("ledger.jsonl"):
        return B1_AEG_LEDGER_TARGET_DENIED
    if relative == Path("manifest"):
        return B1_AEG_MANIFEST_TARGET_DENIED
    if _is_runs_file(relative, "evidence_packet.json"):
        return B1_AEG_EVIDENCE_TARGET_DENIED
    if _is_runs_file(relative, "verify_basis.json"):
        return B1_AEG_VERIFY_BASIS_TARGET_DENIED
    if ".." in submitted_path.parts:
        return B1_AEG_TRAVERSAL_TARGET_DENIED
    if _has_symlink_alias(absolute_path, protected_root):
        return B1_AEG_SYMLINK_TARGET_DENIED
    return B1_AEG_DIRECT_TARGET_DENIED


def _is_runs_file(relative_path: Path, filename: str) -> bool:
    return len(relative_path.parts) >= 3 and relative_path.parts[0] == "runs" and relative_path.name == filename


def _has_symlink_alias(absolute_path: Path, protected_root: Path) -> bool:
    if STATE_DIR in absolute_path.parts:
        return False
    for candidate in (absolute_path, *absolute_path.parents):
        if candidate == protected_root.parent:
            break
        if candidate.is_symlink():
            return True
    return False


def _is_relative_to_or_same(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _decision_id(
    *,
    submitted_path: str,
    resolved_path: str,
    protected_root: str,
    protected_target: bool,
    target_class: str,
    denial_reason: str,
) -> str:
    payload = {
        "component": B1_AEG_INTEGRITY_DENY_ONLY_GUARD,
        "submitted_path": submitted_path,
        "resolved_path": resolved_path,
        "protected_root": protected_root,
        "protected_target": protected_target,
        "target_class": target_class,
        "denial_reason": denial_reason,
        "wiring_status": NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    }
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return f"b1-aeg-integrity-guard:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


__all__ = [
    "B1AegIntegrityGuardDecision",
    "decide_b1_aeg_integrity_guard",
]
