"""Phase 11-C-2 Claude Code tool call to structured action candidate mapping.

This module is contract-level only. It maps validated Claude Code PreToolUse
input into inert structured action candidates; it does not implement a hook
command, return a hook response, execute tools, or grant authority.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Mapping, Sequence
from jangseung.records import dataclass
from types import MappingProxyType
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Any

from jangseung.classify import PathPolicy, is_host_resolved_path, is_protected_path, is_read_protected_path, is_secret_path
from jangseung.contracts import HIGH, LOW, NOT_CHECKED, SAFE_DEFAULT, STATE_DIR
from jangseung.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD
from jangseung.evidence.claude_code_pretooluse_input_contract import (
    ClaudeCodePreToolUseInput,
    PHASE11C_1_PRETOOLUSE_INPUT_CONTRACT_VERSION,
    UNTRUSTED_RAW_EXECUTOR_OUTPUT,
)
from jangseung.evidence.shell_command_risk import (
    BASH_TRAILING_ESCAPE_REASON,
    bash_dangerous_reasons,
    command_name,
    git_subcommand,
    inline_code_words,
    nested_shell_payloads,
    powershell_dangerous_reasons,
    scan_bash_command,
    strip_assignments,
)

PHASE11C_2_TOOL_CALL_MAPPING_VERSION = (
    "phase11c_2_tool_call_to_structured_action_mapping_v0"
)

READ_REPO = "READ_REPO"
WRITE_FILE = "WRITE_FILE"
EDIT_FILE = "EDIT_FILE"
RUN_COMMAND = "RUN_COMMAND"
HOLD_CURRENT_STATE = "HOLD_CURRENT_STATE"

STRUCTURED_ACTION_CANDIDATE = "STRUCTURED_ACTION_CANDIDATE"
DENY_CANDIDATE = "DENY_CANDIDATE"
HOLD_CURRENT_STATE_CANDIDATE = "HOLD_CURRENT_STATE_CANDIDATE"

NORMAL_REPO_PATH = "NORMAL_REPO_PATH"
PROTECTED_PATH = "PROTECTED_PATH"
BASH_DANGEROUS = "BASH_DANGEROUS"
BASH_NOT_CHECKED = "BASH_NOT_CHECKED"
POWERSHELL_DANGEROUS = "POWERSHELL_DANGEROUS"
POWERSHELL_NOT_CHECKED = "POWERSHELL_NOT_CHECKED"
POWERSHELL_SAFE_READ_ONLY = "POWERSHELL_SAFE_READ_ONLY"
POWERSHELL_TARGETS_EXTRACTED = "POWERSHELL_TARGETS_EXTRACTED"
UNKNOWN_TOOL = "UNKNOWN_TOOL"
INVALID_TOOL_INPUT = "INVALID_TOOL_INPUT"


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
    *,
    path_policy: PathPolicy | None = None,
) -> ToolCallStructuredActionCandidate:
    """Map validated PreToolUse input to an inert structured action candidate."""

    if not isinstance(hook_input, ClaudeCodePreToolUseInput):
        raise TypeError("hook_input must be ClaudeCodePreToolUseInput")

    if hook_input.tool_name == "Read":
        return _map_read(hook_input, path_policy)
    if hook_input.tool_name in {"Grep", "Glob"}:
        return _map_search(hook_input, path_policy)
    if hook_input.tool_name == "Write":
        return _map_write(hook_input, path_policy)
    if hook_input.tool_name == "Edit":
        return _map_edit(hook_input, path_policy)
    if hook_input.tool_name in {"MultiEdit", "NotebookEdit"}:
        return _map_file_edit_variant(hook_input, path_policy)
    if hook_input.tool_name == "Bash":
        return _map_bash(hook_input)
    if hook_input.tool_name == "PowerShell":
        return _map_powershell(hook_input)
    if hook_input.tool_name == "apply_patch":
        return _map_apply_patch(hook_input, path_policy)

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


def _map_read(
    hook_input: ClaudeCodePreToolUseInput,
    path_policy: PathPolicy | None,
) -> ToolCallStructuredActionCandidate:
    file_path = hook_input.tool_input.get("file_path")
    if not _is_non_empty_string(file_path):
        return _invalid_tool_input_candidate(
            hook_input,
            READ_REPO,
            "missing_or_invalid_tool_input:file_path",
        )
    status, risk_status, reason = _path_candidate_posture(file_path, path_policy, for_read=True)
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


def _map_search(
    hook_input: ClaudeCodePreToolUseInput,
    path_policy: PathPolicy | None,
) -> ToolCallStructuredActionCandidate:
    tool_input = hook_input.tool_input
    pattern = tool_input.get("pattern")
    if not _is_non_empty_string(pattern):
        return _invalid_tool_input_candidate(
            hook_input,
            READ_REPO,
            "missing_or_invalid_tool_input:pattern",
        )
    search_path = tool_input.get("path")
    target = search_path if _is_non_empty_string(search_path) else "."
    status, risk_status, reason = _path_candidate_posture(target, path_policy, for_read=True)
    if status != DENY_CANDIDATE:
        search_denial = _search_pattern_denial_reason(hook_input.tool_name, tool_input, path_policy)
        if search_denial is not None:
            status, risk_status, reason = DENY_CANDIDATE, PROTECTED_PATH, search_denial
    return _build_candidate(
        hook_input,
        candidate_action_type=READ_REPO,
        candidate_status=status,
        reasons=(reason, "search_candidate_only_no_authority"),
        declared_risk=HIGH if status == DENY_CANDIDATE else LOW,
        risk_status=risk_status,
        capability_requirements=("read_repo",),
        target_scope={"repo_relative": risk_status == NORMAL_REPO_PATH, "paths": (target,)},
        payload={"file_path": target},
    )


def _search_pattern_denial_reason(
    tool_name: str,
    tool_input: Mapping[str, Any],
    path_policy: PathPolicy | None,
) -> str | None:
    if tool_name == "Glob":
        pattern = str(tool_input.get("pattern")).strip()
        if (
            pattern.startswith("/")
            or is_host_resolved_path(pattern)
            or _looks_like_windows_drive_path(pattern)
            or ".." in _path_parts(pattern)
        ):
            return "glob_pattern_leaves_repository_maps_to_deny_candidate"
        return None
    glob = tool_input.get("glob")
    if isinstance(glob, str):
        for candidate in re.split(r"[{},\s]+", glob):
            if candidate and (is_secret_path(candidate, path_policy) or is_secret_path(candidate.rstrip("*?"), path_policy)):
                return "grep_glob_selects_secret_files_maps_to_deny_candidate"
    return None


def _map_file_edit_variant(
    hook_input: ClaudeCodePreToolUseInput,
    path_policy: PathPolicy | None,
) -> ToolCallStructuredActionCandidate:
    field_name = "notebook_path" if hook_input.tool_name == "NotebookEdit" else "file_path"
    file_path = hook_input.tool_input.get(field_name)
    if not _is_non_empty_string(file_path):
        return _invalid_tool_input_candidate(
            hook_input,
            EDIT_FILE,
            f"missing_or_invalid_tool_input:{field_name}",
        )
    status, risk_status, reason = _path_candidate_posture(file_path, path_policy)
    return _build_candidate(
        hook_input,
        candidate_action_type=EDIT_FILE,
        candidate_status=status,
        reasons=(reason, "edit_candidate_only_no_patch_application_or_authority"),
        declared_risk=HIGH if status == DENY_CANDIDATE else LOW,
        risk_status=risk_status,
        capability_requirements=("edit_file",),
        target_scope={"repo_relative": risk_status == NORMAL_REPO_PATH, "paths": (file_path,)},
        payload={"file_path": file_path},
    )


def _map_write(
    hook_input: ClaudeCodePreToolUseInput,
    path_policy: PathPolicy | None,
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
    status, risk_status, reason = _path_candidate_posture(file_path, path_policy)
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
    path_policy: PathPolicy | None,
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
    status, risk_status, reason = _path_candidate_posture(file_path, path_policy)
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


def _map_powershell(
    hook_input: ClaudeCodePreToolUseInput,
) -> ToolCallStructuredActionCandidate:
    command = hook_input.tool_input.get("command")
    if not _is_non_empty_string(command):
        return _invalid_tool_input_candidate(
            hook_input,
            RUN_COMMAND,
            "missing_or_invalid_tool_input:command",
        )

    extraction = extract_powershell_write_delete_targets(command)
    dangerous_reasons = powershell_dangerous_reasons(powershell_argvs(command))
    if dangerous_reasons:
        candidate_status = DENY_CANDIDATE
        declared_risk = HIGH
        risk_status = POWERSHELL_DANGEROUS
        reasons = dangerous_reasons
    elif extraction.parse_ambiguous:
        candidate_status = HOLD_CURRENT_STATE_CANDIDATE
        declared_risk = NOT_CHECKED
        risk_status = POWERSHELL_NOT_CHECKED
        reasons = (
            f"powershell_target_parse_ambiguous:{extraction.reason}",
            "powershell_not_proven_safe_maps_to_hold_current_state",
        )
    elif extraction.write_delete_targets:
        candidate_status = HOLD_CURRENT_STATE_CANDIDATE
        declared_risk = NOT_CHECKED
        risk_status = POWERSHELL_TARGETS_EXTRACTED
        reasons = (
            "powershell_write_delete_targets_extracted_structurally",
            "powershell_target_risk_judged_by_hook_target_gate",
        )
    elif extraction.read_only:
        candidate_status = STRUCTURED_ACTION_CANDIDATE
        declared_risk = LOW
        risk_status = POWERSHELL_SAFE_READ_ONLY
        reasons = (
            "powershell_read_only_command_has_no_write_delete_target",
            "powershell_read_only_candidate_only_no_execution_or_authority",
        )
    else:
        candidate_status = HOLD_CURRENT_STATE_CANDIDATE
        declared_risk = NOT_CHECKED
        risk_status = POWERSHELL_NOT_CHECKED
        reasons = (
            "powershell_command_not_proven_safe_maps_to_hold_current_state",
        )

    return _build_candidate(
        hook_input,
        candidate_action_type=RUN_COMMAND,
        candidate_status=candidate_status,
        reasons=(*reasons, "powershell_candidate_only_no_execution_or_powershell_safe_claim"),
        declared_risk=declared_risk,
        risk_status=risk_status,
        capability_requirements=("run_command",),
        target_scope={
            "repo_relative": False,
            "paths": extraction.write_delete_targets,
        },
        payload={
            "command": command,
            "target_paths": extraction.write_delete_targets,
            "target_operations": extraction.target_operations,
        },
    )


def _map_apply_patch(
    hook_input: ClaudeCodePreToolUseInput,
    path_policy: PathPolicy | None,
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
        for reason in (_path_denial_reason(path, path_policy),)
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


def _path_candidate_posture(
    path_value: str,
    path_policy: PathPolicy | None = None,
    *,
    for_read: bool = False,
) -> tuple[str, str, str]:
    denial_reason = _path_denial_reason(path_value, path_policy, for_read=for_read)
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


def _path_denial_reason(
    path_value: str,
    path_policy: PathPolicy | None = None,
    *,
    for_read: bool = False,
) -> str | None:
    stripped = path_value.strip()
    if not stripped:
        return "empty_path_maps_to_deny_candidate"
    if is_host_resolved_path(stripped):
        return f"host_resolved_path_maps_to_deny_candidate:{path_value}"
    if stripped.startswith("/") or _looks_like_windows_drive_path(stripped):
        return f"absolute_path_maps_to_deny_candidate:{path_value}"
    parts = _path_parts(stripped)
    if any(part == ".." for part in parts):
        return f"parent_traversal_path_maps_to_deny_candidate:{path_value}"
    if _contains_state_dir_path(parts):
        return f"state_dir_path_maps_to_deny_candidate:{path_value}"
    if for_read:
        if is_read_protected_path(stripped, path_policy):
            return f"secret_path_maps_to_deny_candidate:{path_value}"
        return None
    if is_protected_path(stripped, path_policy):
        return f"jangseung.classify.is_protected_path_maps_to_deny_candidate:{path_value}"
    return None


def _bash_risk(command: str) -> tuple[str, tuple[str, ...]]:
    stripped = command.strip()
    if not stripped or stripped == NOT_CHECKED:
        return (
            BASH_NOT_CHECKED,
            ("bash_command_not_checked_maps_to_hold_current_state",),
        )

    scan = scan_bash_command(stripped)
    if scan.error == BASH_TRAILING_ESCAPE_REASON:
        # A version-dependent parse must not hide an otherwise blocked command
        # (for example `aeg uninstall` followed by an unquoted backslash).
        return (BASH_DANGEROUS, (BASH_TRAILING_ESCAPE_REASON,))
    if scan.error is not None:
        return (
            BASH_NOT_CHECKED,
            (f"bash_parse_not_checked:{scan.error}",),
        )

    dangerous_reasons = bash_dangerous_reasons(scan)
    if dangerous_reasons:
        return (BASH_DANGEROUS, dangerous_reasons)

    return (
        BASH_NOT_CHECKED,
        ("bash_not_proven_safe_maps_to_hold_current_state",),
    )


_DIRECTORY_CHANGE_COMMANDS = frozenset({"cd", "pushd", "chdir", "set-location", "sl"})
_SHELL_INTERPRETER_TOKENS = frozenset(
    {"bash", "sh", "zsh", "dash", "ksh", "fish", "eval", "exec", "source", "."}
)
_NESTED_EXEC_TOKENS = frozenset({"xargs"})
_BASH_WRITE_DELETE_COMMANDS = frozenset(
    {"tee", "cp", "mv", "install", "rm", "dd", "truncate", "ln", "rmdir", "unlink", "shred", "touch", "mkdir", "sed", "git"}
)


@dataclass(frozen=True)
class BashTargetExtraction:
    """Structurally-parsed file write/delete targets of a Bash command.

    ``parse_ambiguous`` is True when the command uses variable/command/process
    substitution, a nested shell, xargs/find -exec, or is otherwise not
    precisely parseable. ``write_delete_targets`` then holds only the literal
    targets that could still be read: a caller can deny on them, but finding
    none proves nothing (fail-closed: ask/defer, never allow).
    """

    write_delete_targets: tuple[str, ...]
    parse_ambiguous: bool
    reason: str
    delete_targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class PowerShellTargetExtraction:
    """Structurally-parsed file write/delete targets of a PowerShell command.

    This covers a deliberately small, common subset of PowerShell syntax:
    known cmdlets/aliases, named parameters, positional path arguments, and
    file redirection. Dynamic targets, variables in targets, unrecognized
    commands, or complex pipelines are ambiguous so callers can fail closed.
    """

    write_delete_targets: tuple[str, ...]
    target_operations: tuple[tuple[str, str], ...]
    parse_ambiguous: bool
    read_only: bool
    reason: str


@dataclass(frozen=True)
class ApplyPatchTargetExtraction:
    """Structurally-parsed file targets from a Codex ``apply_patch`` command."""

    target_paths: tuple[str, ...]
    target_operations: tuple[tuple[str, str], ...]
    parse_ambiguous: bool
    reason: str


def extract_bash_write_delete_targets(command: str) -> BashTargetExtraction:
    """Parse a Bash command structurally (not by string matching) and extract
    the file paths it would write to or delete via redirection, tee, cp, mv, rm,
    dd of=, truncate, ln, sed -i and similar. Case-preserving. Obfuscation that
    quoting removal resolves (e.g. ``.en"v"`` -> ``.env``) is handled; anything
    relying on substitution or a nested shell is also reported as ambiguous."""

    stripped = command.strip()
    if not stripped:
        return BashTargetExtraction((), False, "empty_command")
    scan = scan_bash_command(stripped)
    if scan.error is not None:
        return BashTargetExtraction((), True, "bash_target_parse_ambiguous_shlex_error")

    targets: list[str] = []
    deletes: list[str] = []
    nested_shell = False
    nested_exec = False
    directory = ""
    redirects = list(zip(scan.redirect_positions, scan.write_redirects))

    def take_redirects(position: int) -> None:
        for redirect_position, word in redirects:
            if redirect_position == position and not word.dynamic:
                targets.append(_relative_to_directory(word.value, directory))

    for position, (segment, argv) in enumerate(zip(scan.segments, scan.argvs())):
        take_redirects(position)
        dynamic_values = {word.value for word in segment if word.dynamic}
        command_argv = strip_assignments(argv)
        if (
            command_argv
            and command_name(command_argv[0]) in _DIRECTORY_CHANGE_COMMANDS
            and len(command_argv) == 2
            and command_argv[1] not in dynamic_values
        ):
            # Later relative targets in the same command resolve from here.
            directory = posixpath.join(directory, _forward_slashes(command_argv[1]))
            continue
        segment_targets = [
            target
            for target in _bash_segment_write_delete_targets(list(argv))
            if target not in dynamic_values
        ]
        segment_deletes = [
            target
            for target in _bash_segment_delete_targets(list(argv))
            if target not in dynamic_values
        ]
        targets.extend(_relative_to_directory(target, directory) for target in segment_targets)
        deletes.extend(_relative_to_directory(target, directory) for target in segment_deletes)
        if command_argv and command_name(command_argv[0]) in _SHELL_INTERPRETER_TOKENS:
            nested_shell = True
        for payload in nested_shell_payloads(argv):
            nested_shell = True
            nested = extract_bash_write_delete_targets(payload)
            targets.extend(nested.write_delete_targets)
            deletes.extend(nested.delete_targets)
        lowered = {token.lower() for token in argv}
        if lowered & _NESTED_EXEC_TOKENS or lowered & {"-exec", "-execdir", "-delete"}:
            nested_exec = True

    take_redirects(len(scan.segments))
    unique = tuple(dict.fromkeys(targets))
    unique_deletes = tuple(dict.fromkeys(deletes))
    if scan.dynamic:
        return BashTargetExtraction(unique, True, "bash_target_parse_ambiguous_substitution", unique_deletes)
    if nested_shell:
        return BashTargetExtraction(unique, True, "bash_target_parse_ambiguous_nested_shell", unique_deletes)
    if nested_exec:
        return BashTargetExtraction(unique, True, "bash_target_parse_ambiguous_nested_exec", unique_deletes)
    return BashTargetExtraction(
        unique,
        False,
        "bash_write_delete_targets_extracted" if unique else "no_write_delete_target",
        unique_deletes,
    )


def _forward_slashes(path_value: str) -> str:
    return "/".join(path_value.split("\\"))


def _relative_to_directory(target: str, directory: str) -> str:
    """Apply an earlier ``cd`` from the same command to a relative target."""

    normalized = _forward_slashes(target)
    if not directory or normalized.startswith(("/", "~")) or _looks_like_windows_drive_path(normalized):
        return target
    return posixpath.normpath(posixpath.join(directory, normalized))


_POWERSHELL_CONTROL_OPERATORS = frozenset({";", "&&", "||"})
_POWERSHELL_GROUPING_TOKENS = frozenset({"(", ")", "{", "}"})
_POWERSHELL_BACKGROUND_OPERATOR = "&"
_POWERSHELL_PIPE_OPERATOR = "|"
# PowerShell itself reads typographic quotes and dashes as their ASCII forms.
_POWERSHELL_TYPOGRAPHIC_FORMS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
    }
)
_POWERSHELL_REDIRECT_OPS = frozenset(
    {
        ">",
        ">>",
        "1>",
        "1>>",
        "2>",
        "2>>",
        "3>",
        "3>>",
        "4>",
        "4>>",
        "5>",
        "5>>",
        "6>",
        "6>>",
        "*>",
        "*>>",
    }
)
_POWERSHELL_DELETE_COMMANDS = frozenset({"remove-item", "rm", "del", "ri", "erase", "rd", "rmdir"})
_POWERSHELL_WRITE_COMMANDS = frozenset(
    {
        "set-content", "sc", "add-content", "ac", "clear-content", "clc", "out-file",
        "tee-object", "tee", "new-item", "ni", "md", "mkdir",
    }
)
_POWERSHELL_FILE_PATH_COMMANDS = frozenset({"out-file", "tee-object", "tee"})
_POWERSHELL_COPY_COMMANDS = frozenset({"copy-item", "cp", "copy", "cpi"})
_POWERSHELL_MOVE_COMMANDS = frozenset({"move-item", "mv", "move", "mi", "rename-item", "rni", "ren"})
_POWERSHELL_READ_ONLY_COMMANDS = frozenset(
    {
        "get-content",
        "gc",
        "cat",
        "type",
        "get-childitem",
        "gci",
        "dir",
        "ls",
        "test-path",
    }
)
_POWERSHELL_PATH_PARAMETERS = frozenset({"path", "literalpath"})
_POWERSHELL_OUT_FILE_PATH_PARAMETERS = frozenset({"filepath", "literalpath"})
_POWERSHELL_DESTINATION_PARAMETERS = frozenset({"destination"})
_POWERSHELL_MOVE_DESTINATION_PARAMETERS = frozenset({"destination", "newname"})
_POWERSHELL_VALUE_PARAMETERS = frozenset(
    {
        "value",
        "inputobject",
        "encoding",
        "stream",
        "width",
        "credential",
        "filter",
        "include",
        "exclude",
    }
)
_POWERSHELL_SWITCH_PARAMETERS = frozenset(
    {
        "force",
        "recurse",
        "confirm",
        "whatif",
        "verbose",
        "debug",
        "erroraction",
        "warningaction",
        "informationaction",
        "errorvariable",
        "warningvariable",
        "informationvariable",
        "outvariable",
        "outbuffer",
        "append",
        "noclobber",
        "nonewline",
        "passthru",
    }
)
_POWERSHELL_BOOLEAN_LITERALS = frozenset({"$true", "$false", "$null"})


@dataclass(frozen=True)
class _PowerShellToken:
    value: str
    variable_expansion: bool = False


def extract_powershell_write_delete_targets(command: str) -> PowerShellTargetExtraction:
    """Extract write/delete targets from a limited PowerShell command subset.

    The parser tokenizes PowerShell quoting/backtick escapes and then walks
    cmdlet parameters/positional arguments. It is intentionally conservative:
    dynamic command names, variables in target arguments, and unrecognized
    commands are ambiguous rather than allowed.
    """

    stripped = command.strip()
    if not stripped:
        return PowerShellTargetExtraction((), (), False, False, "empty_command")

    try:
        tokens = _powershell_tokenize(stripped)
    except ValueError as exc:
        return PowerShellTargetExtraction(
            (),
            (),
            True,
            False,
            f"powershell_tokenize_error:{exc.__class__.__name__}",
        )

    if not tokens:
        return PowerShellTargetExtraction((), (), False, False, "empty_command")

    operations: list[tuple[str, str]] = []
    ambiguous_reasons: list[str] = []
    read_only_seen = False
    command_seen = False
    if any(token.value in _POWERSHELL_GROUPING_TOKENS for token in tokens):
        ambiguous_reasons.append("powershell_subexpression_or_script_block")
    directory = ""

    for statement in _split_powershell_statements(tokens):
        if not statement:
            continue

        if (
            command_name(statement[0].value) in _DIRECTORY_CHANGE_COMMANDS
            and len(statement) == 2
            and not statement[1].variable_expansion
        ):
            # Later relative targets in the same command resolve from here. The
            # command stays unproven, so this can only add a deny, never an allow.
            directory = posixpath.join(directory, _forward_slashes(statement[1].value))
            command_seen = True
            ambiguous_reasons.append("powershell_directory_change")
            continue
        if directory:
            statement = _powershell_statement_from_directory(statement, directory)

        (
            redirect_ops,
            clean_statement,
            redirect_ambiguous,
        ) = _powershell_redirection_operations(statement)
        operations.extend(redirect_ops)
        if redirect_ambiguous:
            ambiguous_reasons.append(redirect_ambiguous)

        pipeline_segments = _split_powershell_pipeline(clean_statement)
        pipeline = len(pipeline_segments) > 1
        pipeline_had_write = bool(redirect_ops)
        pipeline_had_unknown = False

        for index, segment in enumerate(pipeline_segments):
            if not segment:
                continue
            result = _powershell_segment_operations(segment)
            command_seen = command_seen or result.command_seen
            read_only_seen = read_only_seen or result.read_only
            operations.extend(result.operations)
            pipeline_had_write = pipeline_had_write or bool(result.operations)
            if result.ambiguous_reason:
                if pipeline and index < len(pipeline_segments) - 1:
                    pipeline_had_unknown = True
                else:
                    ambiguous_reasons.append(result.ambiguous_reason)

        if pipeline and pipeline_had_unknown and not pipeline_had_write:
            ambiguous_reasons.append("powershell_pipeline_without_known_write_target")
        elif pipeline and pipeline_had_unknown:
            ambiguous_reasons.append("powershell_pipeline_has_unclassified_input")

    unique_operations = tuple(dict.fromkeys(operations))
    unique_targets = tuple(dict.fromkeys(path for _, path in unique_operations))
    parse_ambiguous = bool(ambiguous_reasons)
    if parse_ambiguous:
        reason = ";".join(dict.fromkeys(ambiguous_reasons))
    elif unique_operations:
        reason = "powershell_write_delete_targets_extracted"
    elif read_only_seen and command_seen:
        reason = "powershell_read_only_command_no_write_delete_target"
    elif command_seen:
        reason = "powershell_no_write_delete_target"
    else:
        reason = "powershell_no_command"

    return PowerShellTargetExtraction(
        unique_targets,
        unique_operations,
        parse_ambiguous,
        read_only_seen and command_seen and not unique_operations and not parse_ambiguous,
        reason,
    )


@dataclass(frozen=True)
class _PowerShellSegmentResult:
    operations: tuple[tuple[str, str], ...]
    ambiguous_reason: str | None
    read_only: bool = False
    command_seen: bool = False


def _powershell_statement_from_directory(
    statement: list[_PowerShellToken],
    directory: str,
) -> list[_PowerShellToken]:
    """Rewrite a statement's non-parameter arguments as if run from ``directory``."""

    rewritten = statement[:1]
    for token in statement[1:]:
        if (
            token.value in _POWERSHELL_REDIRECT_OPS
            or token.value in {",", _POWERSHELL_PIPE_OPERATOR}
            or _powershell_is_parameter(token.value)
        ):
            rewritten.append(token)
        else:
            rewritten.append(
                _PowerShellToken(_relative_to_directory(token.value, directory), token.variable_expansion)
            )
    return rewritten


