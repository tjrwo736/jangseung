"""Explain uses the real pure renderer without executing, storing or echoing input."""
import hashlib
import io
import json
from unittest.mock import patch

import pytest

from src.cli.explain import MAX_INPUT_CHARACTERS, build_explanation, cmd_explain
from src.cli.hook_run import render_hook_response
from src.cli.main import main


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "README.md").write_text("# public fixture", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "한글 문서.md").write_text("fixture", encoding="utf-8")
    (tmp_path / ".aeg").mkdir()
    (tmp_path / ".aeg" / "hook_ledger.jsonl").write_text("existing audit record\n", encoding="utf-8")
    return tmp_path


def snapshot(repo):
    return {str(p.relative_to(repo)): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in repo.rglob("*") if p.is_file()}


@pytest.mark.parametrize("substrate", ["claude-code", "codex"])
@pytest.mark.parametrize("payload,category", [
    ({"tool_name": "Read", "tool_input": {"file_path": "README.md"}}, "allowed"),
    ({"tool_name": "Read", "tool_input": {"file_path": "../outside.md"}}, "outside_repository"),
    ({"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "fixture"}}, "policy_gate"),
    ({"tool_name": "Write", "tool_input": {"file_path": ".aeg/ledger.jsonl", "content": "fixture"}}, "protected_state"),
    ({"tool_name": "Bash", "tool_input": {"command": "cat README.md"}}, "allowed"),
    ({"tool_name": "Bash", "tool_input": {"command": "cat 'docs/한글 문서.md'"}}, "allowed"),
    ({"tool_name": "PowerShell", "tool_input": {"command": "Get-Content README.md"}}, "allowed"),
    ({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, "dangerous_command"),
    ({"tool_name": "Bash", "tool_input": {"command": "pwd"}}, "unclassified"),
    ({"tool_name": "Bash", "tool_input": {"command": "cat missing.md"}}, "unclassified"),
    ({"tool_name": "Bash", "tool_input": {"command": "rg --no-config --color never x README.md"}}, "unclassified"),
    ("not-json", "invalid_input"),
    ("null", "invalid_input"),
    ({"tool_name": "unknown", "tool_input": {}}, "invalid_input"),
])
def test_explanation_preserves_real_judgment_and_state(repo, substrate, payload, category):
    raw = payload if isinstance(payload, str) else json.dumps(dict(payload, tool_use_id="explain-test"))
    expected = render_hook_response(raw, repo_root=repo, substrate=substrate)
    before = snapshot(repo)
    with patch("src.cli.hook_run.append_hook_decision_record", side_effect=AssertionError("must not record")), \
         patch("subprocess.run", side_effect=AssertionError("must not execute")):
        report = build_explanation(raw, repo_root=repo, substrate=substrate)
    assert report["category"] == category
    assert (report["permission_decision"], report["hook_decision"], report["hook_exit_code"], report["fail_closed"]) == (
        expected.permission_decision, expected.hook_decision, expected.exit_code, expected.fail_closed)
    assert not report["store_write_performed"]
    assert not report["tool_execution_performed"]
    assert report["recording_status"] == "NOT_ATTEMPTED"
    assert report["host_execution"] == "NOT_CHECKED"
    assert snapshot(repo) == before


@pytest.mark.parametrize("as_json", [True, False])
@pytest.mark.parametrize("place", ["content", "tool_name", "malformed"])
def test_secret_and_arbitrary_input_never_echoed(repo, as_json, place):
    secret = "sk-proj-DO-NOT-DISPLAY-abcdefghijklmnop"
    raw = json.dumps({"tool_name": secret if place == "tool_name" else "Write",
                      "tool_input": {"file_path": ".env", "content": secret}, "tool_use_id": secret})
    if place == "malformed":
        raw = '{"invalid":' + secret
    out = io.StringIO()
    cmd_explain(repo, stdin=io.StringIO(raw), stdout=out, as_json=as_json)
    assert secret not in out.getvalue()
    assert '.env' not in out.getvalue()
    assert raw not in out.getvalue()


def test_unclassified_is_not_described_as_dangerous_and_codex_mapping_is_visible(repo):
    out = io.StringIO()
    assert cmd_explain(repo, command="pwd", substrate="codex", stdin=io.StringIO(), stdout=out) == 0
    assert "not a finding that the command is dangerous" in out.getvalue()
    assert "upgrades ask/defer to deny" in out.getvalue()
    assert "exit 0 does not mean allow" in out.getvalue()


@pytest.mark.parametrize("args", [
    ["explain", "--command", "cat README.md", "--substrate", "codex", "--json"],
    ["explain", "--file", "README.md", "--json"],
    ["explain", "--command", "Get-Content README.md", "--tool", "PowerShell", "--json"],
])
def test_cli_dispatch_and_convenience_inputs(repo, monkeypatch, capsys, args):
    monkeypatch.chdir(repo)
    before = snapshot(repo)
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["permission_decision"] == "allow"
    assert snapshot(repo) == before


def test_diagnostic_exit_is_not_hook_exit_and_no_state_created(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["explain", "--command", "rm -rf /", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["permission_decision"] == "deny"
    assert report["hook_exit_code"] == 2
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setattr("sys.stdin", io.StringIO("invalid"))
    assert main(["explain", "--stdin", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["fail_closed"]


@pytest.mark.parametrize("args", [
    ["explain"], ["explain", "--file", "README.md", "--command", "pwd"],
    ["explain", "--file", "README.md", "--tool", "PowerShell"],
])
def test_cli_requires_unambiguous_input(args):
    with pytest.raises(SystemExit) as result:
        main(args)
    assert result.value.code == 2


def test_oversized_or_unreadable_input_is_not_echoed(repo):
    for stream in (io.StringIO("x" * (MAX_INPUT_CHARACTERS + 1)), io.StringIO()):
        if not stream.getvalue():
            stream.close()
        out = io.StringIO()
        assert cmd_explain(repo, stdin=stream, stdout=out, as_json=True) == 1
        assert json.loads(out.getvalue())["permission_decision"] == "NOT_CHECKED"
        assert len(out.getvalue()) < 1000


def test_internal_diagnostic_failure_does_not_echo_exception(repo):
    with patch("src.cli.explain.render_hook_response", side_effect=RuntimeError("private diagnostic input")):
        out = io.StringIO()
        assert cmd_explain(repo, command="private command", stdin=io.StringIO(), stdout=out) == 1
    assert "private" not in out.getvalue()


def test_required_field_names_survive_filtering(repo):
    report = build_explanation('{}', repo_root=repo)
    assert "missing_required_field:tool_input" in report["reason_codes"]
    assert "missing_required_field:tool_name" in report["reason_codes"]


def test_file_preview_does_not_read_file_contents(repo):
    with patch("pathlib.Path.read_text", side_effect=AssertionError("do not read contents")), \
         patch("pathlib.Path.read_bytes", side_effect=AssertionError("do not read contents")):
        out = io.StringIO()
        assert cmd_explain(repo, file="README.md", stdin=io.StringIO(), stdout=out, as_json=True) == 0
    assert json.loads(out.getvalue())["permission_decision"] == "allow"
