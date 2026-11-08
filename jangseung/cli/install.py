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
import sysconfig
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence, TextIO

AEGIS_HOOK_MATCHER = "Write|Edit|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob"
WINDOWS_AEGIS_HOOK_MATCHER = f"{AEGIS_HOOK_MATCHER}|PowerShell"
CODEX_AEGIS_HOOK_MATCHER = "Write|Edit|Bash|Read|apply_patch"
# The opt-in MCP entry. It is separate because Codex trusts each entry by a hash
# that includes its matcher: widening the existing matcher would switch off the
# whole guard until the user approved it again. Resource reads carry no prefix.
CLAUDE_CODE_MCP_HOOK_MATCHER = "^(mcp__.*|ReadMcpResourceTool)$"
CODEX_MCP_HOOK_MATCHER = "^(mcp__.*|read_mcp_resource)$"
# Marks the MCP entry's command so install, uninstall and doctor tell it apart.
MCP_HOOK_FLAG = "--mcp"
HOOK_KIND_MAIN = "main"
HOOK_KIND_MCP = "mcp"
HOOK_KINDS = (HOOK_KIND_MAIN, HOOK_KIND_MCP)
# -I keeps the project's own files off sys.path: with plain ``python -m`` a
# planted json.py in the working directory would run inside the guard.
ISOLATED_MODULE_ARGS = ("-I", "-m", "jangseung.cli")
# Earlier releases shipped the package as ``src`` and registered these forms.
# They no longer start, so they are only recognized to be upgraded or removed.
LEGACY_MODULE_ARGS = ("-m", "src.cli")
MANAGED_MODULE_ARGS = (ISOLATED_MODULE_ARGS, ("-m", "jangseung.cli"), LEGACY_MODULE_ARGS)
# A hook that cannot start or crashes must stop the tool call, not wave it through.
CLAUDE_HOOK_ON_FAILURE = "block"
HOOK_EVENT_NAME = "PreToolUse"
BACKUP_SUFFIX_PREFIX = "aegis-backup"
TARGET_CLAUDE_CODE = "claude-code"
TARGET_CODEX = "codex"
INSTALL_TARGETS = (TARGET_CLAUDE_CODE, TARGET_CODEX)


class InstallStructureError(Exception):
    """Raised when the existing settings has a structure we will not modify."""


def _installed_console_script() -> str | None:
    """Locate the ``aeg`` script of this interpreter, on PATH or not.

    A script found directly in the working directory is ignored: Windows
    searches there first, and a project must not choose its own guard.
    """

    found = shutil.which("aeg")
    if isinstance(found, str):
        try:
            if Path(found).resolve().parent != Path.cwd().resolve():
                return found
        except OSError:
            pass
    names = ("aeg.exe",) if os.name == "nt" else ("aeg",)
    directories = (sysconfig.get_path("scripts"), sysconfig.get_path("scripts", f"{os.name}_user"))
    for directory in directories:
        for name in names:
            candidate = Path(directory) / name
            if candidate.is_file():
                return str(candidate)
    return None


def resolve_hook_command(*, substrate: str | None = None, mcp: bool = False) -> str:
    """Return the command string the substrate should run for the hook, using
    the installed ``aeg`` console script if available (absolute path, no
    PYTHONPATH needed), else the current interpreter's isolated module form."""

    command, args = resolve_hook_command_parts(substrate=substrate, mcp=mcp)
    return shlex.join((command, *args))


def resolve_hook_command_parts(
    *,
    substrate: str | None = None,
    mcp: bool = False,
) -> tuple[str, tuple[str, ...]]:
    """Return the hook executable and argv tail without shell tokenization."""

    aeg_path = _installed_console_script()
    if aeg_path:
        command = aeg_path
        args = ["hook-run"]
    else:
        command = sys.executable
        args = [*ISOLATED_MODULE_ARGS, "hook-run"]
    if substrate:
        args.extend(("--substrate", substrate))
    if mcp:
        args.append(MCP_HOOK_FLAG)
    return (command, tuple(args))


