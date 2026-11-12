"""Phase 11-D-2 ``aeg hook-run`` stdin/stdout/exit-code wiring.

This is the real I/O boundary that lets the existing in-memory Aegis hook
judgment brain (Phase 11-C-8 ``judge_pretooluse_with_aeg_engine``) act as a
PreToolUse hook command: it reads untrusted PreToolUse JSON from stdin, routes
it through the shared judgment brain, and writes a
``hookSpecificOutput.permissionDecision`` response to stdout with a
substrate-specific exit code. Selected execution requests in Claude Code's
``default`` mode return an empty JSON object: the host's permission rules decide,
not an automatic hook allow and not Claude Code's unrelated wire-level ``defer``.

Safety properties enforced here (not in the judgment brain, which is not
modified by this module):

* stdin JSON is treated as untrusted raw executor output; it is never trusted
  as a decision or authority and is always routed through validate/map/judge.
* fail-closed: any parse failure, missing/invalid field, unknown tool, or
  internal exception resolves to a ``deny`` JSON response. There is no code
  path where a failure resolves to ``allow``. ``jangseung.cli.entry`` extends
  this to failures that happen before this module can run.
* the reason string carries only fixed sentences, decision codes and the tool
  name. The hook ledger adds redacted names: project-relative target paths, the
  program names of a command and a hash of the input. Neither holds file content,
  command text or arguments. Only ``updatedInput``, read by the host alone,
  returns the tool's own input with secrets left out.
* recording is append-only and tamper-evident.  A recording failure never
  changes the permission decision or process exit code; it adds a safe reason
  code to the response instead.

This module does not install a hook, modify ``.claude/settings.json``, execute
Claude Code itself, execute any tool, or call a provider/model/network.  Its
state writes are the record in ``.aeg/hook_ledger.jsonl`` and, when a write
names a secret file, a mark in ``.aeg/session_marks.json``.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, TextIO

from jangseung.cli.reason_text import hook_reason_sentence
from jangseung.contracts import SAFE_DEFAULT, STATE_DIR
from jangseung.evidence.claude_code_pretooluse_input_contract import (
    validate_claude_code_pretooluse_input,
)
from jangseung.evidence.hook_decision_adapter import ALLOW, ASK, DEFER, DENY
from jangseung.evidence.hook_judgment_engine_alignment import (
    judge_pretooluse_with_aeg_engine,
)
from jangseung.state.hook_ledger import append_hook_decision_record
from jangseung.state.allow_once import consume_once
from jangseung.state.session_marks import mark_secret_naming_write, session_key


CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE = "PreToolUse"

# PreToolUse permissionDecision values used by the supported hook substrates.
# The brain's "defer" is not the host's wire-level "defer" protocol. Claude
# normally maps it to ask; eligible default-mode execution omits the decision.
# The explicit Codex substrate path
# upgrades ``ask``/``defer`` to ``deny`` because Codex does not enforce ask.
PERMISSION_ALLOW = "allow"
PERMISSION_DENY = "deny"
PERMISSION_ASK = "ask"
# Internal diagnostic/ledger value only; NEVER sent as permissionDecision.
PERMISSION_HOST = "host"
HOST_PERMISSION_FLOW_REASON = "claude_default_host_permission_flow"
ALLOW_ONCE_REASON = "hook_allow_once_approved_command"
ALLOW_ONCE_NOT_SPENT_REASON = "allow_once_could_not_be_spent_fail_closed_deny"
# Modes where Claude Code was measured to ask a person before every command family
# this hook leaves to it (2.1.316, Windows, 33 forms each, 2026-11-12). ``acceptEdits``
# runs file commands such as ``rm`` on its own, which is why those are never left to it.
HOST_DELEGATION_MODES = frozenset({"default", "acceptEdits"})

SUBSTRATE_CLAUDE_CODE = "claude-code"
SUBSTRATE_CODEX = "codex"
CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON = (
    "codex_substrate_ask_not_enforced_upgraded_to_deny"
)
HOOK_DECISION_RECORDING_FAILED_REASON = "hook_decision_recording_failed"
SESSION_MARK_RECORDING_FAILED_REASON = "session_mark_recording_failed"
OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON = "output_excludes_read_protected_files"
MAX_STDIN_BYTES = 16 * 1024 * 1024

# Exit codes. Claude Code uses exit 2 as the hard-blocking deny path. Codex
# consumes the JSON permissionDecision when the process exits 0, so Codex
# substrate responses always exit 0 and carry allow/deny in stdout JSON.
EXIT_ALLOW_OR_ASK = 0
EXIT_BLOCK = 2

# Default hook_decision -> (permissionDecision, exit) mapping. The narrowly
# eligible Claude default-mode host delegation is applied after this table.
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
    reason_codes: tuple[str, ...]
    tool_name: str
    substrate: str
    updated_input: Mapping[str, Any] | None = None
    # Redacted facts for the hook record; see ``jangseung.state.hook_ledger``.
    session_id: str = ""
    audit_targets: tuple[str, ...] = ()
    audit_commands: tuple[str, ...] = ()
    input_hash: str = ""
    written_text_names_secret_file: bool = False
    # The exact command an ``aeg allow-once`` approval allowed; spent before the answer is sent.
    allow_once_command: str = ""
    allow_once_tool: str = ""


def render_hook_response(
    raw_stdin_text: str,
    *,
    repo_root: str | Path,
    substrate: str | None = None,
    working_dir: str | Path | None = None,
) -> HookRunResult:
    """Render a PreToolUse hook response from untrusted stdin text.

    Side-effect free: performs no stream I/O or filesystem writes. Path gates
    inspect filesystem metadata; shell-read allow requires existing regular
    files. Every failure mode returns a ``deny`` JSON.
    """

    effective_substrate = _normalize_substrate(substrate)

    try:
        payload = json.loads(raw_stdin_text)
    except Exception:  # noqa: BLE001 - includes RecursionError from deeply nested input.
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
        decision = judge_pretooluse_with_aeg_engine(
            payload,
            repo_root=repo_root,
            working_dir=working_dir,
        )
        hook_decision = decision.hook_decision
        decision_reasons = tuple(decision.decision_reasons)
        tool_name = decision.request.tool_name
        updated_input = decision.updated_tool_input
        session_id = session_key(payload.get("session_id"))
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

    permission_decision, mapped_exit_code, substrate_reason_codes = mapping
    reason_codes = (*decision_reasons, *substrate_reason_codes)
    if (
        effective_substrate == SUBSTRATE_CLAUDE_CODE
        and isinstance(payload.get("permission_mode"), str)
        and payload.get("permission_mode") in HOST_DELEGATION_MODES
        and hook_decision == DEFER
        and decision.host_delegation_eligible
        and updated_input is None
    ):
        permission_decision = PERMISSION_HOST
        reason_codes = (*reason_codes, HOST_PERMISSION_FLOW_REASON)
    if updated_input is not None:
        reason_codes = (*reason_codes, OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON)
    reason = _reason_string(
        permission_decision=permission_decision,
        hook_decision=hook_decision,
        tool_name=tool_name,
        decision_reasons=reason_codes,
        substrate=effective_substrate,
        fail_closed=False,
    )
    stdout_json = _permission_decision_json(permission_decision, reason, updated_input)
    stderr_text = reason if mapped_exit_code == EXIT_BLOCK else ""
    exit_code = _process_exit_code_for_substrate(
        substrate=effective_substrate,
        mapped_exit_code=mapped_exit_code,
    )
    return HookRunResult(
        stdout_json=stdout_json,
        stderr_text=stderr_text,
        exit_code=exit_code,
        permission_decision=permission_decision,
        hook_decision=hook_decision,
        fail_closed=False,
        reason=reason,
        reason_codes=reason_codes,
        tool_name=tool_name,
        substrate=effective_substrate,
        updated_input=updated_input,
        session_id=session_id,
        audit_targets=tuple(decision.audit_targets),
        audit_commands=tuple(decision.audit_commands),
        input_hash=decision.request.raw_hook_input_hash,
        written_text_names_secret_file=(
            decision.written_text_names_secret_file and permission_decision != PERMISSION_DENY
        ),
        allow_once_command=(
            str(payload.get("tool_input", {}).get("command", ""))
            if permission_decision == PERMISSION_ALLOW and ALLOW_ONCE_REASON in reason_codes
            else ""
        ),
        allow_once_tool=str(tool_name or ""),
    )


def resolve_hook_project_root(
    working_dir: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the fixed project root, which must not follow the session's ``cd``.

    Claude Code publishes the root in ``CLAUDE_PROJECT_DIR``. Without it, use the
    nearest ancestor holding hook state or a Git repository, then the directory.
    """

    env = os.environ if environ is None else environ
    published = env.get("CLAUDE_PROJECT_DIR")
    if published:
        candidate = Path(published)
        if candidate.is_absolute() and candidate.is_dir():
            return candidate.resolve()
    current = Path(working_dir).resolve()
    for candidate in (current, *current.parents):
        if (candidate / STATE_DIR).is_dir() or (candidate / ".git").exists():
            return candidate
    return current


