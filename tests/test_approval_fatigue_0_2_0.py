"""Approval fatigue changes must not turn uncertainty or a failed gate into allow."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest import mock

import pytest

from jangseung.cli.explain import build_explanation
from jangseung.cli.hook_run import render_hook_response, run_aeg_hook_run
from jangseung.state.hook_ledger import read_hook_ledger, verify_hook_ledger
from jangseung.state.hook_ledger import compute_hook_record_hash


@pytest.fixture
def project(tmp_path):
    for name, text in {
        "README.md": "public\n", "notes.txt": "ordinary\n", "src/app.py": "print(1)\n",
        ".env": "DUMMY_ONLY=x\n", "package.json": "{}\n", ".github/workflows/ci.yml": "name: dummy\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / ".aeg").mkdir()
    (tmp_path / ".git").mkdir()
    return tmp_path


def payload(root, command, *, mode="default", tool="Bash", session="fatigue-test", cwd=None):
    data = {
        "tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "t",
        "session_id": session, "cwd": str(cwd or root), "hook_event_name": "PreToolUse",
    }
    if mode is not None:
        data["permission_mode"] = mode
    return json.dumps(data)


def result(root, command, **kwargs):
    substrate = kwargs.pop("substrate", "claude-code")
    return render_hook_response(payload(root, command, **kwargs), repo_root=root, substrate=substrate)


@pytest.mark.parametrize("command", [
    "pytest", "python src/app.py", "python -m unittest", "npm install", "npm test", "npx prettier src/app.py",
    "make test", "cargo build", "git pull", "gh pr list", "ruff check src", "go test ./src",
])
@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_default_execution_has_no_hook_permission_decision(project, command, tool):
    answer = result(project, command, tool=tool)
    assert (answer.permission_decision, answer.exit_code, answer.hook_decision) == ("host", 0, "defer")
    assert json.loads(answer.stdout_json) == {}
    assert answer.updated_input is None
    assert "claude_default_host_permission_flow" in answer.reason_codes


@pytest.mark.parametrize("mode", ["acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan", None, "Default", [], {}])
@pytest.mark.parametrize("substrate", ["claude-code", "codex"])
def test_other_modes_and_codex_keep_the_existing_gate(project, mode, substrate):
    answer = result(project, "pytest", mode=mode, substrate=substrate)
    assert answer.permission_decision == ("deny" if substrate == "codex" else "ask")


def test_codex_default_still_denies(project):
    answer = result(project, "pytest", substrate="codex")
    assert answer.permission_decision == "deny"
    assert answer.exit_code == 0


@pytest.mark.parametrize("command", [
    "grep -rn x .", "rg x", "find .", "sed -i s/x/y/ notes.txt", "git grep x",
    "git log --follow -p README.md", "git diff src .", "cd src && ls",
    "unknown-reader README.md", "bash src/app.py", "env pytest", "python -c 'print(1)'",
    "pytest && cat .env", "pytest | cat", "pytest > notes.txt", "pytest $(cat .env)",
    "pytest\ncat .env", "pytest *.py", "python -m src.cli uninstall", "aeg policy add --command pytest",
    "python -m jangseung.cli policy add --command pytest", "npm publish", "git push --force",
])
def test_reads_wrappers_complex_syntax_and_danger_never_delegate(project, command):
    assert result(project, command).permission_decision in {"ask", "deny"}


@pytest.mark.parametrize("command", [
    "pytest .env", "python ../outside.py", "npm --prefix ../outside test",
    "npm --prefix=../outside test", "pytest .aeg/data", "python .github/workflows/ci.yml",
])
def test_literal_protected_and_outside_paths_never_delegate(project, command):
    assert result(project, command).permission_decision in {"ask", "deny"}


def test_external_working_directory_never_delegates(project, tmp_path):
    outside = tmp_path.parent
    assert result(project, "pytest", cwd=outside).permission_decision != "host"


def test_unprotected_git_directory_never_delegates(project):
    (project / ".git").rmdir()
    assert result(project, "git pull").permission_decision == "ask"


def test_session_warning_also_holds_host_approval(project):
    write = json.dumps({
        "tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "open('.env')"},
        "tool_use_id": "w", "session_id": "fatigue-test", "permission_mode": "default",
    })
    assert run_aeg_hook_run(stdin=io.StringIO(write), stdout=io.StringIO(), stderr=io.StringIO(), repo_root=project) == 0
    assert result(project, "pytest").permission_decision == "ask"
    assert result(project, "pytest", session="different-session").permission_decision == "host"
    assert result(project, "cat README.md").permission_decision == "allow"


def test_corrupt_policy_or_session_marks_never_delegate(project):
    (project / ".aeg/session_marks.json").write_text("{broken", encoding="utf-8")
    assert result(project, "pytest").permission_decision != "host"
    (project / ".aeg/session_marks.json").unlink()
    (project / ".aeg/policy.json").write_text("{broken", encoding="utf-8")
    assert result(project, "pytest").permission_decision != "host"


def test_host_result_is_recorded_without_claiming_allow(project):
    stdout = io.StringIO()
    assert run_aeg_hook_run(stdin=io.StringIO(payload(project, "pytest")), stdout=stdout, stderr=io.StringIO(), repo_root=project) == 0
    assert json.loads(stdout.getvalue()) == {}
    record = json.loads((project / ".aeg/hook_ledger.jsonl").read_text(encoding="utf-8"))
    assert record["record_version"] == "hook_decision_record_v2"
    assert record["permission_decision"] == "host"
    assert record["hook_decision"] == "defer"
    assert record["commands"] == ["pytest"]
    assert verify_hook_ledger(project).ok
    assert read_hook_ledger(project)[0].to_summary()["decision"] == "HOST"


def test_recording_failure_does_not_allow_or_force_a_prompt(project):
    stdout = io.StringIO()
    with mock.patch("jangseung.cli.hook_run.append_hook_decision_record", side_effect=OSError("unavailable")):
        code = run_aeg_hook_run(stdin=io.StringIO(payload(project, "pytest")), stdout=stdout, stderr=io.StringIO(), repo_root=project)
    response = json.loads(stdout.getvalue())
    assert code == 0
    assert "hookSpecificOutput" not in response
    assert "hook_decision_recording_failed" in response["systemMessage"]


def test_internal_failure_still_denies(project):
    with mock.patch("jangseung.cli.hook_run.judge_pretooluse_with_aeg_engine", side_effect=RuntimeError("failure")):
        answer = result(project, "pytest")
    assert (answer.permission_decision, answer.fail_closed) == ("deny", True)


def test_explain_distinguishes_host_from_safe_allow(project):
    answer = build_explanation(payload(project, "pytest"), repo_root=project)
    assert answer["category"] == "host_permission_flow"
    assert answer["permission_decision"] == "host"
    assert answer["host_execution"] == "NOT_CHECKED"
    assert not answer["reason_details_redacted"]


@pytest.mark.parametrize("command", [
    "mkdir -p docs/new", "mkdir docs", "touch new.txt", "touch one.txt two.txt",
    "cp README.md copy.md", "mv notes.txt moved.txt", "rm notes.txt",
    "echo hello > new.txt", "echo 'hello world' >> notes.txt",
])
@pytest.mark.parametrize("substrate", ["claude-code", "codex"])
@pytest.mark.parametrize("mode", ["default", "auto", None])
def test_simple_file_operations_allow(project, command, substrate, mode):
    answer = result(project, command, substrate=substrate, mode=mode)
    assert (answer.permission_decision, answer.exit_code) == ("allow", 0)
    assert "structurally_classified_simple_file_operation" in answer.reason_codes


@pytest.mark.parametrize("command", [
    "Copy-Item -LiteralPath README.md -Destination copy.md",
    "Move-Item -LiteralPath notes.txt -Destination moved.txt",
    "Remove-Item -LiteralPath notes.txt", "Write-Output hello > new.txt",
])
def test_native_powershell_file_operations(project, command):
    assert result(project, command, tool="PowerShell").permission_decision == "allow"


@pytest.mark.parametrize("command", [
    "cp .env copy.txt", "mv .env notes.txt", "rm .env", "echo hello > .env", "touch .aeg/new",
    "cp README.md .git/config", "mv notes.txt ../outside.txt", "cp ../outside.txt copied.txt",
    "rm -rf src", "rm src", "mv src moved", "cp -r src copied", "cp README.md src",
    "touch *.txt", "touch ~/new.txt", "touch C:relative.txt", "touch NUL", "touch new.txt.",
    "touch new.txt; cat .env", "echo $(cat .env) > new.txt", "echo x>new.txt", "echo -e x > new.txt",
    "touch new.txt && pytest", "rm notes.txt README.md", "sed -i s/a/b/ notes.txt",
])
def test_unsupported_or_protected_operations_never_auto_allow(project, command):
    assert result(project, command).permission_decision in {"ask", "deny"}


@pytest.mark.parametrize("command", ["touch package.json", "mv notes.txt package.json", "echo x > package.json"])
def test_review_targets_still_ask_or_deny(project, command):
    assert result(project, command).permission_decision == "ask"
    assert result(project, command, mode="auto").permission_decision == "deny"
    assert result(project, command, substrate="codex").permission_decision == "deny"


def test_project_protection_cannot_be_overridden_by_simple_grammar(project):
    (project / ".aeg/policy.json").write_text(json.dumps({"protect_paths": ["notes.txt"]}), encoding="utf-8")
    assert result(project, "rm notes.txt").permission_decision == "deny"


def test_file_links_never_auto_allow(project):
    alias = project / "alias.txt"
    try:
        os.link(project / "notes.txt", alias)
    except OSError as error:
        pytest.skip(f"hard links unavailable: {type(error).__name__}")
    for command in ("echo x > alias.txt", "cp README.md alias.txt", "mv alias.txt moved.txt", "rm alias.txt"):
        assert result(project, command).permission_decision in {"ask", "deny"}


def test_symlink_parent_never_auto_allows(project):
    link = project / "linked"
    try:
        link.symlink_to(project / "src", target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {type(error).__name__}")
    assert result(project, "touch linked/new.txt").permission_decision in {"ask", "deny"}


@pytest.mark.parametrize("operator", [";", "&&", "||", "|", "&", "\n", "\r", "\x00", "\x0c", "\u00a0", "\u2003"])
@pytest.mark.parametrize("prefix", ["pytest", "touch new.txt"])
def test_operator_and_word_boundary_differentials_do_not_gain_permission(project, operator, prefix):
    answer = result(project, prefix + operator + "cat README.md")
    assert answer.permission_decision in {"ask", "deny"}


@pytest.mark.parametrize("command", [
    "pytest safe,../outside", "pytest 'a'foo", 'pytest "a"foo', "pytest x`ny", "pytest %PATH%",
    "touch -- new.txt", "cp -- README.md copied.md", "rm -- notes.txt",
    "uv run aeg policy add --command pytest", "npx aeg policy add --command pytest",
    "python -Im jangseung.cli policy add --command pytest",
    "python -m runpy jangseung.cli policy add --command pytest",
    "pip uninstall jangseung", "python -m pip uninstall jangseung",
])
def test_cross_shell_and_guard_control_forms_never_delegate_or_allow(project, command):
    for tool in ("Bash", "PowerShell"):
        assert result(project, command, tool=tool).permission_decision in {"ask", "deny"}


def test_v1_v2_v1_chain_remains_verifiable(project):
    for command in ("cat README.md", "pytest", "touch new.txt"):
        run_aeg_hook_run(stdin=io.StringIO(payload(project, command)), stdout=io.StringIO(), stderr=io.StringIO(), repo_root=project)
    checked = verify_hook_ledger(project)
    assert checked.ok, checked.errors
    assert [record["record_version"] for record in checked.records] == [
        "hook_decision_record_v1", "hook_decision_record_v2", "hook_decision_record_v1",
    ]


@pytest.mark.parametrize("field,value", [
    ("substrate", "codex"), ("permission_decision", "allow"), ("tool_name", "Read"),
    ("hook_decision", "allow"), ("fail_closed", True), ("exit_code", 2), ("reason_codes", []),
])
def test_host_record_semantics_are_verified_even_with_a_recomputed_hash(project, field, value):
    run_aeg_hook_run(stdin=io.StringIO(payload(project, "pytest")), stdout=io.StringIO(), stderr=io.StringIO(), repo_root=project)
    ledger = project / ".aeg/hook_ledger.jsonl"
    record = json.loads(ledger.read_text(encoding="utf-8"))
    record[field] = value
    record["record_hash"] = compute_hook_record_hash(record)
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")
    assert not verify_hook_ledger(project).ok


def test_explain_cli_mode_is_explicit_and_does_not_record(project):
    import sys

    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    checked = subprocess.run(
        [sys.executable, "-m", "jangseung.cli", "explain", "--command", "pytest", "--permission-mode", "default", "--json"],
        cwd=project, env=env, capture_output=True, text=True, check=True,
    )
    answer = json.loads(checked.stdout)
    assert answer["permission_decision"] == "host"
    assert not (project / ".aeg/hook_ledger.jsonl").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction check")
def test_windows_junction_parent_is_not_auto_allowed(project):
    link = project / "linked"
    created = subprocess.run(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "mklink", "/J", str(link), str(project / "src")],
        capture_output=True, text=True,
    )
    if created.returncode:
        pytest.skip("junction creation is unavailable")
    try:
        assert result(project, "touch linked/new.txt").permission_decision in {"ask", "deny"}
    finally:
        # Remove just this fixture's junction, never its target directory.
        link.rmdir()


_FILE_COMMANDS = [
    ("mkdir fresh", "fresh", "directory"),
    ("mkdir -p docs/new", "docs/new", "directory"),
    ("cp README.md copy.md", "copy.md", "public"),
    ("mv notes.txt moved.txt", "moved.txt", "ordinary"),
    ("rm notes.txt", "notes.txt", "absent"),
    ("echo hello > new.txt", "new.txt", "hello"),
    ("echo 'hello world' >> notes.txt", "notes.txt", "hello world"),
]


@pytest.fixture(scope="module", params=["Bash", "PowerShell"])
def real_shell(request):
    if request.param == "Bash":
        candidates = [shutil.which("bash")]
        if os.name == "nt":
            candidates.insert(0, r"C:\Program Files\Git\bin\bash.exe")
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                probe = subprocess.run([candidate, "-c", "printf ok"], capture_output=True, timeout=30)
                if probe.returncode == 0 and probe.stdout == b"ok":
                    return "Bash", [candidate, "--noprofile", "--norc", "-c"]
    else:
        candidate = shutil.which("pwsh") or shutil.which("powershell")
        if candidate:
            return "PowerShell", [candidate, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command"]
    pytest.skip(f"{request.param} is not installed")


@pytest.mark.parametrize("command,target,expected", _FILE_COMMANDS)
def test_allowed_file_grammar_matches_real_shell_effects(project, real_shell, command, target, expected):
    tool, shell = real_shell
    protected = {path: (project / path).read_bytes() for path in (".env", ".github/workflows/ci.yml", "package.json")}
    assert result(project, command, tool=tool).permission_decision == "allow"
    # Only the explicit fixture commands above run, with the temporary project
    # as cwd. There is no recursive removal, dynamic command, or real secret.
    completed = subprocess.run([*shell, command], cwd=project, capture_output=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    destination = project / target
    if expected == "directory":
        assert destination.is_dir()
    elif expected == "absent":
        assert not destination.exists()
    else:
        data = destination.read_bytes()
        # Windows PowerShell 5 redirects in UTF-16; PowerShell 7 and Bash use
        # UTF-8 here. The encoding difference is not a permission difference.
        assert expected.encode("utf-8") in data or expected.encode("utf-16-le") in data
    if command.startswith("mv "):
        assert not (project / "notes.txt").exists()
    assert {path: (project / path).read_bytes() for path in protected} == protected
