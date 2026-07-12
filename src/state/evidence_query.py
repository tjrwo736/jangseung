"""Read-only queries over persisted run evidence.

This module deliberately does not import any state-writing helpers.  It reads
the existing run ledger and artifacts defensively so an inspection command can
report damaged entries without changing ``.aeg/`` or crashing the whole list.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.contracts import LEDGER_FILE, RUNS_DIR
from src.state.store import state_root

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
class RunEvidenceItem:
    """One ledger line and the artifact paths it describes."""

    line_number: int
    readable: bool
    entry: dict[str, Any] | None
    error: str | None
    run_path: Path | None = None
    evidence_path: Path | None = None
    manifest_path: Path | None = None

    @property
    def run_id(self) -> str:
        if self.entry is None:
            return f"ledger-line-{self.line_number}"
        value = self.entry.get("run_id")
        return value if isinstance(value, str) and value else f"ledger-line-{self.line_number}"

    def to_summary(self) -> dict[str, Any]:
        entry = self.entry or {}
        status = "UNREADABLE" if not self.readable else str(entry.get("status", "NOT_CHECKED"))
        return {
            "kind": "run",
            "id": self.run_id,
            "timestamp": str(entry.get("recorded_at", "")),
            "decision": status,
            "risk_level": str(entry.get("risk_level", "")),
            "readability": "READABLE" if self.readable else "UNREADABLE",
            "artifacts": {
                "run": bool(self.run_path and self.run_path.is_file()),
                "evidence": bool(self.evidence_path and self.evidence_path.is_file()),
                "manifest": bool(self.manifest_path and self.manifest_path.is_file()),
            },
            "error": self.error,
        }


@dataclass(frozen=True)
class RunEvidenceDetail:
    item: RunEvidenceItem
    evidence: dict[str, Any] | None
    manifest: dict[str, Any] | None
    error: str | None = None

    @property
    def readable(self) -> bool:
        return self.item.readable and self.error is None


def list_run_evidence(repo_root: str | Path, *, limit: int | None = None) -> list[RunEvidenceItem]:
    """Return ledger entries newest-first without mutating state."""

    ledger_path = state_root(repo_root) / LEDGER_FILE
    if not ledger_path.is_file():
        return []

    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [_unreadable_item(0, f"ledger unreadable: {exc.__class__.__name__}")]

    items: list[RunEvidenceItem] = []
    numbered_lines = [(number, line) for number, line in enumerate(lines, start=1) if line.strip()]
    for line_number, line in reversed(numbered_lines):
        if limit is not None and len(items) >= limit:
            break
        items.append(_parse_ledger_line(repo_root, line_number, line))
    return items


def load_run_evidence(repo_root: str | Path, run_id: str) -> RunEvidenceDetail | None:
    """Load one run's evidence and manifest, tolerating unrelated bad lines."""

    for item in list_run_evidence(repo_root):
        if item.entry is None or item.run_id != run_id:
            continue
        if not item.readable:
            return RunEvidenceDetail(item=item, evidence=None, manifest=None, error=item.error)
        try:
            evidence = _read_json_object(item.evidence_path, "evidence")
            manifest = _read_json_object(item.manifest_path, "manifest")
        except (OSError, ValueError) as exc:
            return RunEvidenceDetail(
                item=item,
                evidence=None,
                manifest=None,
                error=str(exc),
            )
        return RunEvidenceDetail(item=item, evidence=evidence, manifest=manifest)
    return None


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


def detail_as_json(detail: RunEvidenceDetail) -> dict[str, Any]:
    """Build a sanitized JSON-ready representation of a run detail."""

    return sanitize_for_display(
        {
            "kind": "run",
            "id": detail.item.run_id,
            "readability": "READABLE" if detail.readable else "UNREADABLE",
            "error": detail.error,
            "ledger_entry": detail.item.entry,
            "artifacts": detail.item.to_summary()["artifacts"],
            "evidence": detail.evidence,
            "manifest": detail.manifest,
        }
    )