def powershell_argvs(command: str) -> tuple[tuple[str, ...], ...]:
    """Return every simple command of a PowerShell string, grouping removed."""

    try:
        tokens = _powershell_tokenize(command)
    except ValueError:
        return ()
    argvs: list[tuple[str, ...]] = []
    for statement in _split_powershell_statements(tokens):
        _, clean_statement, _ = _powershell_redirection_operations(statement)
        for segment in _split_powershell_pipeline(clean_statement):
            argv = tuple(token.value for token in segment if token.value != ",")
            if argv:
                argvs.append(argv)
    return tuple(argvs)


def powershell_words(command: str, *, depth: int = 0) -> tuple[str, ...]:
    """Return every literal word of a PowerShell string, nested commands included."""

    try:
        words = [token.value for token in _powershell_tokenize(command)]
    except ValueError:
        return ()
    for argv in powershell_argvs(command):
        words.extend(inline_code_words(argv))
        if depth < 4:
            for payload in nested_shell_payloads(argv):
                words.extend(powershell_words(payload, depth=depth + 1))
    return tuple(words)


def _powershell_tokenize(command: str) -> tuple[_PowerShellToken, ...]:
    command = command.translate(_POWERSHELL_TYPOGRAPHIC_FORMS)
    tokens: list[_PowerShellToken] = []
    current: list[str] = []
    current_variable = False
    index = 0
    length = len(command)

    def emit() -> None:
        nonlocal current, current_variable
        if current:
            tokens.append(_PowerShellToken("".join(current), current_variable))
            current = []
            current_variable = False

    while index < length:
        char = command[index]

        if char in "\r\n":
            # A line break ends the statement; it is not mere whitespace.
            emit()
            tokens.append(_PowerShellToken(";"))
            index += 1
            continue
        if char.isspace():
            emit()
            index += 1
            continue

        two = command[index : index + 2]
        if two == "<#" and not current:
            end = command.find("#>", index + 2)
            index = length if end == -1 else end + 2
            continue
        if two in ("&&", "||", ">>"):
            emit()
            tokens.append(_PowerShellToken(two))
            index += 2
            continue
        if char == "&" and tokens and tokens[-1].value in {">", ">>"} and not current:
            # ``2>&1`` merges streams; the ampersand is not an operator here.
            current.append(char)
            index += 1
            continue
        if char in (";", "|", ">", ",", "&", "(", ")", "{", "}"):
            emit()
            tokens.append(_PowerShellToken(char))
            index += 1
            continue
        if char == "#" and not current:
            newline = min(
                (position for position in (command.find("\n", index), command.find("\r", index)) if position != -1),
                default=length,
            )
            index = newline
            continue
        if char == "`":
            if index + 1 >= length:
                raise ValueError("dangling_backtick_escape")
            if command[index + 1] in "\r\n":
                # Line continuation joins the two lines into one statement.
                emit()
                index += 3 if command[index + 1 : index + 3] == "\r\n" else 2
                continue
            current.append(command[index + 1])
            index += 2
            continue
        if char in "'\"":
            # A quote that opens a word also ends it: '.env'-Force is two arguments.
            opens_word = not current
            if char == "'":
                index = _consume_powershell_single_quoted(command, index + 1, current)
            else:
                index, had_variable = _consume_powershell_double_quoted(command, index + 1, current)
                current_variable = current_variable or had_variable
            if opens_word:
                emit()
            continue

        current.append(char)
        current_variable = current_variable or char == "$"
        index += 1

    emit()
    return tuple(_combine_powershell_stream_redirect_tokens(tokens))


