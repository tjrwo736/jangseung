"""Folder-local Aegis state APIs.

Names load on first use: this package is imported on every hook call, and the
hook ledger needs none of the run-state store.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_ATTRIBUTES = frozenset(
    {
        "ensure_initialized",
        "latest_run_entry",
        "load_latest_evidence",
        "save_run",
        "state_root",
    }
)


def __getattr__(name: str) -> Any:
    if name not in _LAZY_ATTRIBUTES:
        raise AttributeError(name)
    return getattr(import_module("jangseung.state.store"), name)


__all__ = sorted(_LAZY_ATTRIBUTES)
