"""Hook diagnostics inspect only metadata/config and never run or repair hooks."""
from dataclasses import asdict
import hashlib
import io
import json
import os
import subprocess
from unittest.mock import patch

import pytest

from src.cli.hook_doctor import run_hook_doctor
from src.cli.install import cmd_install
from src.cli.main import main
from src.state.doctor import run_doctor, doctor_status
from src.state.hook_ledger import append_hook_decision_record


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "--allow-empty", "-qm", "fixture"], cwd=tmp_path, check=True)
    return tmp_path.resolve()


def snapshot(repo):
    return {str(p.relative_to(repo)): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in repo.rglob("*") if p.is_file()}


def install(repo, target):
    executable = repo / "virtual env" / ("aeg.exe" if os.name == "nt" else "aeg")
    executable.parent.mkdir(exist_ok=True)
    executable.write_text("not an executable program; must never be invoked", encoding="utf-8")
    executable.chmod(0o755)
    with patch("src.cli.install.shutil.which", return_value=str(executable)):
        assert cmd_install(repo, target=target, assume_yes=True, output_stream=io.StringIO()) == 0
    return executable


def checks_by_name(repo, target="codex"):
    return {check.name: check for check in run_hook_doctor(repo, target=target)}


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_installed_hook_checks_are_readonly(repo, target):
    install(repo, target)
    before = snapshot(repo)
    checks = checks_by_name(repo, target)
    assert all(check.status == "PASS" for check in checks.values()), checks
    assert checks[f"{target} hook 1 executable"].status == "PASS"
    assert checks["hook diagnostic scope"].details[0] == ("host_execution", "NOT_CHECKED")
    assert snapshot(repo) == before
    # Install's internal ignore file must not cause doctor's old false failure.
    assert doctor_status(run_doctor(repo)) == "PASS"
    assert snapshot(repo) == before


def test_cli_json_and_default_doctor_are_additive(repo, monkeypatch, capsys):
    install(repo, "codex")
    monkeypatch.chdir(repo)
    before = snapshot(repo)
    assert main(["doctor", "--hooks", "--target", "codex", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PASS"
    assert report["host_execution"] == "NOT_CHECKED"
    assert not report["hook_execution_performed"]
    assert not report["store_write_performed"]
    assert main(["doctor"]) == 0
    assert "hook registration" not in capsys.readouterr().out
    assert snapshot(repo) == before
    with pytest.raises(SystemExit) as error:
        main(["doctor", "--target", "codex"])
    assert error.value.code == 2


def test_missing_setup_is_reported_without_creation(repo):
    before = snapshot(repo)
    checks = checks_by_name(repo)
    assert checks["codex hook config"].status == "WARN"
    assert checks["hook recording directory"].status == "WARN"
    assert snapshot(repo) == before


@pytest.mark.parametrize("target,filename,content", [
    ("codex", ".codex/config.toml", b"broken = [ sk-proj-private-input"),
    ("claude-code", ".claude/settings.json", b'{"secret": sk-proj-private-input'),
    ("codex", ".codex/config.toml", b"\xff"),
    ("claude-code", ".claude/settings.json", b"[]"),
    ("codex", ".codex/config.toml", b"hooks = 'private input'"),
])
def test_invalid_config_is_not_echoed_or_repaired(repo, target, filename, content):
    path = repo / filename
    path.parent.mkdir()
    path.write_bytes(content)
    before = snapshot(repo)
    checks = checks_by_name(repo, target)
    assert checks[f"{target} hook config"].status == "FAIL"
    assert "private" not in json.dumps([asdict(check) for check in checks.values()])
    assert snapshot(repo) == before


def test_missing_executable_fails_without_running_commands(repo):
    executable = install(repo, "codex")
    executable.unlink()
    before = snapshot(repo)
    assert checks_by_name(repo)["codex hook 1 executable"].status == "FAIL"
    assert snapshot(repo) == before


def test_python_module_fallback_is_explicitly_unverified(repo):
    with patch("src.cli.install.shutil.which", return_value=None):
        assert cmd_install(repo, target="claude-code", assume_yes=True, output_stream=io.StringIO()) == 0
    check = checks_by_name(repo, "claude-code")["claude-code hook 1 executable"]
    assert check.status == "WARN"
    assert "NOT_CHECKED" in check.message


def test_wrong_substrate_custom_matcher_and_duplicates(repo):
    path = repo / ".codex" / "config.toml"
    path.parent.mkdir()
    path.write_text('[[hooks.PreToolUse]]\nmatcher="Read"\n[[hooks.PreToolUse.hooks]]\ntype="command"\ncommand="aeg hook-run"\n'
                    '[[hooks.PreToolUse.hooks]]\ntype="command"\ncommand="aeg hook-run"\n', encoding="utf-8")
    checks = checks_by_name(repo)
    assert checks["codex hook registration"].status == "WARN"
    assert checks["codex hook 1 substrate"].status == "FAIL"
    assert checks["codex hook 1 matcher"].status == "WARN"


def test_wrapper_mention_is_not_claimed_as_registered(repo):
    path = repo / ".claude" / "settings.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo 'aeg hook-run secret phrase'"}]}]}}), encoding="utf-8")
    checks = checks_by_name(repo, "claude-code")
    assert checks["claude-code hook registration"].status == "WARN"
    assert "secret phrase" not in str(checks)


