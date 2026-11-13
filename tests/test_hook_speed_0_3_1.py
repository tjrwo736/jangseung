"""0.3.1: a faster hook process with the same decisions.

The hook is a new Python process on every tool call. 0.3.1 removes work from that
process without changing any judgment:

* ``jangseung.records`` replaces ``dataclasses`` on the hook path (no runtime
  ``exec``, no ``inspect`` import);
* SHA-256 comes from the built-in module instead of OpenSSL;
* the built-in file-name globs are matched with string tests (``GlobSet``);
* the ledger tail is taken from a head marker's name when the ledger is exactly as
  the previous append left it, instead of reading a file that just changed;
* the plugin starts one Python per call and skips the Microsoft Store stub.
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
from fnmatch import fnmatchcase
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
from unittest import mock

import pytest

from jangseung import records
from jangseung.classify import rules
from jangseung.state import hook_ledger
from jangseung.state.hook_ledger import (
    HOOK_LEDGER_FILE,
    HOOK_LEDGER_HEAD_PREFIX,
    append_hook_decision_record,
    archive_hook_ledger,
    repair_hook_ledger,
    verify_hook_ledger,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- records: the dataclass stand-in


@records.dataclass(frozen=True)
class _Point:
    x: int
    y: int = 0
    tags: list[str] = records.field(default_factory=list)


@records.dataclass(frozen=True)
class _Checked:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("negative")


@records.dataclass
class _Mutable:
    items: list[str] = records.field(default_factory=list)


def test_records_build_like_dataclasses():
    assert _Point(1) == _Point(x=1, y=0, tags=[])
    assert _Point(1, 2) != _Point(1, 3)
    assert _Point(1) != (1, 0, [])
    assert repr(_Point(1, 2, ["a"])) == "_Point(x=1, y=2, tags=['a'])"
    assert _Point.__match_args__ == ("x", "y", "tags")
    first, second = _Point(1), _Point(1)
    assert first.tags is not second.tags
    with pytest.raises(TypeError):
        _Point()
    with pytest.raises(TypeError):
        _Point(1, 2, [], 4)
    with pytest.raises(TypeError):
        _Point(1, x=2)
    with pytest.raises(TypeError):
        _Point(1, z=2)
    with pytest.raises(ValueError):
        _Checked(-1)


def test_frozen_records_raise_the_dataclasses_error_and_hash_by_value():
    point = _Point(1, 2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        point.x = 5
    with pytest.raises(dataclasses.FrozenInstanceError):
        del point.y
    assert hash(_Checked(3)) == hash(_Checked(3))
    with pytest.raises(TypeError):
        hash(_Mutable())
    changed = _Mutable()
    changed.items = ["x"]
    assert changed == _Mutable(["x"])


def test_records_replace_and_asdict():
    point = _Point(1, 2, ["a"])
    assert records.replace(point, y=5) == _Point(1, 5, ["a"])
    with pytest.raises(TypeError):
        records.replace(point, z=1)
    with pytest.raises(ValueError):
        records.replace(_Checked(1), value=-1)
    assert records.asdict(point) == {"x": 1, "y": 2, "tags": ["a"]}
    with pytest.raises(TypeError):
        records.asdict(object())


def test_records_refuse_what_they_do_not_support():
    with pytest.raises(TypeError):
        @records.dataclass(frozen=True)
        class _Child(_Point):
            z: int = 0
    with pytest.raises(TypeError):
        @records.dataclass(frozen=True)
        class _Order:
            a: int = 0
            b: int
    with pytest.raises(ValueError):
        @records.dataclass(frozen=True)
        class _Shared:
            a: list = []  # noqa: RUF012


def test_the_hook_path_loads_no_dataclasses_inspect_or_openssl():
    code = (
        f"import sys, json; sys.path.insert(0, {str(REPO_ROOT)!r}); import jangseung.cli.hook_run; "
        "print(json.dumps({name: name in sys.modules for name in ('dataclasses', 'inspect', '_hashlib', 'typing', 'datetime')}))"
    )
    loaded = json.loads(subprocess.run([sys.executable, "-I", "-c", code], cwd=REPO_ROOT, capture_output=True, text=True,
                                       check=True).stdout)
    assert not loaded["dataclasses"] and not loaded["_hashlib"] and not loaded["datetime"]
    if sys.version_info >= (3, 12):  # measured on 3.14; older standard libraries were not checked
        assert not loaded["inspect"] and not loaded["typing"]


def test_reason_text_keeps_the_mcp_codes_of_the_gate():
    from jangseung.cli import reason_text
    from jangseung.evidence import mcp_tool_gate

    assert reason_text.MCP_TOOL_REQUIRES_APPROVAL == mcp_tool_gate.MCP_TOOL_REQUIRES_APPROVAL
    assert reason_text.MCP_RESOURCE_READ_REQUIRES_APPROVAL == mcp_tool_gate.MCP_RESOURCE_READ_REQUIRES_APPROVAL


def test_sha256_helper_matches_hashlib():
    import hashlib

    from jangseung._sha256 import sha256

    for data in (b"", b"abc", "장승".encode("utf-8"), bytes(range(256)) * 300):
        assert sha256(data).hexdigest() == hashlib.sha256(data).hexdigest()


# --- GlobSet: the built-in globs without regular expressions


def _names_for(patterns: tuple[str, ...]) -> list[str]:
    names = {"", "a", "x.txt", ".env", "/", "a/b", "*", "?"}
    for pattern in patterns:
        bare = pattern.replace("*", "")
        names |= {pattern, bare, bare[1:], bare[:-1], bare.upper(), f"x{bare}", f"{bare}x", f"x/{bare}", f"{bare}/x"}
        names |= {pattern.replace("*", fill) for fill in ("", "a", "a/b", ".", "*")}
        names |= {pattern.replace("*", "", 1), pattern[::-1]}
    return sorted(names)


@pytest.mark.parametrize("patterns", [
    rules.PROTECTED_FILE_NAME_GLOBS, rules.AGENT_INSTRUCTION_GLOBS, rules.PROTECTED_GLOBS,
    rules.SECRET_FILE_GLOBS, rules._CONTENT_SECRET_GLOBS,
    ("a*b", "*x*", "x*", "*x", "x", "a?c", "[ab]c", "**", "*a*b*", "a*", "*"),
])
def test_glob_set_answers_like_fnmatchcase(patterns):
    match = rules.GlobSet(patterns)
    for name in _names_for(tuple(patterns)):
        assert match(name) == any(fnmatchcase(name, pattern) for pattern in patterns), (name, patterns)


# --- the ledger head marker


def _append(root: Path, number: int = 0) -> dict:
    return append_hook_decision_record(
        root, substrate="claude-code", tool_name="Bash", hook_decision="allow", permission_decision="allow",
        fail_closed=False, reason_codes=(f"code_{number}",), exit_code=0,
    )


@pytest.fixture()
def ledger_root(tmp_path: Path) -> Path:
    (tmp_path / ".aeg").mkdir()
    return tmp_path


def _markers(root: Path) -> list[str]:
    return sorted(name for name in os.listdir(root / ".aeg") if name.startswith(HOOK_LEDGER_HEAD_PREFIX))


def test_appends_chain_through_the_marker_without_reading_the_ledger(ledger_root):
    first = _append(ledger_root, 1)
    assert _markers(ledger_root) == [
        f"{HOOK_LEDGER_HEAD_PREFIX}1.{(ledger_root / '.aeg' / HOOK_LEDGER_FILE).stat().st_size}."
        f"{(ledger_root / '.aeg' / HOOK_LEDGER_FILE).stat().st_mtime_ns}.{first['record_hash']}"
    ]
    with mock.patch.object(hook_ledger, "_verified_tail_record", side_effect=AssertionError("read the tail")):
        records_written = [_append(ledger_root, n) for n in range(2, 12)]
    assert [r["sequence_number"] for r in records_written] == list(range(2, 12))
    assert records_written[0]["previous_record_hash"] == first["record_hash"]
    assert verify_hook_ledger(ledger_root).ok
    assert len(_markers(ledger_root)) == 1


def test_a_ledger_changed_by_another_writer_is_read_again(ledger_root):
    _append(ledger_root, 1)
    ledger = ledger_root / ".aeg" / HOOK_LEDGER_FILE
    # An older hook version appends without touching the marker.
    tail = hook_ledger._verified_tail_record(ledger)
    hook_ledger._append_record(
        ledger, previous_hash=tail["record_hash"], sequence_number=2, timestamp=None, substrate="codex",
        tool_name="Bash", hook_decision="deny", permission_decision="deny", fail_closed=True,
        reason_codes=("older_writer",), exit_code=0,
    )
    third = _append(ledger_root, 3)
    assert third["sequence_number"] == 3
    assert verify_hook_ledger(ledger_root).ok


def test_a_torn_or_rewritten_tail_is_still_refused(ledger_root):
    _append(ledger_root, 1)
    ledger = ledger_root / ".aeg" / HOOK_LEDGER_FILE
    with ledger.open("ab") as handle:
        handle.write(b'{"partial":')
    with pytest.raises(ValueError, match="incomplete"):
        _append(ledger_root, 2)
    ledger.write_bytes(ledger.read_bytes()[: -len(b'{"partial":')])
    # The same size with other bytes: the modification time no longer matches.
    raw = bytearray(ledger.read_bytes())
    raw[raw.index(b"code_1")] = ord("C")
    ledger.write_bytes(bytes(raw))
    with pytest.raises(ValueError, match="invalid"):
        _append(ledger_root, 2)


def test_an_edit_that_restores_size_and_time_is_left_to_verify_hooks(ledger_root):
    # The documented limit: the marker trusts an unchanged size and modification
    # time. Someone who rewrites bytes and puts the time back is caught by the
    # full chain check, as an edited ledger always was.
    _append(ledger_root, 1)
    ledger = ledger_root / ".aeg" / HOOK_LEDGER_FILE
    before = ledger.stat()
    raw = bytearray(ledger.read_bytes())
    raw[raw.index(b"code_1")] = ord("C")
    ledger.write_bytes(bytes(raw))
    os.utime(ledger, ns=(before.st_atime_ns, before.st_mtime_ns))
    _append(ledger_root, 2)
    assert not verify_hook_ledger(ledger_root).ok


def test_unusable_markers_fall_back_and_are_replaced(ledger_root):
    _append(ledger_root, 1)
    state = ledger_root / ".aeg"
    (state / f"{HOOK_LEDGER_HEAD_PREFIX}garbage").write_bytes(b"")
    (state / f"{HOOK_LEDGER_HEAD_PREFIX}9.1.1.{'0' * 64}").write_bytes(b"")
    second = _append(ledger_root, 2)
    assert second["sequence_number"] == 2
    assert len(_markers(ledger_root)) == 1
    for name in _markers(ledger_root):
        os.replace(state / name, state / f"{HOOK_LEDGER_HEAD_PREFIX}7.1.1.{'0' * 64}")
    assert _append(ledger_root, 3)["sequence_number"] == 3
    assert verify_hook_ledger(ledger_root).ok


def test_a_marker_that_cannot_be_written_does_not_fail_the_append(ledger_root):
    _append(ledger_root, 1)
    with mock.patch.object(hook_ledger.os, "replace", side_effect=OSError("denied")):
        assert _append(ledger_root, 2)["sequence_number"] == 2
    assert _markers(ledger_root) == []
    assert _append(ledger_root, 3)["sequence_number"] == 3
    assert verify_hook_ledger(ledger_root).ok


def test_repair_and_archive_drop_the_marker(ledger_root):
    for number in range(3):
        _append(ledger_root, number)
    archive_hook_ledger(ledger_root)
    assert _markers(ledger_root) == []
    after_archive = _append(ledger_root, 9)
    assert after_archive["sequence_number"] == 2
    ledger = ledger_root / ".aeg" / HOOK_LEDGER_FILE
    with ledger.open("ab") as handle:
        handle.write(b"not json\n")
    repair_hook_ledger(ledger_root)
    assert _markers(ledger_root) == []
    assert _append(ledger_root, 10)["sequence_number"] == 4
    assert verify_hook_ledger(ledger_root).ok


# --- the plugin launcher


def _run_launcher(version: tuple[int, int, int], argv: list[str], env: dict[str, str]) -> tuple[int, str]:
    out = io.StringIO()
    with mock.patch.object(sys, "version_info", version), mock.patch.object(sys, "argv", ["aeg", *argv]), \
            mock.patch.dict(os.environ, env, clear=False), mock.patch.object(sys, "stdout", out):
        try:
            runpy.run_path(str(REPO_ROOT / "aeg"), run_name="__main__")
        except SystemExit as stop:
            return int(stop.code or 0), out.getvalue()
    return 0, out.getvalue()


def test_the_launcher_hands_an_old_python_back_to_the_shell(monkeypatch):
    monkeypatch.delenv("JANGSEUNG_PYTHON_FALLBACK", raising=False)
    assert _run_launcher((3, 9, 6), ["hook-run"], {}) == (97, "")
    code, text = _run_launcher((3, 9, 6), ["hook-run"], {"JANGSEUNG_PYTHON_FALLBACK": "1"})
    assert code == 2 and json.loads(text)["hookSpecificOutput"]["permissionDecision"] == "deny"
    code, text = _run_launcher((3, 9, 6), ["session-check", "--plugin"], {"JANGSEUNG_PYTHON_FALLBACK": "1"})
    assert code == 0 and "3.10" in json.loads(text)["systemMessage"]


def test_the_launcher_stays_readable_by_old_pythons():
    import ast

    source = (REPO_ROOT / "aeg").read_text(encoding="utf-8")
    assert "from __future__" not in source
    ast.parse(source, feature_version=(3, 7))


def _plugin_command(name: str) -> str:
    data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return data["hooks"][name][0]["hooks"][0]["command"]


def _bash() -> str | None:
    found = shutil.which("bash")
    if not found or (os.name == "nt" and "system32" in found.lower()):
        return None  # WSL's bash.exe is not the shell Claude Code uses
    return found


def _fake_python(folder: Path, name: str, body: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / name
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8", newline="\n")
    script.chmod(0o755)


def _posix(path: Path) -> str:
    text = str(path)
    if os.name == "nt" and len(text) > 1 and text[1] == ":":
        return f"/{text[0].lower()}{text[2:]}".replace("\\", "/")
    return text


@pytest.mark.skipif(_bash() is None, reason="needs a POSIX shell")
def test_the_plugin_line_skips_the_store_stub_and_retries_an_old_python(tmp_path):
    bash = _bash()
    real = Path(sys.executable)
    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "t", "cwd": str(project),
                          "hook_event_name": "PreToolUse", "session_id": "s", "permission_mode": "plan"})
    stub = tmp_path / "Microsoft" / "WindowsApps"
    _fake_python(stub, "python3", "echo STUB; exit 9")
    old = tmp_path / "old"
    _fake_python(old, "python3", "exit 97")
    good = tmp_path / "good"
    _fake_python(good, "python", f'exec "{_posix(real)}" "$@"')
    base = {"CLAUDE_PLUGIN_ROOT": _posix(REPO_ROOT), "CLAUDE_PROJECT_DIR": str(project)}
    for first in (stub, old):
        env = {**os.environ, **base, "PATH": ":".join(_posix(p) for p in (first, good)) + ":" + _posix(Path(bash).parent)}
        done = subprocess.run([bash, "-c", _plugin_command("PreToolUse")], input=payload, capture_output=True, text=True,
                              cwd=project, env=env, timeout=60)
        assert "STUB" not in done.stdout, first
        answer = json.loads(done.stdout)
        assert answer["hookSpecificOutput"]["permissionDecision"] == "allow", (first, done.stdout, done.stderr)


def test_the_plugin_lines_keep_their_shape():
    for name, tail in (("PreToolUse", "hook-run --ensure-state"), ("SessionStart", "session-check --plugin")):
        command = _plugin_command(name)
        assert command.count(tail) == 2
        assert '-I -S "${CLAUDE_PLUGIN_ROOT}/aeg"' in command
        assert "$(" not in command and "`" not in command  # a subshell costs a fork on every call
        assert "export JANGSEUNG_PYTHON_FALLBACK=1; exec python" in command
