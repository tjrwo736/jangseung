"""Phase 11-C-8 hook judgment alignment with existing Aegis gates.

This module is a pure adapter from validated Claude Code PreToolUse-shaped data
to existing Aegis judgment components. It does not install hooks, emit hook
output, execute tools, read secrets, write state, or grant authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.classify import Classification, classify_task, is_protected_path
from src.contracts import (
    CLEAN_CORE,
    GIT_WORKING_TREE,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    LOW,
    MEDIUM,
    NEEDS_USER_GATE,
    NOT_CHECKED,
    NOT_CHECKED_SOURCE,
    SAFE_DEFAULT,
)
from src.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard
from src.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    validate_claude_code_pretooluse_input,
)
from src.evidence.claude_code_tool_call_mapping import (
    BASH_DANGEROUS,
    BASH_NOT_CHECKED,
    DENY_CANDIDATE,
    EDIT_FILE,
    READ_REPO,
    STRUCTURED_ACTION_CANDIDATE,
    UNKNOWN_TOOL,
    extract_apply_patch_targets,
    extract_bash_write_delete_targets,
    map_pretooluse_input_to_structured_action_candidate,
)
from src.evidence.claude_code_tool_call_mapping import RUN_COMMAND as MAPPING_RUN_COMMAND
from src.evidence.claude_code_tool_call_mapping import WRITE_FILE as MAPPING_WRITE_FILE
from src.evidence.hook_decision_adapter import ALLOW, ASK, DEFER, DENY
from src.evidence.mediated_repo_boundary_write_path import resolve_repo_boundary_path
from src.evidence.structured_action_capabilities import (
    CAPABILITY_DENIED,
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
    FUTURE_GATE_REQUIRED,
    NOT_IMPLEMENTED_REJECTED,
    REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
    SCOPE_LIMIT_REJECTED,
    UNKNOWN_CAPABILITY_REJECTED,
    evaluate_action_capabilities,
)
from src.evidence.structured_actions import (
    NOOP,
    REQUEST_REPO_READ,
    RUN_COMMAND,
    WRITE_FILE,
)
from src.law import apply_law

PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION = (
    "phase11c_8_hook_judgment_engine_alignment_v0"
)
PHASE11C_8_COMPLETE_LABEL = (
    "PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_COMPLETE_NOT_INSTALLED_NOT_LIVE_RUNTIME"
)

ENGINE_ALLOWED_CAPABILITY_RESULTS = frozenset(
    {
        CAPABILITY_GATE_ALLOWED,
        CAPABILITY_GATE_LIMITED_ALLOWED,
    }
)
ENGINE_DENY_CAPABILITY_RESULTS = frozenset(
    {
        CAPABILITY_DENIED,
        FUTURE_GATE_REQUIRED,
        NOT_IMPLEMENTED_REJECTED,
        UNKNOWN_CAPABILITY_REJECTED,
        REPORTED_ONLY_CAPABILITY_GRANT_REJECTED,
        SCOPE_LIMIT_REJECTED,
    }
)

HOOK_DECISION_STRENGTH = MappingProxyType({ALLOW: 0, ASK: 1, DEFER: 2, DENY: 3})
ENGINE_BASIS_SOURCES = (
    "src.classify.classify_task",
    "src.classify.is_protected_path",
    "src.law.apply_law",
    "src.evidence.structured_action_capabilities.evaluate_action_capabilities",
    "src.evidence.b1_aeg_integrity_guard.decide_b1_aeg_integrity_guard",
    "src.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path",
)

# WRITE_FILE/RUN_COMMAND capability policy answers "may Aegis itself execute
# this action" (always denied under the 11-B propose-only executor model).
# That is a different question from "should the hook allow this substrate
# tool call", which must be judged by the target path/command risk
# (is_protected_path, the .aeg state-dir guard, the dangerous-Bash gate, and
# classify/law), not by reusing Aegis's own self-execution capability denial
# as if it answered the hook question. These two action types are therefore
# excluded from driving the hook decision via the capability gate; the
# capability gate result is still computed and recorded in evidence for
# transparency, but it is not treated as hook judgment basis for them.
_SELF_EXECUTION_CAPABILITY_ACTION_TYPES_NOT_HOOK_JUDGMENT_BASIS = frozenset(
    {MAPPING_WRITE_FILE, EDIT_FILE, MAPPING_RUN_COMMAND}
)
_WRITE_LIKE_CANDIDATE_ACTION_TYPES = frozenset({MAPPING_WRITE_FILE, EDIT_FILE})
_WRITE_LIKE_TOOL_NAMES = frozenset({"Write", "Edit", "apply_patch"})

# Read/Write/Edit of a repo-internal, non-protected file that the existing
# engine classified as a definite LOW or MEDIUM change is "clearly safe normal
# work" and is allowed so the hook does not obstruct ordinary safe operations.
# Everything ambiguous is deliberately excluded from this set:
#  - protected paths / dangerous Bash / repo-external / traversal already
#    returned DENY before this check;
#  - Bash maps to HOLD_CURRENT_STATE_CANDIDATE with impact NOT_CHECKED, so it is
#    never a STRUCTURED_ACTION_CANDIDATE and never clearly-safe -> ask/defer;
#  - a NOT_CHECKED / NOT_CHECKED_NO_MUTATION impact (unclassifiable / unknown
#    source) is not in the safe impact set -> ask/defer.
_CLEARLY_SAFE_FILE_ACTION_TYPES = frozenset(
    {READ_REPO, MAPPING_WRITE_FILE, EDIT_FILE}
)
_CLEARLY_SAFE_IMPACT_RISKS = frozenset({LOW, MEDIUM})
_CLEARLY_SAFE_RISK_LEVELS = frozenset({LOW, MEDIUM})

_REPORTED_ONLY_KEYS = frozenset(
    {
        "reported_only",
        "report_only",
        "self_report",
        "self_reported",
        "self_reported_allow",
        "self_reported_decision",
    }
)
_REPORTED_ONLY_VALUE_KEYS = frozenset({"basis", "source", "grant_source"})


@dataclass(frozen=True)
class HookJudgmentEngineRequest:
    tool_name: str | None
    tool_use_id: str | None
    target_paths: tuple[str, ...]
    command_present: bool
    raw_hook_input_hash: str
    raw_hook_input_hash_algorithm: str = "sha256_canonical_json_v0"
    raw_hook_input_stored: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_paths", tuple(self.target_paths))

    def to_record(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "target_paths": self.target_paths,
            "command_present": self.command_present,
            "raw_hook_input_hash": self.raw_hook_input_hash,
            "raw_hook_input_hash_algorithm": self.raw_hook_input_hash_algorithm,
            "raw_hook_input_stored": self.raw_hook_input_stored,
        }


@dataclass(frozen=True)
class HookJudgmentEngineDecision:
    decision_id: str
    decision_hash: str
    contract_version: str
    completion_label: str
    request: HookJudgmentEngineRequest
    engine_decision: str
    hook_decision: str
    decision_reasons: tuple[str, ...]
    engine_decision_basis: Mapping[str, Any]
    engine_basis_sources: tuple[str, ...]
    hook_decision_matches_or_is_stricter_than_engine: bool
    protected_path_policy_duplicated_in_hook: bool = False
    hook_policy_divergence_allowed: bool = False
    reported_only_trusted_as_judgment_basis: bool = False
    not_checked_is_allow: bool = False
    unclassified_bash_is_allow: bool = False
    adapter_output_is_actual_hook_response: bool = False
    hook_command_implemented: bool = False
    hook_installation_implemented: bool = False
    claude_code_execution_performed: bool = False
    real_hook_response_emitted: bool = False
    stdout_stderr_hook_output_written: bool = False
    provider_model_network_implemented: bool = False
    api_key_env_secret_loading_implemented: bool = False
    store_write_binding_implemented: bool = False
    aeg_write_performed: bool = False
    write_authority_granted: bool = False
    public_release_performed: bool = False
    main_merge_performed: bool = False
    safe_default: str = SAFE_DEFAULT
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_reasons", tuple(self.decision_reasons))
        object.__setattr__(self, "engine_basis_sources", tuple(self.engine_basis_sources))
        object.__setattr__(
            self,
            "engine_decision_basis",
            _freeze_value(self.engine_decision_basis),
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            **_plain_json_data(_decision_payload(self)),
        }


def judge_pretooluse_with_aeg_engine(
    raw_hook_input: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> HookJudgmentEngineDecision:
    """Return a hook decision candidate aligned with existing Aegis gates."""

    validation = validate_claude_code_pretooluse_input(raw_hook_input)
    hook_input = validation.hook_input
    ignored_reported_only_fields = _reported_only_fields(raw_hook_input)

    if not validation.valid or hook_input is None:
        request = _build_request(raw_hook_input, hook_input)
        basis = {
            "input_validation": _validation_record(validation),
            "ignored_reported_only_fields": ignored_reported_only_fields,
            "reported_only_trusted_as_judgment_basis": False,
            "not_checked_is_allow": False,
            "safe_default": SAFE_DEFAULT,
        }
        return _build_decision(
            request=request,
            engine_decision=DEFER,
            hook_decision=DEFER,
            reasons=(
                "pretooluse_input_invalid_or_unsupported",
                "invalid_unknown_or_unsupported_tool_maps_to_defer",
                "safe_default_hold_current_state",
            ),
            basis=basis,
        )

    # Claude Code sends tool_input file paths as absolute paths. Normalize a
    # repo-internal absolute path to its repo-relative form so the existing
    # engine judges it correctly; a repo-external or traversal-escaping
    # absolute path is left absolute so the existing scope defense still
    # rejects it. This rewrites the input the engine sees; it does not change
    # any engine logic.
    hook_input, path_normalization = _normalize_hook_input_repo_paths(
        hook_input, repo_root
    )
    request = _build_request(raw_hook_input, hook_input)

    action_candidate = map_pretooluse_input_to_structured_action_candidate(hook_input)
    classification = _classify_hook_target(hook_input, request.target_paths)
    law_result = apply_law(classification)
    engine_action = _engine_action_for_hook_input(hook_input, classification.risk_level)
    capability_result = evaluate_action_capabilities(engine_action, repo_root=repo_root)
    aeg_guard_records = _aeg_guard_records(repo_root, request.target_paths)
    repo_boundary_records = _repo_boundary_records(repo_root, request.target_paths)
    protected_path_gate = _protected_path_gate(request.target_paths)
    bash_target_gate = _bash_write_delete_target_gate(hook_input, repo_root)
    dangerous_bash_gate = {
        "risk_status": action_candidate.risk_status,
        "dangerous_bash": action_candidate.risk_status == BASH_DANGEROUS,
        "unclassified_bash": action_candidate.risk_status == BASH_NOT_CHECKED,
        "unclassified_bash_is_allow": False,
        "reasons": action_candidate.reasons,
    }

    basis = {
        "input_validation": _validation_record(validation),
        "tool_call_mapping": {
            "candidate_status": action_candidate.candidate_status,
            "candidate_action_type": action_candidate.candidate_action_type,
            "risk_status": action_candidate.risk_status,
            "declared_risk": action_candidate.declared_risk,
            "reasons": action_candidate.reasons,
            "protected_path_policy_source": "src.classify.is_protected_path",
            "protected_path_policy_duplicated_in_hook": False,
        },
        "classification": classification.as_dict(),
        "law": law_result.as_dict(),
        "capability_gate": _capability_record(capability_result),
        "protected_path_gate": protected_path_gate,
        "aeg_guard": aeg_guard_records,
        "repo_boundary_gate": repo_boundary_records,
        "path_normalization": path_normalization,
        "bash_target_gate": bash_target_gate,
        "dangerous_bash_gate": dangerous_bash_gate,
        "ignored_reported_only_fields": ignored_reported_only_fields,
        "reported_only_trusted_as_judgment_basis": False,
        "not_checked_is_allow": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }

    engine_decision, reasons = _collapse_engine_decision(
        candidate_action_type=action_candidate.candidate_action_type,
        law_status=law_result.status,
        capability_gate_result=capability_result.gate_result,
        action_candidate_status=action_candidate.candidate_status,
        action_risk_status=action_candidate.risk_status,
        aeg_guard_records=aeg_guard_records,
        repo_boundary_records=repo_boundary_records,
        classification=classification,
        bash_target_gate=bash_target_gate,
    )
    hook_decision = engine_decision
    return _build_decision(
        request=request,
        engine_decision=engine_decision,
        hook_decision=hook_decision,
        reasons=reasons,
        basis=basis,
    )


def build_hook_judgment_engine_alignment_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION,
        "completion_label": PHASE11C_8_COMPLETE_LABEL,
        "engine_basis_sources": ENGINE_BASIS_SOURCES,
        "protected_path_policy_source": "src.classify.is_protected_path",
        "structured_action_capability_gate_source": (
            "src.evidence.structured_action_capabilities.evaluate_action_capabilities"
        ),
        "law_gate_source": "src.law.apply_law",
        "classification_source": "src.classify.classify_task",
        "aeg_guard_source": (
            "src.evidence.b1_aeg_integrity_guard.decide_b1_aeg_integrity_guard"
        ),
        "repo_boundary_gate_source": (
            "src.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path"
        ),
        "hook_decision_matches_or_is_stricter_than_engine": True,
        "protected_path_policy_duplicated_in_hook": False,
        "hook_policy_divergence_allowed": False,
        "dangerous_bash_safety_net_present": True,
        "unclassified_bash_is_allow": False,
        "write_edit_judgment_basis": "target_path_risk_via_is_protected_path_aeg_guard_repo_boundary",
        "run_command_judgment_basis": "dangerous_bash_gate_and_tool_call_mapping_deny_candidate",
        "write_edit_capability_gate_used_as_hook_judgment_basis": False,
        "run_command_capability_gate_used_as_hook_judgment_basis": False,
        "read_capability_gate_used_as_hook_judgment_basis": True,
        "aegis_self_write_file_capability_unchanged_and_denied": True,
        "aegis_self_run_command_capability_unchanged_and_denied": True,
        "bash_write_delete_target_protected_or_out_of_scope_maps_to_deny": True,
        "bash_target_parsing_is_structural_shlex_not_string_match": True,
        "bash_unparseable_target_maps_to_ask_defer_not_deny_not_allow": True,
        "bash_target_gate_covers": (
            "redirect",
            "tee",
            "cp",
            "mv",
            "rm",
            "dd_of",
            "truncate",
            "ln",
        ),
        "apply_patch_tool_supported": True,
        "apply_patch_maps_to_write_file_judgment": True,
        "apply_patch_targets_reuse_existing_path_gates": True,
        "apply_patch_target_parsing_is_structural_directive_parse": True,
        "apply_patch_unparseable_maps_to_deny": True,
        "clearly_safe_normal_file_operation_maps_to_allow": True,
        "clearly_safe_requires_definite_low_or_medium_impact_classification": True,
        "clearly_safe_file_action_types": tuple(sorted(_CLEARLY_SAFE_FILE_ACTION_TYPES)),
        "clearly_safe_impact_risks": tuple(sorted(_CLEARLY_SAFE_IMPACT_RISKS)),
        "not_checked_impact_maps_to_allow": False,
        "unclassified_bash_maps_to_allow": False,
        "ambiguous_input_maps_to_allow": False,
        "reported_only_trusted_as_judgment_basis": False,
        "not_checked_is_allow": False,
        "adapter_output_is_actual_hook_response": False,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "provider_model_network_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "store_write_binding_implemented": False,
        "aeg_write_performed": False,
        "write_authority_granted": False,
        "public_release_performed": False,
        "main_merge_performed": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }


# tool_input fields that carry a repo file path for Read/Write/Edit.
_PATH_TOOL_INPUT_FIELDS = ("file_path",)


def _normalize_hook_input_repo_paths(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
) -> tuple[ClaudeCodePreToolUseInput, tuple[Mapping[str, Any], ...]]:
    """Rewrite repo-internal absolute file paths in tool_input to repo-relative.

    Repo-external, traversal-escaping, symlink-escaping, and Windows-style
    absolute paths are left unchanged so the existing scope defense still
    rejects them. Non-absolute paths are also left unchanged so existing
    relative-path behaviour (including relative traversal rejection) is
    preserved.
    """

    tool_input = dict(hook_input.tool_input)
    records: list[Mapping[str, Any]] = []
    changed = False
    for field_name in _PATH_TOOL_INPUT_FIELDS:
        value = tool_input.get(field_name)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized, record = _normalize_repo_internal_absolute_path(value, repo_root)
        records.append({"field": field_name, **record})
        if normalized != value:
            tool_input[field_name] = normalized
            changed = True

    if not changed:
        return hook_input, tuple(records)
    return replace(hook_input, tool_input=tool_input), tuple(records)


def _normalize_repo_internal_absolute_path(
    path_value: str,
    repo_root: str | Path,
) -> tuple[str, dict[str, Any]]:
    stripped = path_value.strip()

    if _looks_like_windows_absolute_path(stripped):
        # Not resolvable as a repo-internal POSIX path here; leave it so the
        # mapping's absolute-path deny-candidate rule rejects it.
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": True,
            "in_repo": False,
            "action": "windows_absolute_kept_for_scope_rejection",
        }

    if not stripped.startswith("/"):
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": False,
            "in_repo": None,
            "action": "non_absolute_unchanged",
        }

    try:
        resolution = resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=stripped,
        )
    except Exception:  # noqa: BLE001 - normalization failure keeps path absolute (fail-closed).
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": True,
            "in_repo": None,
            "action": "normalization_error_kept_absolute_fail_closed",
        }

    if not resolution.target_under_repo:
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": True,
            "in_repo": False,
            "action": "outside_repo_kept_absolute_for_scope_rejection",
        }

    try:
        relative = Path(resolution.canonical_target).relative_to(
            Path(resolution.repo_root)
        )
        normalized = relative.as_posix() or "."
    except Exception:  # noqa: BLE001 - keep absolute on any relativization error.
        return path_value, {
            "original": path_value,
            "normalized": path_value,
            "was_absolute": True,
            "in_repo": True,
            "action": "relative_computation_error_kept_absolute_fail_closed",
        }

    return normalized, {
        "original": path_value,
        "normalized": normalized,
        "was_absolute": True,
        "in_repo": True,
        "action": "repo_internal_absolute_normalized_to_relative",
    }


def _build_request(
    raw_hook_input: Mapping[str, Any],
    hook_input: ClaudeCodePreToolUseInput | None,
) -> HookJudgmentEngineRequest:
    tool_input = hook_input.tool_input if hook_input is not None else {}
    return HookJudgmentEngineRequest(
        tool_name=hook_input.tool_name if hook_input is not None else _string_or_none(raw_hook_input.get("tool_name")),
        tool_use_id=(
            hook_input.tool_use_id
            if hook_input is not None
            else _string_or_none(raw_hook_input.get("tool_use_id"))
        ),
        target_paths=_target_paths(hook_input),
        command_present=isinstance(tool_input.get("command"), str),
        raw_hook_input_hash=_sha256_json(raw_hook_input),
    )


def _target_paths(hook_input: ClaudeCodePreToolUseInput | None) -> tuple[str, ...]:
    if hook_input is None:
        return tuple()
    if hook_input.tool_name in {"Read", "Write", "Edit"}:
        file_path = hook_input.tool_input.get("file_path")
        if isinstance(file_path, str) and file_path.strip():
            return (file_path,)
    if hook_input.tool_name == "apply_patch":
        command = hook_input.tool_input.get("command")
        if isinstance(command, str) and command.strip():
            extraction = extract_apply_patch_targets(command)
            if not extraction.parse_ambiguous:
                return extraction.target_paths
    return tuple()


def _classify_hook_target(
    hook_input: ClaudeCodePreToolUseInput,
    target_paths: tuple[str, ...],
):
    if hook_input.tool_name == "Bash":
        return classify_task(
            "run command through Claude Code Bash tool",
            changed_files=[],
            changed_files_source=NOT_CHECKED_SOURCE,
            no_mutation=False,
        )

    intent_text = "update documentation"
    if hook_input.tool_name == "Read":
        intent_text = "read documentation"
    elif hook_input.tool_name == "apply_patch":
        intent_text = "apply patch file update"
    return classify_task(
        intent_text,
        changed_files=target_paths,
        changed_files_source=GIT_WORKING_TREE if target_paths else NOT_CHECKED_SOURCE,
        no_mutation=hook_input.tool_name == "Read",
    )


def _engine_action_for_hook_input(
    hook_input: ClaudeCodePreToolUseInput,
    declared_risk: str,
) -> dict[str, Any]:
    target_paths = _target_paths(hook_input)
    if hook_input.tool_name == "Read":
        action_type = REQUEST_REPO_READ
        capabilities = ["read_repo"]
    elif hook_input.tool_name in _WRITE_LIKE_TOOL_NAMES:
        action_type = WRITE_FILE
        capabilities = ["write_file"]
    elif hook_input.tool_name == "Bash":
        action_type = RUN_COMMAND
        capabilities = ["run_command"]
    else:
        action_type = NOOP
        capabilities = ["noop"]

    return {
        "action_type": action_type,
        "action_id": f"phase11c8:{hook_input.tool_use_id}",
        "declared_intent": f"Claude Code {hook_input.tool_name} PreToolUse judgment",
        "declared_risk": declared_risk,
        "capability_requirements": capabilities,
        "target_scope": {
            "repo_relative": all(_repo_relative_candidate(path) for path in target_paths),
            "target_paths": list(target_paths),
        },
        "payload": {
            "request_kind": "claude_code_pretooluse_engine_judgment",
            "tool_name": hook_input.tool_name,
        },
    }


def _bash_write_delete_target_gate(
    hook_input: ClaudeCodePreToolUseInput,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Deny a Bash command whose structurally-parsed write/delete target is a
    protected path or outside the repo. Fail-closed: if the command is not
    precisely parseable (substitution, nested shell, ...), no target is
    claimed and the decision is left to the existing ask/defer path -- never
    promoted to allow, and never falsely claimed as denied."""

    if hook_input.tool_name != "Bash":
        return {
            "applicable": False,
            "deny": False,
            "parse_ambiguous": False,
            "targets": tuple(),
            "deny_targets": tuple(),
            "reason": "not_a_bash_tool_call",
        }

    command = hook_input.tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return {
            "applicable": True,
            "deny": False,
            "parse_ambiguous": True,
            "targets": tuple(),
            "deny_targets": tuple(),
            "reason": "missing_or_empty_command",
        }

    extraction = extract_bash_write_delete_targets(command)
    if extraction.parse_ambiguous:
        return {
            "applicable": True,
            "deny": False,
            "parse_ambiguous": True,
            "targets": tuple(),
            "deny_targets": tuple(),
            "reason": (
                "bash_target_unparseable_maps_to_ask_defer_not_allow_not_falsely_denied:"
                f"{extraction.reason}"
            ),
        }

    deny_targets: list[dict[str, str]] = []
    for target in extraction.write_delete_targets:
        kind = _classify_bash_target(target, repo_root)
        if kind in ("out_of_scope", "protected_path", "protected_state_dir"):
            deny_targets.append({"target": target, "kind": kind})

    return {
        "applicable": True,
        "deny": bool(deny_targets),
        "parse_ambiguous": False,
        "targets": extraction.write_delete_targets,
        "deny_targets": tuple(deny_targets),
        "protected_path_policy_source": "src.classify.is_protected_path",
        "repo_boundary_policy_source": (
            "src.evidence.mediated_repo_boundary_write_path.resolve_repo_boundary_path"
        ),
        "reason": extraction.reason,
    }


