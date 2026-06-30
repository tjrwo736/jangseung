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
    REPORTED_ONLY,
)


def build_citizen_one_evidence(requested: bool) -> dict[str, Any]:
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
    }