def resolve_claude_code_hook_command(
    *,
    platform: str | None = None,
    mcp: bool = False,
) -> tuple[str, tuple[str, ...] | None]:
    """Return the Claude Code command config.

    POSIX platforms keep the existing shell-form command string. Windows uses
    Claude Code exec form (``command`` + ``args``) so Git Bash/PowerShell never
    reinterpret backslashes or spaces in the Python executable path.
    """

    effective_platform = sys.platform if platform is None else platform
    if effective_platform == "win32":
        return resolve_windows_hook_command_parts(mcp=mcp)
    return (resolve_hook_command(mcp=mcp), None)


def claude_code_hook_matcher(*, platform: str | None = None) -> str:
    """Return the Claude Code matcher for the current platform.

    Windows Claude Code exposes file mutation through both Bash and PowerShell
    tool calls. POSIX keeps the historical matcher unchanged.
    """

    effective_platform = sys.platform if platform is None else platform
    if effective_platform == "win32":
        return WINDOWS_AEGIS_HOOK_MATCHER
    return AEGIS_HOOK_MATCHER


def resolve_windows_hook_command_parts(*, mcp: bool = False) -> tuple[str, tuple[str, ...]]:
    """Return a Windows exec-form hook target that Claude Code can spawn."""

    tail = (MCP_HOOK_FLAG,) if mcp else ()
    aeg_path = _installed_console_script()
    if isinstance(aeg_path, str) and _is_windows_exe_path(aeg_path):
        return (aeg_path, ("hook-run", *tail))
    return (sys.executable, (*ISOLATED_MODULE_ARGS, "hook-run", *tail))


def resolve_codex_windows_hook_command(*, platform: str | None = None, mcp: bool = False) -> str | None:
    """Return a Windows command string for Codex, when installing on Windows."""

    effective_platform = sys.platform if platform is None else platform
    if effective_platform != "win32":
        return None
    command, args = resolve_windows_hook_command_parts()
    tail = (MCP_HOOK_FLAG,) if mcp else ()
    return subprocess.list2cmdline((command, *args, "--substrate", TARGET_CODEX, *tail))


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
    kind: str = HOOK_KIND_MAIN,
) -> tuple[dict[str, Any], bool]:
    """Return (new_settings, already_installed). Preserves all existing content.

    Appends one Aegis PreToolUse entry of ``kind``, or brings an existing one up
    to date so re-running install repairs a stale command, matcher or failure
    mode. The command must already carry the MCP flag for the MCP kind.
    """

    new_data = deepcopy(data)
    hooks = new_data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallStructureError("'hooks' is not a JSON object")
    pretooluse = hooks.setdefault(HOOK_EVENT_NAME, [])
    if not isinstance(pretooluse, list):
        raise InstallStructureError(f"'hooks.{HOOK_EVENT_NAME}' is not a JSON array")

    existing = _find_aegis_hook(pretooluse, kind=kind)
    if existing is not None:
        entry, hook = existing
        desired = _command_hook(command, args=args)
        changed = entry.get("matcher") != matcher or any(hook.get(key) != value for key, value in desired.items())
        if args is None and "args" in hook:
            changed = True
        if not changed:
            return (new_data, True)
        entry["matcher"] = matcher
        hook.update(desired)
        if args is None:
            hook.pop("args", None)
        return (new_data, False)

    pretooluse.append(
        {
            "matcher": matcher,
            "hooks": [_command_hook(command, args=args)],
        }
    )
    return (new_data, False)


