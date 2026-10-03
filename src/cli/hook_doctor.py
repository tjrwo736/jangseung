"""Read-only project hook diagnostics; no command, lock or writer is invoked."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
from typing import Any

from src.cli.install import (
    CODEX_AEGIS_HOOK_MATCHER, INSTALL_TARGETS, _is_managed_hook,
    _parse_managed_command, claude_code_hook_matcher,
)
from src.state import git
from src.state.doctor import DoctorCheck, FAIL, PASS, WARN
from src.state.file_lock import _pid_is_dead
from src.state.hook_ledger import verify_hook_ledger

MAX_CONFIG_BYTES = 1_048_576
MAX_LEDGER_BYTES = 16 * 1_048_576
_SUBSTRATES = (None, "claude-code", "codex")


def _regular(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and info.st_nlink == 1


def _config_checks(repo: Path, target: str) -> list[DoctorCheck]:
    directory, filename = ((".codex", "config.toml") if target == "codex" else (".claude", "settings.json"))
    parent = repo / directory
    path = parent / filename
    name = f"{target} hook config"
    install_hint = "Run aeg install" + (" --target codex" if target == "codex" else "") + " from the project root after reviewing the changes."
    try:
        if parent.is_symlink() or parent.resolve() != parent or path.is_symlink():
            return [DoctorCheck(name, FAIL, "Linked config paths are not inspected.", fix_hint="Inspect the linked configuration manually; no files were changed.")]
        if not path.exists():
            if parent.exists() and not parent.is_dir():
                return [DoctorCheck(name, FAIL, "The config parent is not a directory.")]
            return [DoctorCheck(name, WARN, "Project-local configuration is absent.", fix_hint=install_hint)]
        if not _regular(path):
            return [DoctorCheck(name, FAIL, "Config must be a regular file without links.")]
        if path.stat().st_size > MAX_CONFIG_BYTES:
            return [DoctorCheck(name, WARN, "Config exceeds the 1 MiB diagnostic limit; contents were not inspected.")]
        text = path.read_text(encoding="utf-8")
        if target == "codex":
            import tomlkit
            data = tomlkit.parse(text).unwrap()
        else:
            data = json.loads(text) if text.strip() else {}
        if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
            raise ValueError("config shape")
        entries = data.get("hooks", {}).get("PreToolUse", [])
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list)
            or any(not isinstance(hook, dict) for hook in entry["hooks"]) for entry in entries
        ):
            raise ValueError("hook shape")
    except Exception:
        # Parser diagnostics can quote arbitrary configuration/credential text.
        return [DoctorCheck(name, FAIL, "Config could not be read as valid UTF-8 with the expected hook structure.",
                            fix_hint="Review the configuration locally. Raw config and parser errors are omitted.")]

    checks = [DoctorCheck(name, PASS, "Project-local config has a readable hook structure.")]
    managed = [(entry, hook) for entry in entries for hook in entry["hooks"] if _is_managed_hook(hook)]
    count = len(managed)
    checks.append(DoctorCheck(f"{target} hook registration", PASS if count == 1 else WARN,
                              f"Recognized managed PreToolUse hooks: {count}. Custom wrappers are not assessed.",
                              fix_hint=install_hint if count == 0 else "Review duplicate registrations." if count > 1 else ""))
    for index, (entry, hook) in enumerate(managed, 1):
        prefix = f"{target} hook {index}"
        expected_substrates = ("codex",) if target == "codex" else (None, "claude-code")
        correct = _is_managed_hook(hook, substrates=expected_substrates)
        checks.append(DoctorCheck(f"{prefix} substrate", PASS if correct else FAIL,
                                  "Substrate matches this target." if correct else "Substrate is missing or does not match this target.",
                                  fix_hint="Review uninstall/reinstall for the correct target; no config was changed." if not correct else ""))
        matcher = entry.get("matcher")
        expected = CODEX_AEGIS_HOOK_MATCHER if target == "codex" else claude_code_hook_matcher()
        # Only the generated literal matcher is claimed, not arbitrary regex equivalence.
        known_matcher = isinstance(matcher, str) and set(matcher.split("|")) == set(expected.split("|"))
        checks.append(DoctorCheck(f"{prefix} matcher", PASS if known_matcher else WARN,
                                  "Matcher covers the installer-generated tool set." if known_matcher else
                                  "Matcher differs from the current installer; tool coverage is NOT_CHECKED.",
                                  next_step="Host trust, global overrides and live dispatch are NOT_CHECKED."))
        checks.append(_executable_check(prefix, hook))
    return checks


def _executable_check(prefix: str, hook: dict[str, Any]) -> DoctorCheck:
    name = f"{prefix} executable"
    if hook.get("args") is not None:
        argv = (hook["command"], *hook["args"])
    else:
        command = hook.get("command_windows", hook.get("command")) if os.name == "nt" else hook.get("command")
        argv = _parse_managed_command(command, _SUBSTRATES)
    if not argv:
        return DoctorCheck(name, WARN, "The current-platform command could not be resolved without executing it.")
    try:
        executable = argv[0]
        if "/" in executable or "\\" in executable:
            path = Path(executable)
            available = path.is_absolute() and path.is_file() and os.access(path, os.X_OK)
        else:
            available = shutil.which(executable) is not None
    except (OSError, ValueError):
        available = False
    if not available:
        return DoctorCheck(name, FAIL, "Configured executable is missing or not executable in this environment.",
                           fix_hint="Activate the intended virtual environment and review reinstalling the hook.")
    if argv[1:3] == ("-m", "src.cli"):
        return DoctorCheck(name, WARN, "Python executable exists; importing src.cli in that interpreter was NOT_CHECKED (not executed).",
                           next_step="Check the intended package installation from a trusted terminal.")
    return DoctorCheck(name, PASS, "Executable is present in the current environment; it was not executed.",
                       next_step="The host application's PATH/trust and actual hook execution remain NOT_CHECKED.")


def _recording_checks(repo: Path) -> list[DoctorCheck]:
    root = repo / ".aeg"
    name = "hook recording directory"
    try:
        if root.is_symlink() or root.resolve() != root or (root.exists() and not root.is_dir()):
            return [DoctorCheck(name, FAIL, ".aeg must be an unlinked project-local directory.")]
        if not root.exists():
            return [DoctorCheck(name, WARN, "Recording directory is absent; hook decisions cannot be recorded yet.",
                                fix_hint="Rerun aeg install for the intended target and approve recording setup.")]
        writable = os.access(root, os.W_OK | os.X_OK)
        checks = [DoctorCheck(name, PASS if writable else FAIL,
                              "Permissions indicate writable state; no write probe was performed." if writable else "Permissions do not indicate writable state.",
                              details=(("write_probe", "NOT_PERFORMED"),))]
        guard = root / "hook_ledger.guard"
        if guard.is_symlink() or (guard.exists() and not _regular(guard)):
            checks.append(DoctorCheck("hook OS guard", FAIL, "Guard is linked or not a regular file."))
        else:
            checks.append(DoctorCheck("hook OS guard", PASS,
                                      "A persistent guard file is normal. OS lock activity is NOT_CHECKED; no lock was acquired."))
        checks.append(_lock_check(root / "hook_ledger.lock"))
        ledger = root / "hook_ledger.jsonl"
        if ledger.is_symlink() or (ledger.exists() and not _regular(ledger)):
            checks.append(DoctorCheck("hook ledger chain", FAIL, "Ledger is linked or not a regular file; contents were not inspected."))
        elif not ledger.exists():
            checks.append(DoctorCheck("hook ledger chain", PASS, "No hook records yet; actual recording is NOT_CHECKED.", details=(("record_count", "0"),)))
        elif ledger.stat().st_size > MAX_LEDGER_BYTES:
            checks.append(DoctorCheck("hook ledger chain", WARN, "Ledger exceeds the 16 MiB diagnostic limit; chain is NOT_CHECKED.",
                                      next_step="Use aeg evidence verify-hooks for a full explicit chain inspection."))
        else:
            result = verify_hook_ledger(repo)
            checks.append(DoctorCheck("hook ledger chain", PASS if result.ok else FAIL,
                                      "Recorded chain matches." if result.ok else "Recorded chain has unreadable or invalid entries; appends will be refused.",
                                      next_step="Use aeg evidence verify-hooks to inspect errors; no repair was performed.",
                                      details=(("record_count", str(len(result.records))), ("error_count", str(len(result.errors))))))
        return checks
    except (OSError, ValueError, RecursionError):
        # Deeply nested damaged JSON can exceed the decoder limit on supported
        # Python versions. Report failure without echoing parser/record data.
        return [DoctorCheck(name, FAIL, "Recording metadata could not be inspected; no state was changed.")]


def _lock_check(path: Path) -> DoctorCheck:
    name = "hook PID lock"
    if path.is_symlink() or (path.exists() and not _regular(path)):
        return DoctorCheck(name, FAIL, "PID sentinel is linked or not a regular file.")
    if not path.exists():
        return DoctorCheck(name, PASS, "No PID sentinel observed at inspection time.")
    with path.open("rb") as handle:
        payload = handle.read(64)
    if not payload.isdigit() or len(payload) > 10 or not 0 < int(payload) <= 0xFFFFFFFF:
        return DoctorCheck(name, WARN, "Lock owner is unknown; recording may time out. The sentinel was not removed.",
                           next_step="Stop relevant writers and inspect the lock before any manual recovery.")
    dead = _pid_is_dead(int(payload))
    return DoctorCheck(name, WARN,
                       "Lock owner has exited; the next writer can attempt safe recovery. No recovery was performed." if dead else
                       "Lock owner may be active or inaccessible; the sentinel was not removed.",
                       details=(("owner_state", "DEAD" if dead else "ACTIVE_OR_UNKNOWN"),))


def run_hook_doctor(cwd: Path, *, target: str = "all") -> list[DoctorCheck]:
    if target not in (*INSTALL_TARGETS, "all"):
        raise ValueError("unsupported diagnostic target")
    try:
        repo = git.repo_root(cwd)
    except (git.GitError, OSError):
        return [DoctorCheck("hook diagnostic scope", FAIL, "Repository root is unavailable; project hooks were not inspected.")]
    checks = [DoctorCheck("hook diagnostic scope", PASS,
                          "Read-only project-local snapshot. No configured commands, write probes, lock recovery or network calls are performed.",
                          details=(("host_execution", "NOT_CHECKED"), ("global_settings", "NOT_CHECKED")))]
    for item in INSTALL_TARGETS if target == "all" else (target,):
        checks.extend(_config_checks(repo, item))
    checks.extend(_recording_checks(repo))
    return checks
