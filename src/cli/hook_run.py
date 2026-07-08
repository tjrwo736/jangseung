"""Phase 11-D-2 ``aeg hook-run`` stdin/stdout/exit-code wiring.

This is the real I/O boundary that lets the existing in-memory Aegis hook
judgment brain (Phase 11-C-8 ``judge_pretooluse_with_aeg_engine``) act as a
Claude Code PreToolUse hook command: it reads untrusted PreToolUse JSON from
stdin, routes it through the unchanged judgment brain, and writes a
Claude Code ``hookSpecificOutput.permissionDecision`` response to stdout with a
spec-aligned exit code.

Safety properties enforced here (not in the judgment brain, which is not
modified by this module):

* stdin JSON is treated as untrusted raw executor output; it is never trusted
  as a decision or authority and is always routed through validate/map/judge.
* fail-closed: any parse failure, missing/invalid field, unknown tool, or
  internal exception resolves to ``deny`` with a blocking exit code. There is
  no code path where a failure resolves to ``allow``.
* the reason string carries only decision codes and the tool name, never raw
  ``tool_input`` content, so secrets in tool input are not echoed to stdout or
  stderr.

This module does not install a hook, modify ``.claude/settings.json``, execute
Claude Code itself, execute any tool, call a provider/model/network, or write
Aegis state.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence.claude_code_pretooluse_input_contract import (
    validate_claude_code_pretooluse_input,
)
from src.evidence.hook_decision_adapter import ALLOW, ASK, DEFER, DENY
from src.evidence.hook_judgment_engine_alignment import (
    judge_pretooluse_with_aeg_engine,
)

PHASE11D_2_AEG_HOOK_RUN_VERSION = "phase11d_2_aeg_hook_run_stdin_stdout_wiring_v0"
PHASE11D_2_COMPLETE_LABEL = (
    "PHASE11D_2_AEG_HOOK_RUN_STDIN_STDOUT_WIRING_COMPLETE_NOT_INSTALLED_NOT_LIVE"
)

CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE = "PreToolUse"

# PreToolUse permissionDecision values used by the supported hook substrates.
# There is no native "defer" value. The default Claude Code path maps the
# judgment brain's ``defer`` to ``ask``; the explicit Codex substrate path
# upgrades ``ask``/``defer`` to ``deny`` because Codex does not enforce ask.
PERMISSION_ALLOW = "allow"
PERMISSION_DENY = "deny"
PERMISSION_ASK = "ask"

SUBSTRATE_CLAUDE_CODE = "claude-code"
SUBSTRATE_CODEX = "codex"
CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON = (
    "codex_substrate_ask_not_enforced_upgraded_to_deny"
)

# Exit codes. allow/ask carry their decision in the stdout JSON with exit 0.
# deny additionally exits with the Claude Code blocking exit code so the tool
# call is blocked even if the stdout JSON were ignored (belt-and-suspenders
# fail-closed). Both mechanisms independently mean "do not run the tool".
EXIT_ALLOW_OR_ASK = 0
EXIT_BLOCK = 2

# hook_decision (from the unchanged 11-C-8 brain) -> (permissionDecision, exit).
# The brain returns DEFER for VALID input whose risk is merely uncertain /
# not-checked (e.g. a medium-risk read, an unclassified but non-dangerous
# command). That is a considered "hold, let the user decide", so it maps to
# ``ask`` -- non-allow, but not a hard block. Dangerous inputs never reach
# DEFER; they return DENY. INVALID input (which never produced a trustworthy
# target/command judgment) is hard-denied earlier, in render_hook_response,
# and never reaches this table.
_DECISION_TO_PERMISSION_AND_EXIT: dict[str, tuple[str, int]] = {
    ALLOW: (PERMISSION_ALLOW, EXIT_ALLOW_OR_ASK),
    ASK: (PERMISSION_ASK, EXIT_ALLOW_OR_ASK),
    DENY: (PERMISSION_DENY, EXIT_BLOCK),
    DEFER: (PERMISSION_ASK, EXIT_ALLOW_OR_ASK),
}


@dataclass(frozen=True)
class HookRunResult:
    stdout_json: str
    stderr_text: str
    exit_code: int
    permission_decision: str
    hook_decision: str | None
    fail_closed: bool
    reason: str


def render_hook_response(
    raw_stdin_text: str,
    *,
    repo_root: str | Path,
    substrate: str | None = None,
) -> HookRunResult:
    """Render a Claude Code PreToolUse hook response from untrusted stdin text.

    Pure and side-effect free: performs no stream or filesystem I/O so it can be
    exercised directly in tests. Every failure mode returns a blocking ``deny``.
    """

    effective_substrate = _normalize_substrate(substrate)

    try:
        payload = json.loads(raw_stdin_text)
    except (json.JSONDecodeError, ValueError):
        return _deny_result(
            "invalid_json_stdin_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            substrate=effective_substrate,
        )

    if not isinstance(payload, Mapping):
        return _deny_result(
            "non_object_json_stdin_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            substrate=effective_substrate,
        )

    # Wiring-level shape validation. Invalid / missing-field / unsupported-tool
    # input never produced a trustworthy target-path or command judgment, so it
    # hard-denies here rather than being routed to the brain (where it would
    # collapse to DEFER and, under the mapping above, downgrade to ``ask``).
    # This closes an input-downgrade gap: e.g. a Write to .env with a missing
    # tool_use_id must not become ``ask`` by skipping path judgment.
    try:
        validation = validate_claude_code_pretooluse_input(payload)
    except Exception:  # noqa: BLE001 - validator failure must fail closed.
        return _deny_result(
            "input_validation_error_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            substrate=effective_substrate,
        )
    if not validation.valid or validation.hook_input is None:
        return _deny_result(
            "invalid_or_unsupported_pretooluse_input_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            extra_reason_codes=tuple(validation.reasons),
            substrate=effective_substrate,
        )

    try:
        decision = judge_pretooluse_with_aeg_engine(payload, repo_root=repo_root)
        hook_decision = decision.hook_decision
        decision_reasons = tuple(decision.decision_reasons)
        tool_name = decision.request.tool_name
    except Exception:  # noqa: BLE001 - any brain/wiring failure must fail closed.
        return _deny_result(
            "internal_judgment_error_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            substrate=effective_substrate,
        )

    mapping = _permission_mapping_for_substrate(hook_decision, effective_substrate)
    if mapping is None:
        return _deny_result(
            f"unmapped_hook_decision_fail_closed_deny:{hook_decision}",
            hook_decision=hook_decision,
            fail_closed=True,
            substrate=effective_substrate,
        )

    permission_decision, exit_code, substrate_reason_codes = mapping
    reason = _reason_string(
        permission_decision=permission_decision,
        hook_decision=hook_decision,
        tool_name=tool_name,
        decision_reasons=(*decision_reasons, *substrate_reason_codes),
        substrate=effective_substrate,
    )
    stdout_json = _permission_decision_json(permission_decision, reason)
    stderr_text = reason if exit_code == EXIT_BLOCK else ""
    return HookRunResult(
        stdout_json=stdout_json,
        stderr_text=stderr_text,
        exit_code=exit_code,
        permission_decision=permission_decision,
        hook_decision=hook_decision,
        fail_closed=False,
        reason=reason,
    )


def run_aeg_hook_run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    repo_root: str | Path,
    substrate: str | None = None,
) -> int:
    """Read PreToolUse JSON from ``stdin``, judge it, write the Claude Code
    hook response to ``stdout``/``stderr``, and return the exit code.

    A failure to read stdin itself also fails closed to a blocking deny.
    """

    try:
        raw_stdin_text = stdin.read()
    except Exception:  # noqa: BLE001 - unreadable stdin must fail closed.
        raw_stdin_text = ""

    result = render_hook_response(
        raw_stdin_text,
        repo_root=repo_root,
        substrate=substrate,
    )
    stdout.write(result.stdout_json + "\n")
    if result.stderr_text:
        stderr.write(result.stderr_text + "\n")
    return result.exit_code


def run_aeg_hook_run_from_process(
    repo_root: str | Path | None = None,
    *,
    substrate: str | None = None,
) -> int:
    """Entry point used by the ``aeg hook-run`` CLI subcommand, bound to the
    real process streams."""

    resolved_root = Path.cwd() if repo_root is None else repo_root
    return run_aeg_hook_run(
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        repo_root=resolved_root,
        substrate=substrate,
    )


def build_aeg_hook_run_contract_evidence() -> dict[str, Any]:
    return {
        "contract_version": PHASE11D_2_AEG_HOOK_RUN_VERSION,
        "completion_label": PHASE11D_2_COMPLETE_LABEL,
        "reads_stdin": True,
        "writes_stdout": True,
        "writes_stderr_on_block": True,
        "returns_exit_code": True,
        "stdin_treated_as_untrusted_raw_executor_output": True,
        "judgment_brain_source": (
            "src.evidence.hook_judgment_engine_alignment.judge_pretooluse_with_aeg_engine"
        ),
        "judgment_brain_modified": False,
        "hook_event_name": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
        "permission_decisions_emitted": (PERMISSION_ALLOW, PERMISSION_DENY, PERMISSION_ASK),
        "codex_apply_patch_tool_call_supported": True,
        "apply_patch_normal_target_maps_to_allow": True,
        "apply_patch_risky_or_malformed_target_maps_to_deny": True,
        "substrate_selection_source": "explicit_hook_run_substrate_argument",
        "tool_name_used_for_substrate_detection": False,
        "default_substrate": SUBSTRATE_CLAUDE_CODE,
        "missing_or_unknown_substrate_defaults_to_claude_code": True,
        "codex_substrate_ask_defer_upgraded_to_deny": True,
        "codex_substrate_upgrade_reason_code": CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON,
        "decision_to_permission_and_exit": {
            decision: {"permissionDecision": permission, "exit_code": exit_code}
            for decision, (permission, exit_code) in _DECISION_TO_PERMISSION_AND_EXIT.items()
        },
        "fail_closed_default": PERMISSION_DENY,
        "fail_closed_exit_code": EXIT_BLOCK,
        "failure_ever_maps_to_allow": False,
        "raw_tool_input_echoed_in_reason": False,
        # This module builds the real I/O boundary only. It does not install a
        # hook, modify settings, or run Claude Code itself.
        "settings_json_modified": False,
        "hook_installed": False,
        "claude_code_execution_performed": False,
        "tool_execution_performed": False,
        "provider_model_network_implemented": False,
        "store_write_performed": False,
        "filesystem_mutation_by_hook_run": False,
        "write_authority_granted": False,
        "safe_default": SAFE_DEFAULT,
        "live_executor_authority": LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    }


def _deny_result(
    reason_code: str,
    *,
    hook_decision: str | None,
    fail_closed: bool,
    extra_reason_codes: tuple[str, ...] = (),
    substrate: str = SUBSTRATE_CLAUDE_CODE,
) -> HookRunResult:
    reason = _reason_string(
        permission_decision=PERMISSION_DENY,
        hook_decision=hook_decision,
        tool_name=None,
        decision_reasons=(reason_code, *extra_reason_codes),
        substrate=substrate,
    )
    return HookRunResult(
        stdout_json=_permission_decision_json(PERMISSION_DENY, reason),
        stderr_text=reason,
        exit_code=EXIT_BLOCK,
        permission_decision=PERMISSION_DENY,
        hook_decision=hook_decision,
        fail_closed=fail_closed,
        reason=reason,
    )


def _reason_string(
    *,
    permission_decision: str,
    hook_decision: str | None,
    tool_name: Any,
    decision_reasons: tuple[str, ...],
    substrate: str,
) -> str:
    # Deliberately excludes raw tool_input so secrets in tool input are never
    # echoed. tool_name is a low-risk enum-like label (Write/Edit/Bash/Read).
    safe_tool_name = tool_name if isinstance(tool_name, str) and tool_name.strip() else "unknown"
    codes = ",".join(decision_reasons) if decision_reasons else "none"
    return (
        f"aegis_pretooluse permissionDecision={permission_decision};"
        f" hook_decision={hook_decision if hook_decision is not None else 'none'};"
        f" substrate={substrate};"
        f" tool_name={safe_tool_name};"
        f" reason_codes={codes};"
        f" safe_default={SAFE_DEFAULT}"
    )


def _permission_decision_json(permission_decision: str, reason: str) -> str:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
            "permissionDecision": permission_decision,
            "permissionDecisionReason": reason,
        }
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _normalize_substrate(substrate: str | None) -> str:
    if substrate == SUBSTRATE_CODEX:
        return SUBSTRATE_CODEX
    return SUBSTRATE_CLAUDE_CODE


def _permission_mapping_for_substrate(
    hook_decision: str,
    substrate: str,
) -> tuple[str, int, tuple[str, ...]] | None:
    mapping = _DECISION_TO_PERMISSION_AND_EXIT.get(hook_decision)
    if mapping is None:
        return None
    if substrate == SUBSTRATE_CODEX and hook_decision in {ASK, DEFER}:
        return (
            PERMISSION_DENY,
            EXIT_BLOCK,
            (CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON,),
        )
    permission_decision, exit_code = mapping
    return (permission_decision, exit_code, tuple())


__all__ = [
    "CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE",
    "CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON",
    "EXIT_ALLOW_OR_ASK",
    "EXIT_BLOCK",
    "PERMISSION_ALLOW",
    "PERMISSION_ASK",
    "PERMISSION_DENY",
    "PHASE11D_2_AEG_HOOK_RUN_VERSION",
    "PHASE11D_2_COMPLETE_LABEL",
    "SUBSTRATE_CLAUDE_CODE",
    "SUBSTRATE_CODEX",
    "HookRunResult",
    "build_aeg_hook_run_contract_evidence",
    "render_hook_response",
    "run_aeg_hook_run",
    "run_aeg_hook_run_from_process",
]
