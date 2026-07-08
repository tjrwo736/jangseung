"""``aeg install`` / ``aeg uninstall`` — register/remove the Aegis PreToolUse
hook in a project-local ``.claude/settings.json``.

Safety model:
  * project-local only (``--global`` is deliberately unsupported here);
  * never write without showing a diff preview and getting y/N confirmation
    (``--yes`` skips the prompt);
  * always back up an existing settings file before writing;
  * merge into existing settings, preserving every other hook and field;
  * abort (do not write) on invalid JSON or an unexpected settings structure.

This module writes only ``.claude/settings.json`` (outside the ``.aeg/`` store);
it does not run tools, call providers, or write Aegis state.
"""

from __future__ import annotations

import datetime
import difflib
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, TextIO

AEGIS_HOOK_MATCHER = "Write|Edit|Bash|Read"
HOOK_RUN_MARKER = "hook-run"
HOOK_EVENT_NAME = "PreToolUse"
BACKUP_SUFFIX_PREFIX = "aegis-backup"


class InstallStructureError(Exception):
    """Raised when the existing settings has a structure we will not modify."""


def resolve_hook_command() -> str:
    """Return the command string Claude Code should run for the hook, using the
    installed ``aeg`` console script if available (absolute path, no PYTHONPATH
    needed), else the current interpreter's module invocation."""

    aeg_path = shutil.which("aeg")
    if aeg_path:
        return f"{aeg_path} hook-run"
    return f"{sys.executable} -m src.cli hook-run"


def is_aegis_hook_command(command: Any) -> bool:
    """Identify an Aegis-generated hook command without touching a user's own
    hooks. Matches the ``hook-run`` subcommand referencing this package."""

    return (
        isinstance(command, str)
        and HOOK_RUN_MARKER in command
        and ("aeg" in command or "src.cli" in command)
    )


def settings_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / ".claude" / "settings.json"


def load_settings(path: Path) -> tuple[dict[str, Any] | None, bool, str | None]:
    """Return (data, existed, error). ``data`` is None only on error; an absent
    file yields ({}, False, None); an empty file yields ({}, True, None)."""

    if not path.exists():
        return ({}, False, None)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return (None, True, f"cannot read {path}: {exc}")
    if not text.strip():
        return ({}, True, None)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return (None, True, f"{path} is not valid JSON ({exc})")
    if not isinstance(data, dict):
        return (None, True, f"{path} top-level is not a JSON object")
    return (data, True, None)


def build_installed_settings(
    data: dict[str, Any],
    command: str,
) -> tuple[dict[str, Any], bool]:
    """Return (new_settings, already_installed). Preserves all existing content;
    appends one Aegis PreToolUse entry unless one is already present."""

    new_data = deepcopy(data)
    hooks = new_data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallStructureError("'hooks' is not a JSON object")
    pretooluse = hooks.setdefault(HOOK_EVENT_NAME, [])
    if not isinstance(pretooluse, list):
        raise InstallStructureError(f"'hooks.{HOOK_EVENT_NAME}' is not a JSON array")

    if _find_aegis_hook(pretooluse):
        return (new_data, True)

    pretooluse.append(
        {
            "matcher": AEGIS_HOOK_MATCHER,
            "hooks": [{"type": "command", "command": command}],
        }
    )
    return (new_data, False)