def read_stdin_text(stdin: TextIO, *, limit: int = MAX_STDIN_BYTES) -> str:
    """Read stdin as UTF-8 bytes; the console's locale encoding is not the host's."""

    buffer = getattr(stdin, "buffer", None)
    if buffer is None:
        return stdin.read()
    raw = buffer.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("hook input exceeds the size limit")
    return raw.decode("utf-8-sig")


def run_aeg_hook_run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    repo_root: str | Path,
    substrate: str | None = None,
    working_dir: str | Path | None = None,
) -> int:
    """Read PreToolUse JSON from ``stdin``, judge it, write the substrate
    hook response to ``stdout``/``stderr``, and return the exit code.

    A failure to read stdin itself also fails closed to a ``deny`` JSON.
    """

    try:
        raw_stdin_text = read_stdin_text(stdin)
    except Exception:  # noqa: BLE001 - unreadable stdin must fail closed.
        raw_stdin_text = ""

    try:
        result = render_hook_response(
            raw_stdin_text,
            repo_root=repo_root,
            substrate=substrate,
            working_dir=working_dir,
        )
    except Exception:  # noqa: BLE001 - nothing below may turn a failure into a pass.
        result = _deny_result(
            "internal_judgment_error_fail_closed_deny",
            hook_decision=None,
            fail_closed=True,
            substrate=_normalize_substrate(substrate),
        )
    if result.allow_once_command:
        # The approval is spent before the answer leaves. If it cannot be spent, or
        # another call spent it first, the command is not allowed on its strength.
        try:
            spent = consume_once(result.allow_once_command, repo_root, result.allow_once_tool or "Bash")
        except Exception:  # noqa: BLE001
            spent = False
        if not spent:
            result = _deny_result(
                ALLOW_ONCE_NOT_SPENT_REASON,
                hook_decision=result.hook_decision,
                fail_closed=True,
                substrate=result.substrate,
            )
    try:
        append_hook_decision_record(
            repo_root,
            substrate=result.substrate,
            tool_name=result.tool_name,
            hook_decision=result.hook_decision,
            permission_decision=result.permission_decision,
            fail_closed=result.fail_closed,
            reason_codes=result.reason_codes,
            exit_code=result.exit_code,
            session_id=result.session_id,
            targets=result.audit_targets,
            commands=result.audit_commands,
            input_hash=result.input_hash,
        )
    except Exception:  # noqa: BLE001 - recording failure must not change the judgment.
        result = _with_recording_failure(result)
    if result.written_text_names_secret_file:
        try:
            mark_secret_naming_write(repo_root, result.session_id, result.audit_targets)
        except Exception:  # noqa: BLE001 - the write was already judged; say the mark is missing.
            result = _with_recording_failure(result, SESSION_MARK_RECORDING_FAILED_REASON)
    try:
        stdout.write(result.stdout_json + "\n")
    except Exception:  # noqa: BLE001 - with no response to read, only exit 2 can block.
        return EXIT_BLOCK
    if result.stderr_text:
        try:
            stderr.write(result.stderr_text + "\n")
        except Exception:  # noqa: BLE001 - the decision was already delivered on stdout.
            pass
    return result.exit_code


