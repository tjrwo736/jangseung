"""0.3.1, fourth part: the resident judging process (``jangseung._resident``).

The same judge kept awake. An answer from the resident process must be, byte
for byte, the answer the hook gives when it judges the call itself; whenever the
resident process cannot be trusted or cannot answer, the hook judges itself.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hmac
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

import pytest

from jangseung import _resident
from jangseung.cli import hook_run

REPO_ROOT = Path(__file__).resolve().parents[1]
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the resident process runs on Windows only")


# --- pieces that run on every system


def test_the_input_limit_and_reader_match_the_hook():
    assert _resident.MAX_STDIN_BYTES == hook_run.MAX_STDIN_BYTES
    for size in (0, 1, 65535, 65536, 65537, 200_000):
        data = (bytes(range(256)) * (size // 256 + 1))[:size]
        for limit in (10, 65536, 100_001, 300_000):
            one, two = io.BytesIO(data), io.BytesIO(data)
            assert _resident.read_at_most(one, limit) == hook_run.read_at_most(two, limit) == data[:limit]
            # No more input is taken than one read(limit) took.
            assert one.tell() == two.tell() == min(size, limit)


def test_the_answer_signature_is_hmac_sha256():
    key = bytes(range(32))
    for data in (b"", b"x", b"y" * 1000):
        assert _resident._mac(key, data) == hmac.new(key, data, "sha256").digest()


def test_signing_works_where_sha256_is_built_in_under_its_older_name(monkeypatch):
    # CPython 3.10 and 3.11 name the built-in module _sha256; 3.12 and later, _sha2.
    import types

    from jangseung._sha256 import sha256

    older = types.ModuleType("_sha256")
    older.sha256 = sha256
    monkeypatch.setitem(sys.modules, "_sha2", None)
    monkeypatch.setitem(sys.modules, "_sha256", older)
    key = bytes(range(32))
    assert _resident._mac(key, b"call") == hmac.new(key, b"call", "sha256").digest()
    assert len(_resident._identity("launcher", ("-I", "-S"))) == 32


def test_messages_round_trip_and_damage_is_refused():
    fields = [b"", b"a", b"\x00" * 70000]
    packed = _resident._pack(*fields)
    assert _resident._unpack(packed, 3) == fields
    for damaged in (packed[:-1], packed + b"x", packed[:3]):
        with pytest.raises(ValueError):
            _resident._unpack(damaged, 3)


def test_the_command_line_is_quoted_as_subprocess_quotes_it():
    for arguments in (
        [r"C:\Program Files\Python\python.exe", "-I", "-S", r"C:\a b\jangseung\_hook.py", "resident-serve"],
        ["x", "", 'a"b', "c\\\\", "tab\there"],
    ):
        assert _resident._command_line(arguments) == subprocess.list2cmdline(arguments)


def test_signatures_are_compared_whole():
    assert _resident._same(b"abc", b"abc")
    assert not _resident._same(b"abc", b"abd")
    assert not _resident._same(b"abc", b"ab")


def test_the_off_switch_and_other_systems_never_use_it(monkeypatch):
    monkeypatch.setattr(_resident._Plan, "identity", None)
    monkeypatch.setenv("JANGSEUNG_RESIDENT", "off")
    assert _resident._plan("launcher") is False
    monkeypatch.setenv("JANGSEUNG_RESIDENT", "")
    monkeypatch.setattr(_resident.sys, "platform", "linux")
    assert _resident._plan("launcher") is False
    assert _resident._plan(None) is False


def test_a_system_exit_gives_the_status_python_gives(capsys):
    from jangseung import _resident_server as server

    assert server._exit_status(None) == 0
    assert server._exit_status(3) == 3
    assert server._exit_status(True) == 1
    assert server._exit_status("stopped") == 1
    assert capsys.readouterr().err == "stopped\n"
    done = subprocess.run([sys.executable, "-c", "raise SystemExit('stopped')"], capture_output=True, text=True)
    assert (done.returncode, done.stderr) == (1, "stopped\n")


def test_the_environment_becomes_exactly_the_callers(monkeypatch):
    from jangseung import _resident_server as server

    monkeypatch.setenv("JANGSEUNG_TEST_GONE", "1")
    wanted = {name: value for name, value in os.environ.items() if name != "JANGSEUNG_TEST_GONE"}
    wanted["JANGSEUNG_TEST_NEW"] = "2"
    saved = dict(os.environ)
    try:
        server._use_environment(wanted)
        assert dict(os.environ) == wanted
    finally:
        server._use_environment(saved)


# --- the resident process on Windows


def _payload(tool: str, tool_input: dict, project: Path, *, mode: str = "default", use_id: str = "t") -> bytes:
    return json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": use_id, "cwd": str(project),
                       "permission_mode": mode, "hook_event_name": "PreToolUse", "session_id": "s"}).encode("utf-8")


def _terminate(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def _alive(pid: int) -> bool:
    return _resident._alive(pid)


class _Setup:
    """A private copy of the package, a project, and a private LOCALAPPDATA."""

    def __init__(self, tmp_path: Path) -> None:
        self.home = tmp_path / "home"
        shutil.copytree(REPO_ROOT / "jangseung", self.home / "jangseung", ignore=shutil.ignore_patterns("__pycache__"))
        self.launcher = str(self.home / "jangseung" / "_hook.py")
        self.project = tmp_path / "프로젝트 folder"
        (self.project / ".aeg").mkdir(parents=True)
        (self.project / "sub").mkdir()
        (self.project / "a.txt").write_text("x\n", encoding="utf-8")
        (self.project / "한글.txt").write_text("x\n", encoding="utf-8")
        (self.project / ".env").write_text("K=1\n", encoding="utf-8")
        (self.project / "CLAUDE.md").write_text("a\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.project)], check=True, capture_output=True)
        self.local = tmp_path / "local"
        self.local.mkdir()
        self.folder = self.local / "jangseung" / "resident"

    def env(self, **extra: str) -> dict:
        env = {name: value for name, value in os.environ.items() if name != "JANGSEUNG_RESIDENT"}
        env.update(CLAUDE_PROJECT_DIR=str(self.project), LOCALAPPDATA=str(self.local))
        env.update(extra)
        return env

    def call(self, payload: bytes, *, resident: bool = True, cwd: Path | None = None,
             arguments: tuple = ("hook-run",), **extra: str) -> tuple:
        env = self.env(**extra)
        if not resident:
            env["JANGSEUNG_RESIDENT"] = "off"
        done = subprocess.run([sys.executable, "-I", "-S", self.launcher, *arguments], input=payload,
                              capture_output=True, cwd=cwd or self.project, env=env, timeout=120)
        return done.returncode, done.stdout, done.stderr

    def key(self) -> Path | None:
        keys = sorted(self.folder.glob("*.key")) if self.folder.is_dir() else []
        return keys[0] if keys else None

    def ready(self, *, not_pid: int | None = None, timeout: float = 30.0) -> int:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            key = self.key()
            if key is not None:
                try:
                    pid = int(key.read_text(encoding="ascii").splitlines()[2])
                except (OSError, ValueError, IndexError):
                    pid = None
                if pid is not None and pid != not_pid:
                    return pid
            time.sleep(0.05)
        found = sorted(path.name for path in self.folder.glob("*")) if self.folder.is_dir() else "no folder"
        raise AssertionError(f"no resident process came up: {found}")

    def ask(self, payload: bytes, *, argv: tuple = ("hook-run",)):
        """Ask the resident process directly, as a hook call would; None means it did not answer."""

        script = (
            "import io, json, sys\n"
            "home, launcher, argv = sys.argv[1], sys.argv[2], sys.argv[3:]\n"
            "sys.path.insert(0, home)\n"
            "from jangseung import _resident\n"
            "_resident._interpreter_options = lambda: ('-I', '-S')\n"
            "sys.argv = [launcher, *argv]\n"
            "answer = _resident.ask(launcher)\n"
            "print(json.dumps(None if answer is None else [answer[0], answer[1].hex(), answer[2].hex()]))\n"
        )
        done = subprocess.run([sys.executable, "-I", "-S", "-c", script, str(self.home), self.launcher, *argv],
                              input=payload, capture_output=True, cwd=self.project, env=self.env(), timeout=120)
        assert done.returncode == 0, done.stderr
        answer = json.loads(done.stdout)
        return None if answer is None else (answer[0], bytes.fromhex(answer[1]), bytes.fromhex(answer[2]))

    def stop(self) -> None:
        for key in sorted(self.folder.glob("*.key")) if self.folder.is_dir() else []:
            try:
                pid = int(key.read_text(encoding="ascii").splitlines()[2])
            except (OSError, ValueError, IndexError):
                continue
            if pid != os.getpid():
                _terminate(pid)


@pytest.fixture
def setup(tmp_path):
    state = _Setup(tmp_path)
    yield state
    state.stop()


@windows_only
def test_a_hook_call_starts_the_resident_process_and_it_answers_the_next(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    first = setup.call(payload)  # judged here, then the resident process is started
    pid = setup.ready()
    answered = setup.ask(payload)
    assert answered is not None
    direct = setup.call(payload, resident=False)
    assert answered == direct == first
    assert setup.call(payload) == direct
    assert _alive(pid)


CASES = [
    ("Bash", {"command": "ls -la"}),
    ("Bash", {"command": "cat .env"}),
    ("Bash", {"command": "git status && git diff"}),
    ("Bash", {"command": "npm test"}),
    ("Bash", {"command": "rm -rf /"}),
    ("Bash", {"command": "cd sub && ls"}),
    ("Read", {"file_path": "a.txt"}),
    ("Read", {"file_path": "한글.txt"}),
    ("Read", {"file_path": ".env"}),
    ("Edit", {"file_path": "CLAUDE.md", "old_string": "a", "new_string": "b"}),
    ("Write", {"file_path": "pyproject.toml", "content": "x"}),
    ("Write", {"file_path": "big.txt", "content": "x" * 300_000}),
    ("PowerShell", {"command": "Get-Content .env"}),
]


@windows_only
def test_answers_are_byte_for_byte_those_of_judging_directly(setup):
    setup.call(_payload("Bash", {"command": "ls"}, setup.project))
    pid = setup.ready()
    checked = 0
    for mode in ("default", "acceptEdits", "plan"):
        for number, (tool, tool_input) in enumerate(CASES):
            payload = _payload(tool, tool_input, setup.project, mode=mode, use_id=f"{mode}-{number}")
            assert setup.call(payload) == setup.call(payload, resident=False), (mode, tool, tool_input)
            checked += 1
    extra = [
        (b"", {}, None, ("hook-run",)),
        (b"not json", {}, None, ("hook-run",)),
        (b"\xef\xbb\xbf" + _payload("Read", {"file_path": "a.txt"}, setup.project), {}, None, ("hook-run",)),
        (_payload("Bash", {"command": "cd sub && ls"}, setup.project), {"CDPATH": "x"}, None, ("hook-run",)),
        (_payload("Bash", {"command": "ls"}, setup.project), {}, setup.project / "sub", ("hook-run",)),
        (_payload("Bash", {"command": "ls"}, setup.project), {}, None, ("hook-run", "--ensure-state")),
        (_payload("Bash", {"command": "cat .env"}, setup.project), {}, None, ("hook-run", "--substrate", "codex")),
        (_payload("Bash", {"command": "ls"}, setup.project), {}, None, ("hook-run", "--bogus")),
    ]
    for payload, variables, cwd, arguments in extra:
        served = setup.call(payload, cwd=cwd, arguments=arguments, **variables)
        direct = setup.call(payload, resident=False, cwd=cwd, arguments=arguments, **variables)
        assert served == direct, (payload[:60], variables, cwd, arguments)
        checked += 1
    # The process that answered is the one that started; it never declined or restarted.
    assert setup.ready() == pid and _alive(pid)
    assert setup.ask(_payload("Bash", {"command": "ls"}, setup.project)) is not None
    assert checked == 3 * len(CASES) + 8


@windows_only
def test_changed_code_on_disk_is_never_answered_with(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload)
    pid = setup.ready()
    assert setup.ask(payload) is not None
    clock = setup.home / "jangseung" / "_clock.py"
    clock.write_text(clock.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    assert setup.ask(payload) is None  # declined; the call is judged directly
    deadline = time.monotonic() + 30
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)
    assert setup.call(payload) == setup.call(payload, resident=False)
    assert setup.ready(not_pid=pid) != pid  # a new process, with the new code


def _fake_pipe_name() -> str:
    return f"{_resident._PIPE_PREFIX}{os.urandom(8).hex()}-{os.urandom(8).hex()}"


def _write_key(setup, pipe: str, pid: int) -> Path:
    identity = _resident._identity(setup.launcher, ("-I", "-S"))
    setup.folder.mkdir(parents=True, exist_ok=True)
    key = setup.folder / f"{identity}.key"
    # Bytes, not text: on Windows write_text would end each line with \r\n.
    key.write_bytes(f"{pipe}\n{os.urandom(32).hex()}\n{pid}\n".encode("ascii"))
    return key


@windows_only
def test_a_pipe_without_the_key_gets_nothing_and_is_replaced(setup):
    # Another process holds the pipe the key file names (say, after the resident one crashed).
    # It cannot prove it holds the key, so the hook sends it nothing, judges itself, and
    # starts a new resident process.
    from jangseung import _resident_server as server
    import _winapi

    pipe = _fake_pipe_name()
    key = _write_key(setup, pipe, os.getpid())
    handle = server._create_pipe(pipe, server._pipe_security(), first=True)
    seen: list = []

    def squat() -> None:
        if not server._accept(handle, 30):
            return
        seen.append(_resident._read_exact(handle, 20, time.monotonic() + 10))  # the challenge
        _resident._write_all(handle, os.urandom(32), time.monotonic() + 10)  # a proof without the key
        try:
            seen.append(_resident._read_exact(handle, 1, time.monotonic() + 10))
        except (OSError, EOFError):
            pass

    thread = threading.Thread(target=squat)
    thread.start()
    payload = _payload("Bash", {"command": "cat .env"}, setup.project)
    try:
        squatted = setup.call(payload)
    finally:
        thread.join(30)
        _winapi.CloseHandle(handle)
    assert len(seen) == 1 and seen[0][:4] == _resident._MAGIC  # only the challenge; not one byte of the call
    direct = setup.call(payload, resident=False)
    assert squatted == direct and b'"permissionDecision":"deny"' in direct[1]
    assert setup.ready(not_pid=os.getpid()) != os.getpid()  # a new resident process replaced the key file
    assert key.read_bytes().split(b"\n")[0].decode() != pipe


@windows_only
def test_a_session_start_replaces_a_key_whose_process_number_was_reused(setup):
    # The key names a pipe nobody serves and the number of a live, unrelated process.
    _write_key(setup, _fake_pipe_name(), os.getpid())
    start = json.dumps({"hook_event_name": "SessionStart", "session_id": "s", "cwd": str(setup.project),
                        "source": "startup"}).encode()
    assert setup.call(start, arguments=("session-check",))[0] == 0
    pid = setup.ready(not_pid=os.getpid())
    assert _alive(pid) and setup.ask(_payload("Bash", {"command": "ls"}, setup.project)) is not None


@windows_only
def test_a_hung_resident_process_costs_one_second_and_is_replaced(setup):
    import ctypes

    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload)
    pid = setup.ready()
    ntdll = ctypes.WinDLL("ntdll")
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.OpenProcess.restype = ctypes.c_void_p
    process = kernel32.OpenProcess(0x0800, False, pid)  # PROCESS_SUSPEND_RESUME
    assert process
    ntdll.NtSuspendProcess(ctypes.c_void_p(process))
    try:
        started = time.monotonic()
        hung = setup.call(payload)
        took = time.monotonic() - started
    finally:
        ntdll.NtResumeProcess(ctypes.c_void_p(process))
        kernel32.CloseHandle(ctypes.c_void_p(process))
    assert hung == setup.call(payload, resident=False)
    assert took < 5, took
    assert setup.ready(not_pid=pid) != pid
    _terminate(pid)


@windows_only
def test_a_new_package_folder_that_could_shadow_a_module_stops_it(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload)
    pid = setup.ready()
    assert setup.ask(payload) is not None
    (setup.home / "jangseung" / "cli" / "newly_added").mkdir()
    assert setup.ask(payload) is None
    deadline = time.monotonic() + 30
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)


@windows_only
def test_deeply_nested_input_is_judged_the_same(setup):
    setup.call(_payload("Bash", {"command": "ls"}, setup.project))
    setup.ready()
    for depth in (450, 480, 490, 492, 493, 495, 500, 520, 600):
        nested: list = []
        for _ in range(depth):
            nested = [nested]
        payload = _payload("Bash", {"command": "ls", "extra": nested}, setup.project, use_id=f"d{depth}")
        assert setup.call(payload) == setup.call(payload, resident=False), depth


def test_only_well_formed_pipe_names_are_used():
    good = f"{_resident._PIPE_PREFIX}{'a' * 16}-{'0' * 16}"
    assert _resident.valid_pipe_name(good)
    for bad in (
        good + "x",
        f"{_resident._PIPE_PREFIX}{'a' * 16}-{'0' * 15}",
        f"{_resident._PIPE_PREFIX}{'A' * 16}-{'0' * 16}",
        f"{_resident._PIPE_PREFIX}x\\..\\..\\C:\\Users\\file",
        f"{_resident._PIPE_PREFIX}{'a' * 16}-{'0' * 8}\\..\\{'0' * 7}",
        r"\\host\pipe\jangseung-" + "a" * 16 + "-" + "0" * 16,
    ):
        assert not _resident.valid_pipe_name(bad), bad


@windows_only
def test_the_off_switch_keeps_every_call_judged_directly(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload, JANGSEUNG_RESIDENT="off")
    setup.call(payload, JANGSEUNG_RESIDENT="OFF")
    time.sleep(1)
    assert not setup.folder.exists()


@windows_only
def test_hooks_started_without_a_launcher_never_start_it(setup):
    # aeg.exe and python -m call run() without a launcher.
    code = ("import sys; sys.path.insert(0, sys.argv[1]); sys.argv = ['aeg', 'hook-run'];"
            " from jangseung.cli.entry import run; raise SystemExit(run())")
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    done = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(setup.home)], input=payload,
                          capture_output=True, cwd=setup.project, env=setup.env(), timeout=120)
    assert done.returncode == 0, done.stderr
    time.sleep(1)
    assert not setup.folder.exists()


@windows_only
def test_parallel_calls_are_each_answered_and_recorded(setup):
    from jangseung.state.hook_ledger import HOOK_LEDGER_FILE, verify_hook_ledger

    commands = ["ls", "cat .env", "npm test", "git status"] * 3
    payloads = [_payload("Bash", {"command": command}, setup.project, use_id=f"p{number}")
                for number, command in enumerate(commands)]
    setup.call(payloads[0])
    setup.ready()
    with ThreadPoolExecutor(8) as pool:
        served = list(pool.map(setup.call, payloads))
    assert served == [setup.call(payload, resident=False) for payload in payloads]
    ledger = (setup.project / ".aeg" / HOOK_LEDGER_FILE).read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 1 + 2 * len(payloads)
    assert verify_hook_ledger(setup.project).ok


@windows_only
def test_the_resident_process_does_not_hold_the_project_folder(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload)
    setup.ready()
    assert setup.ask(payload) is not None
    # Windows refuses to rename a folder that any process has as its working folder.
    setup.project.rename(setup.project.with_name("moved"))


@windows_only
def test_the_resident_process_answers_nothing_but_hook_run(setup):
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    setup.call(payload)
    setup.ready()
    assert setup.ask(payload, argv=("doctor",)) is None
    assert setup.ask(payload) is not None


@windows_only
def test_the_resident_process_stops_when_idle(setup):
    code = (
        "import sys; home, launcher = sys.argv[1], sys.argv[2]; sys.path.insert(0, home)\n"
        "from jangseung import _resident, _resident_server\n"
        "_resident._interpreter_options = lambda: ('-I', '-S')\n"
        "sys.argv = [launcher, 'resident-serve']\n"
        "raise SystemExit(_resident_server.serve(launcher, idle_seconds=1))\n"
    )
    process = subprocess.Popen([sys.executable, "-I", "-S", "-c", code, str(setup.home), setup.launcher],
                               env=setup.env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert setup.ready() == process.pid
        assert process.wait(timeout=30) == 0
        assert setup.key() is None
    finally:
        if process.poll() is None:
            process.kill()


@windows_only
def test_a_session_start_starts_it_before_the_first_tool_call(setup):
    start = json.dumps({"hook_event_name": "SessionStart", "session_id": "s", "cwd": str(setup.project),
                        "source": "startup"}).encode()
    done = setup.call(start, arguments=("session-check",))
    assert done[0] == 0
    pid = setup.ready()
    payload = _payload("Bash", {"command": "ls"}, setup.project)
    assert setup.ask(payload) is not None
    assert setup.ready() == pid
