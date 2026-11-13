"""0.3.1, third part: hook processes read compiled modules from one file.

``jangseung._import_cache`` keeps the compiled forms a hook process loaded in
``__pycache__/hook-imports.<tag>.bin``. Python still finds each module and still
checks each compiled form against its source, so the code that runs is the same;
only the number of files opened changes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from jangseung.cli import entry

REPO_ROOT = Path(__file__).resolve().parents[1]
TAG = sys.implementation.cache_tag
# The cache is used on Windows only, where opening a file costs about 0.3 ms.
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the import cache is used on Windows only")


def _home(tmp_path: Path) -> Path:
    """A private copy of the package, so the cache file is written there and not in the repository."""

    home = tmp_path / "home"
    shutil.copytree(REPO_ROOT / "jangseung", home / "jangseung", ignore=shutil.ignore_patterns("__pycache__"))
    return home


def _cache(home: Path) -> Path:
    return home / "jangseung" / "__pycache__" / f"hook-run-imports.{TAG}.bin"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    (project / "a.txt").write_text("x\n", encoding="utf-8")
    return project


def _hook(home: Path, project: Path, *flags: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "a.txt"}, "tool_use_id": "t", "cwd": str(project),
                          "permission_mode": "default", "hook_event_name": "PreToolUse", "session_id": "s"})
    return subprocess.run([sys.executable, "-I", "-S", *flags, str(home / "jangseung" / "_hook.py"), "hook-run"],
                          input=payload, capture_output=True, text=True, cwd=project, timeout=120,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})


def _decision(done: subprocess.CompletedProcess) -> str:
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["hookSpecificOutput"]["permissionDecision"]


def _entries(cache: Path) -> dict:
    import binascii
    import marshal

    data = cache.read_bytes()
    assert binascii.crc32(data[4:]) == int.from_bytes(data[:4], "little")
    version, magic, entries = marshal.loads(data[4:])
    assert version == 2
    return entries


def _compiled_files(home: Path) -> list[Path]:
    return [path for path in (home / "jangseung").rglob("*.pyc")]


@windows_only
def test_a_hook_process_writes_the_cache_once_and_then_reads_from_it(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    first = _hook(home, project)
    assert _decision(first) == "allow"
    cache = _cache(home)
    entries = _entries(cache)
    assert any(key.endswith(os.path.join("evidence", "__pycache__", f"hook_judgment_engine_alignment.{TAG}.pyc")) for key in entries)
    assert any(os.path.join("json", "__pycache__") in key for key in entries)  # standard modules too
    written = cache.stat().st_mtime_ns

    # With every __pycache__ file gone, a module read from the cache is not compiled
    # again, so Python writes no new compiled file for it.
    for path in _compiled_files(home):
        path.unlink()
    second = _hook(home, project)
    assert (second.returncode, second.stdout, second.stderr) == (first.returncode, first.stdout, first.stderr)
    # Only the modules loaded before the cache starts are compiled and written again.
    assert sorted(path.relative_to(home).as_posix() for path in _compiled_files(home)) == [
        f"jangseung/__pycache__/__init__.{TAG}.pyc",
        f"jangseung/__pycache__/_import_cache.{TAG}.pyc",
        f"jangseung/__pycache__/_resident.{TAG}.pyc",  # asked first; switched off in tests
        f"jangseung/cli/__pycache__/__init__.{TAG}.pyc",
        f"jangseung/cli/__pycache__/entry.{TAG}.pyc",
    ]
    assert cache.stat().st_mtime_ns == written


@windows_only
def test_a_changed_module_runs_from_its_source(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    assert _decision(_hook(home, project)) == "allow"
    cache = _cache(home)
    before = cache.read_bytes()
    clock = home / "jangseung" / "_clock.py"
    clock.write_text(clock.read_text(encoding="utf-8") + "\nimport sys\nsys.stderr.write('CHANGED-SOURCE\\n')\n",
                     encoding="utf-8")
    changed = _hook(home, project)
    assert _decision(changed) == "allow" and "CHANGED-SOURCE" in changed.stderr
    assert cache.read_bytes() != before  # the stale form was replaced
    written = cache.stat().st_mtime_ns
    again = _hook(home, project)
    assert "CHANGED-SOURCE" in again.stderr
    assert cache.stat().st_mtime_ns == written


@windows_only
def test_a_damaged_cache_is_ignored_and_replaced(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    assert _decision(_hook(home, project)) == "allow"
    cache = _cache(home)
    cache.write_bytes(b"not a cache")
    assert _decision(_hook(home, project)) == "allow"
    assert _entries(cache)


def test_no_cache_is_written_when_python_writes_no_compiled_files(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    assert _decision(_hook(home, project, "-B")) == "allow"
    assert not _cache(home).exists()


@windows_only
def test_a_stale_stored_form_falls_back_to_the_pycache_file(tmp_path):
    # A stored form whose header no longer names the source is not handed to
    # Python; the __pycache__ file is read instead, and the cache marked for rewrite.
    module = tmp_path / "mod" / "probe_module.py"
    module.parent.mkdir()
    module.write_text("VALUE = 2\n", encoding="utf-8")
    script = f"""
