"""Citizen One control-plane evidence skeleton."""

from __future__ import annotations

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
    PROPOSAL_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROPOSAL_KIND_NOT_GENERATED,
    PROPOSAL_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROPOSAL_SOURCE_NONE,
    PROPOSAL_STATUS_PROVIDER_NOT_CONFIGURED,
    REPORTED_ONLY,
)


def build_citizen_one_evidence(requested: bool, proposal_requires_user_gate: bool = False) -> dict[str, Any]:
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
            "provider_secret_observed": False,
            "model_output_hash_candidate": "",
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
        "provider_secret_observed": False,
        "model_output_hash_candidate": "",
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
