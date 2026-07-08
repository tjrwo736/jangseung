"""Phase 11-C-2 Claude Code tool call to structured action candidate mapping.

This module is contract-level only. It maps validated Claude Code PreToolUse
input into inert structured action candidates; it does not implement a hook
command, return a hook response, execute tools, or grant authority.
"""

from __future__ import annotations

import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from src.classify import is_protected_path
from src.contracts import HIGH, LOW, NOT_CHECKED, SAFE_DEFAULT, STATE_DIR
from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from src.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
)

PHASE11C_2_TOOL_CALL_MAPPING_VERSION = (
    "phase11c_2_tool_call_to_structured_action_mapping_v0"
)
PHASE11C_2_COMPLETE_LABEL = (
    "PHASE11C_2_TOOL_CALL_TO_STRUCTURED_ACTION_MAPPING_COMPLETE_NOT_HOOK_RUNTIME"
)

READ_REPO = "READ_REPO"
WRITE_FILE = "WRITE_FILE"
EDIT_FILE = "EDIT_FILE"
RUN_COMMAND = "RUN_COMMAND"
HOLD_CURRENT_STATE = "HOLD_CURRENT_STATE"

STRUCTURED_ACTION_CANDIDATE = "STRUCTURED_ACTION_CANDIDATE"
DENY_CANDIDATE = "DENY_CANDIDATE"
HIGH_USER_GATE_CANDIDATE = "HIGH_USER_GATE_CANDIDATE"
HOLD_CURRENT_STATE_CANDIDATE = "HOLD_CURRENT_STATE_CANDIDATE"

NORMAL_REPO_PATH = "NORMAL_REPO_PATH"
PROTECTED_PATH = "PROTECTED_PATH"
BASH_DANGEROUS = "BASH_DANGEROUS"
BASH_NOT_CHECKED = "BASH_NOT_CHECKED"
UNKNOWN_TOOL = "UNKNOWN_TOOL"
INVALID_TOOL_INPUT = "INVALID_TOOL_INPUT"

SUPPORTED_TOOL_TO_CANDIDATE_ACTION = MappingProxyType(
    {
        "Read": READ_REPO,
        "Write": WRITE_FILE,
        "Edit": EDIT_FILE,
        "Bash": RUN_COMMAND,
        "apply_patch": WRITE_FILE,
    }
)

DANGEROUS_BASH_TOKENS = frozenset(
    {
        "curl",
        "wget",
        "env",
        "printenv",
        "chmod",
        "chown",
        "sudo",
    }
)


@dataclass(frozen=True)
class ToolCallStructuredActionCandidate:
    candidate_action_type: str
    candidate_status: str
    reasons: tuple[str, ...]
    source_tool_name: str
    source_tool_use_id: str
    action_id: str
    declared_risk: str
    risk_status: str
    capability_requirements: tuple[str, ...]
    target_scope: Mapping[str, Any]
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]
    contract_version: str = PHASE11C_2_TOOL_CALL_MAPPING_VERSION
    source_contract_version: str = PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION
    decision: str = SAFE_DEFAULT
    safe_default: str = SAFE_DEFAULT
    live_executor_authority: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    mapping_output_is_structured_action_candidate_only: bool = True
    mapping_output_is_execution: bool = False
    mapping_output_is_permission_decision: bool = False
    mapping_output_is_hook_response: bool = False
    mapping_output_grants_write_authority: bool = False
    mapping_output_applies_patch: bool = False
    hook_input_trusted_as_decision: bool = False
    hook_input_trusted_as_capability_grant: bool = False
    unsupported_unknown_or_not_checked_is_pass: bool = False
    execution_allowed: bool = False
    mutation_allowed: bool = False
    write_authority_granted: bool = False
    hook_response_produced: bool = False
    patch_application_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(
            self,
            "capability_requirements",
            tuple(self.capability_requirements),
        )
        object.__setattr__(self, "target_scope", _freeze_value(self.target_scope))
        object.__setattr__(self, "payload", _freeze_value(self.payload))
        object.__setattr__(self, "provenance", _freeze_value(self.provenance))


