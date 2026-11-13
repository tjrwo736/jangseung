"""The resident judging process; see :mod:`jangseung._resident` for the rules it keeps.

Started by a hook call through the same launcher, with the same Python and
interpreter options, as ``<launcher> resident-serve``. It loads the judging path
once, then answers ``hook-run`` calls one at a time over its named pipe until it
has been idle for :data:`jangseung._resident.IDLE_SECONDS` or finds its code
changed on disk.

Each connection goes: the hook sends a challenge; this process proves it holds
the key; only then does the hook send its call; the answer is signed over that
call. A hook that gets no proof within a second judges the call itself.
"""

import os
import sys
import time

from jangseung import _resident
from jangseung._resident import (
    _ANSWER_SECONDS,
    _ANSWERED,
    _CHALLENGE_BYTES,
    _DECLINED,
    _KEY_BYTES,
    _MAGIC,
    _MAX_MESSAGE_BYTES,
    _PIPE_PREFIX,
    _PROOF_LABEL,
    _Plan,
    _digest,
    _mac,
    _pack,
    _read_exact,
    _read_key,
    _unpack,
    _untext,
    _write_all,
)

# A hook writes its challenge as soon as it connects; anything slower is not one.
_HELLO_SECONDS = 0.25
_REQUEST_SECONDS = 2.0
_CLOSE_MILLISECONDS = 1000

# Windows API values.
_FILE_FLAG_OVERLAPPED = 0x40000000
_FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
_PIPE_ACCESS_DUPLEX = 0x00000003
_PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
_PIPE_UNLIMITED_INSTANCES = 255
_PIPE_BUFFER_BYTES = 65536
_ERROR_NO_DATA = 232
_WAIT_OBJECT_0 = 0


def serve(launcher: str, idle_seconds: float = _resident.IDLE_SECONDS) -> int:
    """Answer hook calls until idle for ``idle_seconds`` or out of date."""

    if not _resident._plan(launcher):
        return 1
    folder, identity = _Plan.folder, _Plan.identity
    os.makedirs(folder, exist_ok=True)
    starting = os.path.join(folder, identity + ".starting")
    # Taken before the judging code is loaded, so no change made while it loads is missed.
    watch = _Watch(launcher)
    try:
        import _winapi

        from jangseung.cli import entry
        import jangseung.cli.hook_run  # noqa: F401 - the whole judging path, loaded once

        watch.add_new_folders()
        security = _pipe_security()
        key = os.urandom(_KEY_BYTES)
        pipe = f"{_PIPE_PREFIX}{identity[:16]}-{os.urandom(8).hex()}"
        handle = _create_pipe(pipe, security, first=True)
        _write_key(folder, identity, pipe, key)
    except Exception as error:  # noqa: BLE001 - hook calls keep judging directly
        _note_failure(folder, identity, error)
        _remove(starting)
        return 1
    _remove(starting)
    _remove(os.path.join(folder, identity + ".failed"))
    # A working folder inside a project would keep that folder from being deleted or renamed.
    os.chdir(folder)
    try:
        while _accept(handle, idle_seconds):
            following = _create_pipe(pipe, security, first=False)
            try:
                keep = _answer_one(handle, key, identity, watch, entry)
            except Exception:  # noqa: BLE001 - that call is judged directly instead
                keep = True
            finally:
                _winapi.CloseHandle(handle)
                os.chdir(folder)
            handle = following
            if not keep:
                break
    finally:
        _winapi.CloseHandle(handle)
        _forget_key(folder, identity, pipe)
    return 0


def _pipe_security():
    """Security attributes letting only this user and SYSTEM open the pipe.

    The default would also let every user, and anonymous ones, open it for
    reading, enough to keep this process waiting on a connection.
    """

    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                             ctypes.POINTER(wintypes.DWORD)]
    advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))  # TokenUser
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]  # TOKEN_USER.User.Sid
        text = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            user = text.value
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.CloseHandle(token)

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]

    descriptor = ctypes.c_void_p()
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;;GA;;;SY)(A;;GA;;;{user})", 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    # Kept for the life of the process; CreateNamedPipe reads it on every new instance.
    return SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)