def _consume_powershell_single_quoted(command: str, index: int, current: list[str]) -> int:
    length = len(command)
    while index < length:
        char = command[index]
        if char == "'":
            if index + 1 < length and command[index + 1] == "'":
                current.append("'")
                index += 2
                continue
            return index + 1
        current.append(char)
        index += 1
    raise ValueError("unterminated_single_quote")


def _consume_powershell_double_quoted(
    command: str,
    index: int,
    current: list[str],
) -> tuple[int, bool]:
    length = len(command)
    had_variable = False
    while index < length:
        char = command[index]
        if char == '"':
            return (index + 1, had_variable)
        if char == "`":
            if index + 1 >= length:
                raise ValueError("dangling_backtick_escape")
            current.append(command[index + 1])
            index += 2
            continue
        current.append(char)
        had_variable = had_variable or char == "$"
        index += 1
    raise ValueError("unterminated_double_quote")


def _combine_powershell_stream_redirect_tokens(
    tokens: tuple[_PowerShellToken, ...],
) -> tuple[_PowerShellToken, ...]:
    combined: list[_PowerShellToken] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            token.value in {"1", "2", "3", "4", "5", "6", "*"}
            and index + 1 < len(tokens)
            and tokens[index + 1].value in {">", ">>"}
        ):
            combined.append(
                _PowerShellToken(
                    token.value + tokens[index + 1].value,
                    token.variable_expansion or tokens[index + 1].variable_expansion,
                )
            )
            index += 2
            continue
        combined.append(token)
        index += 1
    return tuple(combined)


