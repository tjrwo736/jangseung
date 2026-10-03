"""Damaged evidence remains inspectable; recovery never blesses a broken chain."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.cli.main import _cmd_evidence_list, _cmd_evidence_show, _cmd_evidence_verify_hooks
from src.state.file_lock import exclusive_hook_lock
from src.state.hook_ledger import append_hook_decision_record, read_hook_ledger, verify_hook_ledger


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / ".aeg").mkdir()
    return tmp_path


def append(repo):
    return append_hook_decision_record(repo, substrate="codex", tool_name="Read", hook_decision="ALLOW",
                                       permission_decision="allow", fail_closed=False, reason_codes=["test"], exit_code=0)


def snapshot(repo):
    return {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (repo / ".aeg").rglob("*") if p.is_file()}


def run_entry(repo, name):
    directory = repo / ".aeg" / "runs" / name
    directory.mkdir(parents=True)
    for filename in ("run.json", "evidence.json", "manifest.json"):
        (directory / filename).write_text("{}", encoding="utf-8")
    return json.dumps({"run_id": name, "status": "CLEAN_CORE", "recorded_at": "2026-10-03T00:00:00Z"}).encode()


def test_non_utf8_run_line_does_not_hide_good_entries(repo, capsys):
    before = run_entry(repo, "before")
    after = run_entry(repo, "after")
    (repo / ".aeg" / "ledger.jsonl").write_bytes(before + b"\n\xff\n" + after + b"\n")
    state = snapshot(repo)
    assert _cmd_evidence_list(repo, as_json=True) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "DEGRADED"
    assert {item["id"] for item in data["items"]} == {"before", "after", "ledger-line-2"}
    assert sum(item["readability"] == "UNREADABLE" for item in data["items"]) == 1
    assert _cmd_evidence_show(repo, "after", as_json=True) == 0
    assert json.loads(capsys.readouterr().out)["readability"] == "READABLE"
    assert snapshot(repo) == state


def test_non_utf8_hook_line_is_unreadable_and_chain_still_fails(repo, capsys):
    append(repo)
    append(repo)
    path = repo / ".aeg" / "hook_ledger.jsonl"
    lines = path.read_bytes().splitlines()
    path.write_bytes(lines[0] + b"\n\xff\n" + lines[1] + b"\n")
    state = snapshot(repo)
    items = read_hook_ledger(repo)
    assert [item.readable for item in items] == [True, False, True]
    assert not verify_hook_ledger(repo).ok
    assert _cmd_evidence_list(repo, as_json=True) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "DEGRADED"
    assert _cmd_evidence_verify_hooks(repo, as_json=True) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"
    with pytest.raises(ValueError, match="chain is invalid"):
        append(repo)
    assert snapshot(repo) == state


@pytest.mark.parametrize("missing", ["run.json", "evidence.json", "manifest.json"])
def test_missing_artifact_is_unreadable_in_list(repo, capsys, missing):
    entry = run_entry(repo, "missing")
    (repo / ".aeg" / "ledger.jsonl").write_bytes(entry + b"\n")
    (repo / ".aeg" / "runs" / "missing" / missing).unlink()
    state = snapshot(repo)
    assert _cmd_evidence_list(repo, as_json=True) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "DEGRADED"
    assert data["items"][0]["readability"] == "UNREADABLE"
    assert data["items"][0]["decision"] == "UNREADABLE"
    assert snapshot(repo) == state


@pytest.mark.parametrize("value", ["null", "[]", "true", '"text"', "42"])
def test_non_object_hook_record_never_passes_verification(repo, value):
    (repo / ".aeg" / "hook_ledger.jsonl").write_text(value + "\n", encoding="utf-8")
    assert not verify_hook_ledger(repo).ok


def child_env():
    return dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONDONTWRITEBYTECODE="1")


def test_dead_writer_lock_is_recovered_without_changing_records(repo):
    append(repo)
    ledger = repo / ".aeg" / "hook_ledger.jsonl"
    before = ledger.read_bytes()
    lock = repo / ".aeg" / "hook_ledger.lock"
    child = subprocess.run([sys.executable, "-B", "-c", "import os,sys\nfrom pathlib import Path\nfrom src.state.file_lock import exclusive_hook_lock\nwith exclusive_hook_lock(Path(sys.argv[1])):\n os._exit(17)\n", str(lock)],
                           env=child_env(), capture_output=True, timeout=15)
    assert child.returncode == 17, child.stderr
    assert lock.exists()
    append(repo)
    assert not lock.exists()
    assert ledger.read_bytes().startswith(before)
    assert len(verify_hook_ledger(repo).records) == 2
    assert verify_hook_ledger(repo).ok


@pytest.mark.parametrize("payload", [str(os.getpid()), "", "unknown", "0"])
def test_live_or_unknown_legacy_owner_is_never_deleted(repo, payload):
    lock = repo / ".aeg" / "hook_ledger.lock"
    lock.write_text(payload, encoding="ascii")
    with pytest.raises(TimeoutError):
        with exclusive_hook_lock(lock, timeout_seconds=0.05):
            pytest.fail("must not steal an active or ambiguous lock")
    assert lock.read_text(encoding="ascii") == payload


def test_os_guard_is_exclusive_and_file_is_reused(repo):
    lock = repo / ".aeg" / "hook_ledger.lock"
    with exclusive_hook_lock(lock):
        with pytest.raises(TimeoutError):
            with exclusive_hook_lock(lock, timeout_seconds=0.05):
                pytest.fail("must not acquire a held lock")
        assert lock.exists()
    guard = lock.with_suffix(".guard")
    inode = guard.stat().st_ino
    with exclusive_hook_lock(lock):
        assert guard.stat().st_ino == inode


def test_concurrent_writers_preserve_chain(repo):
    code = "from src.state.hook_ledger import append_hook_decision_record\nimport sys\nfor i in range(4):\n append_hook_decision_record(sys.argv[1],substrate='codex',tool_name='Read',hook_decision='ALLOW',permission_decision='allow',fail_closed=False,reason_codes=['test'],exit_code=0)\n"
    workers = [subprocess.Popen([sys.executable, "-B", "-c", code, str(repo)], env=child_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    try:
        for process in workers:
            _, stderr = process.communicate(timeout=20)
            assert process.returncode == 0, stderr
    finally:
        for process in workers:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
    result = verify_hook_ledger(repo)
    assert result.ok
    assert len(result.records) == 12