def _create_pipe(name: str, security, *, first: bool):
    import ctypes
    import _winapi

    open_mode = _PIPE_ACCESS_DUPLEX | _FILE_FLAG_OVERLAPPED | (_FILE_FLAG_FIRST_PIPE_INSTANCE if first else 0)
    # Byte mode, local clients only.
    return _winapi.CreateNamedPipe(name, open_mode, _PIPE_REJECT_REMOTE_CLIENTS, _PIPE_UNLIMITED_INSTANCES,
                                   _PIPE_BUFFER_BYTES, _PIPE_BUFFER_BYTES, 0, ctypes.addressof(security))


def _accept(handle, idle_seconds: float) -> bool:
    import _winapi

    try:
        overlapped = _winapi.ConnectNamedPipe(handle, overlapped=True)
    except OSError as error:
        if error.winerror == _ERROR_NO_DATA:  # a client came and already left
            return True
        raise
    if _winapi.WaitForSingleObject(overlapped.event, int(idle_seconds * 1000)) != _WAIT_OBJECT_0:
        overlapped.cancel()
        try:
            overlapped.GetOverlappedResult(True)
        except OSError:
            pass
        return False
    overlapped.GetOverlappedResult(True)
    return True


def _answer_one(handle, key: bytes, identity: str, watch, entry) -> bool:
    hello = _read_exact(handle, len(_MAGIC) + _CHALLENGE_BYTES, time.monotonic() + _HELLO_SECONDS)
    if hello[:4] != _MAGIC:
        return True
    _write_all(handle, _mac(key, _PROOF_LABEL + hello[4:]), time.monotonic() + _HELLO_SECONDS)
    deadline = time.monotonic() + _REQUEST_SECONDS
    size = int.from_bytes(_read_exact(handle, 4, deadline), "little")  # a proof-only check ends here
    if size > _MAX_MESSAGE_BYTES:
        return True
    body = _read_exact(handle, size, deadline)
    binding = _digest(body)
    kind, asked, argv, cwd, environment, data, *codecs = _unpack(body, 9)
    arguments = _untext(argv).split("\0")
    if kind != b"judge" or asked != identity.encode("ascii") or arguments[1:2] != ["hook-run"]:
        _send(handle, key, binding, _DECLINED, _pack(b"not answered here"))
        return True
    if watch.changed():
        _send(handle, key, binding, _DECLINED, _pack(b"code changed on disk"))
        return False
    if not _still_waiting(handle):
        return True  # the hook gave up and judges the call itself; judging here too would record it twice
    pairs = (item.split("=", 1) for item in _untext(environment).split("\0") if item)
    code, out, err = _judge(entry, arguments, _untext(cwd), dict(pair for pair in pairs if len(pair) == 2), data,
                            [_untext(codec).split("\0", 1) for codec in codecs])
    _send(handle, key, binding, _ANSWERED, _pack(str(code).encode("ascii"), out, err))
    watch.add_new_folders()
    return True


def _still_waiting(handle) -> bool:
    import _winapi

    try:
        _winapi.PeekNamedPipe(handle, 0)
    except OSError:
        return False
    return True


def _judge(entry, arguments, cwd, environment, data, codecs):
    import io
    import warnings

    (in_encoding, in_errors), (out_encoding, out_errors), (err_encoding, err_errors) = codecs
    _use_environment(environment)
    os.chdir(cwd)
    saved = sys.argv, sys.stdin, sys.stdout, sys.stderr
    limit = sys.getrecursionlimit()
    out_buffer, err_buffer = io.BytesIO(), io.BytesIO()
    try:
        sys.argv = arguments
        sys.stdin = io.TextIOWrapper(io.BytesIO(data), encoding=in_encoding, errors=in_errors)
        sys.stdout = io.TextIOWrapper(out_buffer, encoding=out_encoding, errors=out_errors)
        sys.stderr = io.TextIOWrapper(err_buffer, encoding=err_encoding, errors=err_errors)
        # In a hook process main() is called from run(), two frames deep (the launcher, run);
        # here it is called deeper. The same headroom keeps deep input judged the same.
        sys.setrecursionlimit(limit + _depth() - 2)
        # A new process would show each warning again; resetting the registry per call does the same.
        with warnings.catch_warnings():
            try:
                code = entry.main(arguments[1:])
            except SystemExit as stop:
                code = _exit_status(stop.code)
        sys.stdout.flush()
        sys.stderr.flush()
        return code, out_buffer.getvalue(), err_buffer.getvalue()
    finally:
        sys.setrecursionlimit(limit)
        sys.argv, sys.stdin, sys.stdout, sys.stderr = saved


def _depth() -> int:
    """How many frames are below the caller's own, counting the caller."""

    frame = sys._getframe(1)
    depth = 0
    while frame is not None:
        depth += 1
        frame = frame.f_back
    return depth