_HOOK_OPTIONS = ("--substrate", "--mcp", "--ensure-state")


def _parse_hook_arguments(arguments: list[str]) -> tuple[str | None, bool]:
    """Read the three ``aeg hook-run`` options by hand.

    ``argparse`` loads ``shutil`` and colour support the hook never uses, about
    12 ms on every tool call. The accepted forms are the ones it accepted: a
    unique prefix of an option, and ``--substrate=codex``. Anything else ends the
    process with status 2, which the hosts treat as a block.
    """

    substrate: str | None = None
    ensure_state = False
    index = 0
    while index < len(arguments):
        word, _, attached = arguments[index].partition("=")
        matches = [option for option in _HOOK_OPTIONS if word.startswith("--") and len(word) > 2 and option.startswith(word)]
        option = word if word in _HOOK_OPTIONS else (matches[0] if len(matches) == 1 else None)
        has_value = "=" in arguments[index]
        if option == "--substrate":
            if not has_value:
                index += 1
                if index >= len(arguments):
                    _hook_usage_error("--substrate needs a value")
                attached = arguments[index]
            if attached not in (SUBSTRATE_CLAUDE_CODE, SUBSTRATE_CODEX):
                _hook_usage_error("--substrate must be claude-code or codex")
            substrate = attached
        elif option == "--ensure-state" and not has_value:
            # Set by the plugin's hook entry, which has no ``aeg install`` step to make ``.aeg/``.
            ensure_state = True
        elif option == "--mcp" and not has_value:
            # Marks the entry ``aeg install --mcp`` adds. Every call is judged the same
            # way, so an MCP call arriving through either entry gets the MCP rules.
            pass
        else:
            _hook_usage_error("unrecognized argument")
        index += 1
    return substrate, ensure_state


