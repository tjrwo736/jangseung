"""Plain-language explanation of a hook decision, built from reason codes only.

Shared by ``aeg explain`` and by the reason the hook hands back to the host. No
input text, path or command ever reaches these sentences.
"""

from __future__ import annotations

from collections.abc import Iterable

from jangseung.evidence.mcp_tool_gate import (
    MCP_RESOURCE_READ_REQUIRES_APPROVAL,
    MCP_TOOL_REQUIRES_APPROVAL,
)

# Kept as literals so this module stays light; the engine defines the same codes.
REVIEW_TIER_REASON = "build_or_dependency_file_change_needs_user_review"
APPROVAL_HELD_REASON = "approved_command_held_after_write_naming_secret_file"


def explain_decision(
    *,
    reason_codes: Iterable[str],
    hook_decision: str | None,
    permission_decision: str,
    fail_closed: bool,
) -> tuple[str, str, str]:
    """Return ``(category, summary, next_step)`` for one decision."""

    codes = set(reason_codes)
    if fail_closed:
        if codes & {"internal_judgment_error_fail_closed_deny", "input_validation_error_fail_closed_deny"}:
            return ("internal_error", "The hook could not complete validation or judgment and denied by default.",
                    "Report the reason codes and package version; do not include raw credentials or disable the hook.")
        return ("invalid_input", "The hook input is malformed, incomplete, or uses an unsupported tool.",
                "Check the PreToolUse JSON shape: tool_name, tool_input and tool_use_id are required.")
    if permission_decision == "host":
        return ("host_permission_flow",
                "Jangseung makes no permission decision for this execution request in Claude Code default mode.",
                "The host's existing allow, ask and deny rules decide. This is not a claim that the command is safe "
                "or that the host asked a person; existing approvals may run it without another prompt.")
    if REVIEW_TIER_REASON in codes:
        return ("build_file_review",
                "This changes a build, CI or dependency file, which runs code on the next install, build, test or commit.",
                "Approve the prompt if the change is expected. A person can stop the question with: "
                "aeg policy add --path <path> (a bare file name applies in every folder)")
    if APPROVAL_HELD_REASON in codes:
        return ("approval_held",
                "A command approved in the project policy was held because this session wrote text that names a secret file.",
                "Review what this session wrote, then approve the prompt or run the command yourself. "
                "A new session starts without the hold.")
    if codes & {"shell_read_targets_secret_state_or_outside_repo", "shell_command_references_secret_path"}:
        return ("secret_or_outside_read", "The command reads a secret, protected state or a path outside the repository.",
                "Run it yourself if it is needed, or list the path under allow_paths in .aeg/policy.json.")
    if codes & {"dangerous_bash_gate_denies_command", "dangerous_powershell_gate_denies_command"}:
        return ("dangerous_command", "The existing command-risk gate identified a dangerous command.",
                "Review the intended operation and narrow its scope; this diagnostic does not authorize execution.")
    if "repo_boundary_gate_denies_outside_repo_target" in codes:
        return ("outside_repository", "The target resolves outside the repository boundary.",
                "Check the project directory and target path, including traversal and symbolic links.")
    if "aeg_integrity_guard_denies_state_dir_target" in codes:
        return ("protected_state", "The request targets protected Aegis state.",
                "Use the evidence commands to inspect records; do not modify the ledger directly.")
    if codes & {"bash_write_delete_target_protected_or_out_of_scope", "powershell_write_delete_target_protected_or_out_of_scope", "protected_path_gate_denies_target"}:
        return ("protected_or_outside_target", "A write/delete target is protected or outside the allowed repository scope.",
                "Review target paths and the intended change before proceeding.")
    if "law_requires_user_gate_hook_uses_deny_safe_default" in codes:
        return ("policy_gate", "The existing policy requires a user gate, so the hook denies by default.",
                "Review protected paths and policy requirements; the explanation does not grant an exception.")
    if any(code.startswith("capability_gate_denies:") for code in codes):
        return ("capability_denied", "The existing capability gate does not permit this request.",
                "Review the requested action and scope; no additional authority is granted here.")
    if codes & {MCP_TOOL_REQUIRES_APPROVAL, MCP_RESOURCE_READ_REQUIRES_APPROVAL}:
        return ("mcp_approval_required",
                "The opt-in MCP hook requires a person's approval for this MCP call; its arguments are not inspected.",
                "Approve it in the host if you trust the tool, or list the tool under allow_mcp_tools in .aeg/policy.json. "
                "Resource reads cannot be listed.")
    if hook_decision == "defer":
        return ("unclassified", "Safety was not established by the current rules; this is not a finding that the command is dangerous.",
                "Check supported command syntax and whether file targets exist inside the repository. Unsupported flags, expansions or missing files can prevent classification.")
    if permission_decision == "allow":
        return ("allowed", "The existing hook rules allow this request in the current filesystem context.",
                "This is a dry-run result, not proof that the host application ran the hook or the tool.")
    if hook_decision == "ask":
        return ("confirmation_required", "The judgment engine requires user confirmation for this request.",
                "Review the requested operation. The selected substrate determines how confirmation is enforced.")
    return ("denied", "The existing hook gates denied the request.",
            "Use the reason codes when reporting the issue; do not include raw secrets.")


# What a person can do about a stop, said to whoever reads the host's message.
_HOOK_NEXT_STEPS = {
    "unclassified": (
        "A person can approve it in the prompt, run it themselves, or allow the command for this project with: "
        "aeg policy add --command \"<command>\""
    ),
    "secret_or_outside_read": (
        "A person can run it themselves. To open a path to agents, a person can run: aeg policy add --path <path> "
        "(a bare file name applies in every folder)"
    ),
    "protected_or_outside_target": (
        "A person can make the change themselves. For a protected project path, a person can run: "
        "aeg policy add --path <path> (a bare file name applies in every folder)"
    ),
    "policy_gate": (
        "A person can make the change themselves. For a protected project path, a person can run: "
        "aeg policy add --path <path> (a bare file name applies in every folder)"
    ),
    "dangerous_command": (
        "A person can run it themselves, or allow this exact command prefix for the project with: "
        "aeg policy add --command \"<command>\""
    ),
}


_READ_TOOL_NAMES = frozenset({"Read", "Grep", "Glob"})
_PATH_STOP_CATEGORIES = frozenset({"protected_or_outside_target", "policy_gate", "capability_denied", "denied"})


def hook_reason_sentence(
    *,
    reason_codes: Iterable[str],
    hook_decision: str | None,
    permission_decision: str,
    fail_closed: bool,
    tool_name: object = None,
) -> str:
    """One readable line for a deny or ask; empty for an allow."""

    if permission_decision == "allow":
        return ""
    category, summary, next_step = explain_decision(
        reason_codes=reason_codes,
        hook_decision=hook_decision,
        permission_decision=permission_decision,
        fail_closed=fail_closed,
    )
    if tool_name in _READ_TOOL_NAMES and category in _PATH_STOP_CATEGORIES:
        # The codes are shared with writes; the tool says which sentence is true.
        return (
            "Jangseung: This reads a secret file, the guard's own records or a path outside the project. "
            + _HOOK_NEXT_STEPS["secret_or_outside_read"]
        )
    return f"Jangseung: {summary} {_HOOK_NEXT_STEPS.get(category, next_step)}"


__all__ = ["APPROVAL_HELD_REASON", "REVIEW_TIER_REASON", "explain_decision", "hook_reason_sentence"]
