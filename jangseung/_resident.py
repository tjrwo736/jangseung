r"""Keep the hook's judging code loaded between tool calls (Windows only).

On Windows a hook process takes about 48 ms, and the judgment itself about
5 ms: the rest is starting Python and loading modules, paid again on every tool
call. This keeps one process per launcher with that code loaded. A hook call
reads its input, hands it to that process over a named pipe, and writes the
answer it gets back. It is the same judge kept awake, under these rules:

* Same code and start. The process is started through the same launcher, with
  the same Python and the same interpreter options as the hook command, and
  judges with :func:`jangseung.cli.entry.main`.
* Same inputs. Each call is judged with its own arguments, working folder,
  environment variables and input bytes, and written out with its own stream
  encodings. Nothing one judgment leaves behind is read by the next.
* Same files. Before every answer the process compares the folders its code was
  loaded from, and those on ``sys.path``, with the disk. Any change makes it
  decline, stop, and leave the call to be judged directly.
* Fail-closed. When the process is missing, slow, declines, or its answer does
  not carry the right MAC, the hook judges the call itself, exactly as before.
* Recorded. The judgment writes its ledger record before the answer is sent.
* Local and private. The pipe takes no remote clients, and only its creator
  (and administrators) may write to it. The key that signs every answer is kept
  in ``%LOCALAPPDATA%\jangseung\resident``, in the user's own profile.

Only ``hook-run`` started by ``jangseung/_hook.py`` or the ``aeg`` launcher on
Windows uses it. ``JANGSEUNG_RESIDENT=off`` in the hook's environment turns it
off. The process stops after 15 minutes without a call. The session-start check
starts it, so the first tool call of a session is already fast.
"""

import os
import sys
import time

SERVE_COMMAND = "resident-serve"
OFF_VARIABLE = "JANGSEUNG_RESIDENT"
# The same limit as jangseung.cli.hook_run.MAX_STDIN_BYTES; a test keeps them equal.
MAX_STDIN_BYTES = 16 * 1024 * 1024
IDLE_SECONDS = 15 * 60

_MAGIC = b"JSR2"
_PIPE_PREFIX = "\\\\.\\pipe\\jangseung-"
_HEX = frozenset("0123456789abcdef")
_KEY_BYTES = 32
_MAC_BYTES = 32
_CHALLENGE_BYTES = 16
_PROOF_LABEL = b"jangseung resident proof\0"
_MAX_MESSAGE_BYTES = 64 * 1024 * 1024
# A live resident process proves itself within milliseconds; one that does not is
# treated as gone. A judgment waits at most 1 s for the ledger lock.
_PROOF_SECONDS = 1.0
_ANSWER_SECONDS = 10.0
_SPAWN_GRACE_SECONDS = 15.0
_FAILURE_PAUSE_SECONDS = 600.0
_ANSWERED = 0
_DECLINED = 1
_OFF_VALUES = ("0", "off", "false", "no")

# Windows API values.
_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_FILE_FLAG_OVERLAPPED = 0x40000000
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_ERROR_PIPE_BUSY = 231
_WAIT_OBJECT_0 = 0
_STILL_ACTIVE = 259

_INNER_PAD = bytes(value ^ 0x36 for value in range(256))
_OUTER_PAD = bytes(value ^ 0x5C for value in range(256))


class _Plan:
    """What this process knows about its resident process."""

    launcher = None
    options: tuple = ()
    identity = None
    folder = None
    start_server = False


# --- the hook side (the resident process itself is in jangseung._resident_server)


def ask(launcher: str):
    """Have the resident process judge this ``hook-run`` call.

    Returns ``(exit code, stdout bytes, stderr bytes)``, or ``None`` when this
    process must judge the call itself; ``sys.stdin`` then holds the same input.
    """

    if not _plan(launcher):
        return None
    streams = (sys.stdin, sys.stdout, sys.stderr)
    if any(stream is None or getattr(stream, "buffer", None) is None for stream in streams):
        return None
    codecs = [_text(f"{stream.encoding}\0{stream.errors}") for stream in streams]
    original = sys.stdin
    # The hook takes at most this much input too, so a call judged here sees the same bytes.
    data = read_at_most(original.buffer, MAX_STDIN_BYTES + 1)
    try:
        answer = _ask(data, codecs)
    except Exception:  # noqa: BLE001 - judged here instead
        answer = None
    if answer is None:
        import io

        sys.stdin = io.TextIOWrapper(io.BytesIO(data), encoding=original.encoding, errors=original.errors)
    return answer


