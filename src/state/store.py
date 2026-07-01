"""Read and write the folder-local ``.aeg/`` state tree."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.contracts import (
    AEG_VERSION,
    CONFIG_FILE,
    LEDGER_FILE,
    LEDGER_INTEGRITY_FIELDS,
    LEDGER_PREVIOUS_HASH_GENESIS,
    LEDGER_PREVIOUS_HASH_NOT_AVAILABLE,
    RUNS_DIR,
    SAFE_DEFAULT,
    STATE_DIR,
)
from src.evidence.binding import (
    bind_evidence_to_manifest,
    build_run_manifest,
    manifest_hash,
    repo_relative_path,
)
from src.evidence.ledger_integrity import (
    build_ledger_integrity_metadata,
    is_sha256_hex,
)


def state_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / STATE_DIR


def _assert_under_state(repo_root: str | Path, path: str | Path) -> Path:
    root = state_root(repo_root).resolve()
    resolved = Path(path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing to write outside {STATE_DIR}: {resolved}")
    return resolved


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_initialized(repo_root: str | Path) -> dict[str, Any]:
    root = state_root(repo_root)
    runs = root / RUNS_DIR
    root.mkdir(exist_ok=True)
    runs.mkdir(exist_ok=True)

    config_path = root / CONFIG_FILE
    created_config = False
    if not config_path.exists():
        _write_json(
            config_path,
            {
                "aeg_version": AEG_VERSION,
                "state_schema": "0.1.0",
                "safe_default": SAFE_DEFAULT,
                "external_accounts_required": False,
            },
        )
        created_config = True

    ledger_path = root / LEDGER_FILE
    created_ledger = False
    if not ledger_path.exists():
        ledger_path.write_text("", encoding="utf-8")
        created_ledger = True

    return {
        "state_root": str(root),
        "config_path": str(config_path),
        "runs_path": str(runs),
        "ledger_path": str(ledger_path),
        "created_config": created_config,
        "created_ledger": created_ledger,
    }


def require_initialized(repo_root: str | Path) -> None:
    root = state_root(repo_root)
    required = [root, root / CONFIG_FILE, root / RUNS_DIR, root / LEDGER_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Aegis state is not initialized; missing: {', '.join(missing)}")


def append_ledger(repo_root: str | Path, entry: dict[str, Any]) -> None:
    ledger_path = _assert_under_state(repo_root, state_root(repo_root) / LEDGER_FILE)
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry, sort_keys=True) + "\n")


def save_run(repo_root: str | Path, evidence: dict[str, Any], run_payload: dict[str, Any]) -> dict[str, str]:
    require_initialized(repo_root)
    run_id = evidence["run_id"]
    run_dir = _assert_under_state(repo_root, state_root(repo_root) / RUNS_DIR / run_id)
    run_dir.mkdir(parents=True, exist_ok=False)

    run_path = _assert_under_state(repo_root, run_dir / "run.json")
    evidence_path = _assert_under_state(repo_root, run_dir / "evidence.json")
    manifest_path = _assert_under_state(repo_root, run_dir / "manifest.json")

    recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ledger_sequence_number, previous_ledger_hash = _next_ledger_position(repo_root)
    manifest = build_run_manifest(repo_root, evidence, run_path, evidence_path)
    ledger_entry_base = _ledger_entry_base(
        repo_root,
        recorded_at,
        evidence,
        run_path,
        evidence_path,
        manifest_path,
    )
    evidence.update(
        build_ledger_integrity_metadata(
            evidence,
            manifest,
            ledger_entry_base,
            ledger_sequence_number,
            previous_ledger_hash,
        )
    )
    manifest = build_run_manifest(repo_root, evidence, run_path, evidence_path)
    bound_manifest_hash = manifest_hash(manifest)
    bind_evidence_to_manifest(
        evidence,
        manifest,
        repo_relative_path(repo_root, manifest_path),
        bound_manifest_hash,
    )

    _write_json(run_path, run_payload)
    _write_json(manifest_path, manifest)
    _write_json(evidence_path, evidence)

    ledger_entry = {
        **ledger_entry_base,
        "manifest_hash": bound_manifest_hash,
        **{field: evidence[field] for field in LEDGER_INTEGRITY_FIELDS},
    }
    append_ledger(repo_root, ledger_entry)

    return {
        "run_path": str(run_path),
        "evidence_path": str(evidence_path),
        "manifest_path": str(manifest_path),
        "manifest_hash": bound_manifest_hash,
    }


def _ledger_entry_base(
    repo_root: str | Path,
    recorded_at: str,
    evidence: dict[str, Any],
    run_path: Path,
    evidence_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    return {
        "recorded_at": recorded_at,
        "run_id": evidence["run_id"],
        "task_text": evidence["task_text"],
        "risk_level": evidence["risk_level"],
        "status": evidence["status"],
        "head_sha": evidence["head_sha"],
        "tree_sha": evidence["tree_sha"],
        "evidence_path": str(evidence_path.relative_to(repo)),
        "run_path": str(run_path.relative_to(repo)),
        "manifest_path": str(manifest_path.relative_to(repo)),
        "manifest_hash": "",
    }


def _next_ledger_position(repo_root: str | Path) -> tuple[int, str]:
    entries = _ledger_entries(repo_root)
    if not entries:
        return 1, LEDGER_PREVIOUS_HASH_GENESIS
    previous_hash = entries[-1].get("ledger_chain_hash")
    if is_sha256_hex(previous_hash):
        return len(entries) + 1, str(previous_hash)
    return len(entries) + 1, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE


def _ledger_entries(repo_root: str | Path) -> list[dict[str, Any]]:
    ledger_path = state_root(repo_root) / LEDGER_FILE
    if not ledger_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def latest_run_entry(repo_root: str | Path) -> dict[str, Any] | None:
    ledger_path = state_root(repo_root) / LEDGER_FILE
    if not ledger_path.exists():
        return None
    lines = [line.strip() for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"invalid_ledger_line": line}
    return None


def load_latest_evidence(repo_root: str | Path) -> tuple[dict[str, Any] | None, Path | None, dict[str, Any] | None]:
    entry = latest_run_entry(repo_root)
    if not entry or "run_id" not in entry:
        return None, None, entry

    evidence_path = state_root(repo_root) / RUNS_DIR / entry["run_id"] / "evidence.json"
    if not evidence_path.exists():
        return None, evidence_path, entry

    with evidence_path.open(encoding="utf-8") as handle:
        return json.load(handle), evidence_path, entry
