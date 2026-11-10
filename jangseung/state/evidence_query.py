"""Read-only queries over persisted hook records.

This module deliberately does not import any state-writing helpers.  It reads
the hook ledger defensively so an inspection command can report damaged
entries without changing ``.aeg/`` or crashing the whole list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jangseung.state.hook_ledger import HookLedgerItem, find_hook_record, read_hook_ledger

REDACTED_CREDENTIAL = "[REDACTED_CREDENTIAL]"

_SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret|credential)(?:$|_)",
    re.IGNORECASE,
)
_CREDENTIAL_SHAPES = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk)-(?:proj-)?[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", re.IGNORECASE),
    re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)\s*[:=]\s*[^\s,;]+",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class HookEvidenceDetail:
    item: HookLedgerItem

    @property
    def readable(self) -> bool:
        return self.item.readable


def list_hook_evidence(
    repo_root: str | Path,
    *,
    limit: int | None = None,
) -> list[HookLedgerItem]:
    """Return hook records newest-first without mutating state."""

    items = list(reversed(read_hook_ledger(repo_root)))
    items.sort(key=_item_timestamp, reverse=True)
    return items if limit is None else items[:limit]


def load_hook_evidence(repo_root: str | Path, identifier: str) -> HookEvidenceDetail | None:
    item = find_hook_record(repo_root, identifier)
    return None if item is None else HookEvidenceDetail(item=item)


def sanitize_for_display(value: Any, *, key: str | None = None) -> Any:
    """Return a display-only copy with credential-shaped values redacted."""

    if key and _SENSITIVE_KEY.search(key) and isinstance(value, str) and value:
        return REDACTED_CREDENTIAL
    if isinstance(value, Mapping):
        return {
            str(child_key): sanitize_for_display(child_value, key=str(child_key))
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_display(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_display(item) for item in value]
    if not isinstance(value, str):
        return value
    sanitized = value
    for pattern in _CREDENTIAL_SHAPES:
        sanitized = pattern.sub(REDACTED_CREDENTIAL, sanitized)
    return sanitized


def hook_detail_as_json(detail: HookEvidenceDetail) -> dict[str, Any]:
    return sanitize_for_display(
        {
            "kind": "hook",
            "id": detail.item.identifier,
            "readability": "READABLE" if detail.readable else "UNREADABLE",
            "error": detail.item.error,
            "record": detail.item.record,
        }
    )


def hook_human_sections(detail: HookEvidenceDetail) -> list[tuple[str, list[tuple[str, Any]]]]:
    record = detail.item.record or {}
    sections = [
        (
            "summary",
            [
                ("kind", "hook"),
                ("record_hash", record.get("record_hash", "")),
                ("sequence_number", record.get("sequence_number", "")),
                ("timestamp", record.get("timestamp", "")),
            ],
        ),
        (
            "decision",
            [
                ("substrate", record.get("substrate", "")),
                ("tool_name", record.get("tool_name", "unknown")),
                ("hook_decision", record.get("hook_decision", "")),
                ("permission_decision", record.get("permission_decision", "")),
                ("fail_closed", record.get("fail_closed", "")),
                ("reason_codes", record.get("reason_codes", [])),
                ("exit_code", record.get("exit_code", "")),
            ],
        ),
        (
            # Absent on records written before 0.2.0.
            "call",
            [
                ("session", record.get("session_id", "")),
                ("targets", record.get("targets", [])),
                ("commands", record.get("commands", [])),
                ("input_hash", record.get("input_hash", "")),
                ("stored", "project-relative paths and program names only; no content or arguments"),
            ],
        ),
        (
            "integrity",
            [
                ("record_version", record.get("record_version", "")),
                ("previous_record_hash", record.get("previous_record_hash", "")),
                ("record_hash", record.get("record_hash", "")),
                ("claim", "tamper-evident, not tamper-proof"),
            ],
        ),
    ]
    return [
        (name, [(key, sanitize_for_display(value, key=key)) for key, value in rows])
        for name, rows in sections
    ]


def _item_timestamp(item: HookLedgerItem) -> str:
    record = item.record or {}
    return str(record.get("timestamp", ""))


__all__ = [
    "REDACTED_CREDENTIAL",
    "HookEvidenceDetail",
    "hook_detail_as_json",
    "hook_human_sections",
    "list_hook_evidence",
    "load_hook_evidence",
    "sanitize_for_display",
]
