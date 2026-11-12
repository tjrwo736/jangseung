"""Append-only, tamper-evident records for live hook decisions.

A record holds the decision and, so a person can later see what was touched, three
redacted facts about the call: project-relative target paths, program names of a
command (never its arguments) and a hash of the input. Raw hook input, file
content and command text are never stored.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from jangseung.contracts import STATE_DIR
from jangseung.evidence.ledger_integrity import is_sha256_hex
from jangseung.state.file_lock import exclusive_hook_lock as _exclusive_lock

HOOK_LEDGER_FILE = "hook_ledger.jsonl"
HOOK_LEDGER_LOCK_FILE = "hook_ledger.lock"
HOOK_RECORD_VERSION = "hook_decision_record_v1"
HOOK_HOST_RECORD_VERSION = "hook_decision_record_v2"
HOOK_RECORD_HASH_GENESIS = "0" * 64
HOOK_LEDGER_REPAIRED_REASON = "hook_ledger_repaired"
HOOK_LEDGER_REPAIR_TOOL_NAME = "aeg-evidence-repair-hooks"
HOOK_LEDGER_ARCHIVED_REASON = "hook_ledger_archived"
HOOK_LEDGER_ARCHIVE_TOOL_NAME = "aeg-evidence-archive-hooks"
HOOK_LEDGER_ARCHIVE_DIR = "archive"
_TAIL_CHUNK_BYTES = 64 * 1024

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
_OPTIONAL_TEXT_LIST_FIELDS = ("targets", "commands")
_MAX_AUDIT_ITEMS = 16
_MAX_AUDIT_TEXT = 240


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
            "what": _what(record),
            "session_id": str(record.get("session_id", "")),
            "substrate": str(record.get("substrate", "")),
            "readability": "READABLE" if self.readable else "UNREADABLE",
            "artifacts": {"hook_record": True},
            "error": self.error,
        }


def _what(record: Mapping[str, Any]) -> str:
    """One short phrase for a listing: the programs or files a call named."""

    names: list[str] = []
    for field in ("commands", "targets"):
        values = record.get(field, [])
        if isinstance(values, list):
            names.extend(str(item) for item in values)
    shown = ", ".join(names[:3])
    return f"{shown}, +{len(names) - 3} more" if len(names) > 3 else shown


@dataclass(frozen=True)
class HookLedgerVerification:
    ok: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...]
    records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class HookLedgerRepair:
    kept_records: int
    quarantined_lines: int
    quarantine_path: str | None


def state_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / STATE_DIR


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
    session_id: str = "",
    targets: Sequence[str] = (),
    commands: Sequence[str] = (),
    input_hash: str = "",
) -> dict[str, Any]:
    """Append one hook record after verifying the record it chains onto.

    Only the last record is checked so a hook call stays fast however long the
    ledger grows. ``aeg evidence verify-hooks`` verifies the whole chain.
    """

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
        tail = _verified_tail_record(ledger_path)
        return _append_record(
            ledger_path,
            previous_hash=tail["record_hash"] if tail is not None else HOOK_RECORD_HASH_GENESIS,
            sequence_number=(tail["sequence_number"] + 1) if tail is not None else 1,
            timestamp=timestamp,
            substrate=substrate,
            tool_name=tool_name,
            hook_decision=hook_decision,
            permission_decision=permission_decision,
            fail_closed=fail_closed,
            reason_codes=reason_codes,
            exit_code=exit_code,
            session_id=session_id,
            targets=targets,
            commands=commands,
            input_hash=input_hash,
        )


def hook_ledger_needs_repair(repo_root: str | Path) -> bool:
    if any(not item.readable for item in read_hook_ledger(repo_root)):
        return True
    return _has_torn_tail(state_root(repo_root) / HOOK_LEDGER_FILE)


@dataclass(frozen=True)
class HookLedgerArchive:
    archived_records: int
    archive_path: str | None


def archive_hook_ledger(repo_root: str | Path) -> HookLedgerArchive:
    """Move an intact ledger to ``.aeg/archive/`` and start a new chain that names it.

    The new chain's first record holds the archived file's record count, last record
    hash and SHA-256, so the two files stay linked: the archive can be checked
    against the record, and ``verify-hooks`` checks the new file from its start.
    A damaged ledger is refused; repair it first.
    """

    root = state_root(repo_root)
    if not root.is_dir():
        raise FileNotFoundError("Aegis state is not initialized; .aeg directory is missing")
    ledger_path = root / HOOK_LEDGER_FILE
    lock_path = root / HOOK_LEDGER_LOCK_FILE
    if ledger_path.is_symlink() or lock_path.is_symlink():
        raise ValueError("hook ledger and its lock must not be symbolic links")
    with _exclusive_lock(lock_path):
        if not ledger_path.is_file():
            return HookLedgerArchive(0, None)
        items = read_hook_ledger(repo_root)
        if not items:
            return HookLedgerArchive(0, None)
        if hook_ledger_needs_repair(repo_root):
            raise ValueError("hook ledger is damaged; run aeg evidence repair-hooks first")
        tail = items[-1].record
        raw = ledger_path.read_bytes()
        archive_root = root / HOOK_LEDGER_ARCHIVE_DIR
        if archive_root.is_symlink() or (archive_root.exists() and not archive_root.is_dir()):
            raise ValueError(".aeg/archive must be a local directory")
        archive_root.mkdir(exist_ok=True)
        stamp = re.sub(r"[^0-9A-Za-z]", "", _utc_timestamp())
        archive = archive_root / f"hook_ledger-{stamp}.jsonl"
        counter = 1
        while archive.exists():
            archive = archive_root / f"hook_ledger-{stamp}-{counter}.jsonl"
            counter += 1
        archive.write_bytes(raw)
        if archive.read_bytes() != raw:
            raise OSError("the archive copy does not match the ledger")
        temporary = root / f"{HOOK_LEDGER_FILE}.archive-{stamp}"
        temporary.write_bytes(b"")
        os.replace(temporary, ledger_path)
        _append_record(
            ledger_path,
            previous_hash=HOOK_RECORD_HASH_GENESIS,
            sequence_number=1,
            timestamp=None,
            substrate="claude-code",
            tool_name=HOOK_LEDGER_ARCHIVE_TOOL_NAME,
            hook_decision=None,
            permission_decision="deny",
            fail_closed=False,
            reason_codes=(
                HOOK_LEDGER_ARCHIVED_REASON,
                f"archived_file:{archive.name}",
                f"archived_records:{len(items)}",
                f"archived_last_record_hash:{tail['record_hash'] if tail else ''}",
                f"archived_sha256:{hashlib.sha256(raw).hexdigest()}",
            ),
            exit_code=0,
        )
        return HookLedgerArchive(len(items), str(archive))


def repair_hook_ledger(repo_root: str | Path) -> HookLedgerRepair:
    """Move everything from the first damaged line onward into a quarantine file.

    Nothing is discarded, and a record in the continued chain names the moved
    bytes by hash, so the repair itself stays visible to anyone auditing later.
    """

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
        items = read_hook_ledger(repo_root)
        first_damaged = next((item for item in items if not item.readable), None)
        if not hook_ledger_needs_repair(repo_root):
            return HookLedgerRepair(len(items), 0, None)

        raw = ledger_path.read_bytes()
        kept_items = [
            item for item in items
            if item.readable and (first_damaged is None or item.line_number < first_damaged.line_number)
        ]
        if first_damaged is None:
            # read_hook_ledger accepted the final line, but it was never terminated.
            kept_items = kept_items[:-1]
        lines = raw.split(b"\n")
        kept_line_count = kept_items[-1].line_number if kept_items else 0
        kept = b"".join(line + b"\n" for line in lines[:kept_line_count])
        damaged = raw[len(kept):]

        stamp = re.sub(r"[^0-9A-Za-z]", "", _utc_timestamp())
        quarantine = root / f"{HOOK_LEDGER_FILE}.quarantine-{stamp}"
        counter = 1
        while quarantine.exists():
            quarantine = root / f"{HOOK_LEDGER_FILE}.quarantine-{stamp}-{counter}"
            counter += 1
        quarantine.write_bytes(damaged)
        temporary = root / f"{HOOK_LEDGER_FILE}.repair-{stamp}"
        temporary.write_bytes(kept)
        os.replace(temporary, ledger_path)

        tail = kept_items[-1].record if kept_items else None
        quarantined_lines = sum(1 for line in damaged.split(b"\n") if line.strip())
        _append_record(
            ledger_path,
            previous_hash=tail["record_hash"] if tail is not None else HOOK_RECORD_HASH_GENESIS,
            sequence_number=(tail["sequence_number"] + 1) if tail is not None else 1,
            timestamp=None,
            substrate="claude-code",
            tool_name=HOOK_LEDGER_REPAIR_TOOL_NAME,
            hook_decision=None,
            permission_decision="deny",
            fail_closed=True,
            reason_codes=(
                HOOK_LEDGER_REPAIRED_REASON,
                f"quarantined_lines:{quarantined_lines}",
                f"quarantined_sha256:{hashlib.sha256(damaged).hexdigest()}",
            ),
            exit_code=0,
        )
        return HookLedgerRepair(len(kept_items), quarantined_lines, str(quarantine))


def _append_record(
    ledger_path: Path,
    *,
    previous_hash: str,
    sequence_number: int,
    timestamp: str | None,
    substrate: str,
    tool_name: str,
    hook_decision: str | None,
    permission_decision: str,
    fail_closed: bool,
    reason_codes: Sequence[str],
    exit_code: int,
    session_id: str = "",
    targets: Sequence[str] = (),
    commands: Sequence[str] = (),
    input_hash: str = "",
) -> dict[str, Any]:
    record_without_hash: dict[str, Any] = {
        "record_version": HOOK_HOST_RECORD_VERSION if permission_decision == "host" else HOOK_RECORD_VERSION,
        "sequence_number": sequence_number,
        "timestamp": timestamp or _utc_timestamp(),
        "substrate": substrate,
        "tool_name": tool_name,
        "hook_decision": hook_decision if hook_decision is not None else "none",
        "permission_decision": permission_decision,
        "fail_closed": bool(fail_closed),
        "reason_codes": [str(code) for code in reason_codes],
        "exit_code": int(exit_code),
        "previous_record_hash": previous_hash,
        # Optional since 0.2.0. Readers accept records without them. Host-delegated
        # records use v2 because older readers must not mistake them for an allow.
        "session_id": str(session_id)[:_MAX_AUDIT_TEXT],
        "targets": [str(item)[:_MAX_AUDIT_TEXT] for item in targets][:_MAX_AUDIT_ITEMS],
        "commands": [str(item)[:_MAX_AUDIT_TEXT] for item in commands][:_MAX_AUDIT_ITEMS],
        "input_hash": input_hash if is_sha256_hex(input_hash) else "",
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


def _has_torn_tail(ledger_path: Path) -> bool:
    if not ledger_path.is_file():
        return False
    with ledger_path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size == 0:
            return False
        handle.seek(size - 1)
        return handle.read(1) != b"\n"


def _read_last_line(ledger_path: Path) -> bytes | None:
    """Return the last non-blank line without reading the whole file."""

    with ledger_path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        data = b""
        while position > 0:
            step = min(_TAIL_CHUNK_BYTES, position)
            position -= step
            handle.seek(position)
            data = handle.read(step) + data
            lines = [line for line in data.split(b"\n") if line.strip()]
            # The first piece may be a partial line until the start of the file.
            if len(lines) > 1 or (lines and position == 0):
                return lines[-1]
    return None


def _verified_tail_record(ledger_path: Path) -> dict[str, Any] | None:
    """Return the last record, or raise when a new record cannot chain onto it."""

    if not ledger_path.is_file():
        return None
    if _has_torn_tail(ledger_path):
        raise ValueError("hook ledger ends in an incomplete record; run aeg evidence repair-hooks")
    line = _read_last_line(ledger_path)
    if line is None:
        return None
    try:
        record = json.loads(line.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise ValueError("hook ledger tail is unreadable; run aeg evidence repair-hooks") from exc
    if not isinstance(record, dict):
        raise ValueError("hook ledger tail is unreadable; run aeg evidence repair-hooks")
    try:
        errors = _validate_record(
            record,
            expected_previous_hash=record.get("previous_record_hash"),
            expected_sequence=record.get("sequence_number"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("hook ledger tail is invalid; run aeg evidence repair-hooks") from exc
    if errors or not isinstance(record.get("sequence_number"), int) or isinstance(record.get("sequence_number"), bool):
        raise ValueError("hook ledger tail is invalid; run aeg evidence repair-hooks")
    return record


def read_hook_ledger(repo_root: str | Path) -> list[HookLedgerItem]:
    """Read all hook lines oldest-first and annotate chain damage."""

    ledger_path = state_root(repo_root) / HOOK_LEDGER_FILE
    if ledger_path.is_symlink():
        return [HookLedgerItem(0, False, None, "hook ledger symbolic link is refused")]
    if not ledger_path.is_file():
        return []
    try:
        lines = ledger_path.read_bytes().split(b"\n")
    except OSError as exc:
        return [HookLedgerItem(0, False, None, f"hook ledger unreadable: {exc.__class__.__name__}")]

    items: list[HookLedgerItem] = []
    expected_previous_hash = HOOK_RECORD_HASH_GENESIS
    expected_sequence = 1
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError:
            items.append(HookLedgerItem(line_number, False, None, "invalid UTF-8 in hook ledger entry"))
            continue
        record: dict[str, Any] | None = None
        errors: list[str] = []
        try:
            parsed = json.loads(line)
        except (ValueError, RecursionError):
            # JSONDecodeError is a ValueError. Decoder depth/integer limits also
            # reject damaged records; none should abort a read-only inspection.
            parsed = None
            errors.append("invalid JSON object")
        if isinstance(parsed, dict):
            record = parsed
            try:
                errors.extend(
                    _validate_record(
                        record,
                        expected_previous_hash=expected_previous_hash,
                        expected_sequence=expected_sequence,
                    )
                )
            except (TypeError, ValueError, RecursionError):
                # Keep malformed nested/type-invalid data out of renderers and
                # never include exception text, which can contain record data.
                record = None
                errors.append("invalid hook record structure")
            candidate_hash = parsed.get("record_hash")
            if isinstance(candidate_hash, str) and is_sha256_hex(candidate_hash):
                expected_previous_hash = candidate_hash
            expected_sequence += 1
        elif not errors:
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
    if record.get("record_version") not in {HOOK_RECORD_VERSION, HOOK_HOST_RECORD_VERSION}:
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
    if record.get("record_version") == HOOK_HOST_RECORD_VERSION:
        if not (
            record.get("permission_decision") == "host"
            and record.get("substrate") == "claude-code"
            and record.get("tool_name") in {"Bash", "PowerShell"}
            and record.get("hook_decision") == "defer"
            and record.get("fail_closed") is False
            and record.get("exit_code") == 0
            and isinstance(record.get("reason_codes"), list)
            and "claude_default_host_permission_flow" in record["reason_codes"]
        ):
            errors.append("invalid host permission delegation")
    elif record.get("permission_decision") not in {"allow", "ask", "deny"}:
        errors.append("invalid permission_decision")
    if not isinstance(record.get("fail_closed"), bool):
        errors.append("fail_closed must be boolean")
    reason_codes = record.get("reason_codes")
    if not isinstance(reason_codes, list) or not all(isinstance(code, str) for code in reason_codes):
        errors.append("reason_codes must be a string list")
    if not isinstance(record.get("exit_code"), int):
        errors.append("exit_code must be an integer")
    if not isinstance(record.get("session_id", ""), str):
        errors.append("session_id must be a string")
    for field in _OPTIONAL_TEXT_LIST_FIELDS:
        values = record.get(field, [])
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            errors.append(f"{field} must be a string list")
    input_hash = record.get("input_hash", "")
    if input_hash != "" and not (isinstance(input_hash, str) and is_sha256_hex(input_hash)):
        errors.append("input_hash is not sha256 hex")
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


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "HOOK_LEDGER_ARCHIVED_REASON",
    "HOOK_LEDGER_FILE",
    "HOOK_LEDGER_REPAIRED_REASON",
    "HookLedgerArchive",
    "archive_hook_ledger",
    "HOOK_RECORD_HASH_GENESIS",
    "HOOK_RECORD_VERSION",
    "HookLedgerItem",
    "HookLedgerRepair",
    "HookLedgerVerification",
    "append_hook_decision_record",
    "compute_hook_record_hash",
    "find_hook_record",
    "hook_ledger_needs_repair",
    "read_hook_ledger",
    "repair_hook_ledger",
    "verify_hook_ledger",
]
