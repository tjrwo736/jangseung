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

After confirmation, this module writes substrate hook config and prepares the
folder-local ``.aeg/`` directory for recording. It never changes existing run
or hook records, runs tools, or calls providers.
"""

from __future__ import annotations

import datetime
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
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
    return shlex.join((command, *args))


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

    return _is_managed_hook({"type": "command", "command": command})


def is_aegis_hook(hook: Any) -> bool:
    """Identify both legacy shell-form and Windows exec-form Aegis hooks."""

    return isinstance(hook, dict) and _is_managed_hook(hook)


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
    except (OSError, UnicodeError) as exc:
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

    Parse and preserve the syntax tree, including comments, inline arrays and
    quoted keys. Never append an array-of-tables onto a statically defined array.
    """

    import tomlkit
    from tomlkit.items import AoT

    data = _parse_codex_config(current_text)
    entries = _codex_entries(data)
    installed = False
    for entry in entries or []:
        for hook in entry["hooks"]:
            plain = hook.unwrap()
            if not _is_managed_codex_hook(plain):
                continue
            if not _is_managed_hook(plain, substrates=(TARGET_CODEX,)):
                raise InstallStructureError(
                    "existing Aegis hook command in .codex/config.toml does not include --substrate codex"
                )
            installed = True
    if installed:
        return current_text, True

    new = tomlkit.parse(_codex_hook_block(command, command_windows=command_windows))
    if "hooks" not in data:
        # Keep existing text byte-for-byte when a new root table can be appended.
        result = _ensure_trailing_newline(current_text)
        result += ("\n" if result else "") + tomlkit.dumps(new)
    else:
        hooks = data["hooks"]
        if entries is None:
            hooks[HOOK_EVENT_NAME] = new["hooks"][HOOK_EVENT_NAME].unwrap()
        elif isinstance(entries, AoT):
            entries.append(new["hooks"][HOOK_EVENT_NAME][0])
        else:
            entries.append(new["hooks"][HOOK_EVENT_NAME][0].unwrap())
        result = tomlkit.dumps(data)
    # Validate the serialized result too, before it is ever offered for writing.
    _codex_entries(_parse_codex_config(result))
    return result, False


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
        return _repair_recording_setup(base_dir, assume_yes, input_stream, out)

    before_text = _json_text(data) if existed else "(no .claude/settings.json yet)\n"
    after_text = _json_text(new_data)

    _write(out, f"aeg install: will register the Aegis PreToolUse hook in {path}")
    _write(out, f"  hook command: {_format_hook_command(command, args=args)}")
    _write(out, f"  matcher:      {matcher}")
    _write(out, "")
    _write_diff(out, before_text, after_text, path)
    _write(out, "Recording setup: ensure local .aeg/ exists; existing records are preserved.")

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if not _write_install(base_dir, path, after_text, existed, out):
        return 1
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
        return _repair_recording_setup(base_dir, assume_yes, input_stream, out)

    preview_before = before_text if existed else "(no .codex/config.toml yet)\n"
    _write(out, f"aeg install: will register the Aegis PreToolUse hook in {path}")
    _write(out, f"  target:       {TARGET_CODEX}")
    _write(out, f"  hook command: {command}")
    if command_windows is not None:
        _write(out, f"  windows cmd:  {command_windows}")
    _write(out, f"  matcher:      {CODEX_AEGIS_HOOK_MATCHER}")
    _write(out, "")
    _write_diff(out, preview_before, after_text, path)
    _write(out, "Recording setup: ensure local .aeg/ exists; existing records are preserved.")

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if not _write_install(base_dir, path, after_text, existed, out):
        return 1
    _write(out, f"aeg install: done. Aegis PreToolUse hook registered in {path}")
    _write(out, "aeg install: note: Codex hook trust/review is handled by Codex itself.")
    return 0


