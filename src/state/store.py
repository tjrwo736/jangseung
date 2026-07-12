"""Read and write the folder-local ``.aeg/`` state tree."""

from __future__ import annotations

import json
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

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
    STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
    STORE_WRITE_MEDIATION_REASON_EXECUTOR_AEG_BLOCKED,
    STORE_WRITE_MEDIATION_REASON_OUT_OF_SCOPE,
    STORE_WRITE_MEDIATION_REASON_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_OUT_OF_SCOPE_UNCHANGED,
    STORE_WRITE_MEDIATION_RESULT_TRUSTED_RUNTIME_ALLOWED,
    STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
    STORE_WRITE_CONTEXT_RESULT_BLOCKED,
    STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED,
    STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
    STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
    STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
    STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
    STORE_WRITE_SINK_APPEND_LEDGER,
    STORE_WRITE_SINK_WRITE_JSON,
    STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
    STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
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

_TRUSTED_STORE_WRITE_CAPABILITY_OWNER = object()


@dataclass(frozen=True)
class _TrustedStoreWriteCapability:
    owner: object
    repo_root: Path
    scope_label: str


@dataclass(frozen=True)
class _StoreWriteSinkContext:
    repo_root: Path
    provenance_type: str
    call_site: str
    executor_claimed_provenance: str = ""
    trusted_capability: _TrustedStoreWriteCapability | None = None
    mediator_route: Callable[[WriteMediationRequest], WriteMediationDecision | Mapping[str, Any]] | None = None


_STORE_WRITE_SINK_CONTEXT: ContextVar[_StoreWriteSinkContext | None] = ContextVar(
    "aeg_store_write_sink_context",
    default=None,
)
_TRUSTED_STORE_WRITE_CAPABILITY_CONTEXT: ContextVar[_TrustedStoreWriteCapability | None] = ContextVar(
    "aeg_trusted_store_write_capability",
    default=None,
)


class StoreWriteMediationBlocked(PermissionError):
    """Raised before a protected ``.aeg`` sink write is allowed to mutate disk."""

    def __init__(self, event: Mapping[str, Any]):
        self.event = dict(event)
        target = self.event.get("canonical_target", "")
        super().__init__(f"store write mediation blocked before sink write: {target}")


def state_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / STATE_DIR


