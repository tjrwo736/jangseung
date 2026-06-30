"""Folder-local Aegis state APIs."""

from src.state.store import (
    append_ledger,
    ensure_initialized,
    latest_run_entry,
    load_latest_evidence,
    save_run,
    state_root,
)

__all__ = [
    "append_ledger",
    "ensure_initialized",
    "latest_run_entry",
    "load_latest_evidence",
    "save_run",
    "state_root",
]
