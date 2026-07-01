"""Disabled provider adapter contract fields.

This module records only disabled/not-configured metadata. It does not read
environment variables, load secrets, call provider SDKs, use the network, or
execute/mutate files.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.contracts import (
    PROVIDER_ADAPTER_DISABLED_REQUEST_ID,
    PROVIDER_ENV_LOADING_STATUS_DISABLED,
    PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED,
    PROVIDER_MODE_DISABLED,
    PROVIDER_MODE_NOT_REQUESTED,
    PROVIDER_MODEL_NONE,
    PROVIDER_NAME_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_NONE,
    PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED,
    PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN,
    PROVIDER_NETWORK_STATUS_NOT_REQUESTED,
    PROVIDER_PROMPT_SOURCE_DISABLED,
    PROVIDER_PROMPT_SOURCE_NONE,
    PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
    PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED,
    PROVIDER_REQUEST_STATUS_NOT_REQUESTED,
    PROVIDER_RUNTIME_ERROR_CLASS_NONE,
    PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED,
    PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE,
    PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RUNTIME_STATUS_NOT_REQUESTED,
    PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
    PROVIDER_RESPONSE_ERROR_CLASS_NONE,
    PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED,
    PROVIDER_RESPONSE_SOURCE_DISABLED_ADAPTER,
    PROVIDER_RESPONSE_SOURCE_NONE,
    PROVIDER_RESPONSE_STATUS_NOT_REQUESTED,
    PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED,
    PROVIDER_SELECTION_SOURCE_DISABLED,
    PROVIDER_SELECTION_SOURCE_NOT_REQUESTED,
    PROVIDER_SELECTION_STATUS_NOT_CONFIGURED,
    PROVIDER_SELECTION_STATUS_NOT_REQUESTED,
    PROVIDER_SECRET_SOURCE_NONE,
    PROVIDER_SECRET_SOURCE_NOT_REQUESTED,
    PROMPT_BUILD_STATUS_NOT_BUILT,
    PROMPT_BUILD_STATUS_PROVIDER_DISABLED,
    PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED,
    PROMPT_SOURCE_DISABLED,
    PROMPT_SOURCE_NONE,
    PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE,
    REPORTED_ONLY,
    RESPONSE_ERROR_CLASS_NONE,
    RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED,
    RESPONSE_ERROR_SAFE_SUMMARY_NONE,
    RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED,
    RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED,
    RESPONSE_SOURCE_DISABLED_ADAPTER,
    RESPONSE_SOURCE_NONE,
    RESPONSE_STATUS_NOT_REQUESTED,
    RESPONSE_STATUS_PROVIDER_DISABLED,
)


def build_disabled_provider_adapter_evidence(requested: bool) -> dict[str, Any]:
    runtime_metadata = _provider_runtime_metadata(requested)
    if not requested:
        return {
            **_prompt_redaction_metadata(requested=False),
            **_response_redaction_metadata(requested=False),
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
            **runtime_metadata,
        }

    return {
        **_prompt_redaction_metadata(requested=True),
        **_response_redaction_metadata(requested=True),
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
        **runtime_metadata,
    }


def _provider_runtime_metadata(requested: bool) -> dict[str, Any]:
    request_id = PROVIDER_ADAPTER_DISABLED_REQUEST_ID if requested else ""
    request_status = (
        PROVIDER_REQUEST_STATUS_BLOCKED_PROVIDER_NOT_CONFIGURED
        if requested
        else PROVIDER_REQUEST_STATUS_NOT_REQUESTED
    )
    response_status = (
        PROVIDER_RESPONSE_STATUS_PROVIDER_NOT_CONFIGURED
        if requested
        else PROVIDER_RESPONSE_STATUS_NOT_REQUESTED
    )
    error_class = (
        PROVIDER_RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED if requested else PROVIDER_RESPONSE_ERROR_CLASS_NONE
    )
    error_summary = (
        PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NOT_CONFIGURED if requested else PROVIDER_RESPONSE_ERROR_SAFE_SUMMARY_NONE
    )

    request_metadata = {
        "provider_request_requested": False,
        "provider_request_status": request_status,
        "provider_request_id": request_id,
        "provider_request_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "provider_request_raw_stored": False,
    }
    response_metadata = {
        "provider_response_present": False,
        "provider_response_status": response_status,
        "provider_response_reported_only": True,
        "provider_response_trust_boundary": REPORTED_ONLY,
        "provider_response_redaction_status": PROVIDER_REDACTION_STATUS_NO_RAW_PROMPT_OR_RESPONSE_STORED,
        "provider_response_raw_stored": False,
        "provider_error_class": error_class,
        "provider_error_safe_summary": error_summary,
    }

    return {
        "provider_runtime_state": PROVIDER_RUNTIME_STATE_HOLD_CURRENT_STATE,
        "provider_runtime_status": (
            PROVIDER_RUNTIME_STATUS_HELD_PROVIDER_NOT_CONFIGURED
            if requested
            else PROVIDER_RUNTIME_STATUS_NOT_REQUESTED
        ),
        "provider_runtime_hold_reason": (
            PROVIDER_RUNTIME_HOLD_REASON_PROVIDER_NOT_CONFIGURED
            if requested
            else PROVIDER_RUNTIME_HOLD_REASON_NOT_REQUESTED
        ),
        "provider_runtime_error_class": (
            PROVIDER_RUNTIME_ERROR_CLASS_PROVIDER_NOT_CONFIGURED if requested else PROVIDER_RUNTIME_ERROR_CLASS_NONE
        ),
        "provider_runtime_error_safe_summary": (
            PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NOT_CONFIGURED
            if requested
            else PROVIDER_RUNTIME_ERROR_SAFE_SUMMARY_NONE
        ),
        "provider_selection_requested": requested,
        "provider_selected": False,
        "provider_selection_source": (
            PROVIDER_SELECTION_SOURCE_DISABLED if requested else PROVIDER_SELECTION_SOURCE_NOT_REQUESTED
        ),
        "provider_selection_status": (
            PROVIDER_SELECTION_STATUS_NOT_CONFIGURED if requested else PROVIDER_SELECTION_STATUS_NOT_REQUESTED
        ),
        "provider_secret_required": False,
        "provider_secret_value_recorded": False,
        "provider_secret_redaction_status": PROVIDER_SECRET_REDACTION_STATUS_NO_SECRET_VALUE_RECORDED,
        "provider_env_loading_requested": False,
        "provider_env_loading_status": (
            PROVIDER_ENV_LOADING_STATUS_DISABLED if requested else PROVIDER_ENV_LOADING_STATUS_NOT_REQUESTED
        ),
        "provider_network_opt_in_requested": False,
        "provider_network_opt_in_allowed": False,
        "provider_network_status": (
            PROVIDER_NETWORK_STATUS_BLOCKED_NO_OPT_IN if requested else PROVIDER_NETWORK_STATUS_NOT_REQUESTED
        ),
        "provider_network_block_reason": (
            PROVIDER_NETWORK_BLOCK_REASON_OPT_IN_NOT_REQUESTED if requested else PROVIDER_NETWORK_BLOCK_REASON_NONE
        ),
        **request_metadata,
        "provider_request_metadata_hash": _safe_metadata_hash(request_metadata),
        **response_metadata,
        "provider_response_metadata_hash": _safe_metadata_hash(response_metadata),
    }


def _safe_metadata_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prompt_redaction_metadata(requested: bool) -> dict[str, Any]:
    return {
        "prompt_build_requested": False,
        "prompt_build_status": (
            PROMPT_BUILD_STATUS_PROVIDER_DISABLED if requested else PROMPT_BUILD_STATUS_NOT_BUILT
        ),
        "prompt_source": PROMPT_SOURCE_DISABLED if requested else PROMPT_SOURCE_NONE,
        "prompt_input_summary": "",
        "prompt_redaction_status": PROMPT_REDACTION_STATUS_NO_RAW_PROMPT_STORED,
        "prompt_hash_candidate": "",
        "prompt_storage_policy": PROMPT_STORAGE_POLICY_NO_RAW_PROMPT_STORAGE,
        "prompt_secret_detected": False,
        "prompt_raw_stored": False,
    }


def _response_redaction_metadata(requested: bool) -> dict[str, Any]:
    return {
        "response_present": False,
        "response_status": RESPONSE_STATUS_PROVIDER_DISABLED if requested else RESPONSE_STATUS_NOT_REQUESTED,
        "response_source": RESPONSE_SOURCE_DISABLED_ADAPTER if requested else RESPONSE_SOURCE_NONE,
        "response_reported_only": True,
        "response_trust_boundary": REPORTED_ONLY,
        "response_redaction_status": RESPONSE_REDACTION_STATUS_NO_RAW_RESPONSE_STORED,
        "response_hash_candidate": "",
        "response_raw_stored": False,
        "response_error_class": (
            RESPONSE_ERROR_CLASS_PROVIDER_NOT_CONFIGURED if requested else RESPONSE_ERROR_CLASS_NONE
        ),
        "response_error_safe_summary": (
            RESPONSE_ERROR_SAFE_SUMMARY_PROVIDER_DISABLED if requested else RESPONSE_ERROR_SAFE_SUMMARY_NONE
        ),
    }