@pytest.mark.parametrize("payload,dead,expected", [("123", True, "DEAD"), (str(os.getpid()), False, "ACTIVE_OR_UNKNOWN"), ("", False, None), ("private invalid owner", False, None)])
def test_locks_are_observed_never_acquired_or_recovered(repo, payload, dead, expected):
    install(repo, "codex")
    (repo / ".aeg" / "hook_ledger.lock").write_text(payload, encoding="utf-8")
    (repo / ".aeg" / "hook_ledger.guard").touch()
    before = snapshot(repo)
    with patch("src.cli.hook_doctor._pid_is_dead", return_value=dead), \
         patch("src.state.hook_ledger._exclusive_lock", side_effect=AssertionError("no lock acquisition")):
        checks = checks_by_name(repo)
    assert checks["hook OS guard"].status == "PASS"
    assert checks["hook PID lock"].status == "WARN"
    if expected:
        assert checks["hook PID lock"].details == (("owner_state", expected),)
    assert "private invalid owner" not in str(checks)
    assert snapshot(repo) == before


def test_good_then_damaged_ledger_is_read_only(repo):
    install(repo, "codex")
    append_hook_decision_record(repo, substrate="codex", tool_name="Read", hook_decision="allow",
                                permission_decision="allow", fail_closed=False, reason_codes=["test"], exit_code=0)
    before = snapshot(repo)
    assert checks_by_name(repo)["hook ledger chain"].status == "PASS"
    assert snapshot(repo) == before
    ledger = repo / ".aeg" / "hook_ledger.jsonl"
    ledger.write_bytes(ledger.read_bytes() + b"\xff private secret\n")
    before = snapshot(repo)
    checks = checks_by_name(repo)
    assert checks["hook ledger chain"].status == "FAIL"
    assert "private secret" not in str(checks)
    assert snapshot(repo) == before


def test_unignored_exception_inside_state_is_detected(repo):
    install(repo, "codex")
    (repo / ".aeg" / ".gitignore").write_text("*\n!exposed.txt\n", encoding="utf-8")
    (repo / ".aeg" / "exposed.txt").write_text("fixture", encoding="utf-8")
    assert any(c.name == ".aeg/ git ignored" and c.status == "FAIL" for c in run_doctor(repo))


def test_unignored_future_hook_record_is_detected(repo):
    install(repo, "codex")
    (repo / ".aeg" / ".gitignore").write_text("*\n!hook_ledger.jsonl\n", encoding="utf-8")
    assert not (repo / ".aeg" / "hook_ledger.jsonl").exists()
    assert any(c.name == ".aeg/ git ignored" and c.status == "FAIL" for c in run_doctor(repo))


