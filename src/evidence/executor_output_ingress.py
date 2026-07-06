"""Phase 11-B-2-1 executor output ingress adapter scaffold.

Executor output is accepted as fixture data only. This adapter parses,
normalizes, validates, evaluates capabilities, returns a runtime-owned packet,
and stops.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import InitVar, dataclass, field
from types import MappingProxyType
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, REPORTED_ONLY, SAFE_DEFAULT
from src.evidence.structured_action_capabilities import (
    ActionCapabilityGateResult,
    evaluate_action_capabilities,
)
from src.evidence.structured_actions import (
    NOOP,
    StructuredActionValidationResult,
    validate_structured_action,
)

EXECUTOR_OUTPUT_INGRESS_ADAPTER_VERSION = (
    "phase11b_2_1_executor_output_ingress_adapter_scaffold_v0"
)
RUNTIME_INGRESS_ADAPTER = "runtime_ingress_adapter"
PARSE_OK = "PARSE_OK"
PARSE_FAILED = "PARSE_FAILED"
VALIDATION_NOT_RUN_PARSE_FAILED = "VALIDATION_NOT_RUN_PARSE_FAILED"
CAPABILITY_NOT_RUN_PARSE_FAILED = "CAPABILITY_NOT_RUN_PARSE_FAILED"
DIRECT_PACKET_SUBMISSION_PARSE_REJECTED = "DIRECT_PACKET_SUBMISSION_PARSE_REJECTED"
DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED = (
    "DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED"
)
DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED = (
    "DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED"
)

PREDEFINED_RAW_OUTPUT_SAMPLE: dict[str, Any] = {
    "action_type": NOOP,
    "action_id": "predefined-raw-output-noop-001",
    "declared_intent": "Predefined fixture sample; no operation.",
    "declared_risk": "LOW",
    "capability_requirements": ["noop"],
    "target_scope": {"repo_relative": True, "paths": []},
    "payload": {},
}

_ACTION_WRAPPER_FIELDS = ("action", "structured_action", "executor_action")
_IGNORABLE_SELF_REPORT_FIELDS = frozenset(
    {
        "approved_by_executor",
        "authority",
        "capability_granted",
        "capability_gate_reason",
        "capability_gate_result",
        "candidate_accepted",
        "created_by",
        "decision",
        "decision_basis",
        "denied_capability_reaches_store",
        "direct_packet_submission_rejected",
        "execution_allowed",
        "execution_authority",
        "executor_output_ingress_required",
        "granted",
        "ignored_reported_only_fields",
        "live_executor_authority",
        "live_executor_ready",
        "mutation_allowed",
        "mutation_authority",
        "packet_id",
        "packet_created_by",
        "packet_runtime_owned",
        "reported_authority",
        "reported_only",
        "reported_only_authority_reaches_store",
        "safe",
        "store_adjacent_candidate",
        "store_adjacent_candidate_eligible",
        "store_adjacent_candidate_gate_metadata_only",
        "store_adjacent_candidate_gate_version",
        "store_path_reachable",
        "store_routing_allowed",
        "unvalidated_action_reaches_store",
        "validation_status",
        "validation_valid",
        "trusted",
        "validated_action_forwarded_to_store",
        "write_authority",
        "write_authority_granted",
    }
)
_REPORTED_ONLY_MARKER_FIELDS = frozenset({"basis", "grant_source", "source"})

_RUNTIME_BUILD_MARKER = object()

_DIRECT_PACKET_FIELDS = frozenset(
    {
        "packet_id",
        "raw_output_hash",
        "parse_status",
        "parse_error",
        "normalized_action",
        "validation_result",
        "capability_result",
        "decision_basis",
        "adapter_version",
        "created_by",
    }
)
_DIRECT_PACKET_EVIDENCE_FIELDS = frozenset(
    {
        "action_decision_packet_evidence_binding_version",
        "action_decision_packet_evidence_hash",
        "packet_created_by",
        "packet_runtime_owned",
    }
)
_DIRECT_STORE_ADJACENT_CANDIDATE_FIELDS = frozenset(
    {
        "candidate_accepted",
        "gate_status",
        "gate_reason",
        "packet_evidence_hash",
        "evidence_verification_status",
        "store_adjacent_candidate_gate_version",
    }
)


@dataclass(frozen=True)
class ActionDecisionPacket:
    packet_id: str
    raw_output_hash: str
    parse_status: str
    parse_error: str | None
    normalized_action: Mapping[str, Any] | None
    validation_result: StructuredActionValidationResult | None
    capability_result: ActionCapabilityGateResult | None
    decision_basis: tuple[str, ...]
    ignored_reported_only_fields: tuple[str, ...]
    adapter_version: str = EXECUTOR_OUTPUT_INGRESS_ADAPTER_VERSION
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    store_routing_allowed: bool = False
    store_path_reachable: bool = False
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    safe_default: str = SAFE_DEFAULT
    created_by: str = RUNTIME_INGRESS_ADAPTER
    runtime_built_by_ingress: bool = field(default=False, init=False)
    _runtime_build_marker: InitVar[Any] = None

    def __post_init__(self, _runtime_build_marker: Any) -> None:
        object.__setattr__(self, "normalized_action", _freeze_value(self.normalized_action))
        object.__setattr__(self, "decision_basis", tuple(self.decision_basis))
        object.__setattr__(
            self,
            "ignored_reported_only_fields",
            tuple(self.ignored_reported_only_fields),
        )
        object.__setattr__(
            self,
            "runtime_built_by_ingress",
            _runtime_build_marker is _RUNTIME_BUILD_MARKER,
        )


def ingest_executor_output(
    raw_output: Mapping[str, Any] | str,
    *,
    repo_root: str | None = None,
) -> ActionDecisionPacket:
    """Create a runtime-owned decision packet from fixture executor output."""

    raw_output_hash = _raw_output_hash(raw_output)
    parsed, parse_status, parse_error = _parse_raw_output(raw_output)

    normalized_action: dict[str, Any] | None = None
    validation_result: StructuredActionValidationResult | None = None
    capability_result: ActionCapabilityGateResult | None = None
    ignored_reported_only_fields: tuple[str, ...] = tuple()

    if parse_status == PARSE_OK and parsed is not None:
        direct_submission_error = _direct_submission_parse_error(parsed)
        if direct_submission_error is not None:
            parse_status = PARSE_FAILED
            parse_error = direct_submission_error
        else:
            normalized_action, ignored_reported_only_fields = _normalize_parsed_output(parsed)
            action_for_validation: Mapping[str, Any] = (
                normalized_action if normalized_action is not None else {}
            )
            validation_result = validate_structured_action(
                action_for_validation,
                repo_root=repo_root,
            )
            capability_result = evaluate_action_capabilities(
                action_for_validation,
                validation_result,
                repo_root=repo_root,
            )

    return ActionDecisionPacket(
        packet_id=_packet_id(raw_output_hash),
        raw_output_hash=raw_output_hash,
        parse_status=parse_status,
        parse_error=parse_error,
        normalized_action=normalized_action,
        validation_result=validation_result,
        capability_result=capability_result,
        decision_basis=_decision_basis(
            parse_status=parse_status,
            validation_result=validation_result,
            capability_result=capability_result,
            ignored_reported_only_fields=ignored_reported_only_fields,
        ),
        ignored_reported_only_fields=ignored_reported_only_fields,
        _runtime_build_marker=_RUNTIME_BUILD_MARKER,
    )


def build_predefined_raw_output_sample() -> dict[str, Any]:
    return _clone_json_data(PREDEFINED_RAW_OUTPUT_SAMPLE)


def is_runtime_built_action_decision_packet(value: Any) -> bool:
    return (
        isinstance(value, ActionDecisionPacket)
        and value.runtime_built_by_ingress is True
    )


def build_executor_output_ingress_adapter_evidence() -> dict[str, Any]:
    return {
        "adapter_version": EXECUTOR_OUTPUT_INGRESS_ADAPTER_VERSION,
        "flow": (
            "raw_executor_output",
            "parse_normalize",
            "validate_structured_action",
            "evaluate_action_capabilities",
            "runtime_owned_action_decision_packet",
            "stop",
        ),
        "created_by": RUNTIME_INGRESS_ADAPTER,
        "executor_output_is_data_not_code": True,
        "raw_output_trusted_as_decision": False,
        "direct_action_decision_packet_submission_rejected": True,
        "direct_packet_evidence_submission_rejected": True,
        "direct_store_adjacent_candidate_submission_rejected": True,
        "validator_pass_is_execution": False,
        "capability_gate_pass_is_execution": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "write_authority_granted": False,
        "store_routing_allowed": False,
        "store_path_reachable": False,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "safe_default": SAFE_DEFAULT,
    }


def _parse_raw_output(
    raw_output: Mapping[str, Any] | str,
) -> tuple[dict[str, Any] | None, str, str | None]:
    try:
        if isinstance(raw_output, str):
            decoded = json.loads(raw_output)
            if not isinstance(decoded, Mapping):
                return None, PARSE_FAILED, "JSON fixture must decode to a mapping"
            return _clone_json_data(decoded), PARSE_OK, None

        if isinstance(raw_output, Mapping):
            return _clone_json_data(raw_output), PARSE_OK, None

        return None, PARSE_FAILED, "raw output must be a fixture mapping or JSON string"
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, PARSE_FAILED, f"{exc.__class__.__name__}: {exc}"


def _normalize_parsed_output(
    parsed: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    ignored_reported_only_fields: list[str] = []
    action_candidate: Any = parsed

    for wrapper_field in _ACTION_WRAPPER_FIELDS:
        if wrapper_field in parsed:
            ignored_reported_only_fields.extend(
                _self_report_paths_outside_action(parsed, wrapper_field)
            )
            action_candidate = parsed[wrapper_field]
            break

    if not isinstance(action_candidate, Mapping):
        return None, tuple(_unique(ignored_reported_only_fields))

    action = _clone_json_data(action_candidate)
    ignored_reported_only_fields.extend(_strip_top_level_self_reports(action, "action"))
    return action, tuple(_unique(ignored_reported_only_fields))


def _direct_submission_parse_error(parsed: Mapping[str, Any]) -> str | None:
    normalized_keys = frozenset(_normalize_key(str(key)) for key in parsed)
    if normalized_keys & _DIRECT_PACKET_EVIDENCE_FIELDS:
        return DIRECT_PACKET_EVIDENCE_SUBMISSION_PARSE_REJECTED
    if normalized_keys & _DIRECT_STORE_ADJACENT_CANDIDATE_FIELDS:
        return DIRECT_STORE_ADJACENT_CANDIDATE_PARSE_REJECTED
    if (
        {"packet_id", "raw_output_hash"}.issubset(normalized_keys)
        and normalized_keys & _DIRECT_PACKET_FIELDS
    ):
        return DIRECT_PACKET_SUBMISSION_PARSE_REJECTED
    return None


def _strip_top_level_self_reports(action: dict[str, Any], location: str) -> tuple[str, ...]:
    stripped: list[str] = []
    for key in tuple(action):
        normalized_key = _normalize_key(key)
        if normalized_key in _IGNORABLE_SELF_REPORT_FIELDS:
            stripped.append(f"{location}.{key}")
            del action[key]
        elif (
            normalized_key in _REPORTED_ONLY_MARKER_FIELDS
            and action[key] == REPORTED_ONLY
        ):
            stripped.append(f"{location}.{key}")
            del action[key]
    return tuple(stripped)


def _self_report_paths_outside_action(
    parsed: Mapping[str, Any],
    action_field: str,
) -> tuple[str, ...]:
    paths: list[str] = []
    for key, value in parsed.items():
        if key == action_field:
            continue
        _collect_self_report_paths(value, f"raw_output.{key}", key, paths)
    return tuple(paths)


def _collect_self_report_paths(
    value: Any,
    location: str,
    key: Any,
    paths: list[str],
) -> None:
    normalized_key = _normalize_key(str(key))
    if normalized_key in _IGNORABLE_SELF_REPORT_FIELDS:
        paths.append(location)
    elif normalized_key in _REPORTED_ONLY_MARKER_FIELDS and value == REPORTED_ONLY:
        paths.append(location)

    if isinstance(value, Mapping):
        for nested_key, nested_value in value.items():
            _collect_self_report_paths(
                nested_value,
                f"{location}.{nested_key}",
                nested_key,
                paths,
            )
    elif _is_sequence(value):
        for index, nested_value in enumerate(value):
            _collect_self_report_paths(
                nested_value,
                f"{location}[{index}]",
                index,
                paths,
            )


def _decision_basis(
    *,
    parse_status: str,
    validation_result: StructuredActionValidationResult | None,
    capability_result: ActionCapabilityGateResult | None,
    ignored_reported_only_fields: tuple[str, ...],
) -> tuple[str, ...]:
    validation_status = (
        validation_result.status
        if validation_result is not None
        else VALIDATION_NOT_RUN_PARSE_FAILED
    )
    capability_status = (
        capability_result.gate_result
        if capability_result is not None
        else CAPABILITY_NOT_RUN_PARSE_FAILED
    )
    basis = [
        "executor_output_is_data_not_code",
        "raw_output_is_not_trusted_decision_or_authority",
        "validator_pass_is_not_execution",
        "capability_gate_pass_is_not_execution_mutation_or_write_authority",
        f"parse_status={parse_status}",
        f"validation_status={validation_status}",
        f"capability_gate_result={capability_status}",
        f"safe_default={SAFE_DEFAULT}",
    ]
    if ignored_reported_only_fields:
        basis.append("reported_only_self_report_fields_ignored")
    return tuple(basis)


def _raw_output_hash(raw_output: Mapping[str, Any] | str) -> str:
    if isinstance(raw_output, str):
        payload = raw_output.encode("utf-8")
    else:
        payload = _canonical_json_bytes(raw_output)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _packet_id(raw_output_hash: str) -> str:
    return f"action-decision-packet-{raw_output_hash.removeprefix('sha256:')[:16]}"


def _canonical_json_bytes(value: Any) -> bytes:
    cloned = _clone_json_data(value)
    return json.dumps(
        cloned,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _clone_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_json_data(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_clone_json_data(nested) for nested in value]
    if isinstance(value, tuple):
        return [_clone_json_data(nested) for nested in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported fixture data type: {type(value).__name__}")


def _freeze_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(nested) for key, nested in value.items()}
        )
    if _is_sequence(value):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _normalize_key(value: str) -> str:
    return "_".join(value.strip().lower().split("-"))


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