def _split_powershell_statements(
    tokens: tuple[_PowerShellToken, ...],
) -> list[list[_PowerShellToken]]:
    statements: list[list[_PowerShellToken]] = []
    current: list[_PowerShellToken] = []
    for token in tokens:
        boundary = token.value in _POWERSHELL_CONTROL_OPERATORS or token.value in _POWERSHELL_GROUPING_TOKENS
        # A leading ampersand is the call operator; anywhere else it starts a job.
        if boundary or (token.value == _POWERSHELL_BACKGROUND_OPERATOR and current):
            if current:
                statements.append(current)
                current = []
        else:
            current.append(token)
    if current:
        statements.append(current)
    return statements


def _split_powershell_pipeline(
    tokens: list[_PowerShellToken],
) -> list[list[_PowerShellToken]]:
    segments: list[list[_PowerShellToken]] = []
    current: list[_PowerShellToken] = []
    for token in tokens:
        if token.value == _POWERSHELL_PIPE_OPERATOR:
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return segments


def _powershell_redirection_operations(
    tokens: list[_PowerShellToken],
) -> tuple[tuple[tuple[str, str], ...], list[_PowerShellToken], str | None]:
    operations: list[tuple[str, str]] = []
    clean: list[_PowerShellToken] = []
    ambiguous_reason: str | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.value in _POWERSHELL_REDIRECT_OPS:
            if index + 1 >= len(tokens):
                ambiguous_reason = "powershell_redirect_missing_target"
                break
            target = tokens[index + 1]
            if target.value.startswith("&"):
                index += 2
                continue
            if target.variable_expansion:
                ambiguous_reason = "powershell_redirect_target_uses_variable"
                break
            operations.append(("write", target.value))
            index += 2
            continue
        clean.append(token)
        index += 1
    return (tuple(operations), clean, ambiguous_reason)