def _use_environment(environment: dict) -> None:
    """Make ``os.environ`` exactly the calling process's, changing only what differs."""

    current = os.environ
    if dict(current) == environment:
        return
    for name in [name for name in current if name not in environment]:
        del current[name]
    for name, value in environment.items():
        if current.get(name) != value:
            current[name] = value


def _exit_status(code) -> int:
    """The exit status Python gives ``SystemExit(code)``, printing a non-number as it does."""

    if code is None:
        return 0
    if isinstance(code, int):
        return code
    try:
        sys.stderr.write(f"{code}\n")
    except Exception:  # noqa: BLE001
        pass
    return 1


def _send(handle, key: bytes, binding: bytes, status: int, body: bytes) -> None:
    import _winapi

    flag = bytes((status,))
    message = _MAGIC + flag + len(body).to_bytes(4, "little") + body + _mac(key, binding + flag + body)
    _write_all(handle, message, time.monotonic() + _ANSWER_SECONDS)
    # Wait until the hook has read the answer and closed its end.
    try:
        overlapped, _ = _winapi.ReadFile(handle, 1, overlapped=True)
    except OSError:
        return
    if _winapi.WaitForSingleObject(overlapped.event, _CLOSE_MILLISECONDS) != _WAIT_OBJECT_0:
        overlapped.cancel()
    try:
        overlapped.GetOverlappedResult(True)
    except OSError:
        pass


class _Watch:
    """The folders the running code came from, as they were on disk."""

    def __init__(self, launcher: str) -> None:
        self.folders: dict = {}
        self.modules = -1
        places = {os.path.dirname(sys.executable), os.path.dirname(os.path.abspath(launcher))}
        package = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the folder holding jangseung
        for root, folders, _ in os.walk(os.path.join(package, "jangseung")):
            folders[:] = [name for name in folders if name != "__pycache__"]
            places.add(root)
        self._add(places)
        self.add_new_folders()

    def changed(self) -> bool:
        return any(_look(place) != seen for place, seen in self.folders.items())

    def add_new_folders(self) -> None:
        if len(sys.modules) == self.modules:
            return
        self.modules = len(sys.modules)
        places = set()
        for module in list(sys.modules.values()):
            location = getattr(module, "__file__", None)
            if isinstance(location, str) and os.path.isabs(location):
                places.add(os.path.dirname(location))
        places.update(entry for entry in sys.path if isinstance(entry, str) and os.path.isabs(entry))
        self._add(places)

    def _add(self, places) -> None:
        for place in places:
            if place not in self.folders:
                self.folders[place] = _look(place)


def _look(place: str):
    """What in ``place`` decides which code an import finds.

    Every file with its modification time and size, and every folder whose name
    could be a package, with its modification time: a new package folder can stand
    in for a module of the same name. ``__pycache__`` is left out.
    """

    try:
        with os.scandir(place) as entries:
            seen = set()
            for entry in entries:
                if entry.is_dir():
                    if entry.name.isidentifier() and entry.name != "__pycache__":
                        seen.add((entry.name, entry.stat().st_mtime_ns, -1))
                else:
                    info = entry.stat()
                    seen.add((entry.name, info.st_mtime_ns, info.st_size))
            return frozenset(seen)
    except NotADirectoryError:
        try:
            info = os.stat(place)
        except OSError:
            return None
        return (info.st_mtime_ns, info.st_size)
    except OSError:
        return None


def _write_key(folder: str, identity: str, pipe: str, key: bytes) -> None:
    path = os.path.join(folder, identity + ".key")
    temporary = f"{path}.{os.getpid()}.tmp"
    with open(temporary, "wb") as stream:
        stream.write(f"{pipe}\n{key.hex()}\n{os.getpid()}\n".encode("ascii"))
    for _ in range(50):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:  # a hook call is reading it
            time.sleep(0.02)
    os.replace(temporary, path)


def _forget_key(folder: str, identity: str, pipe: str) -> None:
    path = os.path.join(folder, identity + ".key")
    found = _read_key(path)
    if found is not None and found[0] == pipe:
        _remove(path)


def _note_failure(folder: str, identity: str, error: BaseException) -> None:
    try:
        with open(os.path.join(folder, identity + ".failed"), "w", encoding="utf-8") as stream:
            stream.write(f"{type(error).__name__}: {error}\n")
    except OSError:
        pass


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
