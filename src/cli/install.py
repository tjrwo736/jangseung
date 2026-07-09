"""``aeg install`` / ``aeg uninstall`` — register/remove the Aegis PreToolUse
hook in a project-local substrate config.

Safety model:
  * project-local only (``--global`` is deliberately unsupported here);
  * never write without showing a diff preview and getting y/N confirmation
    (``--yes`` skips the prompt);
  * always back up an existing settings file before writing;
  * merge into existing settings, preserving every other hook and field;
  * abort (do not write) on invalid Claude Code JSON or an unexpected hook
    structure.

This module writes only substrate hook config files (outside the ``.aeg/``
store); it does not run tools, call providers, or write Aegis state.
"""

from __future__ import annotations

import datetime
import difflib
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence, TextIO

AEGIS_HOOK_MATCHER = "Write|Edit|Bash|Read"
WINDOWS_AEGIS_HOOK_MATCHER = "Write|Edit|Bash|Read|PowerShell"
CODEX_AEGIS_HOOK_MATCHER = "Write|Edit|Bash|Read|apply_patch"
HOOK_RUN_MARKER = "hook-run"
HOOK_EVENT_NAME = "PreToolUse"
BACKUP_SUFFIX_PREFIX = "aegis-backup"
TARGET_CLAUDE_CODE = "claude-code"
TARGET_CODEX = "codex"
INSTALL_TARGETS = (TARGET_CLAUDE_CODE, TARGET_CODEX)


class InstallStructureError(Exception):
    """Raised when the existing settings has a structure we will not modify."""


def resolve_hook_command(*, substrate: str | None = None) -> str:
    """Return the command string the substrate should run for the hook, using
    the installed ``aeg`` console script if available (absolute path, no
    PYTHONPATH needed), else the current interpreter's module invocation."""

    command, args = resolve_hook_command_parts(substrate=substrate)
    command = " ".join((command, *args))
    return command