def _powershell_segment_operations(
    segment: list[_PowerShellToken],
) -> _PowerShellSegmentResult:
    if not segment:
        return _PowerShellSegmentResult((), None)

    command_token = segment[0]
    if command_token.value in {"&", "."} or command_token.variable_expansion:
        return _PowerShellSegmentResult(
            (),
            "powershell_dynamic_command_invocation",
            command_seen=True,
        )

    command = _powershell_command_name(command_token.value)
    args = segment[1:]

    if command in _POWERSHELL_DELETE_COMMANDS:
        return _powershell_delete_operations(args)
    if command in _POWERSHELL_WRITE_COMMANDS:
        return _powershell_write_operations(command, args)
    if command in _POWERSHELL_COPY_COMMANDS:
        return _powershell_copy_operations(args)
    if command in _POWERSHELL_MOVE_COMMANDS:
        return _powershell_move_operations(args)
    if command in {"powershell", "pwsh"}:
        payloads = nested_shell_payloads(tuple(token.value for token in segment))
        operations = tuple(
            operation
            for payload in payloads
            for operation in extract_powershell_write_delete_targets(payload).target_operations
        )
        return _PowerShellSegmentResult(operations, "powershell_nested_shell", command_seen=True)
    if command in _POWERSHELL_READ_ONLY_COMMANDS:
        if _powershell_args_have_unapproved_variables(args):
            return _PowerShellSegmentResult(
                (),
                "powershell_read_only_arguments_use_variable",
                read_only=True,
                command_seen=True,
            )
        return _PowerShellSegmentResult((), None, read_only=True, command_seen=True)

    if _powershell_args_have_unapproved_variables(args):
        return _PowerShellSegmentResult(
            (),
            "powershell_unknown_command_or_arguments_use_variable",
            command_seen=True,
        )
    return _PowerShellSegmentResult(
        (),
        f"powershell_unrecognized_command:{command}",
        command_seen=True,
    )