@pytest.mark.parametrize("target", ["config", "state", "ledger", "guard", "lock"])
def test_linked_files_are_not_followed(repo, target):
    install(repo, "codex")
    outside = repo.parent / "outside-private"
    outside.write_text("private contents must not be read", encoding="utf-8")
    path = {"config": repo / ".codex" / "config.toml", "state": repo / ".aeg-link",
            "ledger": repo / ".aeg" / "hook_ledger.jsonl", "guard": repo / ".aeg" / "hook_ledger.guard",
            "lock": repo / ".aeg" / "hook_ledger.lock"}[target]
    if target == "state":
        # Preserve the fixture's original state while testing a directory link.
        (repo / ".aeg").rename(repo / ".aeg-original")
        path = repo / ".aeg"
    elif path.exists():
        path.unlink()
    try:
        path.symlink_to(repo / ".aeg-original" if target == "state" else outside, target_is_directory=target == "state")
    except OSError:
        pytest.skip("symlinks unavailable")
    checks = checks_by_name(repo)
    assert any(c.status == "FAIL" for c in checks.values())
    assert "private contents" not in str(checks)


@pytest.mark.parametrize("filename,check_name", [
    ("hook_ledger.jsonl", "hook ledger chain"),
    ("hook_ledger.guard", "hook OS guard"),
    ("hook_ledger.lock", "hook PID lock"),
])
def test_directory_instead_of_runtime_file_is_a_failure(repo, filename, check_name):
    install(repo, "codex")
    (repo / ".aeg" / filename).mkdir()
    before = snapshot(repo)
    assert checks_by_name(repo)[check_name].status == "FAIL"
    assert snapshot(repo) == before


def test_large_inputs_are_explicitly_unchecked(repo):
    install(repo, "codex")
    with patch("src.cli.hook_doctor.MAX_CONFIG_BYTES", 1):
        assert checks_by_name(repo)["codex hook config"].status == "WARN"
    (repo / ".aeg" / "hook_ledger.jsonl").write_text("large fixture", encoding="utf-8")
    with patch("src.cli.hook_doctor.MAX_LEDGER_BYTES", 1):
        check = checks_by_name(repo)["hook ledger chain"]
    assert check.status == "WARN" and "NOT_CHECKED" in check.message


def test_valid_config_secrets_are_not_in_json_output(repo, monkeypatch, capsys):
    install(repo, "codex")
    config = repo / ".codex" / "config.toml"
    secret = "sk-proj-PRIVATE-CONFIG-abcdefghijklmnop"
    config.write_text(f'private_value = "{secret}"\n' + config.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["doctor", "--hooks", "--target", "codex", "--json"]) == 0
    assert secret not in capsys.readouterr().out


def test_windows_override_is_used_only_on_windows(repo):
    executable = install(repo, "codex")
    from src.cli.hook_doctor import _executable_check
    import shlex
    valid = (subprocess.list2cmdline((str(executable), "hook-run", "--substrate", "codex"))
             if os.name == "nt" else shlex.join((str(executable), "hook-run", "--substrate", "codex")))
    invalid = "/missing/virtual-environment/aeg hook-run --substrate codex"
    hook = {"command": invalid if os.name == "nt" else valid,
            "command_windows": valid if os.name == "nt" else invalid}
    assert _executable_check("test", hook).status == "PASS"


@pytest.mark.parametrize("as_json", [False, True])
def test_deeply_nested_ledger_is_reported_without_crash_or_writes(repo, monkeypatch, capsys, as_json):
    install(repo, "codex")
    # Small on disk, but beyond the JSON decoder's recursion limit.
    (repo / ".aeg" / "hook_ledger.jsonl").write_text("[" * 1500 + "0" + "]" * 1500 + "\n", encoding="utf-8")
    before = snapshot(repo)
    monkeypatch.chdir(repo)
    args = ["doctor", "--hooks", "--target", "codex", *(["--json"] if as_json else [])]
    assert main(args) == 1
    output = capsys.readouterr().out
    if as_json:
        assert json.loads(output)["status"] == "FAIL"
    else:
        assert "status: FAIL" in output
    assert "[[[[[" not in output
    assert snapshot(repo) == before