def map_pretooluse_input_to_structured_action_candidate(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    """Map validated PreToolUse input to an inert structured action candidate."""

    if not isinstance(hook_input, ClaudeCodePreToolUseInput):
        raise TypeError("hook_input must be ClaudeCodePreToolUseInput")

    if hook_input.tool_name == "Read":
        return _map_read(hook_input)
    if hook_input.tool_name == "Write":
        return _map_write(hook_input)
    if hook_input.tool_name == "Edit":
        return _map_edit(hook_input)
    if hook_input.tool_name == "Bash":
        return _map_bash(hook_input)
    if hook_input.tool_name == "apply_patch":
        return _map_apply_patch(hook_input)

    return _build_candidate(
        hook_input,
        candidate_action_type=HOLD_CURRENT_STATE,
        candidate_status=HOLD_CURRENT_STATE_CANDIDATE,
        reasons=(
            f"unsupported_or_unknown_tool_name:{hook_input.tool_name}",
            "unsupported_unknown_or_not_checked_is_not_pass",
        ),
        declared_risk=NOT_CHECKED,
        risk_status=UNKNOWN_TOOL,
        capability_requirements=("noop",),
        target_scope={"repo_relative": False, "paths": tuple()},
        payload={},
    )


def build_tool_call_mapping_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11C_2_TOOL_CALL_MAPPING_VERSION,
        "completion_label": PHASE11C_2_COMPLETE_LABEL,
        "source_contract_version": PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
        "supported_tool_mappings": dict(SUPPORTED_TOOL_TO_CANDIDATE_ACTION),
        "protected_path_policy_source": "src.classify.is_protected_path",
        "state_dir_boundary_source": "src.contracts.STATE_DIR",
        "absolute_or_traversal_path_deny_candidate": True,
        "apply_patch_tool_supported": True,
        "codex_apply_patch_tool_call_supported": True,
        "apply_patch_maps_to_write_file_candidate": True,
        "apply_patch_target_parsing_is_structural_directive_parse": True,
        "apply_patch_unparseable_maps_to_deny_candidate": True,
        "apply_patch_target_directives": (
            "*** Add File: ",
            "*** Update File: ",
            "*** Delete File: ",
            "*** Move to: ",
        ),
        "dangerous_bash_tokens": tuple(sorted(DANGEROUS_BASH_TOKENS)),
        "rm_recursive_force_is_dangerous": True,
        "git_reset_hard_is_dangerous": True,
        "git_clean_force_delete_is_dangerous": True,
        "git_push_is_dangerous": True,
        "deploy_token_is_dangerous": True,
        "mapping_output_is_structured_action_candidate_only": True,
        "mapping_output_is_execution": False,
        "mapping_output_is_permission_decision": False,
        "mapping_output_is_hook_response": False,
        "mapping_output_grants_write_authority": False,
        "mapping_output_applies_patch": False,
        "hook_input_trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "hook_input_trusted_as_decision": False,
        "hook_input_trusted_as_capability_grant": False,
        "unsupported_unknown_or_not_checked_is_pass": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
        "hook_command_implemented": False,
        "hook_installation_implemented": False,
        "claude_code_execution_performed": False,
        "codex_implementation_added": False,
        "provider_model_network_implemented": False,
        "api_key_env_secret_loading_implemented": False,
        "network_client_implemented": False,
        "action_execution_engine_implemented": False,
        "tool_runtime_implemented": False,
        "write_authority_granted": False,
        "filesystem_mutation_by_mapping": False,
        "patch_application_implemented": False,
        "public_release_performed": False,
        "universal_prompt_injection_prevention_claimed": False,
        "sandbox_process_isolation_claimed": False,
        "bash_safe_claimed": False,
    }


