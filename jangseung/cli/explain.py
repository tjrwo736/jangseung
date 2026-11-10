"""Read-only explanations of the existing hook decision, never an executor.

Only the pure hook renderer is called. Raw inputs, command text, paths and
arbitrary validator suffixes are not part of the display schema. This command
is diagnostic: its process exit status is NOT the simulated hook exit status.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, TextIO

from jangseung.cli.hook_run import (
    HookRunResult, read_stdin_text, render_hook_response, resolve_hook_project_root,
)
from jangseung.evidence.claude_code_pretooluse_input_contract import (
    OPTIONAL_HOOK_METADATA_FIELDS, REQUIRED_HOOK_INPUT_FIELDS, SUPPORTED_INITIAL_TARGET_TOOLS, is_mcp_tool_name,
)
from jangseung.evidence.hook_judgment_engine_alignment import ENGINE_DENY_CAPABILITY_RESULTS
from jangseung.cli.reason_text import APPROVAL_HELD_REASON, REVIEW_TIER_REASON, explain_decision
from jangseung.evidence.mcp_tool_gate import MCP_GATE_REASON_CODES

MAX_INPUT_CHARACTERS = 1_048_576

_FIXED_CODES = frozenset({
    "repo_boundary_gate_denies_outside_repo_target",
    "aeg_integrity_guard_denies_state_dir_target",
    "tool_call_mapping_deny_candidate",
    "dangerous_bash_gate_denies_command",
    "dangerous_powershell_gate_denies_command",
    "protected_path_gate_denies_target",
    "shell_read_targets_secret_state_or_outside_repo",
    "shell_command_references_secret_path",
    "hook_policy_approved_command",
    "bash_write_delete_target_protected_or_out_of_scope",
    "powershell_write_delete_target_protected_or_out_of_scope",
    "law_requires_user_gate_hook_uses_deny_safe_default",
    "hook_decision_matches_or_is_stricter_than_engine",
    "structurally_classified_read_only_shell_command",
    "shell_read_paths_are_regular_non_secret_files_in_repo",
    "hook_decision_matches_engine_decision",
    "engine_classified_normal_non_protected_in_repo_file_operation_as_safe",
    "clearly_safe_normal_work_maps_to_allow",
    "ambiguous_not_checked_or_unclassified_never_reaches_this_branch",
    "classification_law_and_capability_gate_allow_read_only_candidate",
    "write_or_edit_judgment_basis_is_target_path_risk_not_capability_gate",
    "normal_target_path_maps_to_ask_candidate",
    "aegis_self_write_file_capability_remains_denied_and_unrelated_to_hook_judgment",
    "not_checked_or_unclassified_maps_to_defer",
    "not_checked_unknown_or_unclassified_never_maps_to_allow",
    "safe_default_hold_current_state",
    "engine_basis_not_clean_maps_to_defer",
    "codex_substrate_ask_not_enforced_upgraded_to_deny",
    "invalid_json_stdin_fail_closed_deny",
    "non_object_json_stdin_fail_closed_deny",
    "invalid_or_unsupported_pretooluse_input_fail_closed_deny",
    "input_validation_error_fail_closed_deny",
    "internal_judgment_error_fail_closed_deny",
    "hook_decision_recording_failed",
    "output_excludes_read_protected_files",
    "claude_default_host_permission_flow",
    "structurally_classified_simple_file_operation",
    "shell_file_targets_are_regular_non_protected_paths_in_repo",
    APPROVAL_HELD_REASON,
    REVIEW_TIER_REASON,
    *MCP_GATE_REASON_CODES,
})
_DETAIL_CODES = frozenset({
    "missing_required_field", "invalid_required_field", "invalid_optional_metadata_field",
    "unsupported_or_unknown_tool_name", "raw_hook_input_contains_unsupported_contract_value",
    "unmapped_hook_decision_fail_closed_deny", "capability_gate_denies",
})
_SAFE_DETAIL_CODES = frozenset({
    *(f"missing_required_field:{field}" for field in REQUIRED_HOOK_INPUT_FIELDS),
    *(f"invalid_optional_metadata_field:{field}_must_be_string" for field in OPTIONAL_HOOK_METADATA_FIELDS),
    *(f"capability_gate_denies:{result}" for result in ENGINE_DENY_CAPABILITY_RESULTS),
    "invalid_required_field:tool_name_must_be_non_empty_string",
    "invalid_required_field:tool_input_must_be_mapping",
    "invalid_required_field:tool_use_id_must_be_non_empty_string",
})


def _display_code(code: str) -> str:
    if code in _FIXED_CODES | _SAFE_DETAIL_CODES or re.fullmatch(r"clearly_safe_impact=(?:LOW|MEDIUM)_risk=(?:LOW|MEDIUM)", code):
        return code
    prefix = code.partition(":")[0]
    # A validator may include an arbitrary tool name or value after ':'.
    return prefix if prefix in _DETAIL_CODES else "unrecognized_reason_code"


def _explanation(result: HookRunResult) -> tuple[str, str, str]:
    return explain_decision(
        reason_codes=result.reason_codes,
        hook_decision=result.hook_decision,
        permission_decision=result.permission_decision,
        fail_closed=result.fail_closed,
    )


def build_explanation(
    raw: str, *, repo_root: str | Path, substrate: str | None = None, working_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Explain exactly one pure hook result without recording or executing it."""
    result = render_hook_response(raw, repo_root=repo_root, substrate=substrate, working_dir=working_dir)
    category, summary, next_step = _explanation(result)
    codes = [_display_code(code) for code in result.reason_codes]
    mapping = (
        "Claude Code default mode: no permissionDecision is emitted; the host's normal permission rules decide."
        if result.permission_decision == "host" else
        "Codex mapping upgrades ask/defer to deny and returns hook exit code 0; exit 0 does not mean allow."
        if "codex_substrate_ask_not_enforced_upgraded_to_deny" in result.reason_codes else
        "Codex hook responses carry the permission decision in JSON and use exit code 0."
        if result.substrate == "codex" else
        "Claude Code mapping uses hook exit code 2 for deny and 0 for allow/ask."
    )
    return {
        "status": "FAIL_CLOSED" if result.fail_closed else "EXPLAINED",
        "mode": "dry-run", "substrate": result.substrate,
        "tool_name": (
            result.tool_name
            if result.tool_name in SUPPORTED_INITIAL_TARGET_TOOLS or is_mcp_tool_name(result.tool_name)
            else "unknown"
        ),
        "hook_decision": result.hook_decision, "permission_decision": result.permission_decision,
        "hook_exit_code": result.exit_code, "fail_closed": result.fail_closed,
        "category": category, "summary": summary, "substrate_mapping": mapping,
        "next_step": next_step, "reason_codes": list(dict.fromkeys(codes)),
        "reason_details_redacted": codes != list(result.reason_codes),
        "tool_execution_performed": False, "store_write_performed": False,
        "recording_status": "NOT_ATTEMPTED", "host_execution": "NOT_CHECKED",
    }