def _assert_under_state(repo_root: str | Path, path: str | Path) -> Path:
    root = state_root(repo_root).resolve()
    resolved = Path(path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing to write outside {STATE_DIR}: {resolved}")
    return resolved


@contextmanager
def _trusted_runtime_store_write_context(repo_root: str | Path, call_site: str) -> Iterator[None]:
    resolved_repo = Path(repo_root).resolve()
    capability = _TrustedStoreWriteCapability(
        owner=_TRUSTED_STORE_WRITE_CAPABILITY_OWNER,
        repo_root=resolved_repo,
        scope_label=call_site,
    )
    context = _StoreWriteSinkContext(
        repo_root=resolved_repo,
        provenance_type=STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
        call_site=call_site,
        trusted_capability=capability,
    )
    capability_token = _TRUSTED_STORE_WRITE_CAPABILITY_CONTEXT.set(capability)
    context_token = _STORE_WRITE_SINK_CONTEXT.set(context)
    try:
        yield
    finally:
        _STORE_WRITE_SINK_CONTEXT.reset(context_token)
        _TRUSTED_STORE_WRITE_CAPABILITY_CONTEXT.reset(capability_token)


@contextmanager
def _executor_attributed_store_write_context(
    repo_root: str | Path,
    call_site: str,
    *,
    executor_claimed_provenance: str | None = None,
    mediator_route: Callable[[WriteMediationRequest], WriteMediationDecision | Mapping[str, Any]] | None = None,
) -> Iterator[None]:
    context = _StoreWriteSinkContext(
        repo_root=Path(repo_root).resolve(),
        provenance_type=STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
        call_site=call_site,
        executor_claimed_provenance=executor_claimed_provenance or "",
        mediator_route=mediator_route,
    )
    token = _STORE_WRITE_SINK_CONTEXT.set(context)
    try:
        yield
    finally:
        _STORE_WRITE_SINK_CONTEXT.reset(token)


def _guard_store_write_sink(
    *,
    target: Path,
    operation: str,
    sink_name: str,
    payload_text: str,
) -> dict[str, Any]:
    context = _STORE_WRITE_SINK_CONTEXT.get()
    submitted_target = _submitted_path_for_sink(context.repo_root if context is not None else None, target)
    target_path = Path(target).resolve(strict=False)
    repo_root = _repo_root_for_sink_target(target_path, context)
    existed_before = target_path.exists()
    ledger_entries_before = _ledger_entry_count_for_sink(target_path, sink_name)
    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=submitted_target,
    )
    provenance_type = _sink_provenance_type(context)
    call_site = context.call_site if context is not None else f"store.py:{sink_name}:omitted_context"
    executor_claimed_provenance = context.executor_claimed_provenance if context is not None else ""
    trusted_runtime_allowed = _sink_context_is_trusted_runtime(context)
    base_event = _store_write_event_base(
        repo_root=repo_root,
        submitted_target=submitted_target,
        target=target_path,
        operation=operation,
        call_site=call_site,
        provenance_type=provenance_type,
        target_exists_before=existed_before,
        executor_claimed_provenance=executor_claimed_provenance,
    )
    base_event.update(
        {
            "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
            "sink_name": sink_name,
            "sink_guarded": True,
            "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
            "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
            "trusted_context_valid": trusted_runtime_allowed,
            "trusted_capability_present": context.trusted_capability is not None if context is not None else False,
            "trusted_capability_runtime_owned": _trusted_capability_is_runtime_owned(context),
            "call_stack_inference_used_as_judgment_basis": STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
            "caller_name_match_used_as_judgment_basis": False,
            "missing_context_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED if context is None else "",
            "omitted_declaration_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED if context is None else "",
            "executor_self_report_trusted_result": (
                STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED
                if executor_claimed_provenance == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
                else ""
            ),
            "guard_router_invoked": True,
            "guard_decision": guard_decision.to_record(),
            "store_write_context_present": context is not None,
            "executor_omitted_declaration": context is None,
            "ledger_entries_before": ledger_entries_before,
            "ledger_entries_after": ledger_entries_before,
            "ledger_entries_appended_count": 0,
        }
    )

    if not guard_decision.protected_target:
        return {
            **base_event,
            "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_OUT_OF_SCOPE_UNCHANGED,
            "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_OUT_OF_SCOPE,
            "mediator_request": None,
            "mediator_decision": None,
            "write_performed": True,
            "fallback_to_unwired": False,
            "wired_path_failed": False,
            "target_exists_after": target_path.exists(),
            "target_file_created": False,
        }

    if trusted_runtime_allowed:
        return {
            **base_event,
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

    mediator_request = WriteMediationRequest(
        request_id=_store_write_request_id(
            actor=STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
            operation=operation,
            submitted_target=submitted_target,
            canonical_target=str(target_path),
            payload=payload_text,
        ),
        actor=f"store.py:{sink_name}:executor_attributed_sink_guard",
        operation=operation,
        write_class=WRITE_CLASS_AEG_STATE_WRITE,
        submitted_target=submitted_target,
        canonical_target=str(target_path),
        declared_scope="phase11b0_store_write_sink_level_mediation_repair_v0",
        repo_boundary="repo_root_resolved_by_sink_guard",
        aeg_boundary=guard_decision.protected_target_status,
        action_summary="executor-attributed .aeg write blocked before store.py sink mutation",
        metadata={
            "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
            "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
            "write_provenance_type": STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
            "executor_claimed_provenance": executor_claimed_provenance,
            "sink_name": sink_name,
            "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
            "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
        },
    )
    route = context.mediator_route if context is not None and context.mediator_route is not None else decide_write_request
    try:
        raw_decision = route(mediator_request)
        mediator_decision = raw_decision.to_record() if isinstance(raw_decision, WriteMediationDecision) else dict(raw_decision)
        wired_path_failed = False
    except Exception as exc:  # noqa: BLE001 - safe default is to block before the sink write.
        mediator_decision = {
            "status": "raised_exception",
            "exception_type": exc.__class__.__name__,
            "write_performed": False,
        }
        wired_path_failed = True

    blocked_event = {
        **base_event,
        "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_BLOCKED,
        "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_EXECUTOR_AEG_BLOCKED,
        "mediator_request": mediator_request.to_record(),
        "mediator_decision": mediator_decision,
        "write_performed": False,
        "fallback_to_unwired": False,
        "wired_path_failed": wired_path_failed,
        "target_exists_after": target_path.exists(),
        "target_file_created": (not existed_before and target_path.exists()),
        "ledger_entries_after": _ledger_entry_count_for_sink(target_path, sink_name),
    }
    blocked_event["ledger_entries_appended_count"] = (
        blocked_event["ledger_entries_after"] - blocked_event["ledger_entries_before"]
    )
    raise StoreWriteMediationBlocked(blocked_event)


def _sink_context_is_trusted_runtime(context: _StoreWriteSinkContext | None) -> bool:
    if context is None or context.provenance_type != STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME:
        return False
    return _trusted_capability_is_runtime_owned(context)


def _trusted_capability_is_runtime_owned(context: _StoreWriteSinkContext | None) -> bool:
    if context is None or context.trusted_capability is None:
        return False
    active_capability = _TRUSTED_STORE_WRITE_CAPABILITY_CONTEXT.get()
    capability = context.trusted_capability
    return (
        capability is active_capability
        and capability.owner is _TRUSTED_STORE_WRITE_CAPABILITY_OWNER
        and capability.repo_root == context.repo_root.resolve()
    )


def _sink_provenance_type(context: _StoreWriteSinkContext | None) -> str:
    if _sink_context_is_trusted_runtime(context):
        return STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
    return STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED


def _repo_root_for_sink_target(target: Path, context: _StoreWriteSinkContext | None) -> Path:
    if context is not None:
        return context.repo_root.resolve()
    for candidate in (target, *target.parents):
        if candidate.name == STATE_DIR:
            return candidate.parent.resolve()
    for candidate in (target.parent, *target.parents):
        if (candidate / ".git").exists():
            return candidate.resolve()
    return Path.cwd().resolve()


def _submitted_path_for_sink(repo_root: str | Path | None, target: str | Path) -> str:
    submitted = Path(target)
    if repo_root is None:
        return str(submitted)
    repo = Path(repo_root).resolve()
    if not submitted.is_absolute():
        return submitted.as_posix()
    try:
        return submitted.relative_to(repo).as_posix()
    except ValueError:
        return str(submitted)


def _ledger_entry_count_for_sink(target: Path, sink_name: str) -> int:
    if sink_name != STORE_WRITE_SINK_APPEND_LEDGER or not target.exists():
        return 0
    return sum(1 for line in target.read_text(encoding="utf-8").splitlines() if line.strip())


def _unblocked_sink_event(
    *,
    repo_root: str | Path,
    target: Path,
    operation: str,
    sink_name: str,
    call_site: str,
    executor_claimed_provenance: str | None,
) -> dict[str, Any]:
    resolved = target.resolve(strict=False)
    entries_after = _ledger_entry_count_for_sink(resolved, sink_name)
    event = _store_write_event_base(
        repo_root=repo_root,
        submitted_target=_repo_relative_or_absolute(repo_root, resolved),
        target=resolved,
        operation=operation,
        call_site=call_site,
        provenance_type=STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
        target_exists_before=False,
        executor_claimed_provenance=executor_claimed_provenance,
    )
    event.update(
        {
            "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
            "sink_name": sink_name,
            "sink_guarded": True,
            "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
            "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
            "trusted_context_valid": False,
            "trusted_capability_present": False,
            "trusted_capability_runtime_owned": False,
            "call_stack_inference_used_as_judgment_basis": STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
            "caller_name_match_used_as_judgment_basis": False,
            "missing_context_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED if executor_claimed_provenance is None else "",
            "omitted_declaration_result": STORE_WRITE_CONTEXT_RESULT_BLOCKED if executor_claimed_provenance is None else "",
            "executor_self_report_trusted_result": (
                STORE_WRITE_EXECUTOR_SELF_REPORT_TRUSTED_REJECTED
                if executor_claimed_provenance == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
                else ""
            ),
            "guard_router_invoked": True,
            "guard_decision": decide_b1_aeg_integrity_guard(
                repo_root=repo_root,
                submitted_path=_repo_relative_or_absolute(repo_root, resolved),
            ).to_record(),
            "store_write_context_present": executor_claimed_provenance is not None,
            "executor_omitted_declaration": executor_claimed_provenance is None,
            "target_exists_after": resolved.exists(),
            "target_file_created": resolved.exists(),
            "ledger_entries_before": 0,
            "ledger_entries_after": entries_after,
            "ledger_entries_appended_count": entries_after,
        }
    )
    return event


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _guard_store_write_sink(
        target=path,
        operation="write_json",
        sink_name=STORE_WRITE_SINK_WRITE_JSON,
        payload_text=body,
    )
    path.write_text(body, encoding="utf-8")


def _append_ledger_unmediated(ledger_path: Path, entry: dict[str, Any]) -> None:
    """Append via trusted-runtime internals, not an executor-bypassable unguarded sink."""

    body = json.dumps(entry, sort_keys=True) + "\n"
    _guard_store_write_sink(
        target=ledger_path,
        operation="append",
        sink_name=STORE_WRITE_SINK_APPEND_LEDGER,
        payload_text=body,
    )
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(body)


def ensure_initialized(repo_root: str | Path) -> dict[str, Any]:
    root = state_root(repo_root)
    runs = root / RUNS_DIR
    root.mkdir(exist_ok=True)
    runs.mkdir(exist_ok=True)

    config_path = root / CONFIG_FILE
    created_config = False
    if not config_path.exists():
        with _trusted_runtime_store_write_context(repo_root, "store.py:ensure_initialized.config_json"):
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
    with _trusted_runtime_store_write_context(repo_root, "store.py:append_ledger.ledger_append"):
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

    with _trusted_runtime_store_write_context(repo_root, "store.py:save_run.run_json"):
        _write_json(run_path, run_payload)
    with _trusted_runtime_store_write_context(repo_root, "store.py:save_run.manifest_json"):
        _write_json(manifest_path, manifest)
    with _trusted_runtime_store_write_context(repo_root, "store.py:save_run.evidence_json"):
        _write_json(evidence_path, evidence)

    ledger_entry = {
        **ledger_entry_base,
        "manifest_hash": bound_manifest_hash,
        **{field: evidence[field] for field in LEDGER_INTEGRITY_FIELDS},
    }
    with _trusted_runtime_store_write_context(repo_root, "store.py:save_run.ledger_append"):
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
    """Attempt an executor-attributed ``.aeg`` write at the ``_write_json`` sink."""

    submitted_path = Path(submitted_target)
    target = submitted_path if submitted_path.is_absolute() else Path(repo_root).resolve() / submitted_path
    try:
        with _executor_attributed_store_write_context(
            repo_root,
            "store.py:attempt_executor_attributed_aeg_write_text",
            executor_claimed_provenance=executor_claimed_provenance,
            mediator_route=mediator_route,
        ):
            _write_json(target, {"executor_payload": payload})
    except StoreWriteMediationBlocked as exc:
        return exc.event

    return {
        **_unblocked_sink_event(
            repo_root=repo_root,
            target=target,
            operation="write_json",
            sink_name=STORE_WRITE_SINK_WRITE_JSON,
            call_site="store.py:attempt_executor_attributed_aeg_write_text",
            executor_claimed_provenance=executor_claimed_provenance,
        ),
        "write_mediation_result": "UNEXPECTED_EXECUTOR_WRITE_PERFORMED",
        "write_mediation_reason": "executor_attributed_sink_write_unexpectedly_performed",
        "mediator_request": None,
        "mediator_decision": None,
        "write_performed": True,
        "fallback_to_unwired": False,
        "wired_path_failed": False,
    }


def attempt_executor_attributed_ledger_append(
    repo_root: str | Path,
    entry: dict[str, Any],
    *,
    executor_claimed_provenance: str | None = None,
    mediator_route: Callable[[WriteMediationRequest], WriteMediationDecision | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Attempt an executor-attributed forged ledger append at the append sink."""

    ledger_path = _assert_under_state(repo_root, state_root(repo_root) / LEDGER_FILE)
    try:
        with _executor_attributed_store_write_context(
            repo_root,
            "store.py:attempt_executor_attributed_ledger_append",
            executor_claimed_provenance=executor_claimed_provenance,
            mediator_route=mediator_route,
        ):
            _append_ledger_unmediated(ledger_path, entry)
    except StoreWriteMediationBlocked as exc:
        return exc.event

    return {
        **_unblocked_sink_event(
            repo_root=repo_root,
            target=ledger_path,
            operation="append",
            sink_name=STORE_WRITE_SINK_APPEND_LEDGER,
            call_site="store.py:attempt_executor_attributed_ledger_append",
            executor_claimed_provenance=executor_claimed_provenance,
        ),
        "write_mediation_result": "UNEXPECTED_EXECUTOR_LEDGER_APPEND_PERFORMED",
        "write_mediation_reason": "executor_attributed_ledger_append_unexpectedly_performed",
        "mediator_request": None,
        "mediator_decision": None,
        "write_performed": True,
        "fallback_to_unwired": False,
        "wired_path_failed": False,
    }


def attempt_executor_omitted_declaration_aeg_write(
    repo_root: str | Path,
    submitted_target: str | Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Attempt a direct sink call with no provenance declaration."""

    target = _target_path(repo_root, submitted_target)
    try:
        _write_json(target, payload)
    except StoreWriteMediationBlocked as exc:
        return exc.event

    return {
        **_unblocked_sink_event(
            repo_root=repo_root,
            target=target,
            operation="write_json",
            sink_name=STORE_WRITE_SINK_WRITE_JSON,
            call_site=f"store.py:{STORE_WRITE_SINK_WRITE_JSON}:omitted_context",
            executor_claimed_provenance=None,
        ),
        "write_mediation_result": "UNEXPECTED_OMITTED_DECLARATION_WRITE_PERFORMED",
        "write_mediation_reason": "omitted_declaration_sink_write_unexpectedly_performed",
        "mediator_request": None,
        "mediator_decision": None,
        "write_performed": True,
        "fallback_to_unwired": False,
        "wired_path_failed": False,
    }


def _collect_store_write_mediation_events(
    *,
    repo_root: str | Path,
    evidence: Mapping[str, Any],
    trusted_runtime_targets: tuple[tuple[Path, str], ...],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    executor_attempts = _executor_attributed_store_write_attempts(evidence)
    for attempt in executor_attempts:
        events.append(
            attempt_executor_attributed_aeg_write_text(
                repo_root,
                attempt["target"],
                attempt["payload"],
                executor_claimed_provenance=attempt.get("executor_claimed_provenance"),
            )
        )
    if executor_attempts:
        events.append(
            attempt_executor_omitted_declaration_aeg_write(
                repo_root,
                ".aeg/executor-omitted-declaration-blocked.json",
                {"attacker": "executor content", "declaration": "omitted"},
            )
        )
        events.append(
            attempt_executor_attributed_ledger_append(
                repo_root,
                {
                    "run_id": "forged-executor-ledger-entry",
                    "task_text": "forged ledger append",
                    "status": "CLEAN_CORE",
                    "risk_level": "LOW",
                    "head_sha": "forged",
                    "tree_sha": "forged",
                },
                executor_claimed_provenance=STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
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
    sink_name = STORE_WRITE_SINK_APPEND_LEDGER if operation == "append" else STORE_WRITE_SINK_WRITE_JSON
    ledger_entries_before = _ledger_entry_count_for_sink(target, sink_name)
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
    base_event.update(
        {
            "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
            "sink_name": sink_name,
            "sink_guarded": True,
            "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
            "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
            "trusted_context_valid": True,
            "trusted_capability_present": True,
            "trusted_capability_runtime_owned": True,
            "call_stack_inference_used_as_judgment_basis": STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
            "caller_name_match_used_as_judgment_basis": False,
            "missing_context_result": "",
            "omitted_declaration_result": "",
            "executor_self_report_trusted_result": "",
            "store_write_context_present": True,
            "executor_omitted_declaration": False,
            "ledger_entries_before": ledger_entries_before,
            "ledger_entries_after": ledger_entries_before + (1 if sink_name == STORE_WRITE_SINK_APPEND_LEDGER else 0),
            "ledger_entries_appended_count": 1 if sink_name == STORE_WRITE_SINK_APPEND_LEDGER else 0,
        }
    )
    with _trusted_runtime_store_write_context(repo_root, call_site):
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


def _trusted_runtime_store_write_gate(
    *,
    repo_root: str | Path,
    target: Path,
    operation: str,
    call_site: str,
) -> dict[str, Any]:
    context = _STORE_WRITE_SINK_CONTEXT.get()
    if not _sink_context_is_trusted_runtime(context):
        raise StoreWriteMediationBlocked(
            {
                "write_mediation_result": STORE_WRITE_MEDIATION_RESULT_BLOCKED,
                "write_mediation_reason": STORE_WRITE_MEDIATION_REASON_EXECUTOR_AEG_BLOCKED,
                "canonical_target": str(target.resolve(strict=False)),
                "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
                "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
                "trusted_context_valid": False,
                "write_performed": False,
            }
        )
    guard_decision = decide_b1_aeg_integrity_guard(
        repo_root=repo_root,
        submitted_path=_repo_relative_or_absolute(repo_root, target),
    )
    return {
        "status": "trusted_runtime_allowed",
        "operation": operation,
        "call_site": call_site,
        "store_write_boundary": STORE_WRITE_BOUNDARY_SINK_LEVEL_GUARDED,
        "sink_name": STORE_WRITE_SINK_APPEND_LEDGER if operation == "append" else STORE_WRITE_SINK_WRITE_JSON,
        "guard_decision": guard_decision.to_record(),
        "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
        "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
        "write_provenance_type": STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
        "trusted_context_required": STORE_WRITE_TRUSTED_CONTEXT_REQUIRED,
        "trusted_context_basis": STORE_WRITE_TRUSTED_CONTEXT_BASIS_RUNTIME_OWNED_CAPABILITY,
        "trusted_context_valid": True,
        "trusted_capability_runtime_owned": True,
        "call_stack_inference_used_as_judgment_basis": STORE_WRITE_CALL_STACK_INFERENCE_NOT_USED,
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
        "write_provenance_source": STORE_WRITE_PROVENANCE_SOURCE_RUNTIME_OWNED_CONTEXT,
        "write_provenance_basis": STORE_WRITE_PROVENANCE_BASIS_RUNTIME_OWNED_CAPABILITY,
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
        "evidence_path": evidence_path.relative_to(repo).as_posix(),
        "run_path": run_path.relative_to(repo).as_posix(),
        "manifest_path": manifest_path.relative_to(repo).as_posix(),
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
