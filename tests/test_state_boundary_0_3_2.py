"""State prerequisites are enforced before either the tool or its audit is released."""

import io
import json
import os
from pathlib import Path

import pytest

from jangseung.cli import hook_run
from jangseung.cli.hook_doctor import _recording_checks
from jangseung.state.hook_ledger import (
    HOOK_LEDGER_FILE, append_hook_decision_record, archive_hook_ledger, hook_ledger_needs_repair,
    repair_hook_ledger, verify_hook_ledger,
)
from jangseung.state.session_marks import mark_secret_naming_write, secret_naming_writes


def _run(repo: Path, *, substrate="claude-code", mark=False):
    raw = json.dumps({
        "tool_name": "Write", "tool_input": {"file_path": "note.py", "content": "label = '.env'" if mark else "label = 'test'"},
        "session_id": "test-session", "tool_use_id": "test-write", "cwd": str(repo),
    })
    out = io.StringIO()
    code = hook_run.run_aeg_hook_run(
        stdin=io.StringIO(raw), stdout=out, stderr=io.StringIO(), repo_root=repo,
        working_dir=repo, substrate=substrate,
    )
    return code, json.loads(out.getvalue())["hookSpecificOutput"]


def _append(repo):
    return append_hook_decision_record(
        repo, substrate="claude-code", tool_name="Read", hook_decision="allow", permission_decision="allow",
        fail_closed=False, reason_codes=(), exit_code=0,
    )


@pytest.mark.parametrize("kind", ["symlink", pytest.param("junction", marks=pytest.mark.skipif(os.name != "nt", reason="Windows only"))])
def test_linked_state_is_never_opened_or_written(tmp_path, kind):
    project, other = tmp_path / "project", tmp_path / "other"
    project.mkdir()
    other.mkdir()
    link = project / ".aeg"
    if kind == "junction":
        import _winapi
        _winapi.CreateJunction(str(other), str(link))
    else:
        try:
            link.symlink_to(other, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlink unavailable")

    assert not hook_run.ensure_recording_directory(project)
    code, decision = _run(project)
    assert code == 2 and decision["permissionDecision"] == "deny"
    assert "unsafe_state_directory_fail_closed_deny" in decision["permissionDecisionReason"]
    assert secret_naming_writes(project, "test-session") is None
    assert not verify_hook_ledger(project).ok
    assert _recording_checks(project)[0].status == "FAIL"
    for op in (_append, repair_hook_ledger, archive_hook_ledger, hook_ledger_needs_repair):
        with pytest.raises(ValueError, match="unlinked"):
            op(project)
    with pytest.raises(ValueError, match="unlinked"):
        mark_secret_naming_write(project, "test-session", ("note.py",))
    assert list(other.iterdir()) == []


@pytest.mark.parametrize(("substrate", "expected_code"), [("claude-code", 2), ("codex", 0)])
def test_required_mark_failure_denies_and_audits_final_response(tmp_path, substrate, expected_code):
    state = tmp_path / ".aeg"
    state.mkdir()
    # A corrupt store must not be silently replaced, clearing other sessions' holds.
    marks = state / "session_marks.json"
    marks.write_bytes(b"not JSON")
    code, decision = _run(tmp_path, substrate=substrate, mark=True)
    assert code == expected_code
    assert decision["permissionDecision"] == "deny"
    assert "session_mark_recording_failed" in decision["permissionDecisionReason"]
    assert "updatedInput" not in decision
    assert marks.read_bytes() == b"not JSON"
    result = verify_hook_ledger(tmp_path)
    assert result.ok and len(result.records) == 1
    record, = result.records
    assert (record["hook_decision"], record["permission_decision"], record["fail_closed"]) == ("deny", "deny", True)
    assert (record["substrate"], record["exit_code"]) == (substrate, code)
    assert record["reason_codes"] == ["session_mark_recording_failed"]
    assert record["tool_name"] == "Write" and record["session_id"] == "test-session"
    assert record["targets"] == ["note.py"] and len(record["input_hash"]) == 64


def test_required_mark_with_no_named_target_still_holds_session(tmp_path):
    (tmp_path / ".aeg").mkdir()
    mark_secret_naming_write(tmp_path, "session", ())
    assert secret_naming_writes(tmp_path, "session")
    assert secret_naming_writes(tmp_path, "other") == ()


def test_legacy_mark_with_no_targets_holds_only_its_session(tmp_path):
    state = tmp_path / ".aeg"
    state.mkdir()
    (state / "session_marks.json").write_text(json.dumps({
        "version": 1, "sessions": {"legacy": {"secret_naming_writes": [], "updated": "previous"}},
    }), encoding="utf-8")
    assert secret_naming_writes(tmp_path, "legacy")
    assert secret_naming_writes(tmp_path, "other") == ()
    mark_secret_naming_write(tmp_path, "other", ("note.py",))
    assert secret_naming_writes(tmp_path, "other") == ("note.py",)
    assert secret_naming_writes(tmp_path, "legacy")


def test_valid_final_json_without_lf_is_uncommitted_until_repair(tmp_path):
    (tmp_path / ".aeg").mkdir()
    _append(tmp_path)
    _append(tmp_path)
    ledger = tmp_path / ".aeg" / HOOK_LEDGER_FILE
    damaged = ledger.read_bytes()[:-1]
    ledger.write_bytes(damaged)
    result = verify_hook_ledger(tmp_path)
    assert not result.ok and len(result.records) == 1
    assert "missing LF" in result.errors[0]
    assert ledger.read_bytes() == damaged
    assert hook_ledger_needs_repair(tmp_path)
    with pytest.raises(ValueError, match="incomplete"):
        _append(tmp_path)
    with pytest.raises(ValueError, match="damaged"):
        archive_hook_ledger(tmp_path)
    repair = repair_hook_ledger(tmp_path)
    assert (repair.kept_records, repair.quarantined_lines) == (1, 1)
    assert Path(repair.quarantine_path).read_bytes() == damaged.split(b"\n")[-1]
    assert verify_hook_ledger(tmp_path).ok


def test_nonregular_ledger_is_not_an_empty_or_repairable_chain(tmp_path):
    state = tmp_path / ".aeg"
    state.mkdir()
    (state / HOOK_LEDGER_FILE).mkdir()
    result = verify_hook_ledger(tmp_path)
    assert not result.ok and result.records == ()
    assert "unlinked regular file" in result.errors[0]
    for op in (hook_ledger_needs_repair, repair_hook_ledger, archive_hook_ledger, _append):
        with pytest.raises(ValueError, match="unlinked regular file"):
            op(tmp_path)
    assert list(state.iterdir()) == [state / HOOK_LEDGER_FILE]
