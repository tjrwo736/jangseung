"""One-time approvals a person grants with ``aeg allow-once``.

Codex has no way for a hook to ask a person, so a command the hook cannot prove
safe is denied there. ``aeg allow-once "<command>"`` lets a person approve that
exact command text for this project, once, for a few minutes. The hook treats it
like an ``allow_commands`` approval: the target, secret and guard gates still apply,
and a session that wrote text naming a secret file is still asked instead.

Only a person runs ``aeg allow-once``; the hook denies an agent's call to it.
The user-owned file holds hashes, never command text. Legacy checkout grants
are deliberately never read or migrated.
"""

from __future__ import annotations

from jangseung._sha256 import sha256
import json
from pathlib import Path
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from datetime import datetime
    from typing import Any

from jangseung.state.approvals import approval_root, read_small_file, write_private
from jangseung.state.file_lock import exclusive_hook_lock

ALLOW_ONCE_FILE = "allow_once.json"
ALLOW_ONCE_LOCK_FILE = "allow_once.lock"
MAX_ENTRIES = 32
MAX_FILE_BYTES = 64 * 1024
DEFAULT_MINUTES = 10
MAX_MINUTES = 60


DEFAULT_TOOL = "Bash"
TOOLS = ("Bash", "PowerShell")


def command_key(command: str, tool: str = DEFAULT_TOOL) -> str:
    """The hash an approval is stored under: the shell tool and the exact text.

    The file sits in user-owned storage scoped to this project, and is honored only when the
    command runs in the project's own folder.
    """

    return sha256(f"{tool}\x00{command}".encode("utf-8", "surrogatepass")).hexdigest()


def _now() -> datetime:
    # Imported here: a hook call without approvals on file never needs it (about 0.5 ms).
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _read(root: Path) -> dict[str, str] | None:
    try:
        raw = read_small_file(root / ALLOW_ONCE_FILE, MAX_FILE_BYTES, personal=True)
        if raw is None:
            return {}
        data: Any = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, RuntimeError, KeyError):
        return None
    if (not isinstance(data, dict) or set(data) != {"version", "entries"}
            or type(data["version"]) is not int or data["version"] != 1):
        return None
    entries = data["entries"]
    if (not isinstance(entries, dict) or len(entries) > MAX_ENTRIES
            or not all(len(key) == 64 and not set(key) - set("0123456789abcdef") and isinstance(value, str)
                       for key, value in entries.items())):
        return None
    from datetime import datetime

    try:
        if any(datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None for value in entries.values()):
            return None
    except ValueError:
        return None
    return entries


def _live(entries: dict[str, str], now: datetime) -> dict[str, str]:
    from datetime import datetime, timedelta

    kept: dict[str, str] = {}
    for key, expires in entries.items():
        try:
            moment = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        except ValueError:
            continue
        if moment.tzinfo is not None and now < moment <= now + timedelta(minutes=MAX_MINUTES):
            kept[key] = expires
    return kept


def approved_once(command: object, repo_root: str | Path, tool: str = DEFAULT_TOOL) -> bool:
    """True when a person approved this exact command text here, and it is not used or expired."""

    if not isinstance(command, str) or not command.strip():
        return False
    try:
        entries = _read(approval_root(repo_root))
    except (OSError, ValueError, RuntimeError, KeyError):
        return False
    if not entries:
        return False
    return command_key(command, tool) in _live(entries, _now())


def _write(root: Path, entries: dict[str, str]) -> None:
    path = root / ALLOW_ONCE_FILE
    text = json.dumps({"version": 1, "entries": entries}, ensure_ascii=True, sort_keys=True, indent=1) + "\n"
    write_private(path, text.encode("ascii"))


def grant_once(command: str, repo_root: str | Path, minutes: int = DEFAULT_MINUTES, tool: str = DEFAULT_TOOL) -> datetime:
    """Store a one-time approval; returns when it expires. Run by a person."""

    from datetime import timedelta

    minutes = max(1, min(int(minutes), MAX_MINUTES))
    root = approval_root(repo_root, create=True)
    expires = _now() + timedelta(minutes=minutes)
    with exclusive_hook_lock(root / ALLOW_ONCE_LOCK_FILE):
        current = _read(root)
        if current is None:
            raise ValueError("cannot update an invalid personal approval file")
        entries = _live(current, _now())
        entries[command_key(command, tool)] = expires.isoformat().replace("+00:00", "Z")
        newest = dict(sorted(entries.items(), key=lambda item: item[1])[-MAX_ENTRIES:])
        _write(root, newest)
    return expires


def consume_once(command: str, repo_root: str | Path, tool: str = DEFAULT_TOOL) -> bool:
    """Remove the approval after the hook used it. False if it was not there."""

    root = approval_root(repo_root)
    if not (root / ALLOW_ONCE_FILE).is_file():
        return False
    with exclusive_hook_lock(root / ALLOW_ONCE_LOCK_FILE):
        entries = _live(_read(root) or {}, _now())
        key = command_key(command, tool)
        if key not in entries:
            return False
        del entries[key]
        _write(root, entries)
    return True


def clear_all(repo_root: str | Path) -> int:
    """Drop every pending one-time approval; returns how many there were."""

    root = approval_root(repo_root)
    if not root.exists():
        return 0
    with exclusive_hook_lock(root / ALLOW_ONCE_LOCK_FILE):
        current = _read(root)
        if current is None:
            raise ValueError("cannot clear invalid personal approval storage")
        count = len(_live(current, _now()))
        if current:
            _write(root, {})
    return count


def pending_count(repo_root: str | Path) -> int:
    entries = _read(approval_root(repo_root))
    if entries is None:
        raise ValueError("cannot inspect invalid personal approval storage")
    return len(_live(entries, _now()))


__all__ = [
    "ALLOW_ONCE_FILE",
    "DEFAULT_MINUTES",
    "MAX_MINUTES",
    "approved_once",
    "clear_all",
    "command_key",
    "consume_once",
    "grant_once",
    "pending_count",
]
