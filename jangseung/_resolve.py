"""Path resolution remembered for the length of one judgment.

On Windows, resolving a path opens it, about 0.1 ms each time, and one hook
judgment resolved the same few paths (the project root, the guard's own folders)
over 30 times. Inside :func:`one_judgment` each distinct path is resolved once
and the answer reused; a failure is not remembered, so it raises again as
before. Outside it, every call resolves afresh, exactly as ``Path.resolve``.

A judgment changes no files, so within it a path resolves the same each time.
The memory ends with the judgment and is never shared between calls.
"""

from pathlib import Path
import os

_memo = None


def resolved(path, *, strict=False):
    """``Path(path).resolve(strict=strict)``, remembered within one judgment."""

    candidate = path if isinstance(path, Path) else Path(path)
    memo = _memo
    if memo is None:
        return candidate.resolve(strict=strict)
    key = (type(candidate), str(candidate), strict)
    found = memo.get(key)
    if found is None:
        found = candidate.resolve(strict=strict)
        memo[key] = found
    return found


def realpath_text(path):
    """``os.path.realpath(path)``, remembered within one judgment."""

    memo = _memo
    if memo is None:
        return os.path.realpath(path)
    key = (str, path)
    found = memo.get(key)
    if found is None:
        found = os.path.realpath(path)
        memo[key] = found
    return found


class one_judgment:
    """Remember resolutions until the outermost judgment ends."""

    __slots__ = ("_outer",)

    def __enter__(self):
        global _memo
        self._outer = _memo
        if _memo is None:
            _memo = {}
        return self

    def __exit__(self, *exc_info):
        global _memo
        _memo = self._outer
        return False