def build_uninstalled_settings(
    data: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Return (new_settings, removed_count). Removes only Aegis hooks; preserves
    every other hook and field; cleans up now-empty structures."""

    new_data = deepcopy(data)
    hooks = new_data.get("hooks")
    if not isinstance(hooks, dict):
        return (new_data, 0)
    pretooluse = hooks.get(HOOK_EVENT_NAME)
    if not isinstance(pretooluse, list):
        return (new_data, 0)

    removed = 0
    kept_entries: list[Any] = []
    for entry in pretooluse:
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            kept_entries.append(entry)
            continue
        nested = entry["hooks"]
        kept_hooks = [
            hook
            for hook in nested
            if not (isinstance(hook, dict) and is_aegis_hook_command(hook.get("command")))
        ]
        removed += len(nested) - len(kept_hooks)
        if len(kept_hooks) == len(nested):
            kept_entries.append(entry)
        elif kept_hooks:
            kept_entries.append({**entry, "hooks": kept_hooks})
        # else: the entry contained only Aegis hooks -> drop the whole entry

    if kept_entries:
        hooks[HOOK_EVENT_NAME] = kept_entries
    else:
        hooks.pop(HOOK_EVENT_NAME, None)
    if not hooks:
        new_data.pop("hooks", None)
    return (new_data, removed)


def cmd_install(
    base_dir: str | Path,
    *,
    assume_yes: bool = False,
    global_requested: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    if global_requested:
        _write(
            out,
            "aeg install: global (~/.claude) install is not supported in this "
            "version.\nOnly project-local install is supported: run 'aeg install' "
            "inside your project directory (writes ./.claude/settings.json).",
        )
        return 2

    path = settings_path(base_dir)
    data, existed, error = load_settings(path)
    if error is not None:
        _write(out, f"aeg install: aborted — {error}")
        _write(out, "Please fix or remove the file manually, then retry.")
        return 1

    command = resolve_hook_command()
    try:
        new_data, already = build_installed_settings(data or {}, command)
    except InstallStructureError as exc:
        _write(out, f"aeg install: aborted — unexpected settings structure: {exc}")
        _write(out, "Please adjust .claude/settings.json manually, then retry.")
        return 1

    if already:
        _write(out, "aeg install: an Aegis PreToolUse hook is already installed; no changes.")
        return 0

    before_text = _json_text(data) if existed else "(no .claude/settings.json yet)\n"
    after_text = _json_text(new_data)

    _write(out, f"aeg install: will register the Aegis PreToolUse hook in {path}")
    _write(out, f"  hook command: {command}")
    _write(out, f"  matcher:      {AEGIS_HOOK_MATCHER}")
    _write(out, "")
    _write_diff(out, before_text, after_text, path)

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if existed:
        backup = _backup_file(path)
        _write(out, f"aeg install: backed up existing settings to {backup}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(after_text, encoding="utf-8")
    _write(out, f"aeg install: done. Aegis PreToolUse hook registered in {path}")
    return 0


def cmd_uninstall(
    base_dir: str | Path,
    *,
    assume_yes: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    path = settings_path(base_dir)
    data, existed, error = load_settings(path)
    if error is not None:
        _write(out, f"aeg uninstall: aborted — {error}")
        _write(out, "Please fix or remove the file manually, then retry.")
        return 1
    if not existed:
        _write(out, f"aeg uninstall: no {path}; nothing to uninstall.")
        return 0

    new_data, removed = build_uninstalled_settings(data or {})
    if removed == 0:
        _write(out, "aeg uninstall: no Aegis PreToolUse hook found; nothing to remove.")
        return 0

    before_text = _json_text(data)
    after_text = _json_text(new_data)
    _write(out, f"aeg uninstall: will remove {removed} Aegis hook entry(ies) from {path}")
    _write(out, "  (other hooks and settings are preserved)")
    _write(out, "")
    _write_diff(out, before_text, after_text, path)

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg uninstall: cancelled; no changes written.")
        return 0

    backup = _backup_file(path)
    _write(out, f"aeg uninstall: backed up existing settings to {backup}")
    path.write_text(after_text, encoding="utf-8")
    _write(out, f"aeg uninstall: done. Removed the Aegis PreToolUse hook from {path}")
    return 0


def _find_aegis_hook(pretooluse: list[Any]) -> bool:
    for entry in pretooluse:
        if not isinstance(entry, dict):
            continue
        nested = entry.get("hooks")
        if not isinstance(nested, list):
            continue
        for hook in nested:
            if isinstance(hook, dict) and is_aegis_hook_command(hook.get("command")):
                return True
    return False


def _json_text(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _write_diff(out: TextIO, before_text: str, after_text: str, path: Path) -> None:
    diff = difflib.unified_diff(
        before_text.splitlines(keepends=True),
        after_text.splitlines(keepends=True),
        fromfile=f"{path} (current)",
        tofile=f"{path} (proposed)",
    )
    body = "".join(diff)
    if not body.strip():
        _write(out, "(no textual change)")
        return
    _write(out, "--- proposed change ---")
    out.write(body if body.endswith("\n") else body + "\n")
    _write(out, "-----------------------")


def _confirm(input_stream: TextIO | None, out: TextIO) -> bool:
    stream = input_stream if input_stream is not None else sys.stdin
    out.write("Proceed? [y/N]: ")
    out.flush()
    try:
        answer = stream.readline()
    except (EOFError, OSError):
        return False
    return answer.strip().lower() in ("y", "yes")


def _backup_file(path: Path) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.{BACKUP_SUFFIX_PREFIX}-{timestamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(
            f"{path.name}.{BACKUP_SUFFIX_PREFIX}-{timestamp}-{counter}"
        )
        counter += 1
    shutil.copy2(path, candidate)
    return candidate


def _write(out: TextIO, line: str) -> None:
    out.write(line + "\n")


__all__ = [
    "AEGIS_HOOK_MATCHER",
    "HOOK_EVENT_NAME",
    "HOOK_RUN_MARKER",
    "InstallStructureError",
    "build_installed_settings",
    "build_uninstalled_settings",
    "cmd_install",
    "cmd_uninstall",
    "is_aegis_hook_command",
    "load_settings",
    "resolve_hook_command",
    "settings_path",
]
