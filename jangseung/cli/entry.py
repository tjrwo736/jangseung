"""Process entry point that keeps ``aeg hook-run`` fail-closed.

Claude Code treats any exit code other than 0 or 2 as a non-blocking error, so
an import failure or an uncaught exception must still produce a deny response.
This module imports nothing from the package until it is inside that protection.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence

_ENTRYPOINT_FAILED_REASON = "hook_entrypoint_failed_fail_closed_deny"


def _load_cli_main() -> Callable[[Sequence[str] | None], int]:
    from jangseung.cli.main import main

    return main


def _load_hook_main() -> Callable[[Sequence[str]], int]:
    # The hook runs on every tool call, so it skips the commands it does not need.
    from jangseung.cli.hook_run import run_hook_cli

    return run_hook_cli


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["session-check"]:
        # A SessionStart hook: it must never stop a session from starting.
        try:
            from jangseung.cli.session_check import main as session_check_main

            return session_check_main(arguments[1:])
        except Exception:  # noqa: BLE001
            return 0
    if arguments[:1] != ["hook-run"]:
        return _load_cli_main()(arguments)
    try:
        return _load_hook_main()(arguments[1:])
    except Exception:  # noqa: BLE001 - any failure of the hook path must deny.
        return _deny(arguments)


def _deny(arguments: Sequence[str]) -> int:
    codex = "codex" in arguments[1:]
    substrate = "codex" if codex else "claude-code"
    reason = (
        "aegis_pretooluse permissionDecision=deny; hook_decision=none;"
        f" substrate={substrate}; tool_name=unknown; reason_codes={_ENTRYPOINT_FAILED_REASON}"
    )
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    try:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        print(reason, file=sys.stderr)
    except Exception:  # noqa: BLE001 - nothing can be written; block by exit code alone.
        return 2
    # Codex reads the decision from JSON and expects exit 0, as hook-run does.
    return 0 if codex else 2


if __name__ == "__main__":
    raise SystemExit(main())
