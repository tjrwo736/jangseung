"""Evidence binding v1 manifest and hash helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.contracts import (
    BOUND,
    CITIZEN_ONE_EVIDENCE_FIELDS,
    EVIDENCE_BINDING_V1,
    RUN_MANIFEST_V1,
    RUNS_DIR,
    SAFE_DEFAULT,
    STATE_DIR,
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def changed_files_hash(changed_files: Any) -> str:
    if not isinstance(changed_files, list):
        return sha256_json([])
    return sha256_json(changed_files)


def manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256_json(manifest)


def expected_artifact_path(run_id: str, filename: str) -> str:
    return (Path(STATE_DIR) / RUNS_DIR / run_id / filename).as_posix()


def repo_relative_path(repo_root: str | Path, path: str | Path) -> str:
    return Path(path).resolve().relative_to(Path(repo_root).resolve()).as_posix()


def build_run_manifest(
    repo_root: str | Path,
    evidence: dict[str, Any],
    run_path: str | Path,
    evidence_path: str | Path,
) -> dict[str, Any]:
    task_text = evidence.get("task_text")
    if not isinstance(task_text, str):
        task_text = ""
    changed_files = evidence.get("changed_files", [])
    if not isinstance(changed_files, list):
        changed_files = []
    pre_run_changed_files = _list_field(evidence, "pre_run_changed_files")
    post_run_changed_files = _list_field(evidence, "post_run_changed_files")
    computed_mutation_delta = _list_field(evidence, "computed_mutation_delta")
    pre_existing_dirty_tree = _list_field(evidence, "pre_existing_dirty_tree")
    executor_created_mutation = _list_field(evidence, "executor_created_mutation")
    citizen_one_fields = citizen_one_manifest_fields(evidence)
    manifest: dict[str, Any] = {
        "manifest_version": RUN_MANIFEST_V1,
        "run_id": evidence.get("run_id", ""),
        "repo_root": evidence.get("repo_root", str(Path(repo_root).resolve())),
        "branch": evidence.get("branch", ""),
        "head_sha": evidence.get("head_sha", ""),
        "tree_sha": evidence.get("tree_sha", ""),
        "changed_files": list(changed_files),
        "changed_files_source": evidence.get("changed_files_source", ""),
        "changed_files_hash": changed_files_hash(changed_files),
        "pre_run_changed_files": list(pre_run_changed_files),
        "post_run_changed_files": list(post_run_changed_files),
        "pre_run_changed_files_hash": sha256_json(pre_run_changed_files),
        "post_run_changed_files_hash": sha256_json(post_run_changed_files),
        "pre_snapshot_source": evidence.get("pre_snapshot_source", ""),
        "post_snapshot_source": evidence.get("post_snapshot_source", ""),
        "snapshot_collector": evidence.get("snapshot_collector", ""),
        "snapshot_trust_boundary": evidence.get("snapshot_trust_boundary", {}),
        "snapshot_trust_boundary_hash": sha256_json(evidence.get("snapshot_trust_boundary", {})),
        "computed_mutation_delta": list(computed_mutation_delta),
        "computed_mutation_delta_hash": sha256_json(computed_mutation_delta),
        "mutation_delta_source": evidence.get("mutation_delta_source", ""),
        "pre_existing_dirty_tree": list(pre_existing_dirty_tree),
        "pre_existing_dirty_tree_hash": sha256_json(pre_existing_dirty_tree),
        "executor_created_mutation": list(executor_created_mutation),
        "executor_created_mutation_hash": sha256_json(executor_created_mutation),
        "protected_path_mutation_detected": evidence.get("protected_path_mutation_detected", False),
        "mutation_boundary_status": evidence.get("mutation_boundary_status", ""),
        "evidence_path": repo_relative_path(repo_root, evidence_path),
        "run_path": repo_relative_path(repo_root, run_path),
        "task_text_hash": sha256_text(task_text),
        "risk_level": evidence.get("risk_level", ""),
        "status": evidence.get("status", ""),
        "safe_default": evidence.get("safe_default", SAFE_DEFAULT),
        **citizen_one_fields,
        "citizen_one_evidence_hash": sha256_json(citizen_one_fields),
    }
    return manifest


def bind_evidence_to_manifest(
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: str,
    bound_manifest_hash: str,
) -> None:
    evidence["binding_version"] = EVIDENCE_BINDING_V1
    evidence["binding_status"] = BOUND
    evidence["binding_reasons"] = []
    evidence["bound_run_id"] = manifest.get("run_id", "")
    evidence["bound_repo_root"] = manifest.get("repo_root", "")
    evidence["bound_branch"] = manifest.get("branch", "")
    evidence["bound_head_sha"] = manifest.get("head_sha", "")
    evidence["bound_tree_sha"] = manifest.get("tree_sha", "")
    evidence["bound_changed_files_hash"] = manifest.get("changed_files_hash", "")
    evidence["bound_pre_run_changed_files_hash"] = manifest.get("pre_run_changed_files_hash", "")
    evidence["bound_post_run_changed_files_hash"] = manifest.get("post_run_changed_files_hash", "")
    evidence["bound_computed_mutation_delta_hash"] = manifest.get("computed_mutation_delta_hash", "")
    evidence["bound_snapshot_trust_boundary_hash"] = manifest.get("snapshot_trust_boundary_hash", "")
    evidence["bound_manifest_hash"] = bound_manifest_hash
    evidence["bound_manifest_path"] = manifest_path
    evidence["bound_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evidence["reported_only"] = False

    checks = evidence.setdefault("checks", {})
    if isinstance(checks, dict):
        checks["evidence_binding_v1_required"] = True
        checks["reported_only_is_not_judgment_basis"] = True
        checks["mutation_boundary_v1_required"] = True


def _list_field(evidence: dict[str, Any], field: str) -> list[Any]:
    value = evidence.get(field, [])
    if isinstance(value, list):
        return list(value)
    return []


def citizen_one_manifest_fields(evidence: dict[str, Any]) -> dict[str, Any]:
    return {field: evidence.get(field) for field in CITIZEN_ONE_EVIDENCE_FIELDS}
