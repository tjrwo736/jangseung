"""Positive read cases and adversarial syntax must reach the real hook boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.cli.hook_run import render_hook_response
from src.evidence.shell_read_only import classify_shell_read


@pytest.fixture
def repo(tmp_path):
    for path in ("README.md", "docs/guide.md", "docs/한글 문서.md", ".env", "src/law/README.md", ".aeg/log.md"):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# harmless fixture\n", encoding="utf-8")
    return tmp_path.resolve()


def judge(repo, command, substrate="codex", tool="Bash"):
    return render_hook_response(json.dumps({"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "read-regression"}), repo_root=repo, substrate=substrate)


@pytest.mark.parametrize("substrate", ["claude-code", "codex"])
@pytest.mark.parametrize("command", [
    "cat README.md", "cat -- README.md docs/guide.md", "cat -n README.md",
    "head -n 20 README.md", "head -n20 README.md", "tail -n 5 README.md",
    "sed -n '1,80p' README.md", "sed -n '1p' docs/guide.md",
    "rg --no-config -n example README.md", "rg --no-config -e '-example' -- README.md",
    "cat README.md | head -n 2", "cat README.md | rg --no-config example",
    "cat 'docs/한글 문서.md'", "Get-Content README.md",
    "Get-Content -LiteralPath 'docs/한글 문서.md' -Raw",
    "Get-Content README.md | Select-Object -First 20",
    "Get-Content -Path README.md -TotalCount 20",
])
def test_normal_reads_allowed(repo, command, substrate):
    result = judge(repo, command, substrate)
    assert result.permission_decision == "allow", result.reason
    assert result.exit_code == 0
    assert "structurally_classified_read_only_shell_command" in result.reason


@pytest.mark.parametrize("command", [
    "cat README.md; rm -rf /", "cat README.md&&touch x", "cat README.md\nrm x",
    "cat README.md > output.txt", "cat README.md>>.env", "cat README.md | tee .env",
    "cat $(whoami)", "cat `whoami`", "cat <(whoami)", "cat $FILE",
    "cat README.md &", "cat README.md || evil", "cat README.md |", "cat 'README.md",
    "cat *", "cat ../README.md", "cat ~/README.md", "cat /dev/null",
    "cat docs", "cat missing.md", "cat .env", "cat src/law/README.md", "cat .aeg/log.md",
    "sed -i '1p' README.md", "sed -n '1e touch pwn' README.md",
    "sed -n '1w output' README.md", "sed -f instructions README.md", "sed -n -e '1p' -e '1e evil' README.md",
    "rg -n example README.md",  # no --no-config: env config could inject --pre
    "rg --no-config --pre evil example README.md", "rg --no-config --pre=evil example README.md",
    "rg --no-config -f .env README.md", "rg --no-config --follow example docs",
    "head --unknown README.md", "tail -f README.md",
    "Get-Content README.md | Set-Content output.md",
    "Get-Content README.md | Select-Object -Property {$_.evil()}",
    "Get-Content README.md -OutVariable leaked", "Get-Content $FILE",
    "Get-Content README.md; Remove-Item .env", "Get-Content .env",
    "Get-Content -LiteralPath C:README.md", "Get-Content README.md:stream",
    "Get-Content \\\\server\\share\\README.md", "Get-Content Env:SECRET",
    "Get-Content README.md | Invoke-Expression", "Get-Content README.md | Select-Object -First 2 -Property name",
    "pwsh -Command 'Get-Content README.md'", "bash -c 'cat README.md'",
])
def test_unsafe_or_unproven_reads_not_promoted(repo, command):
    result = judge(repo, command)
    assert result.permission_decision == "deny", result.reason
    assert result.exit_code == 0


def test_native_powershell_pipeline(repo):
    assert judge(repo, "Get-Content README.md | Select-Object -Skip 1 -First 20", tool="PowerShell").permission_decision == "allow"
    assert judge(repo, "Get-Content README.md | Select-Object -First 20 | Invoke-Expression", tool="PowerShell").permission_decision != "allow"


def test_powershell_splat_is_not_a_literal_file(repo):
    (repo / "@args").write_text("fixture", encoding="utf-8")
    assert not classify_shell_read("Get-Content @args", tool_name="Bash").classified
    assert judge(repo, "Get-Content @args").permission_decision == "deny"


def test_absolute_and_outside_paths(repo):
    inside = (repo / "docs" / "guide.md").as_posix()
    outside = (repo.parent / "outside.md").as_posix()
    assert judge(repo, f"cat '{inside}'").permission_decision == "allow"
    assert judge(repo, f"cat '{outside}'").permission_decision == "deny"
    assert judge(repo, f"Get-Content -LiteralPath '{repo / 'docs' / 'guide.md'}' -Raw").permission_decision == "allow"


def test_symlink_to_protected_file_not_allowed(repo):
    link = repo / "innocent.md"
    try:
        link.symlink_to(repo / ".env")
    except OSError:
        pytest.skip("symlinks not supported")
    assert judge(repo, "cat innocent.md").permission_decision == "deny"


@pytest.mark.parametrize("command", ["rm -rf .", "git reset --hard", "echo bad > .env", "cp README.md ../outside.md"])
def test_dangerous_commands_still_denied(repo, command):
    for substrate, code in [("claude-code", 2), ("codex", 0)]:
        result = judge(repo, command, substrate)
        assert result.permission_decision == "deny"
        assert result.exit_code == code


def test_unsupported_tool_still_fails_closed(repo):
    assert judge(repo, "cat README.md", tool="unknown-tool").permission_decision == "deny"


def test_cli_read_records_allow_without_raw_command(repo):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONIOENCODING="utf-8")
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat README.md"}, "tool_use_id": "smoke"}
    result = subprocess.run([sys.executable, "-m", "src.cli", "hook-run", "--substrate", "codex"], input=json.dumps(payload), text=True, encoding="utf-8", cwd=repo, env=env, capture_output=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "allow"
    ledger = (repo / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8")
    assert "cat README.md" not in ledger
    assert json.loads(ledger.splitlines()[-1])["permission_decision"] == "allow"