def _ask(data: bytes, codecs: list):
    found = _read_key(_key_path())
    if found is None:
        _Plan.start_server = True
        return None
    pipe, key, _ = found
    environment = "\0".join(f"{name}={value}" for name, value in os.environ.items())
    body = _pack(b"judge", _Plan.identity.encode("ascii"), _text("\0".join(sys.argv)), _text(os.getcwd()),
                 _text(environment), data, *codecs)
    try:
        status, answer = _exchange(pipe, key, body)
    except _Unproven:
        # Gone, hung, or not the process that holds the key: nothing was sent to it.
        _Plan.start_server = True
        return None
    except (OSError, EOFError, ValueError):  # it proved itself but did not answer in time
        return None
    if status != _ANSWERED:
        _Plan.start_server = True  # its code changed on disk; a new one is needed
        return None
    code, out, err = _unpack(answer, 3)
    return int(code), out, err


def read_at_most(buffer, size: int) -> bytes:
    """The same reading as :func:`jangseung.cli.hook_run.read_at_most`; a test keeps them equal."""

    read = getattr(buffer, "read1", None) or buffer.read
    parts = []
    total = 0
    while total < size:
        part = read(min(65536, size - total))
        if not part:
            break
        parts.append(part)
        total += len(part)
    return b"".join(parts)


def plan_session(launcher: str) -> None:
    """At session start, plan to start the resident process if none is running."""

    if not _plan(launcher):
        return
    found = _read_key(_key_path())
    if found is None:
        _Plan.start_server = True
        return
    try:
        _exchange(found[0], found[1], None)  # only asks it to prove itself
    except _Unproven:
        _Plan.start_server = True
    except Exception:  # noqa: BLE001 - it proved itself; nothing more to do
        pass


def start_if_needed() -> None:
    """Start the resident process when this call found none. Runs after the answer is out."""

    if not _Plan.start_server:
        return
    _Plan.start_server = False
    folder, identity = _Plan.folder, _Plan.identity
    os.makedirs(folder, exist_ok=True)
    try:
        if time.time() - os.stat(os.path.join(folder, identity + ".failed")).st_mtime < _FAILURE_PAUSE_SECONDS:
            return
    except OSError:
        pass
    if not _claim(os.path.join(folder, identity + ".starting")):
        return
    import _winapi

    command = _command_line([sys.executable, *_Plan.options, _Plan.launcher, SERVE_COMMAND])
    # No handle is inherited, so the new process cannot keep this hook's output pipe open.
    process, thread, _, _ = _winapi.CreateProcess(
        None, command, None, None, False, _DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP, None, folder, _StartupInfo()
    )
    _winapi.CloseHandle(thread)
    _winapi.CloseHandle(process)


def _plan(launcher) -> bool:
    if _Plan.identity is not None:
        return True
    if sys.platform != "win32" or not launcher:
        return False
    if os.environ.get(OFF_VARIABLE, "").strip().lower() in _OFF_VALUES:
        return False
    options = _interpreter_options()
    base = os.environ.get("LOCALAPPDATA", "")
    if options is None or not os.path.isabs(base):
        return False
    _Plan.launcher = launcher
    _Plan.options = options
    _Plan.identity = _identity(launcher, options)
    _Plan.folder = os.path.join(base, "jangseung", "resident")
    return True


def _interpreter_options():
    """The options this Python was started with, between the program and the launcher."""

    original = getattr(sys, "orig_argv", None)
    if not original or not sys.argv or len(original) <= len(sys.argv):
        return None
    start = len(original) - len(sys.argv)
    if original[start:] != sys.argv:
        return None
    return tuple(original[1:start])