def _powershell_delete_operations(args: list[_PowerShellToken]) -> _PowerShellSegmentResult:
    path_values, ambiguous = _powershell_collect_path_values(
        args,
        named_path_parameters=_POWERSHELL_PATH_PARAMETERS,
        positional_count=None,
    )
    if ambiguous is not None:
        return _PowerShellSegmentResult((), ambiguous, command_seen=True)
    if not path_values:
        return _PowerShellSegmentResult(
            (),
            "powershell_remove_item_missing_target",
            command_seen=True,
        )
    return _PowerShellSegmentResult(
        tuple(("delete", path) for path in path_values),
        None,
        command_seen=True,
    )


def _powershell_write_operations(
    command: str,
    args: list[_PowerShellToken],
) -> _PowerShellSegmentResult:
    named_parameters = (
        _POWERSHELL_OUT_FILE_PATH_PARAMETERS
        if command in _POWERSHELL_FILE_PATH_COMMANDS
        else _POWERSHELL_PATH_PARAMETERS
    )
    path_values, ambiguous = _powershell_collect_path_values(
        args,
        named_path_parameters=named_parameters,
        positional_count=1,
    )
    if ambiguous is not None:
        return _PowerShellSegmentResult((), ambiguous, command_seen=True)
    if not path_values:
        return _PowerShellSegmentResult(
            (),
            f"powershell_{command}_missing_target",
            command_seen=True,
        )
    return _PowerShellSegmentResult(
        tuple(("write", path) for path in path_values),
        None,
        command_seen=True,
    )


