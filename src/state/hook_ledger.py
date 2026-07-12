"""Append-only, tamper-evident records for live hook decisions.

The hook ledger is intentionally separate from the run evidence ledger.  It
stores decision metadata only and never accepts raw hook input.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from src.evidence.ledger_integrity import is_sha256_hex
from src.state.store import state_root

HOOK_LEDGER_FILE = "hook_ledger.jsonl"
HOOK_LEDGER_LOCK_FILE = "hook_ledger.lock"
HOOK_RECORD_VERSION = "hook_decision_record_v1"
HOOK_RECORD_HASH_GENESIS = "0" * 64

_REQUIRED_FIELDS = (
    "record_version",
    "sequence_number",
    "timestamp",
    "substrate",
    "tool_name",
    "hook_decision",
    "permission_decision",
    "fail_closed",
    "reason_codes",
    "exit_code",
    "previous_record_hash",
    "record_hash",
)
_FORBIDDEN_RAW_KEYS = {"tool_input", "raw_tool_input", "stdin", "raw_stdin_text"}


@dataclass(frozen=True)
class HookLedgerItem:
    line_number: int
    readable: bool
    record: dict[str, Any] | None
    error: str | None

    @property
    def record_hash(self) -> str:
        if self.record is None:
            return ""
        value = self.record.get("record_hash")
        return value if isinstance(value, str) else ""

    @property
    def identifier(self) -> str:
        return self.record_hash or f"hook-ledger-line-{self.line_number}"

    def to_summary(self) -> dict[str, Any]:
        record = self.record or {}
        return {
            "kind": "hook",
            "id": self.identifier,
            "timestamp": str(record.get("timestamp", "")),
            "decision": str(record.get("permission_decision", "UNREADABLE")).upper(),
            "risk_level": "",
            "hook_decision": str(record.get("hook_decision", "")),
            "tool_name": str(record.get("tool_name", "unknown")),
            "substrate": str(record.get("substrate", "")),
            "readability": "READABLE" if self.readable else "UNREADABLE",
            "artifacts": {"hook_record": True},
            "error": self.error,
        }


@dataclass(frozen=True)
class HookLedgerVerification:
    ok: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...]
    records: tuple[dict[str, Any], ...]


def append_hook_decision_record(
    repo_root: str | Path,
    *,
    substrate: str,
    tool_name: str,
    hook_decision: str | None,
    permission_decision: str,
    fail_closed: bool,
    reason_codes: Sequence[str],
    exit_code: int,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Append one hook record after verifying the existing chain."""

    root = state_root(repo_root)
    if not root.is_dir():
        raise FileNotFoundError("Aegis state is not initialized; .aeg directory is missing")
    ledger_path = root / HOOK_LEDGER_FILE
    lock_path = root / HOOK_LEDGER_LOCK_FILE
    if ledger_path.is_symlink():
        raise ValueError("hook ledger must not be a symbolic link")
    if lock_path.is_symlink():
        raise ValueError("hook ledger lock must not be a symbolic link")
    with _exclusive_lock(lock_path):
        verification = verify_hook_ledger(repo_root)
        if not verification.ok:
            raise ValueError("hook ledger chain is invalid; refusing to append")
        previous_hash = (
            verification.records[-1]["record_hash"]
            if verification.records
            else HOOK_RECORD_HASH_GENESIS
        )
        record_without_hash: dict[str, Any] = {
            "record_version": HOOK_RECORD_VERSION,
            "sequence_number": len(verification.records) + 1,
            "timestamp": timestamp or _utc_timestamp(),
            "substrate": substrate,
            "tool_name": tool_name,
            "hook_decision": hook_decision if hook_decision is not None else "none",
            "permission_decision": permission_decision,
            "fail_closed": bool(fail_closed),
            "reason_codes": [str(code) for code in reason_codes],
            "exit_code": int(exit_code),
            "previous_record_hash": previous_hash,
        }
        record = {
            **record_without_hash,
            "record_hash": compute_hook_record_hash(record_without_hash),
        }
        encoded = json.dumps(
            record,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record


def read_hook_ledger(repo_root: str | Path) -> list[HookLedgerItem]:
    """Read all hook lines oldest-first and annotate chain damage."""

    ledger_path = state_root(repo_root) / HOOK_LEDGER_FILE
    if ledger_path.is_symlink():
        return [HookLedgerItem(0, False, None, "hook ledger symbolic link is refused")]
    if not ledger_path.is_file():
        return []
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [HookLedgerItem(0, False, None, f"hook ledger unreadable: {exc.__class__.__name__}")]

    items: list[HookLedgerItem] = []
    expected_previous_hash = HOOK_RECORD_HASH_GENESIS
    expected_sequence = 1
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        record: dict[str, Any] | None = None
        errors: list[str] = []
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parsed = None
            errors.append("invalid JSON object")
        if isinstance(parsed, dict):
            record = parsed
            errors.extend(
                _validate_record(
                    record,
                    expected_previous_hash=expected_previous_hash,
                    expected_sequence=expected_sequence,
                )
            )
            candidate_hash = record.get("record_hash")
            if isinstance(candidate_hash, str) and is_sha256_hex(candidate_hash):
                expected_previous_hash = candidate_hash
            expected_sequence += 1
        elif parsed is not None:
            errors.append("hook ledger entry is not a JSON object")
        items.append(
            HookLedgerItem(
                line_number=line_number,
                readable=not errors,
                record=record,
                error="; ".join(errors) if errors else None,
            )
        )
    return items


def verify_hook_ledger(repo_root: str | Path) -> HookLedgerVerification:
    items = read_hook_ledger(repo_root)
    errors = tuple(
        f"line {item.line_number}: {item.error}"
        for item in items
        if not item.readable and item.error
    )
    records = tuple(item.record for item in items if item.record is not None and item.readable)
    checks: list[str] = []
    if not items:
        checks.append("hook ledger absent or empty; no hook records to verify")
    elif not errors:
        checks.append(f"hook ledger hash chain matched for {len(records)} record(s)")
        checks.append("hook ledger records contain decision metadata only")
    return HookLedgerVerification(
        ok=not errors,
        checks=tuple(checks),
        errors=errors,
        records=records,
    )


def find_hook_record(repo_root: str | Path, identifier: str) -> HookLedgerItem | None:
    """Find a hook record by full hash or an unambiguous hash prefix."""

    matches = [
        item
        for item in read_hook_ledger(repo_root)
        if item.record_hash == identifier or item.record_hash.startswith(identifier)
    ]
    return matches[0] if len(matches) == 1 else None


def compute_hook_record_hash(record: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_record(
    record: Mapping[str, Any],
    *,
    expected_previous_hash: str,
    expected_sequence: int,
) -> list[str]:
    errors: list[str] = []
    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        errors.append(f"missing required fields: {','.join(missing)}")
    if record.get("record_version") != HOOK_RECORD_VERSION:
        errors.append("unsupported record_version")
    if record.get("sequence_number") != expected_sequence:
        errors.append(f"sequence_number mismatch: expected {expected_sequence}")
    if record.get("previous_record_hash") != expected_previous_hash:
        errors.append("previous_record_hash mismatch")
    record_hash = record.get("record_hash")
    if not isinstance(record_hash, str) or not is_sha256_hex(record_hash):
        errors.append("record_hash is not sha256 hex")
    elif record_hash != compute_hook_record_hash(record):
        errors.append("record_hash mismatch")
    if not isinstance(record.get("timestamp"), str) or not record.get("timestamp"):
        errors.append("timestamp must be a non-empty UTC string")
    if record.get("substrate") not in {"claude-code", "codex"}:
        errors.append("invalid substrate")
    if not isinstance(record.get("tool_name"), str):
        errors.append("tool_name must be a string")
    if not isinstance(record.get("hook_decision"), str):
        errors.append("hook_decision must be a string")
    if record.get("permission_decision") not in {"allow", "ask", "deny"}:
        errors.append("invalid permission_decision")
    if not isinstance(record.get("fail_closed"), bool):
        errors.append("fail_closed must be boolean")
    reason_codes = record.get("reason_codes")
    if not isinstance(reason_codes, list) or not all(isinstance(code, str) for code in reason_codes):
        errors.append("reason_codes must be a string list")
    if not isinstance(record.get("exit_code"), int):
        errors.append("exit_code must be an integer")
    if _contains_forbidden_key(record):
        errors.append("raw hook input key is forbidden")
    return errors


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_RAW_KEYS or _contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


@contextmanager
def _exclusive_lock(lock_path: Path, *, timeout_seconds: float = 1.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("hook ledger append lock is busy")
            time.sleep(0.02)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "HOOK_LEDGER_FILE",
    "HOOK_RECORD_HASH_GENESIS",
    "HOOK_RECORD_VERSION",
    "HookLedgerItem",
    "HookLedgerVerification",
    "append_hook_decision_record",
    "compute_hook_record_hash",
    "find_hook_record",
    "read_hook_ledger",
    "verify_hook_ledger",
]