def _map_read(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    file_path = hook_input.tool_input.get("file_path")
    if not _is_non_empty_string(file_path):
        return _invalid_tool_input_candidate(
            hook_input,
            READ_REPO,
            "missing_or_invalid_tool_input:file_path",
        )
    status, risk_status, reason = _path_candidate_posture(file_path)
    return _build_candidate(
        hook_input,
        candidate_action_type=READ_REPO,
        candidate_status=status,
        reasons=(reason, "read_candidate_only_no_authority"),
        declared_risk=HIGH if status == DENY_CANDIDATE else LOW,
        risk_status=risk_status,
        capability_requirements=("read_repo",),
        target_scope={"repo_relative": risk_status == NORMAL_REPO_PATH, "paths": (file_path,)},
        payload={"file_path": file_path},
    )


def _map_write(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    file_path = hook_input.tool_input.get("file_path")
    content = hook_input.tool_input.get("content")
    if not _is_non_empty_string(file_path):
        return _invalid_tool_input_candidate(
            hook_input,
            WRITE_FILE,
            "missing_or_invalid_tool_input:file_path",
        )
    if not isinstance(content, str):
        return _invalid_tool_input_candidate(
            hook_input,
            WRITE_FILE,
            "missing_or_invalid_tool_input:content",
        )
    status, risk_status, reason = _path_candidate_posture(file_path)
    return _build_candidate(
        hook_input,
        candidate_action_type=WRITE_FILE,
        candidate_status=status,
        reasons=(reason, "write_candidate_only_no_execution_or_authority"),
        declared_risk=HIGH if status == DENY_CANDIDATE else LOW,
        risk_status=risk_status,
        capability_requirements=("write_file",),
        target_scope={"repo_relative": risk_status == NORMAL_REPO_PATH, "paths": (file_path,)},
        payload={"file_path": file_path, "content": content},
    )


def _map_edit(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    file_path = hook_input.tool_input.get("file_path")
    old_string = hook_input.tool_input.get("old_string")
    new_string = hook_input.tool_input.get("new_string")
    if not _is_non_empty_string(file_path):
        return _invalid_tool_input_candidate(
            hook_input,
            EDIT_FILE,
            "missing_or_invalid_tool_input:file_path",
        )
    if not isinstance(old_string, str):
        return _invalid_tool_input_candidate(
            hook_input,
            EDIT_FILE,
            "missing_or_invalid_tool_input:old_string",
        )
    if not isinstance(new_string, str):
        return _invalid_tool_input_candidate(
            hook_input,
            EDIT_FILE,
            "missing_or_invalid_tool_input:new_string",
        )
    status, risk_status, reason = _path_candidate_posture(file_path)
    return _build_candidate(
        hook_input,
        candidate_action_type=EDIT_FILE,
        candidate_status=status,
        reasons=(reason, "edit_candidate_only_no_patch_application_or_authority"),
        declared_risk=HIGH if status == DENY_CANDIDATE else LOW,
        risk_status=risk_status,
        capability_requirements=("edit_file",),
        target_scope={"repo_relative": risk_status == NORMAL_REPO_PATH, "paths": (file_path,)},
        payload={
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
        },
    )


def _map_bash(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    command = hook_input.tool_input.get("command")
    if not _is_non_empty_string(command):
        return _invalid_tool_input_candidate(
            hook_input,
            RUN_COMMAND,
            "missing_or_invalid_tool_input:command",
        )

    bash_status, reasons = _bash_risk(command)
    if bash_status == BASH_DANGEROUS:
        candidate_status = DENY_CANDIDATE
        declared_risk = HIGH
    else:
        candidate_status = HOLD_CURRENT_STATE_CANDIDATE
        declared_risk = NOT_CHECKED

    return _build_candidate(
        hook_input,
        candidate_action_type=RUN_COMMAND,
        candidate_status=candidate_status,
        reasons=(*reasons, "bash_candidate_only_no_execution_or_bash_safe_claim"),
        declared_risk=declared_risk,
        risk_status=bash_status,
        capability_requirements=("run_command",),
        target_scope={"repo_relative": False, "paths": tuple()},
        payload={"command": command},
    )


def _map_apply_patch(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    command = hook_input.tool_input.get("command")
    if not _is_non_empty_string(command):
        return _invalid_apply_patch_candidate(
            hook_input,
            "missing_or_invalid_tool_input:command",
        )

    extraction = extract_apply_patch_targets(command)
    if extraction.parse_ambiguous:
        return _invalid_apply_patch_candidate(
            hook_input,
            f"apply_patch_parse_failed:{extraction.reason}",
        )

    denial_reasons = tuple(
        reason
        for path in extraction.target_paths
        for reason in (_path_denial_reason(path),)
        if reason is not None
    )
    if denial_reasons:
        candidate_status = DENY_CANDIDATE
        declared_risk = HIGH
        risk_status = PROTECTED_PATH
        reasons = (
            *denial_reasons,
            "apply_patch_target_path_maps_to_deny_candidate",
        )
    else:
        candidate_status = STRUCTURED_ACTION_CANDIDATE
        declared_risk = LOW
        risk_status = NORMAL_REPO_PATH
        reasons = (
            "normal_repo_paths_map_to_apply_patch_candidate",
            "apply_patch_targets_extracted_from_structural_directives",
        )

    return _build_candidate(
        hook_input,
        candidate_action_type=WRITE_FILE,
        candidate_status=candidate_status,
        reasons=(
            *reasons,
            "apply_patch_candidate_only_no_patch_application_or_authority",
        ),
        declared_risk=declared_risk,
        risk_status=risk_status,
        capability_requirements=("write_file",),
        target_scope={
            "repo_relative": risk_status == NORMAL_REPO_PATH,
            "paths": extraction.target_paths,
        },
        payload={
            "command": command,
            "target_paths": extraction.target_paths,
            "target_operations": extraction.target_operations,
        },
    )


def _invalid_tool_input_candidate(
    hook_input: ClaudeCodePreToolUseInput,
    candidate_action_type: str,
    reason: str,
) -> ToolCallStructuredActionCandidate:
    return _build_candidate(
        hook_input,
        candidate_action_type=candidate_action_type,
        candidate_status=HOLD_CURRENT_STATE_CANDIDATE,
        reasons=(reason, "invalid_tool_input_maps_to_hold_current_state"),
        declared_risk=NOT_CHECKED,
        risk_status=INVALID_TOOL_INPUT,
        capability_requirements=("noop",),
        target_scope={"repo_relative": False, "paths": tuple()},
        payload={},
    )


def _invalid_apply_patch_candidate(
    hook_input: ClaudeCodePreToolUseInput,
    reason: str,
) -> ToolCallStructuredActionCandidate:
    return _build_candidate(
        hook_input,
        candidate_action_type=WRITE_FILE,
        candidate_status=DENY_CANDIDATE,
        reasons=(reason, "apply_patch_unparseable_or_invalid_maps_to_deny_candidate"),
        declared_risk=HIGH,
        risk_status=INVALID_TOOL_INPUT,
        capability_requirements=("write_file",),
        target_scope={"repo_relative": False, "paths": tuple()},
        payload={},
    )


def _path_candidate_posture(path_value: str) -> tuple[str, str, str]:
    denial_reason = _path_denial_reason(path_value)
    if denial_reason is not None:
        return (
            DENY_CANDIDATE,
            PROTECTED_PATH,
            denial_reason,
        )
    return (
        STRUCTURED_ACTION_CANDIDATE,
        NORMAL_REPO_PATH,
        f"normal_repo_path_maps_to_candidate:{path_value}",
    )


def _path_denial_reason(path_value: str) -> str | None:
    stripped = path_value.strip()
    if not stripped:
        return "empty_path_maps_to_deny_candidate"
    if stripped.startswith("/") or _looks_like_windows_absolute_path(stripped):
        return f"absolute_path_maps_to_deny_candidate:{path_value}"
    parts = _path_parts(stripped)
    if any(part == ".." for part in parts):
        return f"parent_traversal_path_maps_to_deny_candidate:{path_value}"
    if _contains_state_dir_path(parts):
        return f"state_dir_path_maps_to_deny_candidate:{path_value}"
    if is_protected_path(stripped):
        return f"src.classify.is_protected_path_maps_to_deny_candidate:{path_value}"
    return None


def _bash_risk(command: str) -> tuple[str, tuple[str, ...]]:
    stripped = command.strip()
    if not stripped or stripped == NOT_CHECKED:
        return (
            BASH_NOT_CHECKED,
            ("bash_command_not_checked_maps_to_hold_current_state",),
        )

    try:
        tokens = tuple(token.lower() for token in shlex.split(stripped))
    except ValueError as exc:
        return (
            BASH_NOT_CHECKED,
            (f"bash_parse_not_checked:{exc.__class__.__name__}",),
        )

    if _rm_recursive_force(tokens):
        return (BASH_DANGEROUS, ("dangerous_bash_rm_recursive_force",))
    if _git_reset_hard(tokens):
        return (BASH_DANGEROUS, ("dangerous_bash_git_reset_hard",))
    if _git_clean_force_delete(tokens):
        return (BASH_DANGEROUS, ("dangerous_bash_git_clean_force_delete",))
    if _git_push(tokens):
        return (BASH_DANGEROUS, ("dangerous_bash_git_push",))
    if _deploy_token(tokens):
        return (BASH_DANGEROUS, ("dangerous_bash_deploy",))

    dangerous_tokens = tuple(token for token in tokens if token in DANGEROUS_BASH_TOKENS)
    if dangerous_tokens:
        return (
            BASH_DANGEROUS,
            tuple(f"dangerous_bash_token:{token}" for token in dangerous_tokens),
        )

    return (
        BASH_NOT_CHECKED,
        ("bash_not_proven_safe_maps_to_hold_current_state",),
    )


def _rm_recursive_force(tokens: tuple[str, ...]) -> bool:
    if "rm" not in tokens:
        return False
    for index, token in enumerate(tokens):
        if token != "rm":
            continue
        following = tokens[index + 1 :]
        has_recursive = False
        has_force = False
        for flag in following:
            if flag == "--":
                break
            if not flag.startswith("-"):
                continue
            if flag in ("--recursive", "--dir"):
                has_recursive = True
            if flag == "--force":
                has_force = True
            if flag.startswith("-") and not flag.startswith("--"):
                has_recursive = has_recursive or "r" in flag or "R" in flag
                has_force = has_force or "f" in flag
        if has_recursive and has_force:
            return True
    return False


_SHELL_INTERPRETER_TOKENS = frozenset(
    {"bash", "sh", "zsh", "dash", "ksh", "fish", "eval", "exec", "source", "."}
)
_NESTED_EXEC_TOKENS = frozenset({"xargs"})
_BASH_CONTROL_OPERATORS = frozenset({";", "&&", "||", "|", "&", "|&", ";;"})
# Ordered longest/most-specific first so ">>" is matched before ">", etc.
_BASH_REDIRECT_OPS = ("&>>", "&>", "1>>", "1>", "2>>", "2>", ">>", ">|", ">")
_BASH_AMBIGUITY_RAW_MARKERS = ("$", "`", "<(", ">(")
_BASH_WRITE_DELETE_COMMANDS = frozenset(
    {"tee", "cp", "mv", "install", "rm", "dd", "truncate", "ln"}
)


@dataclass(frozen=True)
class BashTargetExtraction:
    """Structurally-parsed file write/delete targets of a Bash command.

    ``parse_ambiguous`` is True when the command uses variable/command/process
    substitution, a nested shell, xargs/find -exec, or is otherwise not
    precisely parseable; in that case ``write_delete_targets`` is empty and the
    caller must NOT claim a precise target judgment (fail-closed: ask/defer,
    never allow).
    """

    write_delete_targets: tuple[str, ...]
    parse_ambiguous: bool
    reason: str


@dataclass(frozen=True)
class ApplyPatchTargetExtraction:
    """Structurally-parsed file targets from a Codex ``apply_patch`` command."""

    target_paths: tuple[str, ...]
    target_operations: tuple[tuple[str, str], ...]
    parse_ambiguous: bool
    reason: str


def extract_bash_write_delete_targets(command: str) -> BashTargetExtraction:
    """Parse a Bash command with shlex (not string matching) and extract the
    file paths it would write to or delete via redirection, tee, cp, mv, rm,
    dd of=, truncate, or ln. Case-preserving. Obfuscation that shlex resolves
    (e.g. ``.en"v"`` -> ``.env``) is handled structurally; anything relying on
    substitution or a nested shell is reported as ambiguous."""

    stripped = command.strip()
    if not stripped:
        return BashTargetExtraction((), False, "empty_command")
    if any(marker in stripped for marker in _BASH_AMBIGUITY_RAW_MARKERS):
        return BashTargetExtraction((), True, "bash_target_parse_ambiguous_substitution")
    try:
        tokens = shlex.split(stripped)
    except ValueError:
        return BashTargetExtraction((), True, "bash_target_parse_ambiguous_shlex_error")

    lowered = [token.lower() for token in tokens]
    if any(token in _SHELL_INTERPRETER_TOKENS for token in lowered):
        return BashTargetExtraction((), True, "bash_target_parse_ambiguous_nested_shell")
    if (
        any(token in _NESTED_EXEC_TOKENS for token in lowered)
        or "-exec" in lowered
        or "-execdir" in lowered
        or "-delete" in lowered
    ):
        return BashTargetExtraction((), True, "bash_target_parse_ambiguous_nested_exec")

    targets: list[str] = []
    for segment in _split_bash_segments(tokens):
        targets.extend(_bash_segment_write_delete_targets(segment))
    unique = tuple(dict.fromkeys(targets))
    return BashTargetExtraction(
        unique,
        False,
        "bash_write_delete_targets_extracted" if unique else "no_write_delete_target",
    )


_APPLY_PATCH_BEGIN = "*** Begin Patch"
_APPLY_PATCH_END = "*** End Patch"
_APPLY_PATCH_END_OF_FILE = "*** End of File"
_APPLY_PATCH_ADD_FILE = "*** Add File: "
_APPLY_PATCH_UPDATE_FILE = "*** Update File: "
_APPLY_PATCH_DELETE_FILE = "*** Delete File: "
_APPLY_PATCH_MOVE_TO = "*** Move to: "


def extract_apply_patch_targets(command: str) -> ApplyPatchTargetExtraction:
    """Parse Codex ``apply_patch`` text and extract directive-declared targets.

    Only exact patch directives declare targets. File content that merely
    mentions a protected path is ignored; malformed structure is ambiguous and
    must be denied by the caller.
    """

    if not isinstance(command, str) or not command.strip():
        return ApplyPatchTargetExtraction(
            tuple(),
            tuple(),
            True,
            "empty_apply_patch_command",
        )

    lines = command.splitlines()
    if len(lines) < 3:
        return ApplyPatchTargetExtraction(
            tuple(),
            tuple(),
            True,
            "apply_patch_too_short",
        )
    if lines[0] != _APPLY_PATCH_BEGIN or lines[-1] != _APPLY_PATCH_END:
        return ApplyPatchTargetExtraction(
            tuple(),
            tuple(),
            True,
            "apply_patch_missing_exact_begin_or_end",
        )

    operations: list[tuple[str, str]] = []
    current_hunk_type: str | None = None
    current_hunk_has_body = False
    current_hunk_move_seen = False
    current_update_operation_index: int | None = None

    def fail(reason: str) -> ApplyPatchTargetExtraction:
        return ApplyPatchTargetExtraction(tuple(), tuple(), True, reason)

    def finish_hunk() -> str | None:
        if current_hunk_type == "Add" and not current_hunk_has_body:
            return "apply_patch_add_file_missing_added_lines"
        if (
            current_hunk_type == "Update"
            and not current_hunk_has_body
            and not current_hunk_move_seen
        ):
            return "apply_patch_update_file_missing_change"
        return None

    for line in lines[1:-1]:
        path = _apply_patch_directive_path(line, _APPLY_PATCH_ADD_FILE)
        if path is not None:
            reason = finish_hunk()
            if reason is not None:
                return fail(reason)
            operations.append(("write", path))
            current_hunk_type = "Add"
            current_hunk_has_body = False
            current_hunk_move_seen = False
            current_update_operation_index = None
            continue

        path = _apply_patch_directive_path(line, _APPLY_PATCH_UPDATE_FILE)
        if path is not None:
            reason = finish_hunk()
            if reason is not None:
                return fail(reason)
            operations.append(("write", path))
            current_hunk_type = "Update"
            current_hunk_has_body = False
            current_hunk_move_seen = False
            current_update_operation_index = len(operations) - 1
            continue

        path = _apply_patch_directive_path(line, _APPLY_PATCH_DELETE_FILE)
        if path is not None:
            reason = finish_hunk()
            if reason is not None:
                return fail(reason)
            operations.append(("delete", path))
            current_hunk_type = "Delete"
            current_hunk_has_body = False
            current_hunk_move_seen = False
            current_update_operation_index = None
            continue

        path = _apply_patch_directive_path(line, _APPLY_PATCH_MOVE_TO)
        if path is not None:
            if (
                current_hunk_type != "Update"
                or current_hunk_has_body
                or current_hunk_move_seen
                or current_update_operation_index is None
            ):
                return fail("apply_patch_move_to_not_first_in_update_hunk")
            old_operation, old_path = operations[current_update_operation_index]
            if old_operation != "write":
                return fail("apply_patch_move_to_source_operation_invalid")
            operations[current_update_operation_index] = ("delete", old_path)
            operations.append(("write", path))
            current_hunk_move_seen = True
            continue

        if line.startswith("*** "):
            if line == _APPLY_PATCH_END_OF_FILE and current_hunk_type == "Update":
                current_hunk_has_body = True
                continue
            return fail("apply_patch_unknown_directive")

        if current_hunk_type is None:
            return fail("apply_patch_content_before_file_directive")
        if current_hunk_type == "Delete":
            return fail("apply_patch_delete_file_has_unexpected_body")
        if current_hunk_type == "Add":
            if not line.startswith("+"):
                return fail("apply_patch_add_file_line_without_plus")
            current_hunk_has_body = True
            continue
        if current_hunk_type == "Update":
            if not (
                line.startswith("@@")
                or line.startswith("+")
                or line.startswith("-")
                or line.startswith(" ")
            ):
                return fail("apply_patch_update_file_unrecognized_change_line")
            current_hunk_has_body = True
            continue
        return fail("apply_patch_internal_parser_state_invalid")

    reason = finish_hunk()
    if reason is not None:
        return fail(reason)
    if not operations:
        return fail("apply_patch_no_file_directives")

    target_paths = tuple(dict.fromkeys(path for _, path in operations))
    return ApplyPatchTargetExtraction(
        target_paths,
        tuple(operations),
        False,
        "apply_patch_targets_extracted",
    )


def _apply_patch_directive_path(line: str, prefix: str) -> str | None:
    if not line.startswith(prefix):
        return None
    path = line[len(prefix) :]
    if not path or path != path.strip() or "\x00" in path:
        return None
    return path


def _split_bash_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _BASH_CONTROL_OPERATORS:
            if current:
                segments.append(current)
                current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    return segments


def _bash_segment_write_delete_targets(segment: list[str]) -> list[str]:
    targets: list[str] = []
    clean: list[str] = []
    index = 0
    length = len(segment)
    while index < length:
        token = segment[index]
        redirect = _bash_redirect_op(token)
        if redirect is not None:
            _, inline_target = redirect
            target: str | None = None
            if inline_target is not None:
                target = inline_target
            elif index + 1 < length:
                target = segment[index + 1]
                index += 1
            if target is not None and not target.startswith("&"):
                targets.append(target)
            index += 1
            continue
        clean.append(token)
        index += 1

    command_index = 0
    while command_index < len(clean) and _is_bash_assignment(clean[command_index]):
        command_index += 1
    if command_index >= len(clean):
        return targets

    command = _bash_basename(clean[command_index]).lower()
    args = clean[command_index + 1 :]
    non_flag = [arg for arg in args if not arg.startswith("-")]

    if command not in _BASH_WRITE_DELETE_COMMANDS:
        return targets
    if command == "tee":
        targets.extend(non_flag)
    elif command in ("cp", "mv", "install"):
        if len(non_flag) >= 2:
            targets.append(non_flag[-1])
    elif command == "rm":
        targets.extend(non_flag)
    elif command == "dd":
        targets.extend(arg[len("of=") :] for arg in args if arg.startswith("of="))
    elif command == "truncate":
        targets.extend(arg for arg in non_flag if not arg.isdigit())
    elif command == "ln":
        if len(non_flag) >= 2:
            targets.append(non_flag[-1])
    return targets


def _bash_redirect_op(token: str) -> tuple[str, str | None] | None:
    for op in _BASH_REDIRECT_OPS:
        if token == op:
            return (op, None)
        if token.startswith(op) and len(token) > len(op):
            return (op, token[len(op) :])
    return None


def _is_bash_assignment(token: str) -> bool:
    return "=" in token and token.split("=", 1)[0].isidentifier()


def _bash_basename(token: str) -> str:
    last = token
    for separator in ("/", "\\"):
        last = last.rsplit(separator, 1)[-1]
    return last


def _git_push(tokens: tuple[str, ...]) -> bool:
    return any(
        token == "git" and index + 1 < len(tokens) and tokens[index + 1] == "push"
        for index, token in enumerate(tokens)
    )


def _git_reset_hard(tokens: tuple[str, ...]) -> bool:
    return any(
        token == "git"
        and index + 2 < len(tokens)
        and tokens[index + 1] == "reset"
        and "--hard" in tokens[index + 2 :]
        for index, token in enumerate(tokens)
    )


def _git_clean_force_delete(tokens: tuple[str, ...]) -> bool:
    for index, token in enumerate(tokens):
        if token != "git" or index + 1 >= len(tokens) or tokens[index + 1] != "clean":
            continue
        following = tokens[index + 2 :]
        has_force = False
        has_delete_dir = False
        for flag in following:
            if flag == "--":
                break
            if not flag.startswith("-"):
                continue
            if flag == "--force":
                has_force = True
            if flag in ("--dir", "--directory"):
                has_delete_dir = True
            if flag.startswith("-") and not flag.startswith("--"):
                has_force = has_force or "f" in flag
                has_delete_dir = has_delete_dir or "d" in flag
        if has_force and has_delete_dir:
            return True
    return False


def _deploy_token(tokens: tuple[str, ...]) -> bool:
    return any(token == "deploy" or token.endswith(":deploy") for token in tokens)


def _build_candidate(
    hook_input: ClaudeCodePreToolUseInput,
    *,
    candidate_action_type: str,
    candidate_status: str,
    reasons: tuple[str, ...],
    declared_risk: str,
    risk_status: str,
    capability_requirements: tuple[str, ...],
    target_scope: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> ToolCallStructuredActionCandidate:
    return ToolCallStructuredActionCandidate(
        candidate_action_type=candidate_action_type,
        candidate_status=candidate_status,
        reasons=reasons,
        source_tool_name=hook_input.tool_name,
        source_tool_use_id=hook_input.tool_use_id,
        action_id=f"pretooluse:{hook_input.tool_use_id}",
        declared_risk=declared_risk,
        risk_status=risk_status,
        capability_requirements=capability_requirements,
        target_scope=target_scope,
        payload=payload,
        provenance=_provenance(hook_input),
    )


def _provenance(hook_input: ClaudeCodePreToolUseInput) -> dict[str, Any]:
    metadata = {
        field_name: getattr(hook_input, field_name)
        for field_name in (
            "cwd",
            "session_id",
            "transcript_path",
            "substrate_name",
            "substrate_version",
            "project_root",
            "timestamp",
        )
        if getattr(hook_input, field_name) is not None
    }
    return {
        "source_tool_name": hook_input.tool_name,
        "source_tool_use_id": hook_input.tool_use_id,
        "source_contract_version": hook_input.contract_version,
        "trust_boundary": UNTRUSTED_RAW_EXECUTOR_OUTPUT,
        "metadata": metadata,
    }


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _path_parts(path_value: str) -> tuple[str, ...]:
    normalized_parts: list[str] = []
    current = []
    for character in path_value:
        if character in ("/", "\\"):
            if current:
                normalized_parts.append("".join(current))
                current = []
            continue
        current.append(character)
    if current:
        normalized_parts.append("".join(current))
    return tuple(part for part in normalized_parts if part and part != ".")


def _contains_state_dir_path(parts: tuple[str, ...]) -> bool:
    return any(part == STATE_DIR for part in parts)


def _looks_like_windows_absolute_path(path_value: str) -> bool:
    return (
        len(path_value) >= 3
        and path_value[1] == ":"
        and path_value[2] in ("/", "\\")
        and path_value[0].isalpha()
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_value(nested) for key, nested in value.items()}
        )
    if _is_sequence(value):
        return tuple(_freeze_value(nested) for nested in value)
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    )
