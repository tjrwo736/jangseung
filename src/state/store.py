"""Read and write the folder-local ``.aeg/`` state tree."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

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
    STORE_WRITE_MEDIATION_REASON_OUT_OF_SCOPE,
    STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_FALLBACK,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED,
    STORE_WRITE_MEDIATION_RESULT_OUT_OF_SCOPE_UNCHANGED,
    STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_PROVENANCE_BASIS_DETERMINISTIC_CALL_SITE,
    STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
    STORE_WRITE_PROVENANCE_SOURCE_DETERMINISTIC_CALL_SITE,
    STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
    WRITE_CLASS_AEG_STATE_WRITE,
)
from src.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard
from src.evidence.binding import (
    bind_evidence_to_manifest,
    build_run_manifest,
    manifest_hash,
    repo_relative_path,
)
from src.evidence.deny_only_mediator import (
    WriteMediationDecision,
    WriteMediationRequest,
    decide_write_request,
)
from src.evidence.ledger_integrity import (
    build_ledger_integrity_metadata,
    is_sha256_hex,
)
from src.evidence.store_write_mediation import build_store_write_mediation_metadata


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


def _append_ledger_unmediated(ledger_path: Path, entry: dict[str, Any]) -> None:
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(entry, sort_keys=True) + "\n")


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
    _append_ledger_unmediated(ledger_path, entry)


def save_run(repo_root: str | Path, evidence: dict[str, Any], run_payload: dict[str, Any]) -> dict[str, str]:
    require_initialized(repo_root)
    run_id = evidence["run_id"]
    run_dir = _assert_under_state(repo_root, state_root(repo_root) / RUNS_DIR / run_id)
    ledger_sequence_number, previous_ledger_hash = _next_ledger_position(repo_root)
    run_dir.mkdir(parents=True, exist_ok=False)

    run_path = _assert_under_state(repo_root, run_dir / "run.json")
    evidence_path = _assert_under_state(repo_root, run_dir / "evidence.json")
    manifest_path = _assert_under_state(repo_root, run_dir / "manifest.json")
    ledger_path = _assert_under_state(repo_root, state_root(repo_root) / LEDGER_FILE)
    mediation_events = _collect_store_write_mediation_events(
        repo_root=repo_root,
        evidence=evidence,
        trusted_runtime_targets=(
            (run_path, "save_run.run_json"),
            (manifest_path, "save_run.manifest_json"),
            (evidence_path, "save_run.evidence_json"),
            (ledger_path, "save_run.ledger_append"),
        ),
    )
    evidence.update(build_store_write_mediation_metadata(mediation_events))

    recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
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
    _append_ledger_unmediated(ledger_path, ledger_entry)

    return {
        "run_path": str(run_path),
        "evidence_path": str(evidence_path),
        "manifest_path": str(manifest_path),
        "manifest_hash": bound_manifest_hash,
    }


def attempt_executor_attributed_aeg_write_text(
    repo_root: str | Path,
    submitted_target: str | Path,
    payload: str,
    *,
    executor_claimed_provenance: str | None = None,
    mediator_route: Callable[[WriteMediationRequest], WriteMediationDecision | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Route an executor-attributed ``.aeg`` write attempt without writing it."""

    route = mediator_route or decide_write_request
    target = _target_path(repo_root, submitted_target)
    existed_before = target.exists()
    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=submitted_target,
    )
    base_event = _store_write_event_base(
        repo_root=repo_root,
        submitted_target=submitted_target,
        target=target,
        operation="write_text",
        call_site="store.attempt_executor_attributed_aeg_write_text",
        provenance_type=STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
        target_exists_before=existed_before,
        executor_claimed_provenance=executor_claimed_provenance,
    )
    base_event["guard_router_invoked"] = True
    base_event["guard_decision"] = guard_decision.to_record()

    if not guard_decision.protected_target:
        return {
            **base_event,
            "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_OUT_OF_SCOPE_UNCHANGED,
            "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_OUT_OF_SCOPE,
            "mediator_request": None,
            "mediator_decision": None,
            "write_performed": False,
            "fallback_to_unwired": False,
            "wired_path_failed": False,
            "target_exists_after": target.exists(),
            "target_file_created": (not existed_before and target.exists()),
        }

    mediator_request = WriteMediationRequest(
        request_id=_store_write_request_id(
            actor=STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
            operation="write_text",
            submitted_target=str(submitted_target),
            canonical_target=str(target),
            payload=payload,
        ),
        actor="store.py:executor_attributed_write_path",
        operation="write_text",
        write_class=WRITE_CLASS_AEG_STATE_WRITE,
        submitted_target=str(submitted_target),
        canonical_target=str(target),
        declared_scope="phase11b0_store_write_mediation_v0",
        repo_boundary="repo_root_resolved_by_b1_guard",
        aeg_boundary=guard_decision.protected_target_status,
        action_summary="executor-attributed .aeg write routed before mutation",
        metadata={
            "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_DETERMINISTIC_CALL_SITE,
            "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_DETERMINISTIC_CALL_SITE,
            "write_provenance_type": STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
            "executor_claimed_provenance": executor_claimed_provenance or "",
        },
    )
    try:
        raw_decision = route(mediator_request)
        mediator_decision = raw_decision.to_record() if isinstance(raw_decision, WriteMediationDecision) else dict(raw_decision)
        wired_path_failed = False
    except Exception as exc:  # noqa: BLE001 - safe default is to block executor-attributed writes.
        mediator_decision = {
            "status": "raised_exception",
            "exception_type": exc.__class__.__name__,
            "write_performed": False,
        }
        wired_path_failed = True

    return {
        **base_event,
        "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_BLOCKED,
        "write_mediation_reason": "executor_attributed_aeg_write_blocked_by_guard_router",
        "mediator_request": mediator_request.to_record(),
        "mediator_decision": mediator_decision,
        "write_performed": False,
        "fallback_to_unwired": False,
        "wired_path_failed": wired_path_failed,
        "target_exists_after": target.exists(),
        "target_file_created": (not existed_before and target.exists()),
    }


