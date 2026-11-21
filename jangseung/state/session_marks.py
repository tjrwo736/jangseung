"""Per-session marks the hook leaves for its own later calls.

One mark exists today: this session wrote text that names a secret file. A command a
person approved in the project policy runs project code, so after such a write the
approval is held and a person is asked instead. The mark is a hint about one obvious
route, not proof either way: text that hides the name leaves no mark, and only the
50 most recently marked sessions are kept.

Only the hook process writes here. Agents cannot, because every tool is denied ``.aeg/``.
"""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
TYPE_CHECKING = False
if TYPE_CHECKING:  # typing costs about 2 ms to import on every hook call
    from typing import Sequence

from jangseung._clock import utc_timestamp
from jangseung.state.file_lock import exclusive_hook_lock
from jangseung.state.paths import state_root

SESSION_MARKS_FILE = "session_marks.json"
SESSION_MARKS_LOCK_FILE = "session_marks.lock"
UNKNOWN_SESSION = "unknown"
MAX_SESSIONS = 50
MAX_PATHS_PER_SESSION = 16
MAX_PATH_CHARACTERS = 200
# Above what the three caps can produce (50 x 16 x 200 characters, at most 12 bytes
# each once escaped), so a file this large was not written by the hook.
MAX_MARKS_BYTES = 4 * 1024 * 1024

_SESSION_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}")


def session_key(session_id: object) -> str:
    """A host session id safe to use as a key; anything else shares one bucket."""

    if isinstance(session_id, str) and _SESSION_ID.fullmatch(session_id):
        return session_id
    return UNKNOWN_SESSION


def _read_sessions(path: Path) -> dict:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {}
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_MARKS_BYTES
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("session marks must be a bounded, unlinked regular file")
    data = json.loads(path.read_text(encoding="utf-8"))
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, dict) or data.get("version") != 1:
        raise ValueError("invalid session marks")
    for entry in sessions.values():
        paths = entry.get("secret_naming_writes") if isinstance(entry, dict) else None
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            raise ValueError("invalid session mark entry")
        if not paths:
            # Older hooks could record a required hold with no displayable
            # targets. Keep *that session* held, without blocking other writers.
            entry["secret_naming_writes"] = ["<unknown>"]
    return sessions


def secret_naming_writes(repo_root: str | Path, session_id: object) -> tuple[str, ...] | None:
    """Paths this session wrote with text naming a secret file.

    ``None`` means the marks could not be read. The caller treats that as marked:
    an approval must not come back because the file that would hold it broke.
    """

    try:
        sessions = _read_sessions(state_root(repo_root) / SESSION_MARKS_FILE)
        return tuple(sessions.get(session_key(session_id), {}).get("secret_naming_writes", ()))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return None


def mark_secret_naming_write(repo_root: str | Path, session_id: object, paths: Sequence[str]) -> None:
    """Record that this session wrote ``paths`` with text naming a secret file."""

    root = state_root(repo_root)
    if not root.is_dir():
        raise FileNotFoundError("Jangseung state is not initialized; .aeg directory is missing")
    path = root / SESSION_MARKS_FILE
    key = session_key(session_id)
    with exclusive_hook_lock(root / SESSION_MARKS_LOCK_FILE):
        # Never erase other sessions' holds to recover from unreadable state.
        sessions = _read_sessions(path)
        known = sessions.pop(key, {}).get("secret_naming_writes", [])
        merged = list(dict.fromkeys([*known, *(paths or ("<unknown>",))]))
        newest = dict(sorted(sessions.items(), key=lambda item: str(item[1].get("updated", "")))[-(MAX_SESSIONS - 1):])
        newest[key] = {
            "secret_naming_writes": [str(item)[:MAX_PATH_CHARACTERS] for item in merged][-MAX_PATHS_PER_SESSION:],
            "updated": utc_timestamp(),
        }
        # ASCII output: a path may hold text UTF-8 cannot encode, such as a lone
        # surrogate, and a mark that cannot be written is an approval not held.
        text = json.dumps({"version": 1, "sessions": newest}, ensure_ascii=True, sort_keys=True, indent=1)
        temporary: Path | None = None
        # Imported here: the hook runs on every tool call and rarely writes a mark,
        # and ``tempfile`` costs about 10 ms to load.
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="ascii", newline="\n", dir=root, prefix=".session-marks-", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(text + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise


__all__ = [
    "SESSION_MARKS_FILE",
    "mark_secret_naming_write",
    "secret_naming_writes",
    "session_key",
]
