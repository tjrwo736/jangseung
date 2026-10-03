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

from src.cli.hook_run import HookRunResult, render_hook_response
from src.evidence.claude_code_pretooluse_input_contract import (
    OPTIONAL_HOOK_METADATA_FIELDS, REQUIRED_HOOK_INPUT_FIELDS, SUPPORTED_INITIAL_TARGET_TOOLS,
)
from src.evidence.hook_judgment_engine_alignment import ENGINE_DENY_CAPABILITY_RESULTS

MAX_INPUT_CHARACTERS = 1_048_576

_FIXED_CODES = frozenset({
    "repo_boundary_gate_denies_outside_repo_target",
    "aeg_integrity_guard_denies_state_dir_target",
    "tool_call_mapping_deny_candidate",
    "dangerous_bash_gate_denies_command",
    "bash_write_delete_target_protected_or_out_of_scope",
    "powershell_write_delete_target_protected_or_out_of_scope",
    "law_requires_user_gate_hook_uses_deny_safe_default",
    "hook_decision_matches_or_is_stricter_than_engine",
    "structurally_classified_read_only_shell_command",
    "shell_read_paths_are_regular_non_protected_files_in_repo",
    "powershell_read_only_command_has_no_write_delete_target",
    "powershell_read_only_maps_to_allow_without_path_deny",
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
    codes = set(result.reason_codes)
    if result.fail_closed:
        if codes & {"internal_judgment_error_fail_closed_deny", "input_validation_error_fail_closed_deny"}:
            return ("internal_error", "The hook could not complete validation or judgment and denied by default.",
                    "Report the reason codes and package version; do not include raw credentials or disable the hook.")
        return ("invalid_input", "The hook input is malformed, incomplete, or uses an unsupported tool.",
                "Check the PreToolUse JSON shape: tool_name, tool_input and tool_use_id are required.")
    if "dangerous_bash_gate_denies_command" in codes:
        return ("dangerous_command", "The existing command-risk gate identified a dangerous command.",
                "Review the intended operation and narrow its scope; this diagnostic does not authorize execution.")
    if "repo_boundary_gate_denies_outside_repo_target" in codes:
        return ("outside_repository", "The target resolves outside the repository boundary.",
                "Check the project directory and target path, including traversal and symbolic links.")
    if "aeg_integrity_guard_denies_state_dir_target" in codes:
        return ("protected_state", "The request targets protected Aegis state.",
                "Use the evidence commands to inspect records; do not modify the ledger directly.")
    if codes & {"bash_write_delete_target_protected_or_out_of_scope", "powershell_write_delete_target_protected_or_out_of_scope"}:
        return ("protected_or_outside_target", "A write/delete target is protected or outside the allowed repository scope.",
                "Review target paths and the intended change before proceeding.")
    if "law_requires_user_gate_hook_uses_deny_safe_default" in codes:
        return ("policy_gate", "The existing policy requires a user gate, so the hook denies by default.",
                "Review protected paths and policy requirements; the explanation does not grant an exception.")
    if any(code.startswith("capability_gate_denies:") for code in codes):
        return ("capability_denied", "The existing capability gate does not permit this request.",
                "Review the requested action and scope; no additional authority is granted here.")
    if result.hook_decision == "defer":
        return ("unclassified", "Safety was not established by the current rules; this is not a finding that the command is dangerous.",
                "Check supported command syntax and whether file targets exist inside the repository. Unsupported flags, expansions or missing files can prevent classification.")
    if result.permission_decision == "allow":
        return ("allowed", "The existing hook rules allow this request in the current filesystem context.",
                "This is a dry-run result, not proof that the host application ran the hook or the tool.")
    if result.hook_decision == "ask":
        return ("confirmation_required", "The judgment engine requires user confirmation for this request.",
                "Review the requested operation. The selected substrate determines how confirmation is enforced.")
    return ("denied", "The existing hook gates denied the request.",
            "Use the reason codes when reporting the issue; do not include raw secrets.")


def build_explanation(raw: str, *, repo_root: str | Path, substrate: str | None = None) -> dict[str, Any]:
    """Explain exactly one pure hook result without recording or executing it."""
    result = render_hook_response(raw, repo_root=repo_root, substrate=substrate)
    category, summary, next_step = _explanation(result)
    codes = [_display_code(code) for code in result.reason_codes]
    mapping = (
        "Codex mapping upgrades ask/defer to deny and returns hook exit code 0; exit 0 does not mean allow."
        if "codex_substrate_ask_not_enforced_upgraded_to_deny" in result.reason_codes else
        "Codex hook responses carry the permission decision in JSON and use exit code 0."
        if result.substrate == "codex" else
        "Claude Code mapping uses hook exit code 2 for deny and 0 for allow/ask."
    )
    return {
        "status": "FAIL_CLOSED" if result.fail_closed else "EXPLAINED",
        "mode": "dry-run", "substrate": result.substrate,
        "tool_name": result.tool_name if result.tool_name in SUPPORTED_INITIAL_TARGET_TOOLS else "unknown",
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
    stdin: TextIO, stdout: TextIO,
) -> int:
    try:
        if command is not None:
            raw = json.dumps({"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "explain-dry-run"})
        elif file is not None:
            raw = json.dumps({"tool_name": "Read", "tool_input": {"file_path": file}, "tool_use_id": "explain-dry-run"})
        else:
            raw = stdin.read(MAX_INPUT_CHARACTERS + 1)
        if len(raw) > MAX_INPUT_CHARACTERS:
            raise ValueError("input size limit")
        # Match hook-run's cwd semantics, including in a subdirectory/non-Git folder.
        report = build_explanation(raw, repo_root=cwd, substrate=substrate)
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
