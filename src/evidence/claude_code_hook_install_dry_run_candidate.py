"""Phase 11-D-1 Claude Code hook install dry-run / settings candidate.

This module builds and validates a `.claude/settings.json`-shaped candidate
for registering a Claude Code PreToolUse hook, and diagnoses whether the
Aegis hook entrypoint actually performs the stdin/stdout/exit-code I/O a real
Claude Code hook command requires. It does not write `.claude/settings.json`
(project-local or user-global), does not install a hook, does not execute
Claude Code, does not perform stdin/stdout hook response emission, does not
execute any tool, and does not mutate the filesystem.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT

PHASE11D_1_HOOK_INSTALL_DRY_RUN_CANDIDATE_VERSION = (
    "phase11d_1_claude_code_hook_install_dry_run_settings_candidate_v0"
)
PHASE11D_1_COMPLETE_LABEL = (
    "PHASE11D_1_CLAUDE_CODE_HOOK_INSTALL_DRY_RUN_SETTINGS_CANDIDATE_COMPLETE_NOT_INSTALLED_NOT_LIVE"
)

SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL = "project_local"
SETTINGS_CANDIDATE_PATH_IF_INSTALLED = ".claude/settings.json"
FORBIDDEN_GLOBAL_SETTINGS_PATH = "~/.claude/settings.json"

HOOK_EVENT_NAME_PRETOOLUSE = "PreToolUse"
HOOK_MATCHER_CANDIDATE = "Write|Edit|Bash|Read"
HOOK_MATCHER_TARGET_TOOLS = ("Write", "Edit", "Bash", "Read")
HOOK_COMMAND_TYPE_CANDIDATE = "command"
HOOK_COMMAND_CANDIDATE = "aeg hook-run"
HOOK_COMMAND_ENTRYPOINT_SUBCOMMAND = "hook-run"

VALID_SETTINGS_CANDIDATE = "VALID_SETTINGS_CANDIDATE"
INVALID_SETTINGS_CANDIDATE = "INVALID_SETTINGS_CANDIDATE"

# Tokens are split so this diagnostic module's own source text does not
# itself contain a literal match when the src/ tree is scanned for real
# stdin/stdout/exit hook I/O.
_STDIN_STDOUT_EXIT_TOKENS: tuple[str, ...] = (
    "sys." + "stdin",
    "sys." + "stdout",
    "sys." + "stderr",
    "sys." + "exit(",
)

_ADD_PARSER_NAME_PATTERN = re.compile(r"add_parser\(\s*[\"']([a-zA-Z0-9_-]+)[\"']")


@dataclass(frozen=True)
class SettingsCandidateValidationResult:
    valid: bool
    status: str
    reasons: tuple[str, ...]
    matcher_covers_target_tools: bool
    command_references_aeg_entrypoint: bool
    scope: str = SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL

    def to_record(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status,
            "reasons": self.reasons,
            "matcher_covers_target_tools": self.matcher_covers_target_tools,
            "command_references_aeg_entrypoint": self.command_references_aeg_entrypoint,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class HookEntrypointStdinStdoutDiagnosis:
    scanned_root: str
    stdin_stdout_exit_tokens_checked: tuple[str, ...]
    files_with_stdin_stdout_exit_io: tuple[str, ...]
    entrypoint_stdin_stdout_exit_wired: bool
    hook_run_subcommand_exists: bool
    diagnosis: str

    def to_record(self) -> dict[str, Any]:
        return {
            "scanned_root": self.scanned_root,
            "stdin_stdout_exit_tokens_checked": self.stdin_stdout_exit_tokens_checked,
            "files_with_stdin_stdout_exit_io": self.files_with_stdin_stdout_exit_io,
            "entrypoint_stdin_stdout_exit_wired": self.entrypoint_stdin_stdout_exit_wired,
            "hook_run_subcommand_exists": self.hook_run_subcommand_exists,
            "diagnosis": self.diagnosis,
        }


def build_claude_code_settings_candidate() -> dict[str, Any]:
    """Return an in-memory `.claude/settings.json`-shaped hook registration
    candidate. This is not written to disk anywhere by this function."""

    return {
        "hooks": {
            HOOK_EVENT_NAME_PRETOOLUSE: [
                {
                    "matcher": HOOK_MATCHER_CANDIDATE,
                    "hooks": [
                        {
                            "type": HOOK_COMMAND_TYPE_CANDIDATE,
                            "command": HOOK_COMMAND_CANDIDATE,
                        }
                    ],
                }
            ]
        }
    }


def validate_claude_code_settings_candidate(
    candidate: Mapping[str, Any],
) -> SettingsCandidateValidationResult:
    """Validate the structural shape of a settings candidate against the
    documented Claude Code hook registration contract. This performs no I/O:
    it does not read or write any real settings file."""

    reasons: list[str] = []

    hooks_section = candidate.get("hooks") if isinstance(candidate, Mapping) else None
    if not isinstance(hooks_section, Mapping):
        reasons.append("missing_or_invalid_hooks_section")
        return _rejected_result(reasons)

    pretooluse_entries = hooks_section.get(HOOK_EVENT_NAME_PRETOOLUSE)
    if not isinstance(pretooluse_entries, Sequence) or isinstance(pretooluse_entries, (str, bytes)) or not pretooluse_entries:
        reasons.append("missing_or_empty_pretooluse_entries")
        return _rejected_result(reasons)

    matcher_covers_target_tools = False
    command_references_aeg_entrypoint = False

    for entry in pretooluse_entries:
        if not isinstance(entry, Mapping):
            reasons.append("pretooluse_entry_must_be_mapping")
            continue

        matcher = entry.get("matcher")
        if not isinstance(matcher, str) or not matcher.strip():
            reasons.append("pretooluse_entry_missing_matcher")
        elif all(tool in matcher for tool in HOOK_MATCHER_TARGET_TOOLS):
            matcher_covers_target_tools = True

        nested_hooks = entry.get("hooks")
        if not isinstance(nested_hooks, Sequence) or isinstance(nested_hooks, (str, bytes)) or not nested_hooks:
            reasons.append("pretooluse_entry_missing_nested_hooks")
            continue

        for nested_hook in nested_hooks:
            if not isinstance(nested_hook, Mapping):
                reasons.append("nested_hook_must_be_mapping")
                continue
            if nested_hook.get("type") != HOOK_COMMAND_TYPE_CANDIDATE:
                reasons.append("nested_hook_type_must_be_command")
            command = nested_hook.get("command")
            if not isinstance(command, str) or not command.strip():
                reasons.append("nested_hook_missing_command")
            elif "aeg" in command:
                command_references_aeg_entrypoint = True

    if not matcher_covers_target_tools:
        reasons.append("matcher_does_not_cover_write_edit_bash_read")
    if not command_references_aeg_entrypoint:
        reasons.append("command_does_not_reference_aeg_entrypoint")

    valid = not reasons
    return SettingsCandidateValidationResult(
        valid=valid,
        status=VALID_SETTINGS_CANDIDATE if valid else INVALID_SETTINGS_CANDIDATE,
        reasons=tuple(reasons),
        matcher_covers_target_tools=matcher_covers_target_tools,
        command_references_aeg_entrypoint=command_references_aeg_entrypoint,
    )


def diagnose_hook_entrypoint_stdin_stdout_wiring() -> HookEntrypointStdinStdoutDiagnosis:
    """Honestly diagnose whether any module under ``src/`` performs real
    stdin/stdout/exit-code hook I/O, and whether the ``aeg hook-run``
    subcommand referenced by the settings candidate currently exists.

    This function only reads source text already on disk; it performs no
    process execution, no stdin/stdout I/O of its own, and no filesystem
    mutation.
    """

    src_root = Path(__file__).resolve().parent.parent
    self_path = Path(__file__).resolve()
    matches: dict[str, tuple[str, ...]] = {}

    for py_file in sorted(src_root.rglob("*.py")):
        if py_file.resolve() == self_path:
            continue
        text = py_file.read_text(encoding="utf-8")
        found = tuple(token for token in _STDIN_STDOUT_EXIT_TOKENS if token in text)
        if found:
            matches[py_file.relative_to(src_root.parent).as_posix()] = found

    wired = bool(matches)
    hook_run_exists = _hook_run_subcommand_exists(src_root)

    return HookEntrypointStdinStdoutDiagnosis(
        scanned_root="src/",
        stdin_stdout_exit_tokens_checked=_STDIN_STDOUT_EXIT_TOKENS,
        files_with_stdin_stdout_exit_io=tuple(sorted(matches)),
        entrypoint_stdin_stdout_exit_wired=wired,
        hook_run_subcommand_exists=hook_run_exists,
        diagnosis=(
            "stdin_stdout_exit_wiring_present_somewhere_in_src"
            if wired
            else "stdin_stdout_exit_wiring_not_present_anywhere_in_src_entrypoint_is_memory_candidate_only"
        ),
    )


def build_hook_install_dry_run_candidate_evidence(
    *,
    settings_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = dict(settings_candidate) if settings_candidate is not None else build_claude_code_settings_candidate()
    validation = validate_claude_code_settings_candidate(candidate)
    diagnosis = diagnose_hook_entrypoint_stdin_stdout_wiring()

    return {
        "contract_version": PHASE11D_1_HOOK_INSTALL_DRY_RUN_CANDIDATE_VERSION,
        "completion_label": PHASE11D_1_COMPLETE_LABEL,
        "settings_candidate": candidate,
        "settings_candidate_validation": validation.to_record(),
        "settings_candidate_scope": SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL,
        "settings_candidate_path_if_installed": SETTINGS_CANDIDATE_PATH_IF_INSTALLED,
        "forbidden_global_settings_path": FORBIDDEN_GLOBAL_SETTINGS_PATH,
        "global_settings_path_referenced_by_candidate": False,
        "entrypoint_stdin_stdout_diagnosis": diagnosis.to_record(),
        "settings_json_modified": False,
        "settings_json_modified_global": False,
        "hook_installed": False,
        "claude_code_execution_performed": False,
        "real_hook_response_emitted": False,
        "stdout_stderr_hook_output_written": False,
        "tool_execution_performed": False,
        "filesystem_mutation_by_dry_run": False,
        "dry_run_only": True,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }


def _hook_run_subcommand_exists(src_root: Path) -> bool:
    cli_main_path = src_root / "cli" / "main.py"
    if not cli_main_path.exists():
        return False
    text = cli_main_path.read_text(encoding="utf-8")
    registered_names = _ADD_PARSER_NAME_PATTERN.findall(text)
    return HOOK_COMMAND_ENTRYPOINT_SUBCOMMAND in registered_names


def _rejected_result(reasons: list[str]) -> SettingsCandidateValidationResult:
    return SettingsCandidateValidationResult(
        valid=False,
        status=INVALID_SETTINGS_CANDIDATE,
        reasons=tuple(reasons),
        matcher_covers_target_tools=False,
        command_references_aeg_entrypoint=False,
    )


__all__ = [
    "FORBIDDEN_GLOBAL_SETTINGS_PATH",
    "HOOK_COMMAND_CANDIDATE",
    "HOOK_COMMAND_ENTRYPOINT_SUBCOMMAND",
    "HOOK_EVENT_NAME_PRETOOLUSE",
    "HOOK_MATCHER_CANDIDATE",
    "HOOK_MATCHER_TARGET_TOOLS",
    "INVALID_SETTINGS_CANDIDATE",
    "PHASE11D_1_COMPLETE_LABEL",
    "PHASE11D_1_HOOK_INSTALL_DRY_RUN_CANDIDATE_VERSION",
    "SETTINGS_CANDIDATE_PATH_IF_INSTALLED",
    "SETTINGS_CANDIDATE_SCOPE_PROJECT_LOCAL",
    "VALID_SETTINGS_CANDIDATE",
    "HookEntrypointStdinStdoutDiagnosis",
    "SettingsCandidateValidationResult",
    "build_claude_code_settings_candidate",
    "build_hook_install_dry_run_candidate_evidence",
    "diagnose_hook_entrypoint_stdin_stdout_wiring",
    "validate_claude_code_settings_candidate",
]
