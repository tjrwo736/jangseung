"""0.3.1, second part: less work around the judgment, with the same decisions.

* each distinct path is resolved once per judgment (``jangseung._resolve``);
* timestamps come from ``time`` instead of ``datetime``;
* the hook commands leave the process with ``os._exit`` once their output is out;
* the plugin starts Python with ``-S``, and the Windows Claude Code install starts
  the interpreter directly on ``jangseung/_hook.py`` instead of going through
  ``aeg.exe`` and a virtual environment's ``python.exe`` redirector.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

import pytest

from jangseung import _clock, _resolve
from jangseung.cli import entry, hook_doctor, install
from jangseung.cli.hook_run import render_hook_response
from jangseung.state.hook_ledger import HOOK_LEDGER_FILE

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- one resolution per path within a judgment


def _counting_resolve(monkeypatch) -> list[str]:
    seen: list[str] = []
    original = Path.resolve

    def resolve(self, strict=False):
        seen.append(str(self))
        return original(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve)
    return seen


def test_outside_a_judgment_every_call_resolves(monkeypatch, tmp_path):
    seen = _counting_resolve(monkeypatch)
    expected = tmp_path.resolve()
    assert _resolve.resolved(tmp_path) == expected
    _resolve.resolved(tmp_path)
    assert seen.count(str(tmp_path)) == 3
    assert _resolve._memo is None


def test_inside_a_judgment_each_path_resolves_once(monkeypatch, tmp_path):
    seen = _counting_resolve(monkeypatch)
    with _resolve.one_judgment():
        first = _resolve.resolved(tmp_path)
        assert _resolve.resolved(str(tmp_path)) is first
        assert _resolve.resolved(tmp_path, strict=True) == first
        with _resolve.one_judgment():  # a nested scope shares the outer one
            assert _resolve.resolved(tmp_path) is first
        assert _resolve._memo is not None
        assert _resolve.realpath_text(str(tmp_path)) == os.path.realpath(str(tmp_path))
    assert seen.count(str(tmp_path)) == 2  # once lenient, once strict
    assert _resolve._memo is None


def test_a_failed_resolution_is_not_remembered(monkeypatch, tmp_path):
    calls = []

    def failing(self, strict=False):
        calls.append(str(self))
        raise OSError("unreadable")

    monkeypatch.setattr(Path, "resolve", failing)
    with _resolve.one_judgment():
        for _ in range(2):
            with pytest.raises(OSError):
                _resolve.resolved(tmp_path)
    assert len(calls) == 2


def _payload(tool: str, tool_input: dict, project: Path) -> str:
    return json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "cwd": str(project),
                       "permission_mode": "default", "hook_event_name": "PreToolUse", "session_id": "s"})


def test_each_judgment_sees_the_files_as_they_are_then(tmp_path):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    (project / "sub").mkdir(parents=True)
    outside.mkdir()
    (project / "sub" / "note.txt").write_text("x\n", encoding="utf-8")
    (outside / "note.txt").write_text("x\n", encoding="utf-8")
    payload = _payload("Read", {"file_path": "sub/note.txt"}, project)
    first = render_hook_response(payload, repo_root=project, working_dir=project)
    assert first.permission_decision == "allow"
    assert _resolve._memo is None
    shutil.rmtree(project / "sub")
    try:
        (project / "sub").symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("this account cannot create symbolic links")
        import _winapi  # a junction needs no privilege

        _winapi.CreateJunction(str(outside), str(project / "sub"))
    second = render_hook_response(payload, repo_root=project, working_dir=project)
    assert second.permission_decision != "allow"


# --- timestamps without datetime


@pytest.mark.parametrize("nanoseconds", [
    1_700_000_000_000_000_000,
    1_700_000_000_000_000_999,
    1_700_000_000_000_001_000,
    1_700_000_000_123_456_789,
    1_700_000_000_999_999_999,
    951_782_400_000_000_000,  # 2000-02-29
    4_102_444_799_999_999_000,  # 2099-12-31 23:59:59.999999
])
def test_the_clock_writes_what_datetime_wrote(monkeypatch, nanoseconds):
    from datetime import datetime, timedelta, timezone

    monkeypatch.setattr(_clock.time, "time_ns", lambda: nanoseconds)
    moment = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=nanoseconds // 1000)
    assert _clock.utc_timestamp() == moment.isoformat().replace("+00:00", "Z")


# --- leaving the process once the answer is out


class _Exited(Exception):
    pass


def _leave(record: list):
    def leave(status):
        record.append(("exit", status))
        raise _Exited

    return leave


@pytest.mark.parametrize("command, code", [("hook-run", 2), ("session-check", 0)])
def test_hook_commands_flush_and_leave_at_once(monkeypatch, command, code):
    order: list = []
    monkeypatch.setattr(entry, "main", lambda arguments: order.append(("main", arguments)) or code)
    monkeypatch.setattr(sys, "stdout", mock.Mock(flush=lambda: order.append("stdout")))
    monkeypatch.setattr(sys, "stderr", mock.Mock(flush=lambda: order.append("stderr")))
    monkeypatch.setattr(os, "_exit", _leave(order))
    with pytest.raises(_Exited):
        entry.run([command, "--x"])
    assert order == [("main", [command, "--x"]), "stdout", "stderr", ("exit", code)]


@pytest.mark.parametrize("command, code", [("hook-run", 2), ("session-check", 0)])
def test_an_answer_that_cannot_leave_still_blocks(monkeypatch, command, code):
    monkeypatch.setattr(entry, "main", lambda arguments: 0)

    def broken():
        raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", mock.Mock(flush=broken))
    monkeypatch.setattr(sys, "stderr", mock.Mock(flush=broken))
    exits: list = []
    monkeypatch.setattr(os, "_exit", _leave(exits))
    with pytest.raises(_Exited):
        entry.run([command])
    assert exits == [("exit", code)]


def test_other_commands_return_normally(monkeypatch):
    monkeypatch.setattr(entry, "main", lambda arguments: 3)
    monkeypatch.setattr(os, "_exit", mock.Mock(side_effect=AssertionError("must not leave early")))
    assert entry.run(["doctor"]) == 3
    assert entry.run([]) == 3


def test_real_hook_processes_write_their_whole_answer(tmp_path):
    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    (project / "a.txt").write_text("x\n", encoding="utf-8")
    payload = _payload("Read", {"file_path": "a.txt"}, project)
    launchers = (
        [sys.executable, "-I", "-S", str(REPO_ROOT / "aeg"), "hook-run"],
        [sys.executable, "-I", "-S", str(REPO_ROOT / "jangseung" / "_hook.py"), "hook-run"],
    )
    for argv in launchers:
        done = subprocess.run(argv, input=payload, capture_output=True, text=True, cwd=project, timeout=60,
                              env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
        assert done.returncode == 0, done.stderr
        assert json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert len((project / ".aeg" / HOOK_LEDGER_FILE).read_text(encoding="utf-8").splitlines()) == len(launchers)


@pytest.mark.parametrize("name", ["aeg", "jangseung/_hook.py"])
def test_the_launchers_compile_without_warnings(name):
    # A script is compiled on every start, so a warning would reach stderr on every tool call.
    import warnings

    source = (REPO_ROOT / name).read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compile(source, name, "exec")


def test_importing_the_launcher_file_runs_nothing():
    code = f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); import jangseung._hook; print('quiet')"
    done = subprocess.run([sys.executable, "-I", "-c", code], input="", capture_output=True, text=True, timeout=60)
    assert done.stdout == "quiet\n" and done.returncode == 0


# --- the direct Windows form: <python.exe> -I -S <...>\jangseung\_hook.py hook-run

_PYTHON = r"C:\Python314\python.exe"
_SCRIPT = r"C:\Users\Name With Space\venv\Lib\site-packages\jangseung\_hook.py"


def _direct(*tail: str) -> dict:
    return {"type": "command", "command": _PYTHON, "args": ["-I", "-S", _SCRIPT, *tail], "onFailure": "block"}


def test_windows_claude_code_install_prefers_the_direct_form(monkeypatch):
    monkeypatch.setattr(install, "_direct_hook_program", lambda: (_PYTHON, _SCRIPT))
    assert install.resolve_claude_code_hook_command(platform="win32") == (_PYTHON, ("-I", "-S", _SCRIPT, "hook-run"))
    assert install.resolve_claude_code_hook_command(platform="win32", mcp=True)[1][-1] == "--mcp"
    # POSIX and Codex keep their forms; Codex switches a changed hook off until it is trusted again.
    assert "_hook.py" not in install.resolve_claude_code_hook_command(platform="linux")[0]
    assert "_hook.py" not in (install.resolve_codex_windows_hook_command(platform="win32") or "")
    monkeypatch.setattr(install, "_direct_hook_program", lambda: None)
    assert "_hook.py" not in str(install.resolve_claude_code_hook_command(platform="win32"))


def test_the_direct_program_is_the_base_interpreter_and_never_a_store_alias(monkeypatch, tmp_path):
    base = tmp_path / "Python314" / "python.exe"
    venv = tmp_path / "venv" / "Scripts" / "python.exe"
    for path in (base, venv):
        path.parent.mkdir(parents=True)
        path.write_bytes(b"")
    monkeypatch.setattr(install.sys, "_base_executable", str(base), raising=False)
    monkeypatch.setattr(install.sys, "executable", str(venv))
    python, script = install._direct_hook_program()
    assert python == str(base) and Path(script) == REPO_ROOT / "jangseung" / "_hook.py"
    monkeypatch.setattr(install.sys, "_base_executable", str(tmp_path / "gone" / "python.exe"))
    assert install._direct_hook_program()[0] == str(venv)
    store = r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe"
    monkeypatch.setattr(install.sys, "_base_executable", store)
    assert install._direct_hook_program() is None
    pythonw = base.with_name("pythonw.exe")
    pythonw.write_bytes(b"")
    monkeypatch.setattr(install.sys, "_base_executable", str(pythonw))
    monkeypatch.setattr(install.sys, "executable", str(pythonw))
    assert install._direct_hook_program() is None


def test_in_a_venv_the_direct_form_needs_the_package_in_its_site_packages(monkeypatch, tmp_path):
    base = tmp_path / "Python314" / "python.exe"
    base.parent.mkdir()
    base.write_bytes(b"")
    venv = tmp_path / "venv"
    monkeypatch.setattr(install.sys, "_base_executable", str(base), raising=False)
    monkeypatch.setattr(install.sys, "prefix", str(venv))
    monkeypatch.setattr(install.sys, "base_prefix", str(base.parent))
    # The package elsewhere (here: this checkout, as with an editable install) keeps aeg.exe.
    (venv / "Lib" / "site-packages").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = x\n", encoding="utf-8")
    assert install._direct_hook_program() is None
    package = venv / "Lib" / "site-packages" / "jangseung"
    (package / "cli").mkdir(parents=True)
    (package / "_hook.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(install, "__file__", str(package / "cli" / "install.py"))
    assert install._direct_hook_program() == (str(base), str(package / "_hook.py"))
    (venv / "pyvenv.cfg").unlink()
    assert install._direct_hook_program() is None


@pytest.mark.parametrize("hook, kind", [
    (_direct("hook-run"), install.HOOK_KIND_MAIN),
    (_direct("hook-run", "--mcp"), install.HOOK_KIND_MCP),
    ({**_direct("hook-run"), "command": r"C:\venv\Scripts\python3.12.exe"}, install.HOOK_KIND_MAIN),
    ({**_direct("hook-run"), "args": ["-S", "-I", _SCRIPT, "hook-run"]}, None),
    ({**_direct("hook-run"), "args": ["-I", _SCRIPT, "hook-run"]}, None),
    ({**_direct("hook-run"), "args": ["-I", "-S", r"jangseung\_hook.py", "hook-run"]}, None),
    ({**_direct("hook-run"), "args": ["-I", "-S", r"C:\x\other\_hook.py", "hook-run"]}, None),
    ({**_direct("hook-run"), "args": ["-I", "-S", _SCRIPT, "hook-run", "--evil"]}, None),
    ({**_direct("hook-run"), "command": r"C:\tools\node.exe"}, None),
    ({**_direct("hook-run"), "command": r"tools\python.exe"}, None),
])
def test_only_the_generated_direct_form_is_recognized(hook, kind):
    assert install._managed_hook_kind(hook) == kind


def test_reinstall_moves_an_aeg_exe_hook_to_the_direct_form_and_uninstall_removes_it():
    old = {"hooks": {"PreToolUse": [{"matcher": install.WINDOWS_AEGIS_HOOK_MATCHER, "hooks": [
        {"type": "command", "command": r"C:\venv\Scripts\aeg.exe", "args": ["hook-run"], "onFailure": "block"}]}]}}
    new, already = install.build_installed_settings(old, _PYTHON, args=("-I", "-S", _SCRIPT, "hook-run"),
                                                    matcher=install.WINDOWS_AEGIS_HOOK_MATCHER)
    assert not already
    assert new["hooks"]["PreToolUse"] == [{"matcher": install.WINDOWS_AEGIS_HOOK_MATCHER, "hooks": [_direct("hook-run")]}]
    command, args = install.session_check_command(_PYTHON, ("-I", "-S", _SCRIPT, "hook-run"))
    assert (command, args) == (_PYTHON, ("-I", "-S", _SCRIPT, "session-check"))
    assert install.is_session_check_hook({"type": "command", "command": command, "args": list(args)})
    assert not install.is_session_check_hook({"type": "command", "command": r"C:\tools\node.exe", "args": list(args)})
    removed, count = install.build_uninstalled_settings(new)
    assert count == 1 and "hooks" not in removed


def test_the_doctor_checks_the_launcher_file_without_running_it(tmp_path):
    python = tmp_path / "python.exe"
    python.write_bytes(b"")
    python.chmod(0o755)
    script = tmp_path / "site-packages" / "jangseung" / "_hook.py"
    hook = {"type": "command", "command": str(python), "args": ["-I", "-S", str(script), "hook-run"]}
    assert hook_doctor._executable_check("h", hook).status == "FAIL"
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    check = hook_doctor._executable_check("h", hook)
    assert check.status == "PASS" and "launcher file" in check.message


@pytest.mark.skipif(os.name != "nt", reason="the direct form is registered on Windows only")
def test_a_venv_keeps_its_protection_under_the_direct_form(tmp_path):
    """Started directly, the base interpreter names the venv as sys.prefix, as the venv's python.exe does."""

    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    venv = project / ".venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, timeout=180)
    site_packages = venv / "Lib" / "site-packages"
    shutil.copytree(REPO_ROOT / "jangseung", site_packages / "jangseung", ignore=shutil.ignore_patterns("__pycache__"))
    launcher = site_packages / "jangseung" / "_hook.py"
    venv_python = venv / "Scripts" / "python.exe"
    base_python = getattr(sys, "_base_executable", sys.executable)

    through_venv = subprocess.run([str(venv_python), "-I", "-c", "import sys; print(sys.prefix)"],
                                  capture_output=True, text=True, check=True, timeout=60)
    probe = (
        "import runpy, sys, types; stub = types.ModuleType('jangseung.cli.entry'); "
        "stub.run = lambda **_: print(sys.prefix) or 0; sys.modules['jangseung.cli.entry'] = stub; "
        f"runpy.run_path({str(launcher)!r}, run_name='__main__')"
    )
    direct = subprocess.run([base_python, "-I", "-S", "-c", probe], capture_output=True, text=True, timeout=60)
    assert Path(direct.stdout.strip()).resolve() == Path(through_venv.stdout.strip()).resolve(), direct.stderr
    chosen = subprocess.run([str(venv_python), "-I", "-c",
                             "from jangseung.cli.install import _direct_hook_program; print(repr(_direct_hook_program()))"],
                            capture_output=True, text=True, check=True, timeout=60)
    python, script = eval(chosen.stdout)  # noqa: S307 - our own repr of two strings
    assert Path(script) == launcher.resolve() and Path(python).resolve() == Path(base_python).resolve()

    calls = [
        ("Write", {"file_path": ".venv/Lib/site-packages/x.pth", "content": "import os\n"}),
        ("Bash", {"command": "echo x > .venv/Lib/site-packages/_sha2.py"}),
        ("Bash", {"command": "ls .venv/Lib"}),
        ("Read", {"file_path": ".venv/pyvenv.cfg"}),
    ]
    forms = (
        [str(venv_python), "-I", "-m", "jangseung.cli", "hook-run"],
        [base_python, "-I", "-S", str(launcher), "hook-run"],
    )
    for tool, tool_input in calls:
        payload = _payload(tool, tool_input, project)
        answers = [
            subprocess.run(argv, input=payload, capture_output=True, text=True, cwd=project, timeout=60,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
            for argv in forms
        ]
        assert [(a.returncode, a.stdout) for a in answers][0] == [(a.returncode, a.stdout) for a in answers][1], tool_input
    write = subprocess.run(forms[1], input=_payload(*calls[0], project), capture_output=True, text=True, cwd=project,
                           timeout=60, env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
    assert json.loads(write.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