def human_sections(detail: RunEvidenceDetail) -> list[tuple[str, list[tuple[str, Any]]]]:
    """Select a compact, structured human view instead of a flat dump."""

    entry = detail.item.entry or {}
    evidence = detail.evidence or {}
    manifest = detail.manifest or {}
    artifacts = detail.item.to_summary()["artifacts"]
    sections = [
        (
            "summary",
            [
                ("kind", "run"),
                ("run_id", detail.item.run_id),
                ("timestamp", entry.get("recorded_at", "")),
                ("task", evidence.get("task_text", entry.get("task_text", ""))),
            ],
        ),
        (
            "decision",
            [
                ("status", evidence.get("status", entry.get("status", "NOT_CHECKED"))),
                ("intent_risk", evidence.get("intent_risk", "")),
                ("impact_risk", evidence.get("impact_risk", "")),
                ("risk_level", evidence.get("risk_level", entry.get("risk_level", ""))),
                ("safe_default", evidence.get("safe_default", "")),
                ("reasons", evidence.get("status_reasons", evidence.get("classification_reasons", []))),
            ],
        ),
        (
            "artifacts",
            [
                ("run", artifacts["run"]),
                ("evidence", artifacts["evidence"]),
                ("manifest", artifacts["manifest"]),
                ("evidence_path", _display_path(detail.item.evidence_path)),
                ("manifest_path", _display_path(detail.item.manifest_path)),
            ],
        ),
        (
            "provenance",
            [
                ("branch", evidence.get("branch", "")),
                ("head_sha", evidence.get("head_sha", entry.get("head_sha", ""))),
                ("tree_sha", evidence.get("tree_sha", entry.get("tree_sha", ""))),
                ("changed_files", evidence.get("changed_files", [])),
                ("changed_files_source", evidence.get("changed_files_source", "")),
            ],
        ),
        (
            "integrity",
            [
                ("binding_status", evidence.get("binding_status", "")),
                ("binding_version", evidence.get("binding_version", "")),
                ("manifest_hash", entry.get("manifest_hash", manifest.get("manifest_hash", ""))),
                ("ledger_sequence_number", evidence.get("ledger_sequence_number", "")),
                ("ledger_chain_hash", evidence.get("ledger_chain_hash", "")),
            ],
        ),
    ]
    return [
        (name, [(key, sanitize_for_display(value, key=key)) for key, value in rows])
        for name, rows in sections
    ]


def _parse_ledger_line(repo_root: str | Path, line_number: int, line: str) -> RunEvidenceItem:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError:
        return _unreadable_item(line_number, "invalid JSON object")
    if not isinstance(parsed, dict):
        return _unreadable_item(line_number, "ledger entry is not a JSON object")
    run_id = parsed.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return RunEvidenceItem(line_number, False, parsed, "missing run_id")

    try:
        run_path = _artifact_path(repo_root, parsed, "run_path", run_id, "run.json")
        evidence_path = _artifact_path(repo_root, parsed, "evidence_path", run_id, "evidence.json")
        manifest_path = _artifact_path(repo_root, parsed, "manifest_path", run_id, "manifest.json")
    except ValueError as exc:
        return RunEvidenceItem(line_number, False, parsed, str(exc))
    return RunEvidenceItem(
        line_number=line_number,
        readable=True,
        entry=parsed,
        error=None,
        run_path=run_path,
        evidence_path=evidence_path,
        manifest_path=manifest_path,
    )


def _artifact_path(
    repo_root: str | Path,
    entry: Mapping[str, Any],
    field: str,
    run_id: str,
    filename: str,
) -> Path:
    raw_path = entry.get(field)
    if not isinstance(raw_path, str) or not raw_path.strip():
        candidate = state_root(repo_root) / RUNS_DIR / run_id / filename
    else:
        raw = Path(raw_path)
        candidate = raw if raw.is_absolute() else Path(repo_root).resolve() / raw
    resolved = candidate.resolve(strict=False)
    resolved_state = state_root(repo_root).resolve(strict=False)
    if not resolved.is_relative_to(resolved_state):
        raise ValueError(f"{field} escapes .aeg")
    return resolved


def _read_json_object(path: Path | None, label: str) -> dict[str, Any]:
    if path is None or not path.is_file():
        raise ValueError(f"{label} artifact is missing")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} artifact is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} artifact is not a JSON object")
    return parsed


def _unreadable_item(line_number: int, error: str) -> RunEvidenceItem:
    return RunEvidenceItem(line_number, False, None, error)


def _display_path(path: Path | None) -> str:
    return "" if path is None else path.as_posix()


__all__ = [
    "REDACTED_CREDENTIAL",
    "RunEvidenceDetail",
    "RunEvidenceItem",
    "detail_as_json",
    "human_sections",
    "list_run_evidence",
    "load_run_evidence",
    "sanitize_for_display",
]
