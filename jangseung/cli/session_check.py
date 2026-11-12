"""``aeg session-check`` — a SessionStart hook that says when protection is off.

Claude Code runs it once when a session starts. It never blocks the session and
prints nothing when all is well. When the guard's own PreToolUse hook is missing,
points at a program that is gone, or would let a call through on a crash, or when
the project policy cannot be read, it shows the person one line saying so.

It reads files only. It runs no configured command and changes nothing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Sequence, TextIO

_MAX_STDIN = 1_048_576


def session_problems(repo: Path, *, plugin: bool) -> list[str]:
    """Short names of what is wrong; empty when protection looks intact."""

    from jangseung.classify.hook_policy import load_hook_policy
    from jangseung.state.doctor import FAIL, WARN

    problems: list[str] = []
    if not plugin:
        from jangseung.cli.hook_doctor import CLAUDE_LOCAL_SETTINGS, _claude_code_checks, _managed_main_hook_count

        checks = _claude_code_checks(repo)
        registered = (
            _managed_main_hook_count(repo / ".claude" / "settings.json")
            + _managed_main_hook_count(repo / ".claude" / CLAUDE_LOCAL_SETTINGS)
        )
        if not registered:
            problems.append("the PreToolUse hook is not registered in .claude/settings.json or settings.local.json")
        for check in checks:
            if check.status == FAIL:
                problems.append(f"{check.name}: {check.message.rstrip('.')}")
            elif check.name.endswith("failure mode") and check.status == WARN:
                problems.append("the hook is not set to block a call when it cannot start (onFailure)")
    policy = load_hook_policy(repo)
    if policy.error is not None:
        problems.append(f"the project policy is ignored ({policy.error})")
    state = repo / ".aeg"
    if state.exists() and (state.is_symlink() or not state.is_dir() or not os.access(state, os.W_OK | os.X_OK)):
        problems.append(".aeg is not a writable folder, so decisions are not recorded")
    elif not plugin and not state.exists():
        problems.append(".aeg is missing, so decisions are not recorded")
    return problems


def run_session_check(arguments: Sequence[str], *, stdin: TextIO, stdout: TextIO) -> int:
    plugin = "--plugin" in arguments
    try:
        raw = stdin.read(_MAX_STDIN)
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:  # noqa: BLE001 - the input only says where the session is.
        payload = {}
    try:
        from jangseung.cli.hook_run import resolve_hook_project_root

        working = payload.get("cwd") if isinstance(payload, dict) else None
        start = Path(working) if isinstance(working, str) and Path(working).is_dir() else Path.cwd()
        repo = Path(resolve_hook_project_root(start))
        problems = session_problems(repo, plugin=plugin)
    except Exception:  # noqa: BLE001 - a check that cannot run says so instead of staying silent.
        problems = ["the self-check could not run"]
    if problems:
        message = (
            "Jangseung: protection may be off or weakened in this project: "
            + "; ".join(problems[:4])
            + ". Run: aeg doctor --hooks"
        )
        stdout.write(json.dumps({"systemMessage": message}) + "\n")
    else:
        stdout.write("{}\n")
    return 0


def main(arguments: Sequence[str]) -> int:
    try:
        return run_session_check(arguments, stdin=sys.stdin, stdout=sys.stdout)
    except Exception:  # noqa: BLE001 - a session must start whatever happens here.
        return 0


__all__ = ["main", "run_session_check", "session_problems"]
