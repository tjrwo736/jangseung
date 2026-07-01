"""Disabled provider adapter contract fields.

This module records only disabled/not-configured metadata. It does not read
environment variables, load secrets, call provider SDKs, use the network, or
execute/mutate files.
"""

from __future__ import annotations

from typing import Any

from src.contracts import (
    PROVIDER_ADAPTER_DISABLED_REQUEST_ID,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_NOT_REQUESTED,
    PROVIDER_MODEL_NONE,
    PROVIDER_NAME_NONE,
    PROVIDER_PROMPT_SOURCE_DISABLED,
    PROVIDER_PROMPT_SOURCE_NONE,
    PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROVIDER_RESPONSE_ERROR_CLASS_NONE,
    PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
    PROVIDER_RESPONSE_SOURCE_NONE,
    PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_SECRET_SOURCE_NONE,
    PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
    REPORTED_ONLY,
)


def build_disabled_provider_adapter_evidence(requested: bool) -> dict[str, Any]:
    if not requested:
        return {
            "provider_request_id": "",
            "provider_mode": PROVIDER_MODE_NOT_REQUESTED,
            "provider_name": PROVIDER_NAME_NONE,
            "provider_model": PROVIDER_MODEL_NONE,
            "provider_prompt_source": PROVIDER_PROMPT_SOURCE_NONE,
            "provider_prompt_hash_candidate": "",
            "provider_request_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
            "provider_network_opt_in": False,
            "provider_secret_source": PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
            "provider_secret_observed": False,
            "provider_response_present": False,
            "provider_response_status": PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
            "provider_response_source": PROVIDER_RESPONSE_SOURCE_NONE,
            "provider_response_reported_only": True,
            "provider_response_trust_boundary": REPORTED_ONLY,
            "provider_response_hash_candidate": "",
            "provider_response_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
            "provider_response_error_class": PROVIDER_RESPONSE_ERROR_CLASS_NONE,
            "provider_response_error_safe_summary": PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE,
        }

    return {
        "provider_request_id": PROVIDER_ADAPTER_DISABLED_REQUEST_ID,
        "provider_mode": PROVIDER_MODE_DISABLED,
        "provider_name": PROVIDER_NAME_NONE,
        "provider_model": PROVIDER_MODEL_NONE,
        "provider_prompt_source": PROVIDER_PROMPT_SOURCE_DISABLED,
        "provider_prompt_hash_candidate": "",
        "provider_request_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "provider_network_opt_in": False,
        "provider_secret_source": PROVIDER_SECRET_SOURCE_NONE,
        "provider_secret_observed": False,
        "provider_response_present": False,
        "provider_response_status": PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
        "provider_response_source": PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
        "provider_response_reported_only": True,
        "provider_response_trust_boundary": REPORTED_ONLY,
        "provider_response_hash_candidate": "",
        "provider_response_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "provider_response_error_class": PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
        "provider_response_error_safe_summary": PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    }