def cmd_uninstall(
    base_dir: str | Path,
    *,
    assume_yes: bool = False,
    target: str = TARGET_CLAUDE_CODE,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    try:
        normalized_target = normalize_install_target(target)
    except ValueError as exc:
        _write(out, f"aeg uninstall: aborted — {exc}")
        return 2
    if normalized_target == TARGET_CODEX:
        return _cmd_uninstall_codex(
            base_dir, assume_yes=assume_yes,
            input_stream=input_stream, output_stream=out,
        )
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

    try:
        backup = _backup_file(path)
        _write(out, f"aeg uninstall: backed up existing settings to {backup}")
        _atomic_write_text(path, after_text)
    except OSError as exc:
        _write(out, f"aeg uninstall: failed to back up or write settings: {exc}")
        return 1
    _write(out, f"aeg uninstall: done. Removed the Aegis PreToolUse hook from {path}")
    return 0


def _is_managed_codex_hook(hook: dict[str, Any]) -> bool:
    """Recognize generated argv, never a shell command merely mentioning aeg."""
    return _is_managed_hook(hook, substrates=(None, TARGET_CODEX))


def _managed_argv(argv: Sequence[str], substrates: tuple[str | None, ...]) -> bool:
    if not argv:
        return False
    executable = argv[0].replace("\\", "/")
    name = executable.rsplit("/", 1)[-1]
    if executable != name and not (
        executable.startswith("/") or re.match(r"^[A-Za-z]:/", executable)
    ):
        return False
    if name.lower().endswith(".exe"):
        name = name.lower()
    if name in {"aeg", "aeg.exe"}:
        prefix = ()
    elif re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", name):
        prefix = ("-m", "src.cli")
    else:
        return False
    return any(tuple(argv[1:]) == (*prefix, "hook-run", *(() if substrate is None else ("--substrate", substrate)))
               for substrate in substrates)


def _managed_command(command: Any, substrates: tuple[str | None, ...]) -> bool:
    if not isinstance(command, str) or any(char in command for char in "\r\n\x00"):
        return False
    try:
        if _managed_argv(shlex.split(command), substrates):
            return True
    except ValueError:
        return False
    # Compatibility with the unquoted native Windows paths emitted by 0.1.2.
    # Restrict this fallback to a single drive-absolute executable, never a
    # shell wrapper or POSIX command prefix which only mentions aeg.
    match = re.fullmatch(
        r"([A-Za-z]:[\\/][^:;&|<>`$\r\n\"']+?)\s+((?:-m\s+src\.cli\s+)?hook-run(?:\s+--substrate\s+(?:codex|claude-code))?)\s*",
        command.strip(),
    )
    return bool(match and _managed_argv((match[1], *match[2].split()), substrates))


def _is_managed_hook(
    hook: dict[str, Any], *, substrates: tuple[str | None, ...] = (None, TARGET_CODEX, TARGET_CLAUDE_CODE),
) -> bool:
    if hook.get("type") != "command":
        return False
    command = hook.get("command")
    args = hook.get("args")
    if args is not None:
        return (isinstance(command, str) and _is_string_sequence(args)
                and hook.get("command_windows") is None
                and _managed_argv((command, *args), substrates))
    commands = [hook[field] for field in ("command", "command_windows") if field in hook]
    return bool(commands) and all(_managed_command(value, substrates) for value in commands)


def _parse_codex_config(current_text: str) -> Any:
    import tomlkit
    from tomlkit.exceptions import ParseError

    try:
        return tomlkit.parse(current_text)
    except ParseError as exc:
        raise InstallStructureError("invalid Codex TOML; repair it before changing hooks") from exc


def _codex_entries(data: Any) -> Any:
    hooks = data.get("hooks")
    if hooks is None:
        return None
    if not isinstance(hooks, dict):
        raise InstallStructureError("'hooks' is not a TOML table")
    entries = hooks.get(HOOK_EVENT_NAME)
    if entries is None:
        return None
    if not isinstance(entries, list):
        raise InstallStructureError("'hooks.PreToolUse' is not a TOML array")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            raise InstallStructureError("unexpected Codex PreToolUse hook structure")
        if any(not isinstance(hook, dict) for hook in entry["hooks"]):
            raise InstallStructureError("unexpected Codex command hook structure")
    return entries


def build_uninstalled_codex_config_text(current_text: str) -> tuple[str, int]:
    """Remove only managed hooks using a comment-preserving TOML syntax tree."""
    import tomlkit
    data = _parse_codex_config(current_text)
    entries = _codex_entries(data)
    if entries is None:
        return current_text, 0
    hooks = data["hooks"]
    removed = 0
    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            raise InstallStructureError("unexpected Codex PreToolUse hook structure")
        nested = entry["hooks"]
        previous_count = len(nested)
        for hook_index in range(len(nested) - 1, -1, -1):
            hook = nested[hook_index]
            if not isinstance(hook, dict):
                raise InstallStructureError("unexpected Codex command hook structure")
            if _is_managed_codex_hook(hook.unwrap()):
                del nested[hook_index]
                removed += 1
        if previous_count and not nested:
            del entries[index]
    if not removed:
        return current_text, 0
    if not entries:
        del hooks[HOOK_EVENT_NAME]
    if not hooks:
        del data["hooks"]
    return tomlkit.dumps(data), removed


def _cmd_uninstall_codex(
    base_dir: str | Path, *, assume_yes: bool,
    input_stream: TextIO | None, output_stream: TextIO,
) -> int:
    path = codex_config_path(base_dir)
    before, existed, error = _load_text_file(path)
    out = output_stream
    if error:
        _write(out, f"aeg uninstall: aborted — {error}")
        return 1
    if not existed:
        _write(out, f"aeg uninstall: no {path}; nothing to uninstall.")
        return 0
    try:
        after, removed = build_uninstalled_codex_config_text(before)
    except InstallStructureError as exc:
        _write(out, f"aeg uninstall: aborted — {exc}")
        return 1
    if not removed:
        _write(out, "aeg uninstall: no Aegis Codex hook found; nothing to remove.")
        return 0
    _write(out, f"aeg uninstall: will remove {removed} Aegis hook entry(ies) from {path}")
    _write_diff(out, before, after, path)
    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg uninstall: cancelled; no changes written.")
        return 0
    try:
        backup = _backup_file(path)
        _write(out, f"aeg uninstall: backed up existing config to {backup}")
        _atomic_write_text(path, after)
    except OSError as exc:
        _write(out, f"aeg uninstall: failed to back up or write Codex config: {exc}")
        return 1
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


def _is_windows_exe_path(path: str) -> bool:
    return path.replace("\\", "/").rstrip("/").lower().endswith(".exe")


def _load_text_file(path: Path) -> tuple[str, bool, str | None]:
    if not path.exists():
        return ("", False, None)
    try:
        return (path.read_text(encoding="utf-8"), True, None)
    except (OSError, UnicodeError) as exc:
        return ("", True, f"cannot read {path}: {exc}")


def _recording_directory(base_dir: str | Path) -> Path:
    base = Path(base_dir).resolve()
    root = base / ".aeg"
    if root.is_symlink() or root.resolve().parent != base:
        raise ValueError(".aeg must be a local directory, not a link outside the project")
    if root.exists() and not root.is_dir():
        raise ValueError(".aeg exists but is not a directory")
    return root


def _prepare_recording(base_dir: str | Path) -> None:
    root = _recording_directory(base_dir)
    if not root.exists():
        root.mkdir(parents=True)
        # Keep newly created local evidence out of Git without editing the
        # project's .gitignore or rewriting existing state/records.
        (root / ".gitignore").write_text("*\n", encoding="utf-8")


def _repair_recording_setup(
    base_dir: str | Path, assume_yes: bool, input_stream: TextIO | None, out: TextIO,
) -> int:
    try:
        if _recording_directory(base_dir).is_dir():
            _write(out, "aeg install: an Aegis hook is already installed; no changes.")
            return 0
        _write(out, "aeg install: hook already installed; will prepare .aeg/ for recording (config unchanged).")
        if not assume_yes and not _confirm(input_stream, out):
            _write(out, "aeg install: cancelled; no changes written.")
            return 0
        _prepare_recording(base_dir)
    except (OSError, ValueError) as exc:
        _write(out, f"aeg install: failed to prepare recording: {exc}")
        return 1
    _write(out, "aeg install: recording directory ready; existing hook config preserved.")
    return 0


def _write_install(base_dir: str | Path, path: Path, text: str, existed: bool, out: TextIO) -> bool:
    try:
        _recording_directory(base_dir)  # Reject invalid state before backup/write.
        if existed:
            backup = _backup_file(path)
            _write(out, f"aeg install: backed up existing settings to {backup}")
        _prepare_recording(base_dir)
        _atomic_write_text(path, text)
    except (OSError, ValueError) as exc:
        _write(out, f"aeg install: failed to prepare recording or write config: {exc}")
        return False
    return True


def _atomic_write_text(path: Path, text: str) -> None:
    """Stage complete config next to its destination, then replace atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".aeg-config-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except PermissionError:
                if os.name != "nt":
                    raise
                # copymode may have copied Windows' read-only bit. Only this
                # newly created temporary file is made writable for cleanup.
                temporary.chmod(0o600)
                temporary.unlink(missing_ok=True)


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
