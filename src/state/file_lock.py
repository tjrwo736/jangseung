"""Crash-recoverable hook locks, compatible with the 0.1.2 PID sentinel.

An OS-held guard serializes new writers and stale-sentinel recovery. Closing the
descriptor (including process death) releases it. The guard file is never
unlinked: replacing its inode could give two writers different locks. The old
PID sentinel is still acquired so an active 0.1.2 writer is never ignored.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import time
from typing import Iterator


def _check_regular(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("hook lock must be a regular file without hardlinks")


def _try_os_lock(descriptor: int) -> None:
    if os.name == "nt":
        import msvcrt
        os.lseek(descriptor, 0, os.SEEK_SET)
        # Windows permits locking a byte beyond EOF, so an empty guard is OK.
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _pid_is_dead(pid: int) -> bool:
    """Only a positive proof of death authorizes sentinel removal."""
    if not 0 < pid <= 0xFFFFFFFF:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)  # POSIX existence probe, not a terminating signal.
        except ProcessLookupError:
            return True
        except (OSError, OverflowError):
            return False
        return False
    # os.kill(pid, 0) is NOT a safe existence probe on Windows.
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # query limited information only
    if not handle:
        return ctypes.get_last_error() == 87  # invalid PID; access denied is unknown
    try:
        code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value != 259
    finally:
        kernel.CloseHandle(handle)


def _recover_dead_sentinel(path: Path) -> bool:
    _check_regular(path)
    try:
        before = path.stat()
        with path.open("rb") as handle:
            payload = handle.read(64)
        if not payload.isdigit() or len(payload) > 10 or not _pid_is_dead(int(payload)):
            return False
        after = path.stat()
        identity = lambda info: (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size)
        if identity(before) != identity(after):
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return True


def _wait(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError("hook ledger append lock is busy or its owner is unknown")
    time.sleep(min(0.02, max(0, deadline - time.monotonic())))


@contextmanager
def exclusive_hook_lock(lock_path: Path, *, timeout_seconds: float = 1.0) -> Iterator[None]:
    deadline = time.monotonic() + timeout_seconds
    guard_path = lock_path.with_suffix(".guard")
    _check_regular(guard_path)
    guard = os.open(guard_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    descriptor: int | None = None
    owned = False
    try:
        info = os.fstat(guard)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("hook guard must be a regular file without hardlinks")
        while True:
            try:
                _try_os_lock(guard)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                _wait(deadline)
        while descriptor is None:
            _check_regular(lock_path)
            try:
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                owned = True
            except FileExistsError:
                if not _recover_dead_sentinel(lock_path):
                    _wait(deadline)
        payload = str(os.getpid()).encode("ascii")
        if os.write(descriptor, payload) != len(payload):
            raise OSError("could not write complete hook lock owner")
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
            if owned:
                lock_path.unlink(missing_ok=True)
        finally:
            os.close(guard)