def _collect_store_write_mediation_events(
    *,
    repo_root: str | Path,
    evidence: Mapping[str, Any],
    trusted_runtime_targets: tuple[tuple[Path, str], ...],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for attempt in _executor_attributed_store_write_attempts(evidence):
        events.append(
            attempt_executor_attributed_aeg_write_text(
                repo_root,
                attempt["target"],
                attempt["payload"],
                executor_claimed_provenance=attempt.get("executor_claimed_provenance"),
            )
        )
    for target, call_site in trusted_runtime_targets:
        events.append(
            _plan_trusted_runtime_store_write(
                repo_root=repo_root,
                target=target,
                operation="append" if target.name == LEDGER_FILE else "write_json",
                call_site=f"store.py:{call_site}",
            )
        )
    return events


def _executor_attributed_store_write_attempts(evidence: Mapping[str, Any]) -> list[dict[str, str]]:
    checks = evidence.get("checks")
    executor = checks.get("executor") if isinstance(checks, Mapping) else None
    attempts = executor.get("executor_attributed_aeg_write_attempts") if isinstance(executor, Mapping) else None
    if not isinstance(attempts, list):
        return []
    normalized: list[dict[str, str]] = []
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            continue
        target = attempt.get("target", attempt.get("submitted_target"))
        if not isinstance(target, str) or not target.strip():
            continue
        payload = attempt.get("payload", "")
        claimed = attempt.get("executor_claimed_provenance", attempt.get("claimed_provenance", ""))
        normalized.append(
            {
                "target": target,
                "payload": payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True),
                "executor_claimed_provenance": claimed if isinstance(claimed, str) else "",
            }
        )
    return normalized


def _plan_trusted_runtime_store_write(
    *,
    repo_root: str | Path,
    target: Path,
    operation: str,
    call_site: str,
) -> dict[str, Any]:
    existed_before = target.exists()
    base_event = _store_write_event_base(
        repo_root=repo_root,
        submitted_target=_repo_relative_or_absolute(repo_root, target),
        target=target,
        operation=operation,
        call_site=call_site,
        provenance_type=STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
        target_exists_before=existed_before,
        executor_claimed_provenance=None,
    )
    try:
        gate_record = _trusted_runtime_store_write_gate(
            repo_root=repo_root,
            target=target,
            operation=operation,
            call_site=call_site,
        )
        return {
            **base_event,
            "guard_router_invoked": True,
            "guard_decision": gate_record.get("guard_decision"),
            "trusted_runtime_gate": gate_record,
            "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED,
            "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_ALLOWED,
            "mediator_request": None,
            "mediator_decision": None,
            "write_performed": True,
            "fallback_to_unwired": False,
            "wired_path_failed": False,
            "target_exists_after": True,
            "target_file_created": not existed_before,
        }
    except Exception as exc:  # noqa: BLE001 - trusted runtime writes must preserve existing save_run behavior.
        return {
            **base_event,
            "guard_router_invoked": True,
            "guard_decision": None,
            "trusted_runtime_gate": {
                "status": "raised_exception",
                "exception_type": exc.__class__.__name__,
                "call_site": call_site,
            },
            "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED,
            "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_FALLBACK,
            "mediator_request": None,
            "mediator_decision": None,
            "write_performed": True,
            "fallback_to_unwired": True,
            "wired_path_failed": True,
            "target_exists_after": True,
            "target_file_created": not existed_before,
        }


