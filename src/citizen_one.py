"""Citizen One control-plane evidence skeleton."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_HOLD_REASON_NONE,
    CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    CITIZEN_ONE_MODE_OFF,
    CITIZEN_ONE_MODE_PROPOSE,
    CITIZEN_ONE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE,
    CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED,
    CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED,
    CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
    CITIZEN_ONE_PROPOSAL_RECORDED,
    DETERMINISTIC_STUB_PROPOSAL_ID,
    DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES,
    DETERMINISTIC_STUB_PROPOSAL_STEPS,
    DETERMINISTIC_STUB_PROPOSAL_SUMMARY,
    PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROPOSAL_HOLD_REASON_NONE,
    PROPOSAL_KIND_DETERMINISTIC_STUB,
    PROPOSAL_KIND_NOT_GENERATED,
    PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROPOSAL_SOURCE_DETERMINISTIC_STUB,
    PROPOSAL_SOURCE_NONE,
    PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
    PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
    REPORTED_ONLY,
)
from src.provider_adapter import build_disabled_provider_adapter_evidence


def build_citizen_one_evidence(
    requested: bool,
    proposal_requires_user_gate: bool = False,
    proposal_stub_requested: bool = False,
) -> dict[str, Any]:
    provider_adapter = build_disabled_provider_adapter_evidence(requested)
    if not requested:
        return {
            "citizen_one_requested": False,
            "citizen_one_mode": CITIZEN_ONE_MODE_OFF,
            "citizen_one_status": CITIZEN_ONE_NOT_REQUESTED,
            "citizen_one_provider_status": CITIZEN_ONE_PROVIDER_STATUS_NOT_REQUESTED,
            "citizen_one_output_present": False,
            "citizen_one_output_trust_boundary": REPORTED_ONLY,
            "citizen_one_reported_only": True,
            "citizen_one_hold_reason": CITIZEN_ONE_HOLD_REASON_NONE,
            "provider_config_source": CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NOT_REQUESTED,
            "provider_network_used": False,
            "model_output_hash_candidate": "",
            **provider_adapter,
        }

    if proposal_stub_requested:
        proposal = _deterministic_stub_proposal(proposal_requires_user_gate)
        return {
            "citizen_one_requested": True,
            "citizen_one_mode": CITIZEN_ONE_MODE_PROPOSE,
            "citizen_one_status": CITIZEN_ONE_PROPOSAL_RECORDED,
            "citizen_one_provider_status": CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED,
            "citizen_one_output_present": True,
            "citizen_one_output_trust_boundary": REPORTED_ONLY,
            "citizen_one_reported_only": True,
            "citizen_one_hold_reason": CITIZEN_ONE_HOLD_REASON_NONE,
            "provider_config_source": CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE,
            "provider_network_used": False,
            "model_output_hash_candidate": "",
            **provider_adapter,
            **proposal,
        }

    return {
        "citizen_one_requested": True,
        "citizen_one_mode": CITIZEN_ONE_MODE_PROPOSE,
        "citizen_one_status": CITIZEN_ONE_HELD_PROVIDER_NOT_CONFIGURED,
        "citizen_one_provider_status": CITIZEN_ONE_PROVIDER_STATUS_NOT_CONFIGURED,
        "citizen_one_output_present": False,
        "citizen_one_output_trust_boundary": REPORTED_ONLY,
        "citizen_one_reported_only": True,
        "citizen_one_hold_reason": CITIZEN_ONE_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
        "provider_config_source": CITIZEN_ONE_PROVIDER_CONFIG_SOURCE_NONE,
        "provider_network_used": False,
        "model_output_hash_candidate": "",
        **provider_adapter,
        "proposal_id": "",
        "proposal_version": CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
        "proposal_kind": PROPOSAL_KIND_NOT_GENERATED,
        "proposal_summary": "",
        "proposal_steps": [],
        "proposal_risk_notes": [],
        "proposal_requires_user_gate": proposal_requires_user_gate,
        "proposal_trust_boundary": REPORTED_ONLY,
        "proposal_reported_only": True,
        "proposal_source": PROPOSAL_SOURCE_NONE,
        "proposal_output_hash_candidate": "",
        "proposal_redaction_status": PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "proposal_status": PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
        "proposal_present": False,
        "proposal_hold_reason": PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    }


def _deterministic_stub_proposal(proposal_requires_user_gate: bool) -> dict[str, Any]:
    proposal = {
        "proposal_id": DETERMINISTIC_STUB_PROPOSAL_ID,
        "proposal_version": CITIZEN_ONE_PROPOSAL_CONTRACT_V0,
        "proposal_kind": PROPOSAL_KIND_DETERMINISTIC_STUB,
        "proposal_summary": DETERMINISTIC_STUB_PROPOSAL_SUMMARY,
        "proposal_steps": list(DETERMINISTIC_STUB_PROPOSAL_STEPS),
        "proposal_risk_notes": list(DETERMINISTIC_STUB_PROPOSAL_RISK_NOTES),
        "proposal_requires_user_gate": proposal_requires_user_gate,
        "proposal_trust_boundary": REPORTED_ONLY,
        "proposal_reported_only": True,
        "proposal_source": PROPOSAL_SOURCE_DETERMINISTIC_STUB,
        "proposal_redaction_status": PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "proposal_status": PROPOSAL_STATUS_DETERMINISTIC_STUB_RECORDED,
        "proposal_present": True,
        "proposal_hold_reason": PROPOSAL_HOLD_REASON_NONE,
    }
    proposal["proposal_output_hash_candidate"] = _proposal_hash_candidate(proposal)
    return proposal


def _proposal_hash_candidate(proposal: dict[str, Any]) -> str:
    hash_payload = {
        "proposal_id": proposal["proposal_id"],
        "proposal_version": proposal["proposal_version"],
        "proposal_kind": proposal["proposal_kind"],
        "proposal_summary": proposal["proposal_summary"],
        "proposal_steps": proposal["proposal_steps"],
        "proposal_risk_notes": proposal["proposal_risk_notes"],
        "proposal_requires_user_gate": proposal["proposal_requires_user_gate"],
        "proposal_trust_boundary": proposal["proposal_trust_boundary"],
        "proposal_reported_only": proposal["proposal_reported_only"],
        "proposal_source": proposal["proposal_source"],
        "proposal_redaction_status": proposal["proposal_redaction_status"],
        "proposal_status": proposal["proposal_status"],
        "proposal_present": proposal["proposal_present"],
        "proposal_hold_reason": proposal["proposal_hold_reason"],
    }
    canonical = json.dumps(hash_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