def _powershell_move_operations(args: list[_PowerShellToken]) -> _PowerShellSegmentResult:
    """A move or rename removes its source as well as writing its destination."""

    sources: list[_PowerShellToken] = []
    destinations: list[_PowerShellToken] = []
    positionals: list[_PowerShellToken] = []
    index = 0
    while index < len(args):
        token = args[index]
        index += 1
        if token.value == ",":
            continue
        if not _powershell_is_parameter(token.value):
            positionals.append(token)
            continue
        name, inline_value = _powershell_parameter_name_and_inline_value(token.value)
        bucket = (
            sources
            if name in _POWERSHELL_PATH_PARAMETERS
            else destinations if name in _POWERSHELL_MOVE_DESTINATION_PARAMETERS else None
        )
        if bucket is None:
            if inline_value is None and name in _POWERSHELL_VALUE_PARAMETERS and index < len(args):
                index += 1
            continue
        if inline_value is not None:
            bucket.append(_PowerShellToken(inline_value, "$" in inline_value))
        elif index < len(args):
            bucket.append(args[index])
            index += 1
        else:
            return _PowerShellSegmentResult((), f"powershell_parameter_missing_value:{name}", command_seen=True)
    for bucket in (sources, destinations):
        if not bucket and positionals:
            bucket.append(positionals.pop(0))
    if not sources and not destinations:
        return _PowerShellSegmentResult((), "powershell_copy_move_missing_destination", command_seen=True)
    if any(token.variable_expansion for token in (*sources, *destinations)):
        return _PowerShellSegmentResult((), "powershell_positional_target_uses_variable", command_seen=True)
    return _PowerShellSegmentResult(
        (
            *(("delete", token.value) for token in sources),
            *(("write", token.value) for token in destinations),
        ),
        None,
        command_seen=True,
    )


def _powershell_copy_operations(
    args: list[_PowerShellToken],
) -> _PowerShellSegmentResult:
    path_values, ambiguous = _powershell_collect_path_values(
        args,
        named_path_parameters=_POWERSHELL_DESTINATION_PARAMETERS,
        positional_count=2,
        positional_target_index=1,
    )
    if ambiguous is not None:
        return _PowerShellSegmentResult((), ambiguous, command_seen=True)
    if not path_values:
        return _PowerShellSegmentResult(
            (),
            "powershell_copy_move_missing_destination",
            command_seen=True,
        )
    return _PowerShellSegmentResult(
        tuple(("write", path) for path in path_values),
        None,
        command_seen=True,
    )


def _powershell_collect_path_values(
    args: list[_PowerShellToken],
    *,
    named_path_parameters: frozenset[str],
    positional_count: int | None,
    positional_target_index: int = 0,
) -> tuple[tuple[str, ...], str | None]:
    paths: list[str] = []
    positionals: list[_PowerShellToken] = []
    index = 0
    stop_parsing = False

    while index < len(args):
        token = args[index]
        value = token.value

        if value == "--%":
            return ((), "powershell_stop_parsing_token_ambiguous")
        if value == "--":
            stop_parsing = True
            index += 1
            continue

        if not stop_parsing and _powershell_is_parameter(value):
            name, inline_value = _powershell_parameter_name_and_inline_value(value)
            if name in named_path_parameters:
                target_token: _PowerShellToken | None
                if inline_value is not None:
                    target_tokens = tuple(
                        _PowerShellToken(
                            item,
                            "$" in item
                            and item.lower() not in _POWERSHELL_BOOLEAN_LITERALS,
                        )
                        for item in _powershell_inline_argument_values(inline_value)
                    )
                elif index + 1 < len(args):
                    target_tokens, index = _powershell_collect_argument_list(
                        args,
                        index + 1,
                    )
                else:
                    return ((), f"powershell_parameter_missing_value:{name}")
                if not target_tokens:
                    return ((), f"powershell_parameter_missing_value:{name}")
                if any(target.variable_expansion for target in target_tokens):
                    return ((), f"powershell_target_parameter_uses_variable:{name}")
                paths.extend(target.value for target in target_tokens)
                index += 1
                continue
            if name in _POWERSHELL_DESTINATION_PARAMETERS:
                return ((), f"powershell_unexpected_destination_parameter:{name}")
            if (
                inline_value is None
                and name in _POWERSHELL_VALUE_PARAMETERS
                and index + 1 < len(args)
            ):
                index += 2
                continue
            index += 1
            continue

        positionals.append(token)
        index += 1

    if paths:
        return (tuple(paths), None)
    if positional_count is None:
        candidate_tokens = [token for token in positionals if token.value != ","]
    elif len(positionals) >= positional_count:
        candidate_tokens, _ = _powershell_collect_argument_list(
            positionals,
            positional_target_index,
        )
    else:
        candidate_tokens = []
    for token in candidate_tokens:
        if token.variable_expansion:
            return ((), "powershell_positional_target_uses_variable")
        paths.append(token.value)
    return (tuple(paths), None)