def _hook_usage_error(message: str) -> None:
    try:
        sys.stderr.write(
            "usage: aeg hook-run [--substrate {claude-code,codex}] [--mcp] [--ensure-state]\n"
            f"aeg hook-run: error: {message}\n"
        )
    except Exception:  # noqa: BLE001 - the exit status alone blocks the call.
        pass
    raise SystemExit(2)


def run_hook_cli(arguments: Sequence[str]) -> int:
    """Parse ``aeg hook-run`` arguments without loading the whole CLI."""

    substrate, ensure_state = _parse_hook_arguments(list(arguments))
    return run_aeg_hook_run_from_process(substrate=substrate, ensure_state=ensure_state)


def run_aeg_hook_run_from_process(
    repo_root: str | Path | None = None,
    *,
    substrate: str | None = None,
    ensure_state: bool = False,
) -> int:
    """Entry point used by the ``aeg hook-run`` CLI subcommand, bound to the
    real process streams."""

    working_dir = Path.cwd()
    # A Codex session started from inside Claude Code inherits its project variable.
    environ = {} if substrate == SUBSTRATE_CODEX else None
    resolved_root = (
        resolve_hook_project_root(working_dir, environ=environ) if repo_root is None else repo_root
    )
    if ensure_state:
        ensure_recording_directory(resolved_root)
    return run_aeg_hook_run(
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        repo_root=resolved_root,
        substrate=substrate,
        working_dir=working_dir,
    )


def ensure_recording_directory(repo_root: str | Path) -> bool:
    """Create ``.aeg/`` the way ``aeg install`` does; never touch one that exists.

    A failure only means this call goes unrecorded, which the response then says.
    """

    try:
        base = Path(repo_root).resolve()
        root = base / STATE_DIR
        if root.is_symlink() or root.exists():
            return root.is_dir() and not root.is_symlink()
        root.mkdir()
        (root / ".gitignore").write_text("*\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _deny_result(
    reason_code: str,
    *,
    hook_decision: str | None,
    fail_closed: bool,
    extra_reason_codes: tuple[str, ...] = (),
    substrate: str = SUBSTRATE_CLAUDE_CODE,
) -> HookRunResult:
    reason_codes = (reason_code, *extra_reason_codes)
    reason = _reason_string(
        permission_decision=PERMISSION_DENY,
        hook_decision=hook_decision,
        tool_name=None,
        decision_reasons=reason_codes,
        substrate=substrate,
        fail_closed=fail_closed,
    )
    exit_code = _process_exit_code_for_substrate(
        substrate=substrate,
        mapped_exit_code=EXIT_BLOCK,
    )
    return HookRunResult(
        stdout_json=_permission_decision_json(PERMISSION_DENY, reason),
        stderr_text=reason,
        exit_code=exit_code,
        permission_decision=PERMISSION_DENY,
        hook_decision=hook_decision,
        fail_closed=fail_closed,
        reason=reason,
        reason_codes=reason_codes,
        tool_name="unknown",
        substrate=substrate,
    )