def _identity(launcher: str, options: tuple) -> str:
    text = "\0".join((sys.executable, *options, launcher, sys.version))
    return _sha256()(_text(text)).hexdigest()[:32]


def _key_path() -> str:
    return os.path.join(_Plan.folder, _Plan.identity + ".key")


def _read_key(path: str):
    try:
        with open(path, "rb") as stream:
            lines = stream.read(512).split(b"\n")
        pipe = lines[0].decode("ascii")
        key = bytes.fromhex(lines[1].decode("ascii"))
        pid = int(lines[2])
    except (OSError, IndexError, ValueError):
        return None
    if not valid_pipe_name(pipe) or len(key) != _KEY_BYTES:
        return None
    return pipe, key, pid


def valid_pipe_name(pipe: str) -> bool:
    """Exactly ``\\\\.\\pipe\\jangseung-<16 hex>-<16 hex>``; nothing that could name a file."""

    tail = pipe[len(_PIPE_PREFIX):] if pipe.startswith(_PIPE_PREFIX) else ""
    first, dash, second = tail.partition("-")
    return dash == "-" and len(first) == len(second) == 16 and set(first + second) <= _HEX


class _Unproven(OSError):
    """The pipe's server is gone, hung, or does not hold the key; nothing was sent to it."""


def _exchange(pipe: str, key: bytes, body):
    """Make the server prove it holds ``key``, then send ``body`` and return its signed answer.

    With ``body`` None, only the proof is asked for.
    """

    import _winapi

    proof_deadline = time.monotonic() + _PROOF_SECONDS
    try:
        handle = _connect(pipe, proof_deadline)
    except OSError as error:
        raise _Unproven(str(error)) from error
    try:
        challenge = _digest(f"{os.getpid()} {time.perf_counter_ns()} {time.time_ns()}".encode("ascii"))[:_CHALLENGE_BYTES]
        try:
            _write_all(handle, _MAGIC + challenge, proof_deadline)
            proof = _read_exact(handle, _MAC_BYTES, proof_deadline)
        except (OSError, EOFError) as error:
            raise _Unproven(str(error)) from error
        if not _same(proof, _mac(key, _PROOF_LABEL + challenge)):
            raise _Unproven("the pipe's server does not hold the key")
        if body is None:
            return None
        deadline = time.monotonic() + _ANSWER_SECONDS
        _write_all(handle, len(body).to_bytes(4, "little") + body, deadline)
        head = _read_exact(handle, 9, deadline)
        if head[:4] != _MAGIC:
            raise ValueError("not an answer from a resident process")
        size = int.from_bytes(head[5:9], "little")
        if size > _MAX_MESSAGE_BYTES:
            raise ValueError("answer too large")
        answer = _read_exact(handle, size, deadline)
        mac = _read_exact(handle, _MAC_BYTES, deadline)
    finally:
        _winapi.CloseHandle(handle)
    # The MAC covers this very request, so an answer to another call cannot be passed off as this one's.
    if not _same(mac, _mac(key, _digest(body) + head[4:5] + answer)):
        raise ValueError("the answer is not signed with this key")
    return head[4], answer


def _connect(pipe: str, deadline: float):
    import _winapi

    while True:
        try:
            return _winapi.CreateFile(pipe, _GENERIC_READ | _GENERIC_WRITE, 0, _winapi.NULL, _OPEN_EXISTING,
                                      _FILE_FLAG_OVERLAPPED, _winapi.NULL)
        except OSError as error:
            if error.winerror != _ERROR_PIPE_BUSY:
                raise
        left = _left_milliseconds(deadline)
        if left <= 0:
            raise TimeoutError("the resident process stayed busy")
        try:
            _winapi.WaitNamedPipe(pipe, min(left, 1000))
        except OSError:
            pass


def _alive(pid: int) -> bool:
    """Whether a process with this number is running (tests use it; a number can be reused)."""

    import _winapi

    try:
        handle = _winapi.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    except OSError:
        return False
    try:
        return _winapi.GetExitCodeProcess(handle) == _STILL_ACTIVE
    finally:
        _winapi.CloseHandle(handle)