def cmd_explain(
    cwd: Path, *, command: str | None = None, file: str | None = None,
    tool: str = "Bash", substrate: str | None = None, as_json: bool = False,
    permission_mode: str | None = None,
    stdin: TextIO, stdout: TextIO,
) -> int:
    try:
        if command is not None:
            data = {"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "explain-dry-run"}
            if permission_mode is not None:
                data["permission_mode"] = permission_mode
            raw = json.dumps(data)
        elif file is not None:
            raw = json.dumps({"tool_name": "Read", "tool_input": {"file_path": file}, "tool_use_id": "explain-dry-run"})
        else:
            raw = read_stdin_text(stdin, limit=4 * MAX_INPUT_CHARACTERS)
        if len(raw) > MAX_INPUT_CHARACTERS:
            raise ValueError("input size limit")
        # Match hook-run's root and working directory, including in a subdirectory.
        report = build_explanation(
            raw, repo_root=resolve_hook_project_root(cwd), substrate=substrate, working_dir=cwd,
        )
    except Exception:  # Do not echo potentially sensitive input or exception text.
        report = {
            "status": "ERROR", "mode": "dry-run", "permission_decision": "NOT_CHECKED",
            "summary": "Could not read or explain the input. Use UTF-8 JSON under 1 Mi characters.",
            "tool_execution_performed": False, "store_write_performed": False,
        }
    if as_json:
        print(json.dumps(report, ensure_ascii=True, sort_keys=True), file=stdout)
    else:
        print("Aegis explain\nmode: dry-run (no tool execution, no recording)", file=stdout)
        for name in ("status", "substrate", "tool_name", "hook_decision", "permission_decision", "hook_exit_code", "fail_closed"):
            if name in report:
                print(f"{name}: {report[name]}", file=stdout)
        print("[explanation]", file=stdout)
        for name in ("category", "summary", "substrate_mapping", "next_step"):
            if name in report:
                print(f"{name}: {report[name]}", file=stdout)
        if report.get("reason_codes"):
            print("[reason codes]", file=stdout)
            for code in report["reason_codes"]:
                print(f"- {code}", file=stdout)
        print("host_execution: NOT_CHECKED", file=stdout)
    # Diagnostic success is different from permission to execute a tool.
    return 0 if report["status"] == "EXPLAINED" else 1