def _with_recording_failure(
    result: HookRunResult,
    reason_code: str = HOOK_DECISION_RECORDING_FAILED_REASON,
) -> HookRunResult:
    reason_codes = (*result.reason_codes, reason_code)
    reason = _reason_string(
        permission_decision=result.permission_decision,
        hook_decision=result.hook_decision,
        tool_name=result.tool_name,
        decision_reasons=reason_codes,
        substrate=result.substrate,
        fail_closed=result.fail_closed,
    )
    return replace(
        result,
        stdout_json=(
            json.dumps({"systemMessage": reason}, ensure_ascii=True, sort_keys=True)
            if result.permission_decision == PERMISSION_HOST else
            _permission_decision_json(result.permission_decision, reason, result.updated_input)
        ),
        stderr_text=reason if result.stderr_text else "",
        reason=reason,
        reason_codes=reason_codes,
    )


def _reason_string(
    *,
    permission_decision: str,
    hook_decision: str | None,
    tool_name: Any,
    decision_reasons: tuple[str, ...],
    substrate: str,
    fail_closed: bool = False,
) -> str:
    # Deliberately excludes raw tool_input so secrets in tool input are never
    # echoed. tool_name is a low-risk enum-like label (Write/Edit/Bash/Read).
    safe_tool_name = tool_name if isinstance(tool_name, str) and tool_name.strip() else "unknown"
    codes = ",".join(decision_reasons) if decision_reasons else "none"
    # A stop opens with a sentence a person can act on; the codes follow for reports.
    sentence = hook_reason_sentence(
        reason_codes=decision_reasons,
        hook_decision=hook_decision,
        permission_decision=permission_decision,
        fail_closed=fail_closed,
        tool_name=tool_name,
    )
    return (
        (f"{sentence} | " if sentence else "")
        + f"aegis_pretooluse permissionDecision={permission_decision};"
        f" hook_decision={hook_decision if hook_decision is not None else 'none'};"
        f" substrate={substrate};"
        f" tool_name={safe_tool_name};"
        f" reason_codes={codes};"
        f" safe_default={SAFE_DEFAULT}"
    )


def _permission_decision_json(
    permission_decision: str,
    reason: str,
    updated_input: Mapping[str, Any] | None = None,
) -> str:
    if permission_decision == PERMISSION_HOST:
        # No permissionDecision, updatedInput or "defer": normal host rules apply.
        return "{}"
    output: dict[str, Any] = {
        "hookEventName": CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
        "permissionDecision": permission_decision,
        "permissionDecisionReason": reason,
    }
    if updated_input is not None:
        output["updatedInput"] = updated_input
    payload = {"hookSpecificOutput": output}
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _normalize_substrate(substrate: str | None) -> str:
    if substrate == SUBSTRATE_CODEX:
        return SUBSTRATE_CODEX
    return SUBSTRATE_CLAUDE_CODE


def _process_exit_code_for_substrate(
    *,
    substrate: str,
    mapped_exit_code: int,
) -> int:
    if substrate == SUBSTRATE_CODEX:
        return EXIT_ALLOW_OR_ASK
    return mapped_exit_code


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
    "HOOK_DECISION_RECORDING_FAILED_REASON",
    "PERMISSION_ALLOW",
    "PERMISSION_ASK",
    "OUTPUT_EXCLUDES_READ_PROTECTED_FILES_REASON",
    "PERMISSION_DENY",
    "SUBSTRATE_CLAUDE_CODE",
    "SUBSTRATE_CODEX",
    "HookRunResult",
    "SESSION_MARK_RECORDING_FAILED_REASON",
    "ensure_recording_directory",
    "read_stdin_text",
    "render_hook_response",
    "resolve_hook_project_root",
    "run_aeg_hook_run",
    "run_hook_cli",
    "run_aeg_hook_run_from_process",
]