def build_uninstalled_settings(
    data: dict[str, Any],
    *,
    kinds: Sequence[str] = HOOK_KINDS,
) -> tuple[dict[str, Any], int]:
    """Return (new_settings, removed_count). Removes only Aegis hooks of
    ``kinds``; preserves every other hook and field; cleans up now-empty
    structures."""

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
            if not (isinstance(hook, dict) and _managed_hook_kind(hook) in kinds)
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
    mcp_command: str | None = None,
    mcp_command_windows: str | None = None,
    add_mcp: bool = False,
) -> tuple[str, bool]:
    """Return (new_config_text, already_installed) for project-local Codex TOML.

    Parse and preserve the syntax tree, including comments, inline arrays and
    quoted keys. Never append an array-of-tables onto a statically defined array.
    An existing MCP entry is repaired when ``mcp_command`` is given; it is added
    only with ``add_mcp``.
    """

    import tomlkit
    from tomlkit.items import AoT

    if add_mcp and mcp_command is None:
        raise ValueError("add_mcp requires mcp_command")
    data = _parse_codex_config(current_text)
    entries = _codex_entries(data)
    desired = {
        HOOK_KIND_MAIN: (command, command_windows),
        HOOK_KIND_MCP: (mcp_command, mcp_command_windows),
    }
    installed = {kind: False for kind in HOOK_KINDS}
    stale = False
    for entry in entries or []:
        for hook in entry["hooks"]:
            plain = hook.unwrap()
            kind = _managed_hook_kind(plain, substrates=(None, TARGET_CODEX))
            if kind is None:
                continue
            if not _is_managed_hook(plain, substrates=(TARGET_CODEX,)):
                raise InstallStructureError(
                    "existing Aegis hook command in .codex/config.toml does not include --substrate codex"
                )
            installed[kind] = True
            wanted, wanted_windows = desired[kind]
            if wanted is None:
                continue
            # Re-running install repairs a command an upgrade made stale.
            if plain.get("command") != wanted:
                hook["command"] = wanted
                stale = True
            if wanted_windows is not None and plain.get("command_windows") != wanted_windows:
                hook["command_windows"] = wanted_windows
                stale = True
    comments = []
    if not installed[HOOK_KIND_MAIN]:
        comments.append(_CODEX_HOOK_COMMENT)
    if add_mcp and not installed[HOOK_KIND_MCP]:
        comments.append(_CODEX_MCP_HOOK_COMMENT)
    if not comments:
        return (tomlkit.dumps(data), False) if stale else (current_text, True)
    blocks = [
        _codex_hook_block(command, command_windows=command_windows)
        if comment == _CODEX_HOOK_COMMENT else
        _codex_hook_block(mcp_command, command_windows=mcp_command_windows,
                          matcher=CODEX_MCP_HOOK_MATCHER, comment=comment)
        for comment in comments
    ]

    new = tomlkit.parse("\n".join(blocks))
    if "hooks" not in data:
        # Keep existing text byte-for-byte when a new root table can be appended.
        result = _ensure_trailing_newline(current_text)
        result += ("\n" if result else "") + tomlkit.dumps(new)
    else:
        hooks = data["hooks"]
        new_entries = new["hooks"][HOOK_EVENT_NAME]
        if entries is None:
            hooks[HOOK_EVENT_NAME] = new_entries.unwrap()
        elif isinstance(entries, AoT):
            for comment, new_entry in zip(comments, new_entries):
                # An appended table drops the comment line above it; put it back
                # after a blank line so the managed entries stay readable.
                new_entry.trivia.indent = f"\n{comment}\n"
                entries.append(new_entry)
        else:
            for new_entry in new_entries:
                entries.append(new_entry.unwrap())
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
    mcp: bool = False,
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
            mcp=mcp,
            input_stream=input_stream,
            output_stream=out,
        )

    return _cmd_install_claude_code(
        base_dir,
        assume_yes=assume_yes,
        mcp=mcp,
        input_stream=input_stream,
        output_stream=out,
    )


