"""Phase 11-C-5 hook evidence binding verification gate.

This module verifies serialized Phase 11-C-4 hook evidence binding candidates.
It is inert verification logic only: it does not implement hook runtime, emit a
Claude Code hook response, execute actions, grant authority, or write state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.claude_code_pretooluse_input_contract import (
    PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
)
from src.evidence.claude_code_tool_call_mapping import (
    PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
)
from src.evidence.hook_decision_adapter import (
    HOOK_DECISION_CANDIDATES,
    PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
)
from src.evidence.hook_evidence_binding import (
    HOOK_EVIDENCE_BINDING_REJECTED,
    HOOK_EVIDENCE_BOUND,
    HookEvidenceBinding,
    PHASE11C_4_COMPLETE_LABEL,
    PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
    TOOL_INPUT_HASH_ALGORITHM,
)

PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION = (
    "phase11c_5_hook_evidence_verification_gate_v0"
)
PHASE11C_5_COMPLETE_LABEL = (
    "PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_COMPLETE_NOT_HOOK_RUNTIME"
)

VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE = (
    "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE"
)
REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE = (
    "REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE"
)
HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE = (
    "HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE"
)

BINDING_HASH_MISMATCH_REJECTED = "BINDING_HASH_MISMATCH_REJECTED"
BINDING_ID_MISMATCH_REJECTED = "BINDING_ID_MISMATCH_REJECTED"
BINDING_COMPLETION_LABEL_MISMATCH_REJECTED = (
    "BINDING_COMPLETION_LABEL_MISMATCH_REJECTED"
)
BINDING_STATUS_MISMATCH_REJECTED = "BINDING_STATUS_MISMATCH_REJECTED"
BINDING_FIELD_MISMATCH_REJECTED = "BINDING_FIELD_MISMATCH_REJECTED"
BINDING_PROVENANCE_MISMATCH_REJECTED = "BINDING_PROVENANCE_MISMATCH_REJECTED"
BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED = (
    "BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED"
)
BINDING_REPORTED_ONLY_PROMOTION_REJECTED = (
    "BINDING_REPORTED_ONLY_PROMOTION_REJECTED"
)
BINDING_NOT_CHECKED_PROMOTION_REJECTED = "BINDING_NOT_CHECKED_PROMOTION_REJECTED"
BINDING_AUTHORITY_FLAG_REJECTED = "BINDING_AUTHORITY_FLAG_REJECTED"
BINDING_RUNTIME_FLAG_REJECTED = "BINDING_RUNTIME_FLAG_REJECTED"
BINDING_STORE_WRITE_FLAG_REJECTED = "BINDING_STORE_WRITE_FLAG_REJECTED"
BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED = (
    "BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED"
)
BINDING_SECRET_FRAGMENT_RETAINED_REJECTED = (
    "BINDING_SECRET_FRAGMENT_RETAINED_REJECTED"
)
BINDING_RECORD_SHAPE_REJECTED = "BINDING_RECORD_SHAPE_REJECTED"

_BINDING_ID_PREFIX = "phase11c-4-hook-evidence:"

_BINDING_PAYLOAD_FIELDS = (
    "binding_version",
    "completion_label",
    "binding_status",
    "binding_reasons",
    "tool_name",
    "tool_use_id",
    "tool_input_hash",
    "tool_input_hash_algorithm",
    "tool_input_redaction_policy",
    "tool_input_raw_stored",
    "tool_input_redacted_metadata",
    "source_tool_use_id",
    "action_id",
    "candidate_action_type",
    "candidate_status",
    "decision_candidate",
    "decision_candidate_status",
    "decision_reasons",
    "declared_risk",
    "risk_status",
    "capability_requirements",
    "target_scope_hash",
    "target_scope_redacted_metadata",
    "payload_hash",
    "payload_redacted_metadata",
    "provenance",
    "safe_default",
    "live_executor_authority",
    "trust_boundary",
    "evidence_binding_is_judgment_basis",
    "evidence_binding_is_execution",
    "evidence_binding_is_hook_response",
    "evidence_binding_is_write_authority",
    "evidence_binding_is_store_write",
    "evidence_binding_mutates_filesystem",
    "reported_only_trusted_as_judgment_basis",
    "reported_only_is_judgment_basis",
    "not_checked_is_pass",
    "safe_default_changed",
    "hook_command_implemented",
    "hook_installation_implemented",
    "claude_code_execution_performed",
    "real_hook_response_emitted",
    "codex_implementation_added",
    "provider_model_network_implemented",
    "llm_call_implemented",
    "api_key_env_secret_loading_implemented",
    "network_client_implemented",
    "process_execution_implemented",
    "shell_execution_implemented",
    "action_execution_engine_implemented",
    "tool_runtime_implemented",
    "write_authority_granted",
    "state_store_module_changed",
    "filesystem_mutation_by_binding",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)

_BINDING_RECORD_FIELDS = ("binding_id", "binding_hash", *_BINDING_PAYLOAD_FIELDS)
_VALID_BINDING_STATUSES = (HOOK_EVIDENCE_BOUND, HOOK_EVIDENCE_BINDING_REJECTED)

_AUTHORITY_FALSE_FIELDS = (
    "evidence_binding_is_judgment_basis",
    "evidence_binding_is_write_authority",
    "reported_only_trusted_as_judgment_basis",
    "reported_only_is_judgment_basis",
    "write_authority_granted",
)

_RUNTIME_FALSE_FIELDS = (
    "evidence_binding_is_execution",
    "evidence_binding_is_hook_response",
    "evidence_binding_mutates_filesystem",
    "safe_default_changed",
    "hook_command_implemented",
    "hook_installation_implemented",
    "claude_code_execution_performed",
    "real_hook_response_emitted",
    "codex_implementation_added",
    "provider_model_network_implemented",
    "llm_call_implemented",
    "api_key_env_secret_loading_implemented",
    "network_client_implemented",
    "process_execution_implemented",
    "shell_execution_implemented",
    "action_execution_engine_implemented",
    "tool_runtime_implemented",
    "filesystem_mutation_by_binding",
    "patch_application_implemented",
    "public_release_performed",
    "universal_prompt_injection_prevention_claimed",
    "sandbox_process_isolation_claimed",
    "bash_safe_claimed",
)

_STORE_WRITE_FALSE_FIELDS = (
    "evidence_binding_is_store_write",
    "state_store_module_changed",
)

_RAW_TOOL_INPUT_KEYS = frozenset(
    {
        "tool_input",
        "raw_tool_input",
        "tool_input_raw",
        "full_tool_input",
    }
)

_RAW_RETENTION_KEYS = frozenset(
    {
        "raw_value_stored",
        "raw_values_stored",
        "raw_tool_input_stored",
    }
)


@dataclass(frozen=True)
class HookEvidenceVerificationGateResult:
    verification_version: str
    completion_label: str
    verification_output: str
    verification_passed: bool
    binding_verified: bool
    binding_rejected: bool
    binding_id: str | None
    binding_hash: str | None
    recomputed_binding_hash: str | None
    binding_status: str | None
    rejection_codes: tuple[str, ...]
    checks: tuple[str, ...]
    safe_default: str = SAFE_DEFAULT
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    trust_boundary: str = UNTRUSTED_RAW_EXECUTOR_OUTPUT
    verification_output_is_judgment_basis: bool = False
    verification_output_is_execution: bool = False
    verification_output_is_hook_response: bool = False
    verification_output_is_write_authority: bool = False
    verification_output_is_store_write: bool = False
    verification_output_mutates_filesystem: bool = False
    verified_candidate_is_real_claude_code_hook_response: bool = False
    rejected_candidate_is_real_claude_code_hook_response: bool = False
    safe_default_changed: bool = False
    hook_command_implemented: bool = False
    hook_installation_implemented: bool = False
    claude_code_execution_performed: bool = False
    real_hook_response_emitted: bool = False
    codex_implementation_added: bool = False
    provider_model_network_implemented: bool = False
    llm_call_implemented: bool = False
    api_key_env_secret_loading_implemented: bool = False
    network_client_implemented: bool = False
    process_execution_implemented: bool = False
    shell_execution_implemented: bool = False
    action_execution_engine_implemented: bool = False
    tool_runtime_implemented: bool = False
    write_authority_granted: bool = False
    state_store_module_changed: bool = False
    filesystem_mutation_by_verification: bool = False
    patch_application_implemented: bool = False
    public_release_performed: bool = False
    universal_prompt_injection_prevention_claimed: bool = False
    sandbox_process_isolation_claimed: bool = False
    bash_safe_claimed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "rejection_codes", tuple(self.rejection_codes))
        object.__setattr__(self, "checks", tuple(self.checks))

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def verify_hook_evidence_binding_candidate(
    record: Mapping[str, Any] | HookEvidenceBinding | Any,
    *,
    known_secret_fragments: Iterable[str] = tuple(),
) -> HookEvidenceVerificationGateResult:
    """Verify a Phase 11-C-4 binding candidate without granting authority."""

    rejections: list[str] = []
    checks: list[str] = []

    try:
        evidence = _coerce_record(record)
    except TypeError as exc:
        return _build_result(
            evidence=None,
            recomputed_binding_hash=None,
            rejections=(BINDING_RECORD_SHAPE_REJECTED,),
            checks=(f"binding record shape rejected:{exc}",),
        )

    recomputed_binding_hash = _verify_record_shape_and_hash(
        evidence,
        rejections,
        checks,
    )
    _verify_required_binding_fields(evidence, rejections, checks)
    _verify_provenance(evidence, rejections, checks)
    _verify_decision_candidate(evidence, rejections, checks)
    _verify_reported_only_and_not_checked(evidence, rejections, checks)
    _verify_false_flags(evidence, rejections, checks)
    _verify_raw_tool_input_not_retained(evidence, rejections, checks)
    _verify_secret_fragments_absent(
        evidence,
        tuple(known_secret_fragments),
        rejections,
        checks,
    )

    return _build_result(
        evidence=evidence,
        recomputed_binding_hash=recomputed_binding_hash,
        rejections=tuple(dict.fromkeys(rejections)),
        checks=tuple(checks),
    )


def hook_evidence_binding_candidate_digest_from_mapping(
    record: Mapping[str, Any],
) -> str:
    """Recompute the Phase 11-C-4 binding hash for a serialized record."""

    evidence = _coerce_record(record)
    return _sha256_json(_binding_payload(evidence))


def build_hook_evidence_verification_gate_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION,
        "completion_label": PHASE11C_5_COMPLETE_LABEL,
        "input_contract_version": PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
        "input_completion_label": PHASE11C_4_COMPLETE_LABEL,
        "verification_outputs": (
            VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
            REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
            HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE,
        ),
        "binding_hash_recomputed": True,
        "binding_id_matches_binding_hash": True,
        "binding_statuses_verified": _VALID_BINDING_STATUSES,
        "tool_input_hash_algorithm": TOOL_INPUT_HASH_ALGORITHM,
        "tool_input_raw_stored_required": False,
        "raw_tool_input_retained_by_default": False,
        "secret_fragments_retained_for_known_probes": False,
        "source_tool_use_id_action_id_provenance_checked": True,
        "decision_candidates": HOOK_DECISION_CANDIDATES,
        "reported_only_is_judgment_basis": False,
        "not_checked_is_pass": False,
        "verification_output_is_judgment_basis": False,
        "verification_output_is_execution": False,
        "verification_output_is_hook_response": False,
        "verification_output_is_write_authority": False,
        "verification_output_is_store_write": False,
        "verification_output_mutates_filesystem": False,
        "verified_candidate_is_real_claude_code_hook_response": False,
        "rejected_candidate_is_real_claude_code_hook_response": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
        "codex_implementation_added": False,
        "provider_model_network_implemented": False,
        "llm_call_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "network_client_implemented": False,
        "process_execution_implemented": False,
        "shell_execution_implemented": False,
        "action_execution_engine_implemented": False,
        "tool_runtime_implemented": False,
        "write_authority_granted": False,
        "state_store_module_changed": False,
        "filesystem_mutation_by_verification": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _verify_record_shape_and_hash(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> str | None:
    field_names = set(evidence)
    expected_names = set(_BINDING_RECORD_FIELDS)
    missing = tuple(sorted(expected_names - field_names))
    unexpected = tuple(sorted(field_names - expected_names))
    if missing:
        _reject(rejections, BINDING_RECORD_SHAPE_REJECTED)
        checks.append(f"binding record missing fields:{','.join(missing)}")
    if unexpected:
        _reject(rejections, BINDING_RECORD_SHAPE_REJECTED)
        checks.append(f"binding record unexpected fields:{','.join(unexpected)}")
    if missing:
        return None

    try:
        expected_hash = _sha256_json(_binding_payload(evidence))
        replay_hash = _sha256_json(_binding_payload(evidence))
    except TypeError as exc:
        _reject(rejections, BINDING_HASH_MISMATCH_REJECTED)
        checks.append(f"binding hash replay failed:{exc}")
        return None

    if expected_hash == replay_hash:
        checks.append("binding_hash replay is deterministic")
    else:
        _reject(rejections, BINDING_HASH_MISMATCH_REJECTED)
        checks.append("binding_hash replay was not deterministic")

    if evidence.get("binding_hash") == expected_hash:
        checks.append("binding_hash matched canonical payload")
    else:
        _reject(rejections, BINDING_HASH_MISMATCH_REJECTED)
        checks.append("binding_hash mismatch rejected")

    expected_binding_id = f"{_BINDING_ID_PREFIX}{evidence.get('binding_hash')}"
    if evidence.get("binding_id") == expected_binding_id:
        checks.append("binding_id matched binding_hash")
    else:
        _reject(rejections, BINDING_ID_MISMATCH_REJECTED)
        checks.append("binding_id mismatch rejected")

    return expected_hash


def _verify_required_binding_fields(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    _expect_equal(
        evidence,
        "binding_version",
        PHASE11C_4_HOOK_EVIDENCE_BINDING_VERSION,
        BINDING_FIELD_MISMATCH_REJECTED,
        rejections,
        checks,
    )
    _expect_equal(
        evidence,
        "completion_label",
        PHASE11C_4_COMPLETE_LABEL,
        BINDING_COMPLETION_LABEL_MISMATCH_REJECTED,
        rejections,
        checks,
    )
    if evidence.get("binding_status") in _VALID_BINDING_STATUSES:
        checks.append("binding_status is a known 11-C-4 status")
    else:
        _reject(rejections, BINDING_STATUS_MISMATCH_REJECTED)
        checks.append("binding_status mismatch rejected")
    _expect_equal(
        evidence,
        "tool_input_raw_stored",
        False,
        BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED,
        rejections,
        checks,
    )
    _expect_equal(
        evidence,
        "tool_input_hash_algorithm",
        TOOL_INPUT_HASH_ALGORITHM,
        BINDING_FIELD_MISMATCH_REJECTED,
        rejections,
        checks,
    )
    _expect_equal(
        evidence,
        "safe_default",
        SAFE_DEFAULT,
        BINDING_FIELD_MISMATCH_REJECTED,
        rejections,
        checks,
    )
    _expect_equal(
        evidence,
        "live_executor_authority",
        LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        BINDING_FIELD_MISMATCH_REJECTED,
        rejections,
        checks,
    )
    _expect_equal(
        evidence,
        "trust_boundary",
        UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        BINDING_FIELD_MISMATCH_REJECTED,
        rejections,
        checks,
    )


def _verify_provenance(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    provenance = evidence.get("provenance")
    if not isinstance(provenance, Mapping):
        _reject(rejections, BINDING_PROVENANCE_MISMATCH_REJECTED)
        checks.append("provenance missing or not a mapping")
        return

    hook_input = provenance.get("hook_input")
    action_candidate = provenance.get("structured_action_candidate")
    decision_candidate = provenance.get("hook_decision_candidate")
    if not all(
        isinstance(value, Mapping)
        for value in (hook_input, action_candidate, decision_candidate)
    ):
        _reject(rejections, BINDING_PROVENANCE_MISMATCH_REJECTED)
        checks.append("provenance source sections missing or not mappings")
        return

    source_tool_use_id = evidence.get("source_tool_use_id")
    tool_use_id = evidence.get("tool_use_id")
    action_id = evidence.get("action_id")
    expected_action_id = f"pretooluse:{source_tool_use_id}"

    expected_pairs = (
        (source_tool_use_id, tool_use_id),
        (action_id, expected_action_id),
        (hook_input.get("contract_version"), PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION),
        (hook_input.get("tool_name"), evidence.get("tool_name")),
        (hook_input.get("tool_use_id"), source_tool_use_id),
        (hook_input.get("tool_input_hash"), evidence.get("tool_input_hash")),
        (hook_input.get("tool_input_raw_stored"), False),
        (hook_input.get("trust_boundary"), evidence.get("trust_boundary")),
        (action_candidate.get("contract_version"), PHASE11C_2_TOOL_CALL_MAPPING_VERSION),
        (action_candidate.get("source_tool_name"), evidence.get("tool_name")),
        (action_candidate.get("source_tool_use_id"), source_tool_use_id),
        (action_candidate.get("action_id"), action_id),
        (
            action_candidate.get("candidate_action_type"),
            evidence.get("candidate_action_type"),
        ),
        (action_candidate.get("candidate_status"), evidence.get("candidate_status")),
        (
            decision_candidate.get("contract_version"),
            PHASE11C_3_HOOK_DECISION_ADAPTER_VERSION,
        ),
        (decision_candidate.get("source_tool_use_id"), source_tool_use_id),
        (decision_candidate.get("action_id"), action_id),
        (decision_candidate.get("decision_candidate"), evidence.get("decision_candidate")),
        (
            decision_candidate.get("decision_candidate_status"),
            evidence.get("decision_candidate_status"),
        ),
    )
    if all(left == right for left, right in expected_pairs):
        checks.append("source_tool_use_id/action_id provenance internally consistent")
        return

    _reject(rejections, BINDING_PROVENANCE_MISMATCH_REJECTED)
    checks.append("source_tool_use_id/action_id provenance mismatch rejected")


def _verify_decision_candidate(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    if evidence.get("decision_candidate") in HOOK_DECISION_CANDIDATES:
        checks.append("decision_candidate is allow/deny/ask/defer")
        return

    _reject(rejections, BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED)
    checks.append("decision_candidate mismatch rejected")


def _verify_reported_only_and_not_checked(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    if (
        evidence.get("reported_only_trusted_as_judgment_basis") is False
        and evidence.get("reported_only_is_judgment_basis") is False
    ):
        checks.append("reported_only remains non-judgment-basis")
    else:
        _reject(rejections, BINDING_REPORTED_ONLY_PROMOTION_REJECTED)
        checks.append("reported_only promotion rejected")

    if evidence.get("not_checked_is_pass") is False and not _has_not_checked_pass_claim(
        evidence
    ):
        checks.append("NOT_CHECKED remains non-PASS")
    else:
        _reject(rejections, BINDING_NOT_CHECKED_PROMOTION_REJECTED)
        checks.append("NOT_CHECKED promotion rejected")


def _verify_false_flags(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    if _all_false(evidence, _AUTHORITY_FALSE_FIELDS):
        checks.append("authority flags remain false")
    else:
        _reject(rejections, BINDING_AUTHORITY_FLAG_REJECTED)
        checks.append("authority flag promotion rejected")

    if _all_false(evidence, _RUNTIME_FALSE_FIELDS):
        checks.append("runtime flags remain false")
    else:
        _reject(rejections, BINDING_RUNTIME_FLAG_REJECTED)
        checks.append("runtime flag promotion rejected")

    if _all_false(evidence, _STORE_WRITE_FALSE_FIELDS):
        checks.append("store-write flags remain false")
    else:
        _reject(rejections, BINDING_STORE_WRITE_FLAG_REJECTED)
        checks.append("store-write flag promotion rejected")


def _verify_raw_tool_input_not_retained(
    evidence: Mapping[str, Any],
    rejections: list[str],
    checks: list[str],
) -> None:
    raw_key_paths = _raw_tool_input_paths(evidence)
    raw_retention_paths = _raw_retention_true_paths(evidence)
    if not raw_key_paths and not raw_retention_paths:
        checks.append("raw full tool_input is not retained by default")
        return

    _reject(rejections, BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED)
    if raw_key_paths:
        checks.append(f"raw tool_input retention rejected:{','.join(raw_key_paths)}")
    if raw_retention_paths:
        checks.append(f"raw value retention rejected:{','.join(raw_retention_paths)}")


def _verify_secret_fragments_absent(
    evidence: Mapping[str, Any],
    secret_fragments: tuple[str, ...],
    rejections: list[str],
    checks: list[str],
) -> None:
    serialized = json.dumps(
        _plain_json_data(evidence),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    retained = tuple(
        fragment for fragment in secret_fragments if fragment and fragment in serialized
    )
    if not retained:
        checks.append("known secret probe fragments absent from serialized record")
        return

    _reject(rejections, BINDING_SECRET_FRAGMENT_RETAINED_REJECTED)
    checks.append("known secret probe fragment retention rejected")


def _build_result(
    *,
    evidence: Mapping[str, Any] | None,
    recomputed_binding_hash: str | None,
    rejections: tuple[str, ...],
    checks: tuple[str, ...],
) -> HookEvidenceVerificationGateResult:
    if rejections:
        verification_output = HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE
    elif evidence and evidence.get("binding_status") == HOOK_EVIDENCE_BOUND:
        verification_output = VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE
    elif evidence and evidence.get("binding_status") == HOOK_EVIDENCE_BINDING_REJECTED:
        verification_output = REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE
    else:
        verification_output = HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE
        rejections = (*rejections, BINDING_STATUS_MISMATCH_REJECTED)

    return HookEvidenceVerificationGateResult(
        verification_version=PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION,
        completion_label=PHASE11C_5_COMPLETE_LABEL,
        verification_output=verification_output,
        verification_passed=not rejections,
        binding_verified=verification_output == VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        binding_rejected=verification_output
        == REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE,
        binding_id=_string_or_none(evidence, "binding_id"),
        binding_hash=_string_or_none(evidence, "binding_hash"),
        recomputed_binding_hash=recomputed_binding_hash,
        binding_status=_string_or_none(evidence, "binding_status"),
        rejection_codes=rejections,
        checks=checks,
    )


def _expect_equal(
    evidence: Mapping[str, Any],
    field_name: str,
    expected: Any,
    rejection_code: str,
    rejections: list[str],
    checks: list[str],
) -> None:
    if evidence.get(field_name) == expected:
        checks.append(f"{field_name} matched")
        return

    _reject(rejections, rejection_code)
    checks.append(f"{field_name} mismatch rejected")


def _binding_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {field_name: evidence[field_name] for field_name in _BINDING_PAYLOAD_FIELDS}


def _coerce_record(record: Mapping[str, Any] | HookEvidenceBinding | Any) -> dict[str, Any]:
    if isinstance(record, HookEvidenceBinding):
        return _plain_json_data(record.to_record())
    if isinstance(record, Mapping):
        return _plain_json_data(record)
    raise TypeError(type(record).__name__)


def _plain_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_data(nested) for key, nested in value.items()}
    if _is_sequence(value):
        return [_plain_json_data(nested) for nested in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(type(value).__name__)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _string_or_none(evidence: Mapping[str, Any] | None, field_name: str) -> str | None:
    if evidence is None:
        return None
    value = evidence.get(field_name)
    if isinstance(value, str):
        return value
    return None


def _all_false(evidence: Mapping[str, Any], field_names: tuple[str, ...]) -> bool:
    return all(evidence.get(field_name) is False for field_name in field_names)


def _raw_tool_input_paths(value: Any, path: str = "$") -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if key_text.lower() in _RAW_TOOL_INPUT_KEYS:
                paths.append(nested_path)
            paths.extend(_raw_tool_input_paths(nested, nested_path))
    elif _is_sequence(value):
        for index, nested in enumerate(value):
            paths.extend(_raw_tool_input_paths(nested, f"{path}[{index}]"))
    return tuple(paths)


def _raw_retention_true_paths(value: Any, path: str = "$") -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if key_text.lower() in _RAW_RETENTION_KEYS and nested is True:
                paths.append(nested_path)
            paths.extend(_raw_retention_true_paths(nested, nested_path))
    elif _is_sequence(value):
        for index, nested in enumerate(value):
            paths.extend(_raw_retention_true_paths(nested, f"{path}[{index}]"))
    return tuple(paths)


def _has_not_checked_pass_claim(value: Any, path: str = "$") -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if (
                "not_checked" in key_text.lower()
                and isinstance(nested, str)
                and nested.upper() == "PASS"
            ):
                return True
            if _has_not_checked_pass_claim(nested, nested_path):
                return True
    elif _is_sequence(value):
        return any(
            _has_not_checked_pass_claim(nested, f"{path}[{index}]")
            for index, nested in enumerate(value)
        )
    return False


def _reject(rejections: list[str], code: str) -> None:
    if code not in rejections:
        rejections.append(code)


__all__ = [
    "BINDING_AUTHORITY_FLAG_REJECTED",
    "BINDING_COMPLETION_LABEL_MISMATCH_REJECTED",
    "BINDING_DECISION_CANDIDATE_MISMATCH_REJECTED",
    "BINDING_FIELD_MISMATCH_REJECTED",
    "BINDING_HASH_MISMATCH_REJECTED",
    "BINDING_ID_MISMATCH_REJECTED",
    "BINDING_NOT_CHECKED_PROMOTION_REJECTED",
    "BINDING_PROVENANCE_MISMATCH_REJECTED",
    "BINDING_RAW_TOOL_INPUT_RETAINED_REJECTED",
    "BINDING_RECORD_SHAPE_REJECTED",
    "BINDING_REPORTED_ONLY_PROMOTION_REJECTED",
    "BINDING_RUNTIME_FLAG_REJECTED",
    "BINDING_SECRET_FRAGMENT_RETAINED_REJECTED",
    "BINDING_STATUS_MISMATCH_REJECTED",
    "BINDING_STORE_WRITE_FLAG_REJECTED",
    "HOLD_CURRENT_STATE_VERIFICATION_CANDIDATE",
    "HookEvidenceVerificationGateResult",
    "PHASE11C_5_COMPLETE_LABEL",
    "PHASE11C_5_HOOK_EVIDENCE_VERIFICATION_GATE_VERSION",
    "REJECTED_HOOK_EVIDENCE_BINDING_CANDIDATE",
    "VERIFIED_HOOK_EVIDENCE_BINDING_CANDIDATE",
    "build_hook_evidence_verification_gate_contract_evidence",
    "hook_evidence_binding_candidate_digest_from_mapping",
    "verify_hook_evidence_binding_candidate",
]
