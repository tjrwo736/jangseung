"""Evidence binding v1 manifest and hash helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.contracts import (
    BOUND,
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
        "evidence_path": repo_relative_path(repo_root, evidence_path),
        "run_path": repo_relative_path(repo_root, run_path),
        "task_text_hash": sha256_text(task_text),
        "risk_level": evidence.get("risk_level", ""),
        "status": evidence.get("status", ""),
        "safe_default": evidence.get("safe_default", SAFE_DEFAULT),
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
    evidence["bound_manifest_hash"] = bound_manifest_hash
    evidence["bound_manifest_path"] = manifest_path
    evidence["bound_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evidence["reported_only"] = False

    checks = evidence.setdefault("checks", {})
    if isinstance(checks, dict):
        checks["evidence_binding_v1_required"] = True
        checks["reported_only_is_not_judgment_basis"] = True
