"""Evidence packet creation and validation.

Names load on first use: this package is imported on every hook call, and the
hook judgment needs none of the run-evidence modules listed here.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_ATTRIBUTES = {
    "VerifyResult": "jangseung.evidence.verify",
    "verify_latest": "jangseung.evidence.verify",
    "changed_files_hash": "jangseung.evidence.binding",
    "manifest_hash": "jangseung.evidence.binding",
    "build_mutation_boundary": "jangseung.evidence.mutation_boundary",
    "capture_mutation_snapshot": "jangseung.evidence.mutation_boundary",
    "compute_mutation_delta": "jangseung.evidence.mutation_boundary",
    "mutation_delta_paths": "jangseung.evidence.mutation_boundary",
    "build_evidence_packet": "jangseung.evidence.packet",
    "new_run_id": "jangseung.evidence.packet",
    "validate_completion_contract_v0": "jangseung.evidence.schema",
    "validate_evidence_binding_v0": "jangseung.evidence.schema",
    "validate_evidence_binding_v1": "jangseung.evidence.schema",
    "validate_evidence_packet": "jangseung.evidence.schema",
    "validate_no_forbidden_raw_prompt_response_keys": "jangseung.evidence.schema",
    "validate_user_gate_reason_card_v1": "jangseung.evidence.schema",
}


def __getattr__(name: str) -> Any:
    module = _LAZY_ATTRIBUTES.get(name)
    if module is None:
        raise AttributeError(name)
    return getattr(import_module(module), name)


__all__ = sorted(_LAZY_ATTRIBUTES)