def _trusted_runtime_store_write_gate(
    *,
    repo_root: str | Path,
    target: Path,
    operation: str,
    call_site: str,
) -> dict[str, Any]:
    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=_repo_relative_or_absolute(repo_root, target),
    )
    return {
        "status": "trusted_runtime_allowed",
        "operation": operation,
        "call_site": call_site,
        "guard_decision": guard_decision.to_record(),
        "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_DETERMINISTIC_CALL_SITE,
        "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_DETERMINISTIC_CALL_SITE,
        "write_provenance_type": STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
    }


def _store_write_event_base(
    *,
    repo_root: str | Path,
    submitted_target: str | Path,
    target: Path,
    operation: str,
    call_site: str,
    provenance_type: str,
    target_exists_before: bool,
    executor_claimed_provenance: str | None,
) -> dict[str, Any]:
    return {
        "event_id": _store_write_event_id(
            repo_root=repo_root,
            submitted_target=str(submitted_target),
            canonical_target=str(target),
            operation=operation,
            call_site=call_site,
            provenance_type=provenance_type,
        ),
        "operation": operation,
        "call_site": call_site,
        "submitted_target": str(submitted_target),
        "canonical_target": str(target),
        "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_DETERMINISTIC_CALL_SITE,
        "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_DETERMINISTIC_CALL_SITE,
        "write_provenance_type": provenance_type,
        "executor_claimed_provenance": executor_claimed_provenance or "",
        "executor_self_report_used": False,
        "trusted_runtime_claim_allowed": False,
        "target_exists_before": target_exists_before,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "phase11b_live_executor_status": PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
    }


def _target_path(repo_root: str | Path, submitted_target: str | Path) -> Path:
    repo = Path(repo_root).resolve()
    target = Path(submitted_target)
    if target.is_absolute():
        return target.resolve(strict=False)
    return (repo / target).resolve(strict=False)


def _repo_relative_or_absolute(repo_root: str | Path, target: Path) -> str:
    repo = Path(repo_root).resolve()
    resolved = target.resolve(strict=False)
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError:
        return str(resolved)


def _store_write_request_id(
    *,
    actor: str,
    operation: str,
    submitted_target: str,
    canonical_target: str,
    payload: str,
) -> str:
    digest = _sha256_json(
        {
            "actor": actor,
            "operation": operation,
            "submitted_target": submitted_target,
            "canonical_target": canonical_target,
            "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    )
    return f"phase11b0-store-write-request:{digest}"


def _store_write_event_id(
    *,
    repo_root: str | Path,
    submitted_target: str,
    canonical_target: str,
    operation: str,
    call_site: str,
    provenance_type: str,
) -> str:
    digest = _sha256_json(
        {
            "repo_root": str(Path(repo_root).resolve()),
            "submitted_target": submitted_target,
            "canonical_target": canonical_target,
            "operation": operation,
            "call_site": call_site,
            "provenance_type": provenance_type,
        }
    )
    return f"phase11b0-store-write-event:{digest}"


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    previous_chain_hash: str | None = None
    for position, entry in enumerate(entries, start=1):
        sequence = entry.get("ledger_sequence_number")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != position:
            raise ValueError(
                "ledger state is malformed; refusing to append after invalid ledger_sequence_number "
                f"at entry {position}"
            )
        previous_hash = entry.get("previous_ledger_hash")
        if position == 1:
            if previous_hash not in (LEDGER_PREVIOUS_HASH_GENESIS, LEDGER_PREVIOUS_HASH_NOT_AVAILABLE):
                raise ValueError("ledger state is malformed; refusing to append after invalid genesis previous hash")
        elif previous_hash != previous_chain_hash:
            raise ValueError("ledger state is malformed; refusing to append after broken previous ledger hash")
        current_chain_hash = entry.get("ledger_chain_hash")
        if not is_sha256_hex(current_chain_hash):
            raise ValueError("ledger state is malformed; refusing to append after invalid ledger_chain_hash")
        previous_chain_hash = str(current_chain_hash)
    if previous_chain_hash is None:
        raise ValueError("ledger state is malformed; refusing to append without a previous ledger hash")
    return len(entries) + 1, previous_chain_hash


def _ledger_entries(repo_root: str | Path) -> list[dict[str, Any]]:
    ledger_path = state_root(repo_root) / LEDGER_FILE
    if not ledger_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ledger state is malformed; line {line_number} is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"ledger state is malformed; line {line_number} is not a JSON object")
        entries.append(parsed)
    return entries


def latest_run_entry(repo_root: str | Path) -> dict[str, Any] | None:
    ledger_path = state_root(repo_root) / LEDGER_FILE
    if not ledger_path.exists():
        return None
    lines = [line.strip() for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return {"invalid_ledger_line": line}
        if not isinstance(parsed, dict):
            return {"invalid_ledger_line": line}
        return parsed
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