def resolve_hook_command_parts(
    *,
    substrate: str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Return the hook executable and argv tail without shell tokenization."""

    aeg_path = shutil.which("aeg")
    if aeg_path:
        command = aeg_path
        args = ["hook-run"]
    else:
        command = sys.executable
        args = ["-m", "src.cli", "hook-run"]
    if substrate:
        args.extend(("--substrate", substrate))
    return (command, tuple(args))


def resolve_claude_code_hook_command(
    *,
    platform: str | None = None,
) -> tuple[str, tuple[str, ...] | None]:
    """Return the Claude Code command config.

    POSIX platforms keep the existing shell-form command string. Windows uses
    Claude Code exec form (``command`` + ``args``) so Git Bash/PowerShell never
    reinterpret backslashes or spaces in the Python executable path.
    """

    effective_platform = sys.platform if platform is None else platform
    if effective_platform == "win32":
        return resolve_windows_hook_command_parts()
    return (resolve_hook_command(), None)


def claude_code_hook_matcher(*, platform: str | None = None) -> str:
    """Return the Claude Code matcher for the current platform.

    Windows Claude Code exposes file mutation through both Bash and PowerShell
    tool calls. POSIX keeps the historical matcher unchanged.
    """

    effective_platform = sys.platform if platform is None else platform
    if effective_platform == "win32":
        return WINDOWS_AEGIS_HOOK_MATCHER
    return AEGIS_HOOK_MATCHER


def resolve_windows_hook_command_parts() -> tuple[str, tuple[str, ...]]:
    """Return a Windows exec-form hook target that Claude Code can spawn."""

    aeg_path = shutil.which("aeg")
    if isinstance(aeg_path, str) and _is_windows_exe_path(aeg_path):
        return (aeg_path, ("hook-run",))
    return (sys.executable, ("-m", "src.cli", "hook-run"))


def resolve_codex_windows_hook_command(*, platform: str | None = None) -> str | None:
    """Return a Windows command string for Codex, when installing on Windows."""

    effective_platform = sys.platform if platform is None else platform
    if effective_platform != "win32":
        return None
    command, args = resolve_windows_hook_command_parts()
    return subprocess.list2cmdline((command, *args, "--substrate", TARGET_CODEX))


def is_aegis_hook_command(command: Any) -> bool:
    """Identify an Aegis-generated hook command without touching a user's own
    hooks. Matches the ``hook-run`` subcommand referencing this package."""

    return (
        isinstance(command, str)
        and HOOK_RUN_MARKER in command
        and ("aeg" in command or "src.cli" in command)
    )


def is_aegis_hook(hook: Any) -> bool:
    """Identify both legacy shell-form and Windows exec-form Aegis hooks."""

    if not isinstance(hook, dict):
        return False
    if is_aegis_hook_command(hook.get("command")):
        return True

    command = hook.get("command")
    args = hook.get("args")
    if not isinstance(command, str) or not _is_string_sequence(args):
        return False
    return _is_aegis_exec_form_hook(command, tuple(args))


def settings_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / ".claude" / "settings.json"


def codex_config_path(base_dir: str | Path) -> Path:
    return Path(base_dir) / ".codex" / "config.toml"


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
    *,
    args: Sequence[str] | None = None,
    matcher: str = AEGIS_HOOK_MATCHER,
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
            "matcher": matcher,
            "hooks": [_command_hook(command, args=args)],
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
            if not is_aegis_hook(hook)
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


def normalize_install_target(target: str) -> str:
    if target in INSTALL_TARGETS:
        return target
    raise ValueError(
        f"unsupported target {target!r}; expected one of: {', '.join(INSTALL_TARGETS)}"
    )


def build_installed_codex_config_text(
    current_text: str,
    command: str,
    *,
    command_windows: str | None = None,
) -> tuple[str, bool]:
    """Return (new_config_text, already_installed) for project-local Codex TOML.

    The Codex config format is TOML and often hand-edited, so this function
    appends a small Aegis hook block instead of reserializing the whole file.
    """

    aegis_commands = tuple(_codex_aegis_hook_commands(current_text))
    if any(_command_has_codex_substrate(command_text) for command_text in aegis_commands):
        return (_ensure_trailing_newline(current_text), True)
    if aegis_commands:
        raise InstallStructureError(
            "existing Aegis hook command in .codex/config.toml does not include "
            "--substrate codex"
        )

    block = _codex_hook_block(command, command_windows=command_windows)
    if not current_text.strip():
        return (block, False)
    return (_ensure_trailing_newline(current_text) + "\n" + block, False)


def cmd_install(
    base_dir: str | Path,
    *,
    assume_yes: bool = False,
    global_requested: bool = False,
    target: str = TARGET_CLAUDE_CODE,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    try:
        normalized_target = normalize_install_target(target)
    except ValueError as exc:
        _write(out, f"aeg install: aborted — {exc}")
        return 2

    if global_requested:
        _write(
            out,
            "aeg install: global install is not supported in this version.\n"
            "Only project-local install is supported: run 'aeg install' inside "
            "your project directory.",
        )
        return 2

    if normalized_target == TARGET_CODEX:
        return _cmd_install_codex(
            base_dir,
            assume_yes=assume_yes,
            input_stream=input_stream,
            output_stream=out,
        )

    return _cmd_install_claude_code(
        base_dir,
        assume_yes=assume_yes,
        input_stream=input_stream,
        output_stream=out,
    )


def _cmd_install_claude_code(
    base_dir: str | Path,
    *,
    assume_yes: bool,
    input_stream: TextIO | None,
    output_stream: TextIO,
) -> int:
    out = output_stream

    path = settings_path(base_dir)
    data, existed, error = load_settings(path)
    if error is not None:
        _write(out, f"aeg install: aborted — {error}")
        _write(out, "Please fix or remove the file manually, then retry.")
        return 1

    command, args = resolve_claude_code_hook_command()
    matcher = claude_code_hook_matcher()
    try:
        new_data, already = build_installed_settings(
            data or {},
            command,
            args=args,
            matcher=matcher,
        )
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
    _write(out, f"  hook command: {_format_hook_command(command, args=args)}")
    _write(out, f"  matcher:      {matcher}")
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


def _cmd_install_codex(
    base_dir: str | Path,
    *,
    assume_yes: bool,
    input_stream: TextIO | None,
    output_stream: TextIO,
) -> int:
    out = output_stream
    path = codex_config_path(base_dir)
    before_text, existed, error = _load_text_file(path)
    if error is not None:
        _write(out, f"aeg install: aborted — {error}")
        _write(out, "Please fix or remove the file manually, then retry.")
        return 1

    command = resolve_hook_command(substrate=TARGET_CODEX)
    command_windows = resolve_codex_windows_hook_command()
    try:
        after_text, already = build_installed_codex_config_text(
            before_text,
            command,
            command_windows=command_windows,
        )
    except InstallStructureError as exc:
        _write(out, f"aeg install: aborted — unexpected Codex config structure: {exc}")
        _write(out, "Please adjust .codex/config.toml manually, then retry.")
        return 1

    if already:
        _write(out, "aeg install: an Aegis Codex PreToolUse hook is already installed; no changes.")
        return 0

    preview_before = before_text if existed else "(no .codex/config.toml yet)\n"
    _write(out, f"aeg install: will register the Aegis PreToolUse hook in {path}")
    _write(out, f"  target:       {TARGET_CODEX}")
    _write(out, f"  hook command: {command}")
    if command_windows is not None:
        _write(out, f"  windows cmd:  {command_windows}")
    _write(out, f"  matcher:      {CODEX_AEGIS_HOOK_MATCHER}")
    _write(out, "")
    _write_diff(out, preview_before, after_text, path)

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if existed:
        backup = _backup_file(path)
        _write(out, f"aeg install: backed up existing config to {backup}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(after_text, encoding="utf-8")
    _write(out, f"aeg install: done. Aegis PreToolUse hook registered in {path}")
    _write(out, "aeg install: note: Codex hook trust/review is handled by Codex itself.")
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
            if is_aegis_hook(hook):
                return True
    return False


def _command_hook(command: str, *, args: Sequence[str] | None = None) -> dict[str, Any]:
    hook: dict[str, Any] = {"type": "command", "command": command}
    if args is not None:
        hook["args"] = list(args)
    return hook


def _format_hook_command(command: str, *, args: Sequence[str] | None = None) -> str:
    if args is None:
        return command
    return f"{command} args={list(args)!r}"


def _is_string_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and all(
        isinstance(item, str) for item in value
    )


def _is_aegis_exec_form_hook(command: str, args: tuple[str, ...]) -> bool:
    if HOOK_RUN_MARKER not in args:
        return False

    command_name = command.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    if command_name in ("aeg", "aeg.exe"):
        return True

    return any(
        args[index : index + 3] == ("-m", "src.cli", HOOK_RUN_MARKER)
        for index in range(max(len(args) - 2, 0))
    )


def _is_windows_exe_path(path: str) -> bool:
    return path.replace("\\", "/").rstrip("/").lower().endswith(".exe")


def _load_text_file(path: Path) -> tuple[str, bool, str | None]:
    if not path.exists():
        return ("", False, None)
    try:
        return (path.read_text(encoding="utf-8"), True, None)
    except OSError as exc:
        return ("", True, f"cannot read {path}: {exc}")


def _codex_hook_block(command: str, *, command_windows: str | None = None) -> str:
    windows_line = (
        f"command_windows = {_toml_string(command_windows)}\n"
        if command_windows is not None
        else ""
    )
    return (
        "# Aegis PreToolUse hook for Codex. Managed by `aeg install --target codex`.\n"
        "[[hooks.PreToolUse]]\n"
        f"matcher = {_toml_string(CODEX_AEGIS_HOOK_MATCHER)}\n"
        "\n"
        "[[hooks.PreToolUse.hooks]]\n"
        "type = \"command\"\n"
        f"command = {_toml_string(command)}\n"
        f"{windows_line}"
    )


def _codex_aegis_hook_commands(text: str) -> list[str]:
    commands: list[str] = []
    current_array_table: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[[") and stripped.endswith("]]"):
            current_array_table = stripped[2:-2].strip()
            continue
        if current_array_table != "hooks.PreToolUse.hooks":
            continue
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() != "command":
            continue
        parsed = _parse_simple_toml_string(value.strip())
        if parsed is not None and is_aegis_hook_command(parsed):
            commands.append(parsed)
    return commands


def _command_has_codex_substrate(command: str) -> bool:
    parts = command.split()
    return any(
        part == "--substrate"
        and index + 1 < len(parts)
        and parts[index + 1] == TARGET_CODEX
        for index, part in enumerate(parts)
    )


def _parse_simple_toml_string(value: str) -> str | None:
    if len(value) < 2:
        return None
    if value[0] == "'" and value[-1] == "'":
        return value[1:-1]
    if value[0] != '"' or value[-1] != '"':
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, str) else None


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _ensure_trailing_newline(text: str) -> str:
    return text if not text or text.endswith("\n") else text + "\n"


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
    "WINDOWS_AEGIS_HOOK_MATCHER",
    "CODEX_AEGIS_HOOK_MATCHER",
    "claude_code_hook_matcher",
    "HOOK_EVENT_NAME",
    "HOOK_RUN_MARKER",
    "INSTALL_TARGETS",
    "InstallStructureError",
    "TARGET_CLAUDE_CODE",
    "TARGET_CODEX",
    "build_installed_codex_config_text",
    "build_installed_settings",
    "build_uninstalled_settings",
    "cmd_install",
    "cmd_uninstall",
    "codex_config_path",
    "is_aegis_hook",
    "is_aegis_hook_command",
    "load_settings",
    "normalize_install_target",
    "resolve_claude_code_hook_command",
    "resolve_codex_windows_hook_command",
    "resolve_hook_command",
    "resolve_hook_command_parts",
    "resolve_windows_hook_command_parts",
    "settings_path",
]