def _classify_bash_target(target: str, repo_root: str | Path) -> str:
    try:
        resolution = resolve_repo_boundary_path(repo_root=repo_root, submitted_target=target)
    except Exception:  # noqa: BLE001 - unresolvable target -> do not deny, leave to ask/defer.
        return "unresolvable_ambiguous"

    if resolution.target_outside_repo:
        return "out_of_scope"

    try:
        relative = Path(resolution.canonical_target).relative_to(
            Path(resolution.repo_root)
        ).as_posix()
    except Exception:  # noqa: BLE001 - keep fail-closed to ask/defer, not a claimed deny.
        return "unresolvable_ambiguous"

    if is_protected_path(relative):
        return "protected_path"

    try:
        guard = decide_b1_aeg_integrity_guard(repo_root=repo_root, submitted_path=target)
    except Exception:  # noqa: BLE001
        return "unresolvable_ambiguous"
    if getattr(guard, "protected_target", False):
        return "protected_state_dir"

    return "safe_in_repo"


def _is_clearly_safe_normal_file_operation(
    *,
    candidate_action_type: str,
    action_candidate_status: str,
    classification: Classification,
    repo_boundary_records: tuple[Mapping[str, Any], ...],
) -> bool:
    """Return True only for a Read/Write/Edit of a repo-internal, non-protected
    file that the existing engine classified as a definite LOW/MEDIUM change.

    Fail-closed: anything ambiguous (Bash, NOT_CHECKED impact, non-candidate
    mapping status, or any out-of-repo boundary record) returns False and is
    left to the ask/defer/deny paths.
    """

    if candidate_action_type not in _CLEARLY_SAFE_FILE_ACTION_TYPES:
        return False
    if action_candidate_status != STRUCTURED_ACTION_CANDIDATE:
        return False
    if classification.risk_level not in _CLEARLY_SAFE_RISK_LEVELS:
        return False
    if classification.impact_risk not in _CLEARLY_SAFE_IMPACT_RISKS:
        return False
    if not repo_boundary_records:
        return False
    if any(record.get("target_outside_repo") is True for record in repo_boundary_records):
        return False
    if not all(record.get("target_under_repo") is True for record in repo_boundary_records):
        return False
    return True