def _cmd_install_claude_code(
    base_dir: str | Path,
    *,
    assume_yes: bool,
    mcp: bool = False,
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
    mcp_command, mcp_args = resolve_claude_code_hook_command(mcp=True)
    try:
        new_data, already = build_installed_settings(
            data or {},
            command,
            args=args,
            matcher=matcher,
        )
        # Plain install keeps an MCP entry a person added earlier up to date.
        mcp_entry = mcp or _find_aegis_hook(new_data["hooks"][HOOK_EVENT_NAME], kind=HOOK_KIND_MCP) is not None
        if mcp_entry:
            new_data, mcp_already = build_installed_settings(
                new_data,
                mcp_command,
                args=mcp_args,
                matcher=CLAUDE_CODE_MCP_HOOK_MATCHER,
                kind=HOOK_KIND_MCP,
            )
            already = already and mcp_already
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
    if mcp_entry:
        _write(out, f"  MCP command:  {_format_hook_command(mcp_command, args=mcp_args)}")
        _write(out, f"  MCP matcher:  {CLAUDE_CODE_MCP_HOOK_MATCHER}")
    _write(out, "")
    _write_diff(out, before_text, after_text, path)
    _write(out, "Recording setup: ensure local .aeg/ exists; existing records are preserved.")

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if not _write_install(base_dir, path, after_text, existed, out):
        return 1
    _write(out, f"aeg install: done. Aegis PreToolUse hook registered in {path}")
    if mcp_entry:
        _write(out, _MCP_INSTALLED_NOTE)
    return 0


def _cmd_install_codex(
    base_dir: str | Path,
    *,
    assume_yes: bool,
    mcp: bool = False,
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
    mcp_command = resolve_hook_command(substrate=TARGET_CODEX, mcp=True)
    mcp_command_windows = resolve_codex_windows_hook_command(mcp=True)
    try:
        after_text, already = build_installed_codex_config_text(
            before_text,
            command,
            command_windows=command_windows,
            mcp_command=mcp_command,
            mcp_command_windows=mcp_command_windows,
            add_mcp=mcp,
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
    if mcp:
        _write(out, f"  MCP command:  {mcp_command}")
        if mcp_command_windows is not None:
            _write(out, f"  MCP windows:  {mcp_command_windows}")
        _write(out, f"  MCP matcher:  {CODEX_MCP_HOOK_MATCHER}")
    _write(out, "")
    _write_diff(out, preview_before, after_text, path)
    _write(out, "Recording setup: ensure local .aeg/ exists; existing records are preserved.")

    if not assume_yes and not _confirm(input_stream, out):
        _write(out, "aeg install: cancelled; no changes written.")
        return 0

    if not _write_install(base_dir, path, after_text, existed, out):
        return 1
    _write(out, f"aeg install: done. Aegis PreToolUse hook registered in {path}")
    _write(out, "aeg install: IMPORTANT: Codex runs a project hook only after you trust it.")
    _write(out, "Until you review and approve this hook in Codex, the hook does not run and nothing is blocked.")
    if mcp:
        _write(out, "The MCP hook is a separate hook: approve it in Codex /hooks as well. Until then MCP calls are not checked.")
        _write(out, _MCP_INSTALLED_NOTE)
    return 0


def cmd_uninstall(
    base_dir: str | Path,
    *,
    assume_yes: bool = False,
    target: str = TARGET_CLAUDE_CODE,
    mcp_only: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    out = output_stream if output_stream is not None else sys.stdout
    try:
        normalized_target = normalize_install_target(target)
    except ValueError as exc:
        _write(out, f"aeg uninstall: aborted — {exc}")
        return 2
    kinds = (HOOK_KIND_MCP,) if mcp_only else HOOK_KINDS
    if normalized_target == TARGET_CODEX:
        return _cmd_uninstall_codex(
            base_dir, assume_yes=assume_yes, kinds=kinds,
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

    new_data, removed = build_uninstalled_settings(data or {}, kinds=kinds)
    if removed == 0:
        if mcp_only:
            _write(out, "aeg uninstall: no Aegis MCP hook found; nothing to remove.")
        else:
            _write(out, "aeg uninstall: no Aegis PreToolUse hook found; nothing to remove.")
        return 0

    before_text = _json_text(data)
    after_text = _json_text(new_data)
    _write(out, f"aeg uninstall: will remove {removed} Aegis {'MCP ' if mcp_only else ''}hook entry(ies) from {path}")
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
    if mcp_only:
        _write(out, f"aeg uninstall: done. Removed the Aegis MCP hook from {path}; the main hook is unchanged.")
    else:
        _write(out, f"aeg uninstall: done. Removed the Aegis PreToolUse hook from {path}")
    return 0


def _is_managed_codex_hook(hook: dict[str, Any]) -> bool:
    """Recognize generated argv, never a shell command merely mentioning aeg."""
    return _is_managed_hook(hook, substrates=(None, TARGET_CODEX))


def _managed_argv_kind(argv: Sequence[str], substrates: tuple[str | None, ...]) -> str | None:
    """Return the hook kind of installer-generated argv, or None."""
    if not argv:
        return None
    executable = argv[0].replace("\\", "/")
    name = executable.rsplit("/", 1)[-1]
    if executable != name and not (
        executable.startswith("/") or re.match(r"^[A-Za-z]:/", executable)
    ):
        return None
    if name.lower().endswith(".exe"):
        name = name.lower()
    if name in {"aeg", "aeg.exe"}:
        prefixes: tuple[tuple[str, ...], ...] = ((),)
    elif re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", name):
        prefixes = MANAGED_MODULE_ARGS
    else:
        return None
    tail = tuple(argv[1:])
    for prefix in prefixes:
        for substrate in substrates:
            expected = (*prefix, "hook-run", *(() if substrate is None else ("--substrate", substrate)))
            if tail == expected:
                return HOOK_KIND_MAIN
            if tail == (*expected, MCP_HOOK_FLAG):
                return HOOK_KIND_MCP
    return None


def _managed_argv(argv: Sequence[str], substrates: tuple[str | None, ...]) -> bool:
    return _managed_argv_kind(argv, substrates) is not None


def _managed_command(command: Any, substrates: tuple[str | None, ...]) -> bool:
    return _parse_managed_command(command, substrates) is not None


def _parse_managed_command(command: Any, substrates: tuple[str | None, ...]) -> tuple[str, ...] | None:
    """Return only installer-recognized argv, for read-only diagnostics too."""
    if not isinstance(command, str) or any(char in command for char in "\r\n\x00"):
        return None
    try:
        argv = tuple(shlex.split(command))
        if _managed_argv(argv, substrates):
            return argv
    except ValueError:
        return None
    # Compatibility with the unquoted native Windows paths emitted by 0.1.2.
    # Restrict this fallback to a single drive-absolute executable, never a
    # shell wrapper or POSIX command prefix which only mentions aeg.
    match = re.fullmatch(
        r"([A-Za-z]:[\\/][^:;&|<>`$\r\n\"']+?)\s+((?:(?:-I\s+)?-m\s+(?:jangseung|src)\.cli\s+)?hook-run(?:\s+--substrate\s+(?:codex|claude-code))?)\s*",
        command.strip(),
    )
    if match:
        argv = (match[1], *match[2].split())
        if _managed_argv(argv, substrates):
            return argv
    return None


def _managed_hook_kind(
    hook: dict[str, Any], *, substrates: tuple[str | None, ...] = (None, TARGET_CODEX, TARGET_CLAUDE_CODE),
) -> str | None:
    """Return ``main`` or ``mcp`` for an installer-generated hook, else None.

    A hook whose POSIX and Windows commands disagree on the kind is not ours.
    """
    if hook.get("type") != "command":
        return None
    command = hook.get("command")
    args = hook.get("args")
    if args is not None:
        if isinstance(command, str) and _is_string_sequence(args) and hook.get("command_windows") is None:
            return _managed_argv_kind((command, *args), substrates)
        return None
    kinds = set()
    for field in ("command", "command_windows"):
        if field not in hook:
            continue
        argv = _parse_managed_command(hook[field], substrates)
        if argv is None:
            return None
        kinds.add(_managed_argv_kind(argv, substrates))
    return kinds.pop() if len(kinds) == 1 else None


def _is_managed_hook(
    hook: dict[str, Any], *, substrates: tuple[str | None, ...] = (None, TARGET_CODEX, TARGET_CLAUDE_CODE),
) -> bool:
    return _managed_hook_kind(hook, substrates=substrates) is not None


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


def build_uninstalled_codex_config_text(
    current_text: str, *, kinds: Sequence[str] = HOOK_KINDS,
) -> tuple[str, int]:
    """Remove only managed hooks of ``kinds`` using a comment-preserving TOML syntax tree."""
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
            if _managed_hook_kind(hook.unwrap(), substrates=(None, TARGET_CODEX)) in kinds:
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
    base_dir: str | Path, *, assume_yes: bool, kinds: Sequence[str] = HOOK_KINDS,
    input_stream: TextIO | None, output_stream: TextIO,
) -> int:
    path = codex_config_path(base_dir)
    before, existed, error = _load_text_file(path)
    out = output_stream
    mcp_only = tuple(kinds) == (HOOK_KIND_MCP,)
    if error:
        _write(out, f"aeg uninstall: aborted — {error}")
        return 1
    if not existed:
        _write(out, f"aeg uninstall: no {path}; nothing to uninstall.")
        return 0
    try:
        after, removed = build_uninstalled_codex_config_text(before, kinds=kinds)
    except InstallStructureError as exc:
        _write(out, f"aeg uninstall: aborted — {exc}")
        return 1
    if not removed:
        if mcp_only:
            _write(out, "aeg uninstall: no Aegis MCP hook found; nothing to remove.")
        else:
            _write(out, "aeg uninstall: no Aegis Codex hook found; nothing to remove.")
        return 0
    _write(out, f"aeg uninstall: will remove {removed} Aegis {'MCP ' if mcp_only else ''}hook entry(ies) from {path}")
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
    if mcp_only:
        _write(out, f"aeg uninstall: done. Removed the Aegis MCP hook from {path}; the main hook is unchanged.")
    else:
        _write(out, f"aeg uninstall: done. Removed the Aegis PreToolUse hook from {path}")
    return 0


def _find_aegis_hook(
    pretooluse: list[Any], *, kind: str = HOOK_KIND_MAIN,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for entry in pretooluse:
        if not isinstance(entry, dict):
            continue
        nested = entry.get("hooks")
        if not isinstance(nested, list):
            continue
        for hook in nested:
            if isinstance(hook, dict) and _managed_hook_kind(hook) == kind:
                return (entry, hook)
    return None


def _command_hook(command: str, *, args: Sequence[str] | None = None) -> dict[str, Any]:
    hook: dict[str, Any] = {"type": "command", "command": command, "onFailure": CLAUDE_HOOK_ON_FAILURE}
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


_CODEX_HOOK_COMMENT = "# Aegis PreToolUse hook for Codex. Managed by `aeg install --target codex`."
_CODEX_MCP_HOOK_COMMENT = (
    "# Aegis MCP PreToolUse hook for Codex. Managed by `aeg install --target codex --mcp`."
)
_MCP_INSTALLED_NOTE = (
    "MCP tool calls and MCP resource reads now need approval (denied on Codex) unless "
    ".aeg/policy.json lists the tool under allow_mcp_tools. Remove only this hook with "
    "aeg uninstall --mcp."
)


def _codex_hook_block(
    command: str,
    *,
    command_windows: str | None = None,
    matcher: str = CODEX_AEGIS_HOOK_MATCHER,
    comment: str = _CODEX_HOOK_COMMENT,
) -> str:
    windows_line = (
        f"command_windows = {_toml_string(command_windows)}\n"
        if command_windows is not None
        else ""
    )
    return (
        f"{comment}\n"
        "[[hooks.PreToolUse]]\n"
        f"matcher = {_toml_string(matcher)}\n"
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
    "CLAUDE_CODE_MCP_HOOK_MATCHER",
    "CLAUDE_HOOK_ON_FAILURE",
    "CODEX_MCP_HOOK_MATCHER",
    "HOOK_KIND_MAIN",
    "HOOK_KIND_MCP",
    "HOOK_KINDS",
    "LEGACY_MODULE_ARGS",
    "MCP_HOOK_FLAG",
    "WINDOWS_AEGIS_HOOK_MATCHER",
    "CODEX_AEGIS_HOOK_MATCHER",
    "claude_code_hook_matcher",
    "HOOK_EVENT_NAME",
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
