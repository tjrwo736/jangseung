"""Evidence packet creation and validation."""

from __future__ import annotations

from typing import Any

from src.evidence.binding import changed_files_hash, manifest_hash
from src.evidence.mediated_write_evidence_binding import (
    build_denied_write_no_mutation_observation,
    build_mediated_write_evidence_record,
    mediated_write_evidence_binding_digest,
)
from src.evidence.mutation_boundary import (
    build_mutation_boundary,
    capture_mutation_snapshot,
    compute_mutation_delta,
    mutation_delta_paths,
)
from src.evidence.packet import build_evidence_packet, new_run_id
from src.evidence.schema import (
    validate_completion_contract_v0,
    validate_evidence_binding_v0,
    validate_evidence_binding_v1,
    validate_evidence_packet,
    validate_no_forbidden_raw_prompt_response_keys,
    validate_user_gate_reason_card_v1,
)


def verify_latest(cwd: Any) -> Any:
    from src.evidence.verify import verify_latest as _verify_latest

    return _verify_latest(cwd)


def __getattr__(name: str) -> Any:
    if name == "VerifyResult":
        from src.evidence.verify import VerifyResult

        return VerifyResult
    raise AttributeError(name)

__all__ = [
    "VerifyResult",
    "build_evidence_packet",
    "build_mutation_boundary",
    "capture_mutation_snapshot",
    "changed_files_hash",
    "compute_mutation_delta",
    "build_denied_write_no_mutation_observation",
    "build_mediated_write_evidence_record",
    "manifest_hash",
    "mediated_write_evidence_binding_digest",
    "mutation_delta_paths",
    "new_run_id",
    "validate_completion_contract_v0",
    "validate_evidence_binding_v0",
    "validate_evidence_binding_v1",
    "validate_evidence_packet",
    "validate_no_forbidden_raw_prompt_response_keys",
    "validate_user_gate_reason_card_v1",
    "verify_latest",
]