def _collapse_engine_decision(
    *,
    candidate_action_type: str,
    law_status: str,
    capability_gate_result: str,
    action_candidate_status: str,
    action_risk_status: str,
    aeg_guard_records: tuple[Mapping[str, Any], ...],
    repo_boundary_records: tuple[Mapping[str, Any], ...],
    classification: Classification,
    bash_target_gate: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if any(record.get("target_outside_repo") is True for record in repo_boundary_records):
        reasons.append("repo_boundary_gate_denies_outside_repo_target")
    if any(record.get("protected_target") is True for record in aeg_guard_records):
        reasons.append("aeg_integrity_guard_denies_state_dir_target")
    if action_candidate_status == DENY_CANDIDATE:
        reasons.append("tool_call_mapping_deny_candidate")
    if action_risk_status == BASH_DANGEROUS:
        reasons.append("dangerous_bash_gate_denies_command")
    if bash_target_gate.get("deny") is True:
        reasons.append("bash_write_delete_target_protected_or_out_of_scope")

    # WRITE_FILE/RUN_COMMAND capability status reflects Aegis's own
    # propose-only self-execution policy (11-B), not the risk of the
    # substrate's tool call target/command. It is excluded from hook
    # judgment for those two action types; the target-path risk gates above
    # (tool_call_mapping deny-candidate, aeg guard, repo boundary) and the
    # dangerous-Bash gate already carry that judgment instead.
    capability_gate_is_hook_judgment_basis = (
        candidate_action_type
        not in _SELF_EXECUTION_CAPABILITY_ACTION_TYPES_NOT_HOOK_JUDGMENT_BASIS
    )
    if capability_gate_is_hook_judgment_basis and capability_gate_result in ENGINE_DENY_CAPABILITY_RESULTS:
        reasons.append(f"capability_gate_denies:{capability_gate_result}")
    if law_status == NEEDS_USER_GATE:
        reasons.append("law_requires_user_gate_hook_uses_deny_safe_default")

    if reasons:
        return DENY, tuple((*reasons, "hook_decision_matches_or_is_stricter_than_engine"))

    # Clearly-safe normal work: a repo-internal, non-protected Read/Write/Edit
    # that the existing engine classified as a definite LOW/MEDIUM change is
    # allowed so the hook does not obstruct ordinary safe operations. This
    # promotion is based only on the existing engine's classification; it never
    # applies to Bash, to ambiguous / NOT_CHECKED-impact inputs, or to anything
    # that produced a deny reason above.
    if _is_clearly_safe_normal_file_operation(
        candidate_action_type=candidate_action_type,
        action_candidate_status=action_candidate_status,
        classification=classification,
        repo_boundary_records=repo_boundary_records,
    ):
        return ALLOW, (
            "engine_classified_normal_non_protected_in_repo_file_operation_as_safe",
            f"clearly_safe_impact={classification.impact_risk}_risk={classification.risk_level}",
            "clearly_safe_normal_work_maps_to_allow",
            "ambiguous_not_checked_or_unclassified_never_reaches_this_branch",
            "hook_decision_matches_engine_decision",
        )

    if (
        capability_gate_is_hook_judgment_basis
        and capability_gate_result in ENGINE_ALLOWED_CAPABILITY_RESULTS
        and law_status == CLEAN_CORE
    ):
        return ALLOW, (
            "classification_law_and_capability_gate_allow_read_only_candidate",
            "hook_decision_matches_engine_decision",
        )

    if (
        candidate_action_type in _WRITE_LIKE_CANDIDATE_ACTION_TYPES
        and action_candidate_status == STRUCTURED_ACTION_CANDIDATE
    ):
        return ASK, (
            "write_or_edit_judgment_basis_is_target_path_risk_not_capability_gate",
            "normal_target_path_maps_to_ask_candidate",
            "aegis_self_write_file_capability_remains_denied_and_unrelated_to_hook_judgment",
            "hook_decision_matches_or_is_stricter_than_engine",
        )

    if action_risk_status in {BASH_NOT_CHECKED, UNKNOWN_TOOL} or law_status == NOT_CHECKED:
        return DEFER, (
            "not_checked_or_unclassified_maps_to_defer",
            "not_checked_unknown_or_unclassified_never_maps_to_allow",
            "safe_default_hold_current_state",
            "hook_decision_matches_or_is_stricter_than_engine",
        )

    return DEFER, (
        "engine_basis_not_clean_maps_to_defer",
        "safe_default_hold_current_state",
        "hook_decision_matches_or_is_stricter_than_engine",
    )


def _build_decision(
    *,
    request: HookJudgmentEngineRequest,
    engine_decision: str,
    hook_decision: str,
    reasons: Sequence[str],
    basis: Mapping[str, Any],
) -> HookJudgmentEngineDecision:
    payload = {
        "contract_version": PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION,
        "completion_label": PHASE11C_8_COMPLETE_LABEL,
        "request": request.to_record(),
        "engine_decision": engine_decision,
        "hook_decision": hook_decision,
        "decision_reasons": tuple(reasons),
        "engine_decision_basis": basis,
        "engine_basis_sources": ENGINE_BASIS_SOURCES,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }
    decision_hash = _sha256_json(payload)
    return HookJudgmentEngineDecision(
        decision_id=f"phase11c8-hook-judgment:{decision_hash}",
        decision_hash=decision_hash,
        contract_version=PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION,
        completion_label=PHASE11C_8_COMPLETE_LABEL,
        request=request,
        engine_decision=engine_decision,
        hook_decision=hook_decision,
        decision_reasons=tuple(reasons),
        engine_decision_basis=basis,
        engine_basis_sources=ENGINE_BASIS_SOURCES,
        hook_decision_matches_or_is_stricter_than_engine=(
            HOOK_DECISION_STRENGTH[hook_decision]
            >= HOOK_DECISION_STRENGTH[engine_decision]
        ),
    )


def _protected_path_gate(target_paths: tuple[str, ...]) -> dict[str, Any]:
    protected_paths = tuple(path for path in target_paths if is_protected_path(path))
    return {
        "policy_source": "src.classify.is_protected_path",
        "target_paths": target_paths,
        "protected_paths": protected_paths,
        "protected_path_detected": bool(protected_paths),
        "protected_path_policy_duplicated_in_hook": False,
    }


def _aeg_guard_records(
    repo_root: str | Path,
    target_paths: tuple[str, ...],
) -> tuple[Mapping[str, Any], ...]:
    records = []
    for path in target_paths:
        records.append(
            decide_b1_aeg_integrity_guard(
                repo_root=repo_root,
                submitted_path=path,
            ).to_record()
        )
    return tuple(records)


def _repo_boundary_records(
    repo_root: str | Path,
    target_paths: tuple[str, ...],
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        resolve_repo_boundary_path(
            repo_root=repo_root,
            submitted_target=path,
        ).to_record()
        for path in target_paths
    )


def _validation_record(validation: Any) -> dict[str, Any]:
    return {
        "valid": validation.valid,
        "status": validation.status,
        "reasons": validation.reasons,
        "tool_support_status": validation.tool_support_status,
        "ignored_untrusted_fields": validation.ignored_untrusted_fields,
        "unsupported_unknown_or_not_checked_is_pass": (
            validation.unsupported_unknown_or_not_checked_is_pass
        ),
        "hook_input_trusted_as_decision": validation.hook_input_trusted_as_decision,
        "hook_input_trusted_as_capability_grant": (
            validation.hook_input_trusted_as_capability_grant
        ),
    }


def _capability_record(capability_result: Any) -> dict[str, Any]:
    return {
        "action_type": capability_result.action_type,
        "required_capabilities": capability_result.required_capabilities,
        "capability_decisions": tuple(
            {
                "capability_name": decision.capability_name,
                "status": decision.status,
                "allowed": decision.allowed,
                "reason": decision.reason,
            }
            for decision in capability_result.capability_decisions
        ),
        "gate_result": capability_result.gate_result,
        "gate_reason": capability_result.gate_reason,
        "schema_validation_status": capability_result.schema_validation_status,
        "execution_allowed": capability_result.execution_allowed,
        "mutation_allowed": capability_result.mutation_allowed,
        "write_authority_granted": capability_result.write_authority_granted,
        "live_executor_ready": capability_result.live_executor_ready,
        "live_executor_authority": capability_result.live_executor_authority,
    }


def _repo_relative_candidate(path: str) -> bool:
    stripped = path.strip()
    if not stripped:
        return False
    if stripped.startswith("/") or _looks_like_windows_absolute_path(stripped):
        return False
    return ".." not in _path_parts(stripped)


def _path_parts(path_value: str) -> tuple[str, ...]:
    normalized = "/".join(path_value.split("\\"))
    return tuple(part for part in normalized.split("/") if part and part != ".")


def _looks_like_windows_absolute_path(path_value: str) -> bool:
    return (
        len(path_value) >= 3
        and path_value[1] == ":"
        and path_value[2] in ("/", "\\")
        and path_value[0].isalpha()
    )


def _reported_only_fields(value: Any) -> tuple[str, ...]:
    fields: list[str] = []
    _scan_reported_only(value, "raw_hook_input", fields)
    return tuple(sorted(dict.fromkeys(fields)))


def _scan_reported_only(value: Any, location: str, fields: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(str(key))
            nested_location = f"{location}.{key}"
            if normalized_key in _REPORTED_ONLY_KEYS:
                fields.append(nested_location)
            if normalized_key in _REPORTED_ONLY_VALUE_KEYS and nested == "reported_only":
                fields.append(nested_location)
            _scan_reported_only(nested, nested_location, fields)
        return
    if _is_sequence(value):
        for index, nested in enumerate(value):
            _scan_reported_only(nested, f"{location}[{index}]", fields)


def _normalize_key(value: str) -> str:
    normalized_spaces = "_".join(value.strip().lower().split())
    return "_".join(normalized_spaces.split("-"))


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _decision_payload(record: HookJudgmentEngineDecision) -> dict[str, Any]:
    return {
        "contract_version": record.contract_version,
        "completion_label": record.completion_label,
        "request": record.request.to_record(),
        "engine_decision": record.engine_decision,
        "hook_decision": record.hook_decision,
        "decision_reasons": record.decision_reasons,
        "engine_decision_basis": record.engine_decision_basis,
        "engine_basis_sources": record.engine_basis_sources,
        "hook_decision_matches_or_is_stricter_than_engine": (
            record.hook_decision_matches_or_is_stricter_than_engine
        ),
        "protected_path_policy_duplicated_in_hook": (
            record.protected_path_policy_duplicated_in_hook
        ),
        "hook_policy_divergence_allowed": record.hook_policy_divergence_allowed,
        "reported_only_trusted_as_judgment_basis": (
            record.reported_only_trusted_as_judgment_basis
        ),
        "not_checked_is_allow": record.not_checked_is_allow,
        "unclassified_bash_is_allow": record.unclassified_bash_is_allow,
        "adapter_output_is_actual_hook_response": record.adapter_output_is_actual_hook_response,
        "hook_command_implemented": record.hook_command_implemented,
        "hook_installation_implemented": record.hook_installation_implemented,
        "claude_code_execution_performed": record.claude_code_execution_performed,
        "real_hook_response_emitted": record.real_hook_response_emitted,
        "stdout_stderr_hook_output_written": record.stdout_stderr_hook_output_written,
        "provider_model_network_implemented": record.provider_model_network_implemented,
        "api_key_env_secret_loading_implemented": (
            record.api_key_env_secret_loading_implemented
        ),
        "store_write_binding_implemented": record.store_write_binding_implemented,
        "aeg_write_performed": record.aeg_write_performed,
        "write_authority_granted": record.write_authority_granted,
        "public_release_performed": record.public_release_performed,
        "main_merge_performed": record.main_merge_performed,
        "safe_default": record.safe_default,
        "live_executor_authority": record.live_executor_authority,
    }


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(nested) for key, nested in value.items()})
    if isinstance(value, tuple):
        return tuple(_freeze_value(nested) for nested in value)
    if isinstance(value, list):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _plain_json_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_data(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return tuple(_plain_json_data(nested) for nested in value)
    if isinstance(value, list):
        return [_plain_json_data(nested) for nested in value]
    return value


def _sha256_json(payload: Any) -> str:
    canonical = json.dumps(
        _plain_json_data(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ENGINE_BASIS_SOURCES",
    "PHASE11C_8_COMPLETE_LABEL",
    "PHASE11C_8_HOOK_JUDGMENT_ENGINE_ALIGNMENT_VERSION",
    "HookJudgmentEngineDecision",
    "HookJudgmentEngineRequest",
    "build_hook_judgment_engine_alignment_evidence",
    "judge_pretooluse_with_aeg_engine",
]