import sys, marshal, py_compile
sys.path.insert(0, {str(REPO_ROOT)!r})
sys.path.append({str(module.parent)!r})
compiled = py_compile.compile({str(module)!r}, doraise=True)
from jangseung import _import_cache as cache
assert cache.start("hook-run")
stale = bytearray(open(compiled, 'rb').read())
stale[8:12] = (int.from_bytes(stale[8:12], 'little') ^ 1).to_bytes(4, 'little')
cache._State.stored[compiled] = bytes(stale)
cache._State.changed = False
import probe_module
print(probe_module.VALUE, cache._State.changed, cache._State.used[compiled] == open(compiled, 'rb').read())
"""
    done = subprocess.run([sys.executable, "-I", "-S", "-c", script], capture_output=True, text=True, timeout=60)
    assert done.stdout.split() == ["2", "True", "True"], done.stderr


def test_entry_imports_nothing_python_had_not_already_loaded():
    script = (
        "import sys; before = set(sys.modules); "
        f"sys.path.insert(0, {str(REPO_ROOT)!r}); import jangseung.cli.entry; "
        "print(sorted(set(sys.modules) - before))"
    )
    done = subprocess.run([sys.executable, "-I", "-S", "-c", script], capture_output=True, text=True, timeout=60)
    assert done.stdout.strip() == "['jangseung', 'jangseung.cli', 'jangseung.cli.entry']", done.stderr


def test_the_plugin_launcher_loads_no_pathlib_before_the_cache():
    source = (REPO_ROOT / "aeg").read_text(encoding="utf-8")
    assert "import pathlib" not in source and "from pathlib" not in source
    # The folder put on sys.path is the one pathlib's resolve() gave before.
    launcher = str(REPO_ROOT / "aeg")
    assert os.path.dirname(os.path.realpath(launcher)) == str(Path(launcher).resolve().parent)


def test_only_a_real_hook_process_start_turns_the_cache_on(monkeypatch):
    started: list = []
    monkeypatch.setattr(entry, "_start_import_cache", started.append)
    monkeypatch.setattr(entry, "main", lambda arguments: 0)
    monkeypatch.setattr(entry, "_exit_now", lambda code, session_check: None)
    hooks = list(sys.path_hooks)
    entry.run(["hook-run"])  # in-process callers pass their arguments
    monkeypatch.setattr(sys, "argv", ["aeg", "doctor"])
    entry.run()
    assert started == []
    for command in ("hook-run", "session-check"):
        monkeypatch.setattr(sys, "argv", ["aeg", command])
        entry.run()
    assert started == ["hook-run", "session-check"]
    assert sys.path_hooks == hooks


@pytest.mark.parametrize("launcher", ["aeg", "jangseung/_hook.py"])
def test_every_launcher_answers_the_same_with_and_without_the_cache(tmp_path, launcher):
    project = _project(tmp_path)
    home = tmp_path / "plugin"
    shutil.copytree(REPO_ROOT / "jangseung", home / "jangseung", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "aeg", home / "aeg")
    for command in ("ls", "cat .env", "git push --force", "rm -rf /"):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "tool_use_id": "t", "cwd": str(project),
                              "permission_mode": "default", "hook_event_name": "PreToolUse", "session_id": "s"})
        _cache(home).unlink(missing_ok=True)
        runs = []
        for flags in (["-B"], [], []):  # no cache at all, writing it, reading from it
            done = subprocess.run([sys.executable, "-I", "-S", *flags, str(home / launcher), "hook-run"], input=payload,
                                  capture_output=True, text=True, cwd=project, timeout=120,
                                  env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
            runs.append((done.returncode, done.stdout, done.stderr))
        assert runs[0] == runs[1] == runs[2], command
        assert _cache(home).exists() == (sys.platform == "win32")


@windows_only
def test_the_session_check_keeps_its_own_cache(tmp_path):
    # The once-a-session check loads modules a tool call never needs; keeping them
    # out of the hook-run file keeps every tool call from reading them.
    home, project = _home(tmp_path), _project(tmp_path)
    start = json.dumps({"hook_event_name": "SessionStart", "session_id": "s", "cwd": str(project), "source": "startup"})
    done = subprocess.run([sys.executable, "-I", "-S", str(home / "jangseung" / "_hook.py"), "session-check"], input=start,
                          capture_output=True, text=True, cwd=project, timeout=120,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
    assert done.returncode == 0, done.stderr
    folder = home / "jangseung" / "__pycache__"
    assert (folder / f"session-check-imports.{TAG}.bin").is_file()
    assert not _cache(home).exists()
    assert _decision(_hook(home, project)) == "allow"
    only_at_start = os.path.join("cli", "__pycache__", f"session_check.{TAG}.pyc")
    assert not any(key.endswith(only_at_start) for key in _entries(_cache(home)))
    assert any(key.endswith(only_at_start) for key in _entries(folder / f"session-check-imports.{TAG}.bin"))


def test_other_systems_keep_python_import_as_it_is(monkeypatch):
    from jangseung import _import_cache

    monkeypatch.setattr(_import_cache.sys, "platform", "linux")
    hooks = list(sys.path_hooks)
    assert _import_cache.start("hook-run") is False
    assert sys.path_hooks == hooks and _import_cache._State.path is None


@windows_only
def test_hash_based_compiled_files_do_not_rewrite_the_cache_on_every_call(tmp_path):
    # pip and uv write checked-hash files when SOURCE_DATE_EPOCH is set. They are
    # never stored, so finding them on disk is not a reason to write the cache again.
    import compileall
    import py_compile

    home, project = _home(tmp_path), _project(tmp_path)
    assert compileall.compile_dir(str(home / "jangseung"), quiet=1,
                                  invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
    assert _decision(_hook(home, project)) == "allow"
    cache = _cache(home)
    written = cache.stat().st_mtime_ns
    assert not any(os.sep + "jangseung" + os.sep in key and str(home) in key for key in _entries(cache))
    for _ in range(2):
        assert _decision(_hook(home, project)) == "allow"
    assert cache.stat().st_mtime_ns == written


@windows_only
def test_a_damaged_entry_is_caught_by_the_checksum_and_rebuilt(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    assert _decision(_hook(home, project)) == "allow"
    cache = _cache(home)
    data = bytearray(cache.read_bytes())
    middle = len(data) // 2
    data[middle:middle + 4096] = bytes(4096)  # a cluster lost as zeros, header and index intact
    cache.write_bytes(bytes(data))
    assert _decision(_hook(home, project)) == "allow"
    assert _entries(cache)  # written again, and its checksum matches


@windows_only
def test_an_oversized_cache_is_ignored_and_optimised_runs_keep_their_own(tmp_path):
    home, project = _home(tmp_path), _project(tmp_path)
    cache = _cache(home)
    cache.parent.mkdir(parents=True)
    cache.write_bytes(bytes(9 * 1024 * 1024))
    assert _decision(_hook(home, project)) == "allow"
    assert cache.stat().st_size < 4 * 1024 * 1024 and _entries(cache)
    before = cache.read_bytes()
    assert _decision(_hook(home, project, "-O")) == "allow"
    assert (cache.parent / f"hook-run-imports.{TAG}.opt-1.bin").is_file()
    assert cache.read_bytes() == before


def test_a_folder_that_cannot_be_written_costs_no_serialising(monkeypatch, tmp_path):
    from jangseung import _import_cache

    monkeypatch.setattr(_import_cache._State, "path", str(tmp_path / "missing" / "hook-run-imports.bin"))
    monkeypatch.setattr(_import_cache._State, "changed", True)
    monkeypatch.setattr(_import_cache._State, "used", {"x.pyc": b"x"})
    monkeypatch.setattr(_import_cache.sys, "dont_write_bytecode", False)

    def refuse(value):
        raise AssertionError("serialised although the file cannot be written")

    monkeypatch.setattr(_import_cache.marshal, "dumps", refuse)
    _import_cache.save()
    assert not (tmp_path / "missing").exists()