def _powershell_collect_argument_list(
    args: list[_PowerShellToken],
    start_index: int,
) -> tuple[tuple[_PowerShellToken, ...], int]:
    values: list[_PowerShellToken] = []
    index = start_index
    expect_value = True
    while index < len(args):
        token = args[index]
        if expect_value:
            if token.value == ",":
                break
            values.append(token)
            index += 1
            expect_value = False
            continue
        if token.value != ",":
            break
        if index + 1 >= len(args) or args[index + 1].value == ",":
            break
        index += 1
        expect_value = True
    return (tuple(values), index - 1)


def _powershell_inline_argument_values(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split(",") if item)


def _powershell_args_have_unapproved_variables(args: list[_PowerShellToken]) -> bool:
    for token in args:
        if not token.variable_expansion:
            continue
        if _powershell_is_parameter(token.value):
            name, inline_value = _powershell_parameter_name_and_inline_value(token.value)
            if inline_value is not None and inline_value.lower() in _POWERSHELL_BOOLEAN_LITERALS:
                continue
            if name in _POWERSHELL_SWITCH_PARAMETERS:
                continue
        if token.value.lower() in _POWERSHELL_BOOLEAN_LITERALS:
            continue
        return True
    return False


def _powershell_is_parameter(value: str) -> bool:
    return len(value) > 1 and value.startswith("-") and value != "--"


def _powershell_parameter_name_and_inline_value(value: str) -> tuple[str, str | None]:
    body = value.lstrip("-")
    if ":" in body:
        name, inline_value = body.split(":", 1)
        return (name.lower(), inline_value)
    return (body.lower(), None)


def _powershell_command_name(value: str) -> str:
    return command_name(value)


_APPLY_PATCH_BEGIN = "*** Begin Patch"
_APPLY_PATCH_END = "*** End Patch"
_APPLY_PATCH_END_OF_FILE = "*** End of File"
_APPLY_PATCH_ADD_FILE = "*** Add File: "
_APPLY_PATCH_UPDATE_FILE = "*** Update File: "
_APPLY_PATCH_DELETE_FILE = "*** Delete File: "
_APPLY_PATCH_MOVE_TO = "*** Move to: "
_APPLY_PATCH_PATH_DIRECTIVES = (
    _APPLY_PATCH_ADD_FILE,
    _APPLY_PATCH_UPDATE_FILE,
    _APPLY_PATCH_DELETE_FILE,
    _APPLY_PATCH_MOVE_TO,
)


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


def rewrite_apply_patch_targets(command: str, rewrite: Callable[[str], str]) -> str:
    """Return the patch with each directive's path replaced by ``rewrite(path)``.

    Lines split the way ``extract_apply_patch_targets`` splits them, so the result
    declares the same operations. Text with nothing to replace comes back unchanged.
    """

    lines = command.splitlines()
    changed = False
    for index, line in enumerate(lines):
        for prefix in _APPLY_PATCH_PATH_DIRECTIVES:
            path = _apply_patch_directive_path(line, prefix)
            if path is None:
                continue
            rewritten = rewrite(path)
            if rewritten != path:
                lines[index] = prefix + rewritten
                changed = True
            break
    return "\n".join(lines) if changed else command


def _apply_patch_directive_path(line: str, prefix: str) -> str | None:
    if not line.startswith(prefix):
        return None
    path = line[len(prefix) :]
    return _normalize_apply_patch_directive_path(path)


def _normalize_apply_patch_directive_path(path: str) -> str | None:
    if not path or path != path.strip() or "\x00" in path:
        return None
    if path[0] in ("'", '"') or path[-1] in ("'", '"'):
        if len(path) < 2 or path[0] != path[-1] or path[0] not in ("'", '"'):
            return None
        path = path[1:-1]
        if not path or path != path.strip() or "\x00" in path:
            return None
    if "'" in path or '"' in path:
        return None
    return path


def _bash_segment_delete_targets(segment: list[str]) -> list[str]:
    """Targets that stop existing, which can take a whole protected tree with them."""

    clean = list(strip_assignments(segment))
    if not clean:
        return []
    command = command_name(clean[0])
    non_flag = [arg for arg in clean[1:] if not arg.startswith("-")]
    if command in ("rm", "rmdir", "unlink", "shred"):
        return non_flag
    if command == "mv":
        return non_flag[:-1]
    if command == "git":
        subcommand, rest = git_subcommand(clean[1:])
        paths = [arg for arg in rest if not arg.startswith("-")]
        return paths if subcommand == "rm" else paths[:-1] if subcommand == "mv" else []
    return []


def _bash_segment_write_delete_targets(segment: list[str]) -> list[str]:
    clean = list(strip_assignments(segment))
    if not clean:
        return []

    command = command_name(clean[0])
    args = clean[1:]
    non_flag = [arg for arg in args if not arg.startswith("-")]

    if command not in _BASH_WRITE_DELETE_COMMANDS:
        return []
    if command in ("tee", "rm", "rmdir", "unlink", "shred", "touch", "mkdir"):
        return non_flag
    if command == "mv":
        # A move removes every source as well as writing the destination.
        return non_flag if len(non_flag) >= 2 else []
    if command in ("cp", "install", "ln"):
        return non_flag[-1:] if len(non_flag) >= 2 else []
    if command == "dd":
        return [arg[len("of=") :] for arg in args if arg.startswith("of=")]
    if command == "truncate":
        return [arg for arg in non_flag if not arg.isdigit()]
    if command == "sed":
        in_place = any(arg.startswith(("-i", "--in-place")) for arg in args)
        return non_flag[1:] if in_place else []
    subcommand, rest = git_subcommand(args)
    if subcommand in {"rm", "mv"}:
        return [arg for arg in rest if not arg.startswith("-")]
    return []


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


def _looks_like_windows_drive_path(path_value: str) -> bool:
    """Drive-absolute (``C:/x``) or drive-relative (``C:x``): neither is in the repo."""

    return len(path_value) >= 2 and path_value[1] == ":" and path_value[0].isalpha()


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
