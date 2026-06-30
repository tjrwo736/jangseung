"""Independent pre/post git mutation boundary helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.classify import is_protected_path
from src.contracts import (
    GIT_STATUS_PORCELAIN_V1,
    MUTATION_BOUNDARY_CLEAN,
    MUTATION_BOUNDARY_DELTA_DETECTED,
    MUTATION_BOUNDARY_DIRTY_PREEXISTING,
    MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT,
    MUTATION_DELTA_SOURCE_COMPUTED,
    MUTATION_DELTA_SOURCE_UNTRUSTED,
    NOT_CHECKED_SOURCE,
    REPORTED_ONLY,
    SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
    SNAPSHOT_TRUST_BOUNDARY_CLI_WRAPPER_V1,
)
from src.state import git


@dataclass(frozen=True)
class MutationSnapshot:
    changed_files: list[dict[str, Any]]
    source: str
    collector: str
    captured_at: str
    error: str | None = None


def capture_mutation_snapshot(repo: str | Path) -> MutationSnapshot:
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        return MutationSnapshot(
            changed_files=git.changed_file_snapshot(repo),
            source=GIT_STATUS_PORCELAIN_V1,
            collector=SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
            captured_at=captured_at,
        )
    except git.GitError as exc:
        return MutationSnapshot(
            changed_files=[],
            source=NOT_CHECKED_SOURCE,
            collector=SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
            captured_at=captured_at,
            error=str(exc),
        )


def build_mutation_boundary(
    pre_snapshot: MutationSnapshot,
    post_snapshot: MutationSnapshot,
    executor_result: dict[str, Any],
) -> dict[str, Any]:
    trust_boundary = snapshot_trust_boundary(pre_snapshot, post_snapshot)
    trusted = trust_boundary.get("trust_boundary_satisfied") is True
    computed_delta = compute_mutation_delta(pre_snapshot.changed_files, post_snapshot.changed_files)
    protected_path_mutation = any(is_protected_path(path) for path in mutation_delta_paths(computed_delta))
    if not trusted:
        boundary_status = MUTATION_BOUNDARY_UNTRUSTED_SNAPSHOT
        mutation_delta_source = MUTATION_DELTA_SOURCE_UNTRUSTED
        executor_created_mutation: list[dict[str, Any]] = []
    elif computed_delta:
        boundary_status = MUTATION_BOUNDARY_DELTA_DETECTED
        mutation_delta_source = MUTATION_DELTA_SOURCE_COMPUTED
        executor_created_mutation = list(computed_delta)
    elif pre_snapshot.changed_files:
        boundary_status = MUTATION_BOUNDARY_DIRTY_PREEXISTING
        mutation_delta_source = MUTATION_DELTA_SOURCE_COMPUTED
        executor_created_mutation = []
    else:
        boundary_status = MUTATION_BOUNDARY_CLEAN
        mutation_delta_source = MUTATION_DELTA_SOURCE_COMPUTED
        executor_created_mutation = []

    return {
        "pre_run_changed_files": list(pre_snapshot.changed_files),
        "post_run_changed_files": list(post_snapshot.changed_files),
        "pre_snapshot_source": pre_snapshot.source,
        "post_snapshot_source": post_snapshot.source,
        "snapshot_collector": pre_snapshot.collector,
        "snapshot_trust_boundary": trust_boundary,
        "executor_reported_changed_files": _reported_list(executor_result.get("changed_files")),
        "executor_reported_changed_files_source": REPORTED_ONLY,
        "executor_reported_mutation_delta": _reported_list(executor_result.get("mutation_delta")),
        "executor_reported_mutation_delta_source": REPORTED_ONLY,
        "computed_mutation_delta": list(computed_delta),
        "mutation_delta_source": mutation_delta_source,
        "pre_existing_dirty_tree": list(pre_snapshot.changed_files),
        "executor_created_mutation": executor_created_mutation,
        "protected_path_mutation_detected": protected_path_mutation,
        "mutation_boundary_status": boundary_status,
    }


def snapshot_trust_boundary(pre_snapshot: MutationSnapshot, post_snapshot: MutationSnapshot) -> dict[str, Any]:
    same_collector = pre_snapshot.collector == post_snapshot.collector == SNAPSHOT_COLLECTOR_GIT_STATUS_V1
    trusted_sources = pre_snapshot.source == post_snapshot.source == GIT_STATUS_PORCELAIN_V1
    no_capture_errors = pre_snapshot.error is None and post_snapshot.error is None
    trust_boundary_satisfied = same_collector and trusted_sources and no_capture_errors
    result: dict[str, Any] = {
        "name": SNAPSHOT_TRUST_BOUNDARY_CLI_WRAPPER_V1,
        "collector": SNAPSHOT_COLLECTOR_GIT_STATUS_V1,
        "executor_controlled": False,
        "pre_captured_before_executor": True,
        "post_captured_after_executor": True,
        "same_collector": same_collector,
        "trusted_sources": trusted_sources,
        "trust_boundary_satisfied": trust_boundary_satisfied,
        "pre_captured_at": pre_snapshot.captured_at,
        "post_captured_at": post_snapshot.captured_at,
    }
    if pre_snapshot.error is not None:
        result["pre_snapshot_error"] = pre_snapshot.error
    if post_snapshot.error is not None:
        result["post_snapshot_error"] = post_snapshot.error
    return result


def compute_mutation_delta(pre_snapshot: list[dict[str, Any]], post_snapshot: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pre_by_key = {_entry_key(entry): _canonical_entry(entry) for entry in pre_snapshot}
    post_by_key = {_entry_key(entry): _canonical_entry(entry) for entry in post_snapshot}
    delta: list[dict[str, Any]] = []
    for key in sorted(set(pre_by_key) | set(post_by_key)):
        before = pre_by_key.get(key)
        after = post_by_key.get(key)
        if before == after:
            continue
        delta.append(
            {
                "path": _delta_path(before, after),
                "transition": _transition(before, after),
                "before": before,
                "after": after,
            }
        )
    return delta


def mutation_delta_paths(delta: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for entry in delta:
        for state_name in ("before", "after"):
            state = entry.get(state_name)
            if not isinstance(state, dict):
                continue
            path = state.get("path")
            if isinstance(path, str) and path:
                paths.append(path)
            original_path = state.get("original_path")
            if isinstance(original_path, str) and original_path:
                paths.append(original_path)
        path = entry.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def _canonical_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(entry.get("path", "")),
        "original_path": entry.get("original_path"),
        "index_status": str(entry.get("index_status", "")),
        "worktree_status": str(entry.get("worktree_status", "")),
        "index_state": str(entry.get("index_state", "")),
        "worktree_state": str(entry.get("worktree_state", "")),
        "tracked_diff_status": str(entry.get("tracked_diff_status", "")),
        "staged": entry.get("staged") is True,
        "unstaged": entry.get("unstaged") is True,
        "tracked": entry.get("tracked") is True,
        "untracked": entry.get("untracked") is True,
    }


def _entry_key(entry: dict[str, Any]) -> tuple[str, str]:
    canonical = _canonical_entry(entry)
    return canonical["path"], str(canonical.get("original_path") or "")


def _delta_path(before: dict[str, Any] | None, after: dict[str, Any] | None) -> str:
    state = after or before or {}
    path = state.get("path")
    return path if isinstance(path, str) else ""


def _transition(before: dict[str, Any] | None, after: dict[str, Any] | None) -> str:
    if before is None and after is not None:
        return "added_to_dirty_state"
    if before is not None and after is None:
        return "removed_from_dirty_state"
    return "dirty_state_changed"


def _reported_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []
