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
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from jangseung.contracts import STATE_DIR
from jangseung.state.file_lock import exclusive_hook_lock

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


def secret_naming_writes(repo_root: str | Path, session_id: object) -> tuple[str, ...] | None:
    """Paths this session wrote with text naming a secret file.

    ``None`` means the marks could not be read. The caller treats that as marked:
    an approval must not come back because the file that would hold it broke.
    """

    path = Path(repo_root) / STATE_DIR / SESSION_MARKS_FILE
    try:
        if path.is_symlink():
            return None
        if not path.exists():
            return ()
        if not path.is_file() or path.stat().st_size > MAX_MARKS_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = data["sessions"].get(session_key(session_id), {})
        paths = entry.get("secret_naming_writes", [])
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            return None
        return tuple(paths)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return None


def mark_secret_naming_write(repo_root: str | Path, session_id: object, paths: Sequence[str]) -> None:
    """Record that this session wrote ``paths`` with text naming a secret file."""

    root = Path(repo_root).resolve() / STATE_DIR
    if not root.is_dir():
        raise FileNotFoundError("Jangseung state is not initialized; .aeg directory is missing")
    path = root / SESSION_MARKS_FILE
    if path.is_symlink():
        raise ValueError("session marks must not be a symbolic link")
    key = session_key(session_id)
    with exclusive_hook_lock(root / SESSION_MARKS_LOCK_FILE):
        sessions: dict[str, dict[str, object]] = {}
        try:
            if path.is_file() and path.stat().st_size <= MAX_MARKS_BYTES:
                loaded = json.loads(path.read_text(encoding="utf-8"))["sessions"]
                if isinstance(loaded, dict):
                    sessions = {name: entry for name, entry in loaded.items() if isinstance(entry, dict)}
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            # A broken file reads as marked for every session; rewriting it restores
            # the other sessions and keeps this one marked.
            sessions = {}
        entry = sessions.get(key, {})
        known = entry.get("secret_naming_writes", [])
        merged = list(dict.fromkeys([*(known if isinstance(known, list) else []), *paths]))
        sessions[key] = {
            "secret_naming_writes": [str(item)[:MAX_PATH_CHARACTERS] for item in merged][-MAX_PATHS_PER_SESSION:],
            "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        newest = sorted(sessions.items(), key=lambda item: str(item[1].get("updated", "")))[-MAX_SESSIONS:]
        # ASCII output: a path may hold text UTF-8 cannot encode, such as a lone
        # surrogate, and a mark that cannot be written is an approval not held.
        text = json.dumps({"version": 1, "sessions": dict(newest)}, ensure_ascii=True, sort_keys=True, indent=1)
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