def _claim(path: str) -> bool:
    """Only one hook call at a time starts a resident process."""

    for _ in range(2):
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return True
        except FileExistsError:
            try:
                if time.time() - os.stat(path).st_mtime < _SPAWN_GRACE_SECONDS:
                    return False
                os.remove(path)
            except OSError:
                return False
        except OSError:
            return False
    return False


class _StartupInfo:
    dwFlags = 0
    wShowWindow = 0
    hStdInput = None
    hStdOutput = None
    hStdError = None
    lpAttributeList = None


def _command_line(arguments: list) -> str:
    """Quote arguments as the Microsoft C runtime reads them (``subprocess.list2cmdline``)."""

    result: list = []
    for argument in arguments:
        backslashes: list = []
        if result:
            result.append(" ")
        quote = (" " in argument) or ("\t" in argument) or not argument
        if quote:
            result.append('"')
        for character in argument:
            if character == "\\":
                backslashes.append(character)
            elif character == '"':
                result.append("\\" * len(backslashes) * 2)
                backslashes = []
                result.append('\\"')
            else:
                if backslashes:
                    result.extend(backslashes)
                    backslashes = []
                result.append(character)
        if backslashes:
            result.extend(backslashes)
        if quote:
            result.extend(backslashes)
            result.append('"')
    return "".join(result)


# --- shared


def _write_all(handle, data: bytes, deadline: float) -> None:
    import _winapi

    while data:
        overlapped, _ = _winapi.WriteFile(handle, data, overlapped=True)
        written, _ = _finish(overlapped, deadline)
        if not written:
            raise OSError("the pipe took no data")
        data = data[written:]


def _read_exact(handle, size: int, deadline: float) -> bytes:
    import _winapi

    parts = []
    while size:
        overlapped, _ = _winapi.ReadFile(handle, size, overlapped=True)
        _finish(overlapped, deadline)
        chunk = overlapped.getbuffer()
        if not chunk:
            raise EOFError("the pipe closed early")
        parts.append(bytes(chunk))
        size -= len(chunk)
    return b"".join(parts)


def _finish(overlapped, deadline: float):
    import _winapi

    if _winapi.WaitForSingleObject(overlapped.event, _left_milliseconds(deadline)) != _WAIT_OBJECT_0:
        overlapped.cancel()
        try:
            overlapped.GetOverlappedResult(True)
        except OSError:
            pass
        raise TimeoutError("the resident process did not answer in time")
    return overlapped.GetOverlappedResult(True)


def _left_milliseconds(deadline: float) -> int:
    return max(0, int((deadline - time.monotonic()) * 1000))


def _pack(*fields: bytes) -> bytes:
    return b"".join(len(field).to_bytes(4, "little") + field for field in fields)


def _unpack(data: bytes, count: int) -> list:
    fields, position = [], 0
    for _ in range(count):
        start = position + 4
        if start > len(data):
            raise ValueError("short message")
        position = start + int.from_bytes(data[position:start], "little")
        if position > len(data):
            raise ValueError("short message")
        fields.append(data[start:position])
    if position != len(data):
        raise ValueError("trailing data")
    return fields


def _text(value: str) -> bytes:
    return value.encode("utf-8", "surrogatepass")


def _untext(value: bytes) -> str:
    return value.decode("utf-8", "surrogatepass")


def _mac(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA256 (RFC 2104) from the built-in SHA-256, without loading OpenSSL."""

    sha256 = _sha256()
    block = key.ljust(64, b"\0")
    inner = sha256(block.translate(_INNER_PAD) + data).digest()
    return sha256(block.translate(_OUTER_PAD) + inner).digest()


def _digest(data: bytes) -> bytes:
    return _sha256()(data).digest()


def _sha256():
    """SHA-256 built into CPython: ``_sha2`` from 3.12, ``_sha256`` in 3.10 and 3.11."""

    try:
        from _sha2 import sha256
    except ImportError:
        from _sha256 import sha256
    return sha256


def _same(left: bytes, right: bytes) -> bool:
    """Compare in time that does not depend on where the bytes differ."""

    if len(left) != len(right):
        return False
    difference = 0
    for one, other in zip(left, right):
        difference |= one ^ other
    return difference == 0
