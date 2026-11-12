"""0.3.0: wider review tier, read sequences, acceptEdits delegation, allow-once, session check,
shared policy, policy suggestions and ledger archives."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from unittest import mock

import pytest

from jangseung.cli.hook_run import render_hook_response, run_aeg_hook_run
from jangseung.cli.main import main as cli_main


@pytest.fixture
def project(tmp_path):
    for name, text in {
        "README.md": "public\n", "src/app.py": "print(1)\n", ".env": "DUMMY_ONLY=x\n", "docs/spec.md": "spec\n",
        "notes.txt": "ordinary\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / ".aeg").mkdir()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def payload(root, tool, tool_input, *, mode="default", session="new-0-3-0"):
    data = {"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "session_id": session,
            "cwd": str(root), "hook_event_name": "PreToolUse"}
    if mode is not None:
        data["permission_mode"] = mode
    return json.dumps(data)


def judge(root, tool, tool_input, *, substrate="claude-code", **kwargs):
    return render_hook_response(payload(root, tool, tool_input, **kwargs), repo_root=root, substrate=substrate,
                                working_dir=root)


def bash(root, command, **kwargs):
    return judge(root, "Bash", {"command": command}, **kwargs)


def edit(root, path, **kwargs):
    return judge(root, "Edit", {"file_path": str(root / path), "old_string": "a", "new_string": "b"}, **kwargs)


def run(root, tool, tool_input, *, substrate="claude-code", **kwargs):
    out = io.StringIO()
    code = run_aeg_hook_run(stdin=io.StringIO(payload(root, tool, tool_input, **kwargs)), stdout=out,
                            stderr=io.StringIO(), repo_root=root, substrate=substrate, working_dir=root)
    return code, json.loads(out.getvalue()).get("hookSpecificOutput", {})


# --- A. review tier

@pytest.mark.parametrize("path", [
    ".vscode/tasks.json", ".vscode/settings.json", ".vscode/launch.json", ".devcontainer/devcontainer.json",
    ".devcontainer.json", "justfile", "Taskfile.yml", "tox.ini", "noxfile.py", "pytest.ini", "lefthook.yml",
    "Cargo.toml", "build.rs", "go.mod", "build.gradle", "build.gradle.kts", "pom.xml", "Gemfile", "Rakefile",
    "composer.json", "CMakeLists.txt", "cmake/tools.cmake", "meson.build", "jest.config.js", "vite.config.ts",
    "webpack.config.cjs", "eslint.config.mjs", ".eslintrc.js", "gulpfile.js", "Gruntfile.js", "compose.yaml",
    "docker-compose.yaml", "sitecustomize.py", "src/usercustomize.py", ".yarnrc.yml", "deno.json", "bunfig.toml",
    "netlify.toml", "vercel.json", "sub/pkg/Cargo.toml",
])
def test_files_that_run_code_are_in_the_review_tier(project, path):
    assert edit(project, path).permission_decision == "ask"
    assert edit(project, path, mode="auto").permission_decision == "deny"
    assert edit(project, path, substrate="codex").permission_decision == "deny"


@pytest.mark.parametrize("path", [
    "CLAUDE.md", "sub/CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".windsurfrules",
    ".clinerules", ".claude/commands/x.md", ".claude/agents/y.md", ".claude/skills/z/SKILL.md",
    ".cursor/rules/a.mdc", ".github/copilot-instructions.md", ".github/instructions/x.md", ".gemini/settings.json",
])
def test_agent_instructions_ask_with_their_own_sentence(project, path):
    answer = edit(project, path)
    assert answer.permission_decision == "ask"
    assert "agent_instruction_file_change_needs_user_review" in answer.reason_codes
    reason = json.loads(answer.stdout_json)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "instructions that coding agents load" in reason


@pytest.mark.parametrize("command", ["echo x >> CLAUDE.md", "cp README.md AGENTS.md"])
def test_a_shell_write_to_agent_instructions_gets_the_same_sentence(project, command):
    answer = bash(project, command)
    assert answer.permission_decision == "ask"
    assert "agent_instruction_file_change_needs_user_review" in answer.reason_codes


@pytest.mark.parametrize("path", ["README.md", "docs/notes.md", "src/app.py", "src/config.py", "app.json",
                                  "tsconfig.json", ".vscode/extensions.json", "tasks.py"])
def test_ordinary_files_stay_editable(project, path):
    assert edit(project, path).permission_decision == "allow"


def test_a_person_can_open_a_review_file_or_instructions(project):
    (project / ".aeg/policy.json").write_text(json.dumps({"allow_paths": ["CLAUDE.md", "justfile"]}), encoding="utf-8")
    assert edit(project, "CLAUDE.md").permission_decision == "allow"
    assert edit(project, "justfile").permission_decision == "allow"
    assert edit(project, "AGENTS.md").permission_decision == "ask"


# --- B. sequences of read commands and status commands

@pytest.mark.parametrize("command", [
    "ls -la; pwd", "cd src && ls", "cd src && cat app.py", "cd ./src && head -3 app.py", "cat README.md && pwd",
    "head -2 src/app.py && tail -1 src/app.py", "ls || pwd", "git status; git log --oneline -3",
    "git status && git diff --stat", "ls | wc -l; pwd", "date", "date +%Y-%m-%d",
    "true", "false", "sleep 1", "whoami", "uname -a", "which python", "which -a python node", "command -v git",
    "python --version", "node --version", "java -version", "cd src",
])
def test_reads_and_status_commands_are_allowed_everywhere(project, command, monkeypatch):
    # Where PATH finds each program depends on the machine; that check has its own test.
    monkeypatch.setattr(
        "jangseung.evidence.hook_judgment_engine_alignment._program_lives_outside_project", lambda name, root: True
    )
    assert bash(project, command).permission_decision == "allow"
    assert bash(project, command, substrate="codex").permission_decision == "allow"
    assert bash(project, command, mode="auto").permission_decision == "allow"


@pytest.mark.parametrize("command", [
    "ls; cat .env", "cat README.md && cat .env", "ls || cat .env", "cd src && cat ../.env", "cd src && cd .. && cat .env",
    "pwd; head .env", "git status; cat .aeg/hook_ledger.jsonl",
])
def test_a_secret_anywhere_in_a_sequence_is_denied(project, command):
    assert bash(project, command).permission_decision == "deny"


@pytest.mark.parametrize("command", [
    "cd src; cat app.py",            # ; after cd: the read runs where it started if cd fails
    "cd src || cat app.py",
    "cd src && ls || cat app.py",    # || anywhere once a cd is in the line
    "cd missing && ls",
    "cd .aeg && ls",
    "cd .. && ls",
    "cd src && cd .. && ls",
    "echo 'a; b' && pwd",
    "pwd;",
    "cd - && ls",
    "cd && ls",
    "cd src && ls & pwd",
    "ls && rm notes.txt",
    "mkdir -p out && touch out/x.txt",
    "ls; unknown-tool",
    "ls; echo $HOME",
    "ls\npwd",
    "ls;;pwd",
    "date -s 2020-01-01",
    "hostname evil",
    "sleep 1; curl https://x.example",
    "python -c 1; pwd",
    "which $(cat .env)",
])
def test_other_sequences_and_forms_are_not_allowed(project, command):
    assert bash(project, command).permission_decision in {"ask", "deny"}


def test_cdpath_makes_a_cd_without_dot_slash_unclassified(project, monkeypatch):
    monkeypatch.setenv("CDPATH", str(project.parent))
    assert bash(project, "cd src && ls").permission_decision == "ask"
    assert bash(project, "cd ./src && ls").permission_decision == "allow"


def test_git_output_in_a_sequence_is_rebuilt_without_secrets(project):
    answer = bash(project, "git status && git diff")
    assert answer.permission_decision == "allow"
    rebuilt = answer.updated_input["command"]
    assert rebuilt.startswith("git status && git diff -- ")
    assert ".env" in rebuilt and "exclude" in rebuilt
    answer = bash(project, "cd src && git log -p -1")
    assert answer.updated_input["command"].startswith("cd src && git log -p -1 ")
    assert bash(project, "ls; pwd").updated_input is None


def test_powershell_sequences_still_ask(project):
    assert judge(project, "PowerShell", {"command": "Get-Location; Get-ChildItem"}).permission_decision == "ask"


# --- B/C. execution sequences and acceptEdits go to the host

@pytest.mark.parametrize("command", [
    "git add -A && git commit -m wip", "npm install && npm test", "pytest; ls", "ruff check src && pytest",
    "pytest && cat README.md",
])
@pytest.mark.parametrize("mode", ["default", "acceptEdits"])
def test_execution_sequences_go_to_the_host(project, command, mode):
    answer = bash(project, command, mode=mode)
    assert answer.permission_decision == "host"
    assert json.loads(answer.stdout_json) == {}


@pytest.mark.parametrize("command", [
    "git add -A && git diff",          # the host would print the diff itself
    "cd src && pytest",                # the host would run in another folder than judged
    "pytest && cat .env",
    "pytest; unknown-tool",
    "pytest && rm notes.txt",
    "git add -A && git push",
])
def test_execution_sequences_that_are_not_left_to_the_host(project, command):
    assert bash(project, command).permission_decision in {"ask", "deny"}


@pytest.mark.parametrize("mode", ["auto", "plan", "dontAsk", "bypassPermissions", None, "acceptedits", [], {}])
def test_only_measured_modes_delegate(project, mode):
    assert bash(project, "pytest", mode=mode).permission_decision == "ask"


def test_acceptedits_delegates_execution_but_never_file_commands(project):
    assert bash(project, "pytest", mode="acceptEdits").permission_decision == "host"
    for command in ("rm notes.txt", "mv notes.txt x.txt", "sed -i s/a/b/ notes.txt", "echo x > notes.txt"):
        assert bash(project, command, mode="acceptEdits").permission_decision != "host"


def test_codex_never_delegates(project):
    assert bash(project, "pytest", substrate="codex", mode="acceptEdits").permission_decision == "deny"


# --- D. allow-once

def _grant(project, command, minutes=10, tool="Bash"):
    from jangseung.state.allow_once import grant_once

    return grant_once(command, project, minutes, tool)


def test_allow_once_lets_one_exact_command_through_once(project):
    command = "curl -s https://api.example.com/x"
    assert run(project, "Bash", {"command": command}, substrate="codex")[1]["permissionDecision"] == "deny"
    _grant(project, command)
    _, first = run(project, "Bash", {"command": command}, substrate="codex")
    assert first["permissionDecision"] == "allow"
    _, second = run(project, "Bash", {"command": command}, substrate="codex")
    assert second["permissionDecision"] == "deny"
    _grant(project, command)
    _, other = run(project, "Bash", {"command": command + " "}, substrate="codex")
    assert other["permissionDecision"] == "deny"


def test_allow_once_works_for_claude_code_too_and_is_recorded(project):
    _grant(project, "docker ps")
    code, answer = run(project, "Bash", {"command": "docker ps"}, mode="plan")
    assert answer["permissionDecision"] == "allow"
    ledger = (project / ".aeg/hook_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert "hook_allow_once_approved_command" in json.loads(ledger[-1])["reason_codes"]
    assert "docker ps" not in (project / ".aeg/allow_once.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("command", ["cat .env", "cp .env x.txt", "aeg uninstall --yes", "rm -rf .git",
                                     "echo x > .claude/settings.json", "aeg allow-once 'rm -rf src'"])
def test_allow_once_never_lifts_secret_guard_or_target_rules(project, command):
    _grant(project, command)
    assert run(project, "Bash", {"command": command}, substrate="codex")[1]["permissionDecision"] == "deny"


def test_allow_once_expires(project):
    _grant(project, "docker ps")
    later = datetime.now(timezone.utc) + timedelta(minutes=11)
    with mock.patch("jangseung.state.allow_once._now", return_value=later):
        assert run(project, "Bash", {"command": "docker ps"}, substrate="codex")[1]["permissionDecision"] == "deny"


def test_allow_once_is_held_after_a_secret_naming_write(project):
    from jangseung.state.session_marks import mark_secret_naming_write

    mark_secret_naming_write(project, "held-session", ("run.py",))
    _grant(project, "docker ps")
    _, answer = run(project, "Bash", {"command": "docker ps"}, session="held-session", mode="plan")
    assert answer["permissionDecision"] == "ask"


def test_an_approval_that_cannot_be_spent_is_not_used(project):
    _grant(project, "docker ps")
    with mock.patch("jangseung.cli.hook_run.consume_once", return_value=False):
        assert run(project, "Bash", {"command": "docker ps"}, substrate="codex")[1]["permissionDecision"] == "deny"
    with mock.patch("jangseung.cli.hook_run.consume_once", side_effect=OSError("disk")):
        assert run(project, "Bash", {"command": "docker ps"}, substrate="codex")[1]["permissionDecision"] == "deny"


def test_a_damaged_or_linked_approval_file_approves_nothing(project):
    from jangseung.state.allow_once import approved_once

    path = project / ".aeg/allow_once.json"
    path.write_text("{broken", encoding="utf-8")
    assert not approved_once("docker ps", project)
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    from jangseung.state.allow_once import command_key

    path.write_text(json.dumps({"entries": {command_key("docker ps", "Bash"): future}}), encoding="utf-8")
    assert not approved_once("docker ps", project)  # further away than any grant can be


@pytest.mark.parametrize("command", ["aeg allow-once 'docker ps'", "python -m jangseung allow-once x",
                                     "aeg evidence archive-hooks --yes"])
def test_agents_cannot_grant_or_archive(project, command):
    assert bash(project, command).permission_decision == "deny"
    assert bash(project, "npx aeg allow-once x").permission_decision in {"ask", "deny"}
    assert bash(project, "npx aeg allow-once x").permission_decision != "host"


def test_allow_once_cli(project, capsys):
    assert cli_main(["allow-once", "docker ps", "--project", str(project), "--minutes", "5"]) == 0
    assert "approved once" in capsys.readouterr().out
    assert cli_main(["allow-once", "--status", "--project", str(project)]) == 0
    assert "1 pending" in capsys.readouterr().out
    assert cli_main(["allow-once", "--clear", "--project", str(project)]) == 0
    assert "removed 1" in capsys.readouterr().out
    assert cli_main(["allow-once", "x", "--minutes", "90", "--project", str(project)]) == 2


def test_the_stop_message_offers_allow_once(project):
    reason = json.loads(bash(project, "docker ps", mode="plan").stdout_json)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "aeg allow-once" in reason and "docker ps" not in reason


@pytest.mark.parametrize("preset,command", [("rust", "cargo test"), ("go", "go test"), ("jvm", "mvn test"),
                                            ("dotnet", "dotnet build")])
def test_new_presets(project, preset, command):
    assert cli_main(["policy", "preset", preset, "--project", str(project), "--yes"]) == 0
    assert bash(project, command, substrate="codex").permission_decision == "allow"


# --- E. session check

def _session_check(project, *arguments):
    from jangseung.cli.session_check import run_session_check

    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project)}):
        assert run_session_check(list(arguments), stdin=io.StringIO(json.dumps({"cwd": str(project)})), stdout=out) == 0
    return json.loads(out.getvalue())


def test_session_check_is_silent_when_installed(project):
    from jangseung.cli.install import cmd_install

    assert cmd_install(project, assume_yes=True, output_stream=io.StringIO()) == 0
    assert _session_check(project) == {}


def test_session_check_speaks_when_the_hook_is_gone(project):
    from jangseung.cli.install import cmd_install

    cmd_install(project, assume_yes=True, output_stream=io.StringIO())
    settings = project / ".claude/settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["hooks"].pop("PreToolUse")
    settings.write_text(json.dumps(data), encoding="utf-8")
    message = _session_check(project)["systemMessage"]
    assert message.startswith("Jangseung: protection may be off") and "not registered" in message


def test_session_check_speaks_about_a_broken_policy_and_a_missing_program(project):
    from jangseung.cli.install import cmd_install

    cmd_install(project, assume_yes=True, output_stream=io.StringIO())
    (project / ".aeg/policy.json").write_text("{broken", encoding="utf-8")
    assert "policy is ignored" in _session_check(project)["systemMessage"]
    (project / ".aeg/policy.json").unlink()
    settings = project / ".claude/settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for entry in data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            # Same program name in a folder that does not exist, same arguments.
            if isinstance(hook.get("args"), list):
                hook["command"] = str(project / "gone" / Path(hook["command"]).name)
            else:
                # POSIX installs one shell line.
                argv = shlex.split(hook["command"])
                hook["command"] = shlex.join([str(project / "gone" / Path(argv[0]).name), *argv[1:]])
    settings.write_text(json.dumps(data), encoding="utf-8")
    assert "executable" in _session_check(project)["systemMessage"]


def test_session_check_in_plugin_mode_skips_registration(project):
    assert _session_check(project, "--plugin") == {}


def test_session_check_never_fails_the_session(project):
    from jangseung.cli.entry import main as entry_main

    with mock.patch("jangseung.cli.session_check.run_session_check", side_effect=RuntimeError("x")):
        assert entry_main(["session-check"]) == 0
    with mock.patch("jangseung.cli.session_check.session_problems", side_effect=RuntimeError("x")):
        assert "could not run" in _session_check(project)["systemMessage"]


def test_install_adds_updates_and_uninstall_removes_the_session_check(project):
    from jangseung.cli.install import cmd_install, cmd_uninstall, is_session_check_hook

    assert cmd_install(project, assume_yes=True, output_stream=io.StringIO()) == 0
    settings = project / ".claude/settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    entries = data["hooks"]["SessionStart"]
    assert len(entries) == 1 and is_session_check_hook(entries[0]["hooks"][0])
    data["hooks"]["SessionStart"].append({"hooks": [{"type": "command", "command": "echo mine"}]})
    settings.write_text(json.dumps(data), encoding="utf-8")
    out = io.StringIO()
    assert cmd_install(project, assume_yes=True, output_stream=out) == 0
    assert len(json.loads(settings.read_text(encoding="utf-8"))["hooks"]["SessionStart"]) == 2
    assert cmd_uninstall(project, assume_yes=True, output_stream=io.StringIO()) == 0
    remaining = json.loads(settings.read_text(encoding="utf-8"))["hooks"]
    assert remaining == {"SessionStart": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}


def test_a_hook_that_only_mentions_session_check_is_not_ours():
    from jangseung.cli.install import is_session_check_hook

    for hook in ({"type": "command", "command": "echo session-check"}, {"type": "command", "command": "bash -c session-check"},
                 {"type": "command", "command": "/x/evil", "args": ["session-check"]}, {"type": "x"}, "text"):
        assert not is_session_check_hook(hook)
    assert is_session_check_hook({"type": "command", "command": "/venv/bin/aeg", "args": ["session-check"]})
    assert is_session_check_hook({"type": "command", "command": "/venv/bin/python -I -m jangseung.cli session-check"})


def test_the_plugin_registers_the_session_check():
    data = json.loads((Path(__file__).resolve().parents[1] / "hooks/hooks.json").read_text(encoding="utf-8"))
    command = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "session-check --plugin" in command and "hook-run" not in command


# --- F. shared policy

def test_a_shared_policy_only_adds_protection(project):
    (project / ".jangseung").mkdir()
    (project / ".jangseung/policy.json").write_text(json.dumps({"protect_paths": ["docs/spec.md"]}), encoding="utf-8")
    assert edit(project, "docs/spec.md").permission_decision == "deny"
    assert edit(project, "README.md").permission_decision == "allow"
    assert bash(project, "pytest").permission_decision == "host"


@pytest.mark.parametrize("content", [
    json.dumps({"allow_paths": [".env"]}), json.dumps({"allow_commands": ["curl"]}),
    json.dumps({"protect_paths": "x"}), "{broken", json.dumps([]),
])
def test_a_shared_policy_that_tries_to_open_anything_makes_the_hook_stricter(project, content):
    (project / ".jangseung").mkdir()
    (project / ".jangseung/policy.json").write_text(content, encoding="utf-8")
    assert bash(project, "pytest").permission_decision == "ask"       # no host delegation
    assert bash(project, "cat .env").permission_decision == "deny"
    assert bash(project, "curl https://x.example").permission_decision == "deny"
    assert bash(project, "touch new.txt").permission_decision != "allow"


@pytest.mark.parametrize("tool,tool_input", [
    ("Write", {"file_path": ".jangseung/policy.json", "content": "{}"}),
    ("Bash", {"command": "rm .jangseung/policy.json"}),
    ("Bash", {"command": "echo {} > .jangseung/policy.json"}),
    ("PowerShell", {"command": "Remove-Item -LiteralPath .jangseung/policy.json"}),
])
def test_agents_cannot_change_the_shared_policy(project, tool, tool_input):
    if "file_path" in tool_input:
        tool_input = {**tool_input, "file_path": str(project / tool_input["file_path"])}
    assert judge(project, tool, tool_input).permission_decision == "deny"


def test_policy_add_shared_cli(project, capsys):
    assert cli_main(["policy", "add", "--shared", "--protect", "docs/spec.md", "--project", str(project), "--yes"]) == 0
    assert json.loads((project / ".jangseung/policy.json").read_text(encoding="utf-8")) == {"protect_paths": ["docs/spec.md"]}
    assert cli_main(["policy", "show", "--project", str(project)]) == 0
    assert "shared (committed)" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli_main(["policy", "add", "--shared", "--command", "pytest", "--project", str(project), "--yes"])


# --- G. suggestions and archives

def _record(project, command, times):
    for _ in range(times):
        run(project, "Bash", {"command": command}, mode="plan")


def test_policy_suggest_names_safe_prefixes_only(project, capsys):
    _record(project, "ruff check src", 4)
    _record(project, "terraform plan", 5)
    _record(project, "python x.py", 5)
    _record(project, "docker ps", 5)
    _record(project, "mypy src", 1)
    assert cli_main(["policy", "suggest", "--project", str(project)]) == 0
    out = capsys.readouterr().out
    assert 'aeg policy add --command "ruff"' in out
    for word in ("terraform", "python", "docker", "mypy"):
        assert f'"{word}"' not in out
    assert not (project / ".aeg/policy.json").exists()


def test_archive_moves_the_ledger_and_starts_a_linked_chain(project):
    from jangseung.state.hook_ledger import archive_hook_ledger, verify_hook_ledger

    _record(project, "docker ps", 3)
    before = (project / ".aeg/hook_ledger.jsonl").read_bytes()
    result = archive_hook_ledger(project)
    assert result.archived_records == 3 and Path(result.archive_path).read_bytes() == before
    verification = verify_hook_ledger(project)
    assert verification.ok and len(verification.records) == 1
    codes = verification.records[0]["reason_codes"]
    assert "hook_ledger_archived" in codes and any(code.startswith("archived_sha256:") for code in codes)
    _record(project, "docker ps", 1)
    assert verify_hook_ledger(project).ok


def test_archive_refuses_a_damaged_ledger(project):
    from jangseung.state.hook_ledger import archive_hook_ledger

    _record(project, "docker ps", 2)
    ledger = project / ".aeg/hook_ledger.jsonl"
    ledger.write_bytes(ledger.read_bytes() + b"{not json}\n")
    with pytest.raises(ValueError):
        archive_hook_ledger(project)
    assert not (project / ".aeg/archive").exists()


def test_the_hook_path_still_skips_heavy_modules():
    code = ("import sys\nbefore = set(sys.modules)\nimport jangseung.cli.hook_run\n"
            "print(sorted({'argparse', 'tempfile', 'shutil'} & (set(sys.modules) - before)))\n")
    root = Path(__file__).resolve().parents[1]
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env=dict(os.environ, PYTHONPATH=str(root)), cwd=root, check=True)
    assert done.stdout.strip() == "[]"


def test_a_status_program_found_inside_the_project_is_not_run_unasked(project, monkeypatch, tmp_path_factory):
    from jangseung.evidence.hook_judgment_engine_alignment import _program_lives_outside_project

    outside = tmp_path_factory.mktemp("bin")
    inside = project / ".venv" / "bin"
    inside.mkdir(parents=True)
    suffix = ".exe" if os.name == "nt" else ""
    for folder in (outside, inside):
        program = folder / f"tool{suffix}"
        program.write_bytes(b"#!/bin/sh" + bytes([10]))
        program.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join([str(outside)]))
    assert _program_lives_outside_project("tool", project)
    assert bash(project, "tool --version").permission_decision != "allow"  # not a known program
    monkeypatch.setenv("PATH", os.pathsep.join([str(inside), str(outside)]))
    assert not _program_lives_outside_project("tool", project)
    monkeypatch.setenv("PATH", os.pathsep.join([".", str(outside)]))
    assert not _program_lives_outside_project("tool", project)
    monkeypatch.setenv("PATH", str(outside))
    assert not _program_lives_outside_project("missing-tool", project)
    (inside / f"python{suffix}").write_bytes(b"#!/bin/sh" + bytes([10]))
    (inside / f"python{suffix}").chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join([str(inside), str(outside)]))
    assert bash(project, "python --version").permission_decision == "ask"
    assert bash(project, "true").permission_decision == "allow"  # a shell builtin is not looked up


# --- findings of the independent review of 0.3.0

@pytest.mark.parametrize("command", [
    "pytest -v", "pytest --version", "pytest -V", "python version", "python -V", "node version", "node -v",
    "bash version", "sh version", "perl version", "npm version", "npx version", "npx --version", "make version",
    "make --version", "mypy -v", "ninja -v", "eslint version", "black version", "claude version", "codex version",
    "claude --version", "aeg --version", "ls && pytest -V", "cd src && python version", "go -v", "java version",
])
def test_version_words_that_run_code_are_not_allowed(project, command, monkeypatch):
    monkeypatch.setattr(
        "jangseung.evidence.hook_judgment_engine_alignment._program_lives_outside_project", lambda name, root: True
    )
    for substrate, mode in (("claude-code", "default"), ("claude-code", "auto"), ("codex", "default")):
        assert bash(project, command, substrate=substrate, mode=mode).permission_decision != "allow", (command, mode)


def test_a_written_file_named_version_is_not_run_unasked(project, monkeypatch):
    monkeypatch.setattr(
        "jangseung.evidence.hook_judgment_engine_alignment._program_lives_outside_project", lambda name, root: True
    )
    (project / "version").write_text("print(open('.env').read())" + chr(10), encoding="utf-8")
    assert bash(project, "python version", substrate="codex").permission_decision == "deny"
    assert bash(project, "python version").permission_decision in {"ask", "host"}


@pytest.mark.parametrize("content", [
    json.dumps({"protect_paths": ["config/prod.yml"], "x": 1}), json.dumps({"$schema": "x", "protect_paths": []}),
    json.dumps({"protect_paths": ["config/prod.yml", ""]}), "{broken",
])
def test_a_broken_shared_policy_protects_every_edit(project, content):
    (project / "config").mkdir()
    (project / "config/prod.yml").write_text("x" + chr(10), encoding="utf-8")
    (project / ".jangseung").mkdir()
    (project / ".jangseung/policy.json").write_text(content, encoding="utf-8")
    for substrate in ("claude-code", "codex"):
        assert edit(project, "config/prod.yml", substrate=substrate).permission_decision == "deny"
        assert edit(project, "src/app.py", substrate=substrate).permission_decision == "deny"
        write = judge(project, "Write", {"file_path": str(project / "README.md"), "content": "y"}, substrate=substrate)
        assert write.permission_decision == "deny"


@pytest.mark.parametrize("command", ["cd ' src' && cat app.py", "cd 'src ' && cat app.py", "cd 'src.' && cat app.py",
                                     "cd ' ' && ls", "cd 'src/ ' && ls"])
def test_cd_targets_the_path_rules_would_tidy_are_not_followed(project, command):
    assert bash(project, command).permission_decision != "allow"


def test_allow_once_is_bound_to_the_project_folder_and_the_tool(project):
    _grant(project, "docker ps")
    subfolder = run_in(project, project / "src", "Bash", "docker ps")
    assert subfolder == "deny"
    assert run(project, "PowerShell", {"command": "docker ps"}, substrate="codex")[1]["permissionDecision"] == "deny"
    assert run(project, "Bash", {"command": "docker ps"}, substrate="codex")[1]["permissionDecision"] == "allow"
    _grant(project, "docker ps", tool="PowerShell")
    assert run(project, "PowerShell", {"command": "docker ps"}, mode="plan")[1]["permissionDecision"] == "allow"


def run_in(root, cwd, tool, command):
    out = io.StringIO()
    data = json.dumps({"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "t", "session_id": "s",
                       "cwd": str(cwd), "hook_event_name": "PreToolUse", "permission_mode": "default"})
    run_aeg_hook_run(stdin=io.StringIO(data), stdout=out, stderr=io.StringIO(), repo_root=root, substrate="codex",
                     working_dir=cwd)
    return json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize("command", [
    "yarn --version", "cargo --version", "rustc --version", "rustup --version", "dotnet --version", "go version",
    "poetry --version", "pdm --version", "composer --version", "npm --version", "pnpm --version", "uv --version",
    "pip --version", "gem --version", "php --version", "eslint --version", "tsc --version", "mypy --version",
])
def test_launchers_that_follow_a_project_file_are_not_version_checks(project, command, monkeypatch):
    """yarnPath, rust-toolchain.toml, global.json, toolchain lines and project plugins pick another program."""

    monkeypatch.setattr(
        "jangseung.evidence.hook_judgment_engine_alignment._program_lives_outside_project", lambda name, root: True
    )
    assert bash(project, command, substrate="codex").permission_decision == "deny"
