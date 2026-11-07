"""0.1.9: opt-in MCP protection.

``aeg install --mcp`` adds a second, separate hook entry. Through it, MCP tool
calls and MCP resource reads need a person's approval (deny on Codex) unless
``.aeg/policy.json`` lists the exact tool in ``allow_mcp_tools``. Arguments are
never inspected. A plain install stays exactly as before.
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import tomlkit

from jangseung.classify.hook_policy import load_hook_policy
from jangseung.cli.explain import build_explanation
from jangseung.cli.hook_doctor import run_hook_doctor
from jangseung.cli.hook_run import render_hook_response, run_aeg_hook_run, run_hook_cli
from jangseung.cli.install import (
    AEGIS_HOOK_MATCHER,
    CLAUDE_CODE_MCP_HOOK_MATCHER,
    CODEX_AEGIS_HOOK_MATCHER,
    CODEX_MCP_HOOK_MATCHER,
    HOOK_KIND_MAIN,
    HOOK_KIND_MCP,
    _managed_hook_kind,
    build_installed_codex_config_text,
    build_uninstalled_codex_config_text,
    claude_code_hook_matcher,
    cmd_install,
    cmd_uninstall,
)
from jangseung.cli.main import main
from jangseung.evidence.claude_code_pretooluse_input_contract import is_mcp_tool_name

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET = "dummy-marker-7f3a"


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".aeg").mkdir()
    return tmp_path.resolve()


def payload(tool_name, tool_input=None, **extra):
    data = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"path": ".env"} if tool_input is None else tool_input,
        "tool_use_id": "toolu_mcp",
        **extra,
    }
    return json.dumps(data)


def judge(repo, tool_name, tool_input=None, substrate=None, **extra):
    return render_hook_response(payload(tool_name, tool_input, **extra), repo_root=repo, substrate=substrate)


def write_policy(repo, **lists):
    (repo / ".aeg" / "policy.json").write_text(json.dumps(lists), encoding="utf-8")


def fake_aeg(repo):
    executable = repo / "virtual env" / ("aeg.exe" if os.name == "nt" else "aeg")
    executable.parent.mkdir(exist_ok=True)
    executable.write_text("not an executable program; must never be invoked", encoding="utf-8")
    executable.chmod(0o755)
    return patch("jangseung.cli.install.shutil.which", return_value=str(executable))


def install(repo, **kwargs):
    with fake_aeg(repo):
        output = io.StringIO()
        assert cmd_install(repo, assume_yes=True, output_stream=output, **kwargs) == 0
    return output.getvalue()


def uninstall(repo, **kwargs):
    output = io.StringIO()
    assert cmd_uninstall(repo, assume_yes=True, output_stream=output, **kwargs) == 0
    return output.getvalue()


def claude_entries(repo):
    return json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]


def codex_text(repo):
    return (repo / ".codex" / "config.toml").read_text(encoding="utf-8")


def codex_entries(repo):
    return tomlkit.parse(codex_text(repo)).unwrap()["hooks"]["PreToolUse"]


def kinds(entries):
    return [(entry["matcher"], _managed_hook_kind(entry["hooks"][0])) for entry in entries]


# --- judgment -----------------------------------------------------------------


@pytest.mark.parametrize("tool_name", ["mcp__probe__read_file", "mcp__node_repl__js", "mcp__a__b__c", "mcp__x-y__z"])
def test_mcp_tool_asks_on_claude_code_and_denies_on_codex(repo, tool_name):
    claude = judge(repo, tool_name)
    assert (claude.permission_decision, claude.exit_code, claude.fail_closed) == ("ask", 0, False)
    assert claude.reason_codes == ("mcp_tool_requires_user_approval",)
    assert claude.tool_name == tool_name
    codex = judge(repo, tool_name, substrate="codex")
    assert (codex.permission_decision, codex.exit_code, codex.fail_closed) == ("deny", 0, False)
    assert codex.reason_codes == ("mcp_tool_requires_user_approval", "codex_substrate_ask_not_enforced_upgraded_to_deny")


@pytest.mark.parametrize("tool_name", ["ReadMcpResourceTool", "read_mcp_resource"])
@pytest.mark.parametrize("substrate,decision", [(None, "ask"), ("codex", "deny")])
def test_resource_reads_need_approval_on_either_host_name(repo, tool_name, substrate, decision):
    result = judge(repo, tool_name, {"server": "probe", "uri": "probe://env"}, substrate=substrate)
    assert result.permission_decision == decision
    assert result.reason_codes[0] == "mcp_resource_read_requires_user_approval"
    assert not result.fail_closed


def test_arguments_never_change_the_decision(repo):
    inputs = ({"path": ".env"}, {"path": "README.md"}, {}, {"code": "require('fs').readFileSync('.e'+'nv')"},
              {"command": "cat .env"}, {"nested": {"deep": [1, 2, {"x": SECRET}]}})
    assert {judge(repo, "mcp__probe__read_file", value).permission_decision for value in inputs} == {"ask"}
    write_policy(repo, allow_mcp_tools=["mcp__probe__read_file"])
    assert {judge(repo, "mcp__probe__read_file", value).permission_decision for value in inputs} == {"allow"}


def test_listed_tool_is_allowed_on_both_hosts(repo):
    write_policy(repo, allow_mcp_tools=["mcp__probe__echo"])
    claude = judge(repo, "mcp__probe__echo", {"text": "hi"})
    codex = judge(repo, "mcp__probe__echo", {"text": "hi"}, substrate="codex")
    assert (claude.permission_decision, claude.exit_code) == ("allow", 0)
    assert (codex.permission_decision, codex.exit_code) == ("allow", 0)
    assert claude.reason_codes == codex.reason_codes == ("mcp_tool_approved_by_project_policy",)
    # Exact names only: another tool of the same server, or a longer name, still asks.
    for other in ("mcp__probe__echo2", "mcp__probe__read_file", "mcp__probe__echo__x", "mcp__probe"):
        assert judge(repo, other).permission_decision == "ask", other


@pytest.mark.parametrize("entries", [
    ["mcp__probe__*"], ["mcp__probe"], ["mcp__"], ["ReadMcpResourceTool"], ["read_mcp_resource"],
    ["Read"], ["mcp__probe__read file"], ["mcp__probe__read_file;x"], [""], [" mcp__probe__echo"],
])
def test_a_bad_entry_voids_the_whole_policy(repo, entries):
    write_policy(repo, allow_mcp_tools=entries, allow_commands=["pytest"])
    policy = load_hook_policy(repo)
    assert policy.error is not None
    assert policy.allow_mcp_tools == frozenset()
    assert policy.allow_commands == ()
    assert judge(repo, "mcp__probe__echo").permission_decision == "ask"
    assert judge(repo, "ReadMcpResourceTool", {"server": "probe", "uri": "probe://env"}).permission_decision == "ask"


@pytest.mark.parametrize("value", ["mcp__probe__echo", {"mcp__probe__echo": True}, [1], [None]])
def test_allow_mcp_tools_must_be_a_list_of_strings(repo, value):
    write_policy(repo, allow_mcp_tools=value)
    assert load_hook_policy(repo).error == "policy_allow_mcp_tools_must_be_a_list_of_strings"


def test_older_policy_files_still_load(repo):
    write_policy(repo, allow_commands=["pytest"])
    policy = load_hook_policy(repo)
    assert policy.error is None
    assert policy.allow_mcp_tools == frozenset()


@pytest.mark.parametrize("tool_name", [
    "mcp__", "mcp__bad name", "MCP__probe__x", "mcp__probe__x\n", "mcp__é__x", "mcp__" + "a" * 251,
    "readMcpResourceTool", "ListMcpResourcesTool", "WebFetch",
])
def test_names_outside_the_host_naming_rules_fail_closed(repo, tool_name):
    result = judge(repo, tool_name)
    assert result.permission_decision == "deny"
    assert result.fail_closed
    assert not is_mcp_tool_name(tool_name)


def test_the_other_input_fields_are_still_required(repo):
    for raw in ('{"tool_name":"mcp__probe__x","tool_input":{}}',
                '{"tool_name":"mcp__probe__x","tool_input":[],"tool_use_id":"t"}',
                '{"tool_name":"mcp__probe__x","tool_input":{},"tool_use_id":""}'):
        result = render_hook_response(raw, repo_root=repo)
        assert (result.permission_decision, result.fail_closed, result.exit_code) == ("deny", True, 2)


def test_host_metadata_does_not_change_the_decision(repo):
    for extra in ({"mcp_server": {"name": "probe", "source": "project"}}, {"permission_mode": "bypassPermissions"},
                  {"permission_mode": "auto", "cwd": str(repo)}):
        assert judge(repo, "mcp__probe__read_file", **extra).permission_decision == "ask"


def test_existing_tools_keep_their_decisions(repo):
    (repo / "README.md").write_text("hello", encoding="utf-8")
    assert judge(repo, "Read", {"file_path": ".env"}).permission_decision == "deny"
    assert judge(repo, "Read", {"file_path": "README.md"}).permission_decision == "allow"
    write_policy(repo, allow_mcp_tools=["mcp__probe__echo"])
    assert judge(repo, "Read", {"file_path": ".env"}).permission_decision == "deny"


def test_ledger_records_the_tool_name_and_decision_only(repo):
    for substrate in (None, "codex"):
        stdout = io.StringIO()
        run_aeg_hook_run(stdin=io.StringIO(payload("mcp__probe__read_file", {"path": ".env", "note": SECRET})),
                         stdout=stdout, stderr=io.StringIO(), repo_root=repo, substrate=substrate)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        assert decision["permissionDecision"] == ("deny" if substrate else "ask")
        assert "updatedInput" not in decision
    ledger = (repo / ".aeg" / "hook_ledger.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in ledger.splitlines()]
    assert [(r["tool_name"], r["permission_decision"]) for r in records] == [
        ("mcp__probe__read_file", "ask"), ("mcp__probe__read_file", "deny"),
    ]
    assert SECRET not in ledger and ".env" not in ledger


def test_explain_reports_the_mcp_rule(repo):
    report = build_explanation(payload("mcp__probe__read_file"), repo_root=repo)
    assert report["category"] == "mcp_approval_required"
    assert report["tool_name"] == "mcp__probe__read_file"
    assert report["reason_codes"] == ["mcp_tool_requires_user_approval"]
    report = build_explanation(payload("read_mcp_resource", {"server": "p", "uri": "p://x"}), repo_root=repo,
                               substrate="codex")
    assert report["permission_decision"] == "deny"
    assert report["reason_codes"] == ["mcp_resource_read_requires_user_approval",
                                      "codex_substrate_ask_not_enforced_upgraded_to_deny"]


@pytest.mark.parametrize("args", [["--mcp"], ["--substrate", "codex", "--mcp"], ["--mcp", "--substrate", "codex"]])
def test_hook_run_accepts_the_mcp_marker(args):
    with patch("jangseung.cli.hook_run.run_aeg_hook_run_from_process", return_value=0) as run:
        assert run_hook_cli(args) == 0
    assert run.call_args.kwargs["substrate"] == ("codex" if "codex" in args else None)


@pytest.mark.parametrize("extra,code,decision", [
    (["--mcp"], 0, "ask"), (["--substrate", "codex", "--mcp"], 0, "deny"), ([], 0, "ask"),
])
def test_real_process_judges_mcp_calls(tmp_path, extra, code, decision):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    proc = subprocess.run([sys.executable, "-I", "-m", "jangseung.cli", "hook-run", *extra],
                          input=payload("mcp__probe__read_file"), capture_output=True, text=True, cwd=tmp_path, env=env)
    if proc.returncode != code and "No module named" in proc.stderr:
        pytest.skip("isolated mode cannot import the package from PYTHONPATH")
    assert proc.returncode == code
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == decision


# --- install, uninstall, doctor: Claude Code -----------------------------------


def test_plain_install_is_unchanged(repo):
    install(repo)
    assert kinds(claude_entries(repo)) == [(claude_code_hook_matcher(), HOOK_KIND_MAIN)]


def test_install_mcp_adds_a_separate_entry(repo):
    output = install(repo, mcp=True)
    entries = claude_entries(repo)
    assert kinds(entries) == [(claude_code_hook_matcher(), HOOK_KIND_MAIN),
                              (CLAUDE_CODE_MCP_HOOK_MATCHER, HOOK_KIND_MCP)]
    hook = entries[1]["hooks"][0]
    assert hook["onFailure"] == "block"
    assert (hook.get("args") or [hook["command"]])[-1].endswith("--mcp")
    assert "MCP matcher:  ^(mcp__.*|ReadMcpResourceTool)$" in output
    assert "allow_mcp_tools" in output
    before = (repo / ".claude" / "settings.json").read_bytes()
    install(repo, mcp=True)
    install(repo)  # a plain reinstall keeps the opt-in
    assert (repo / ".claude" / "settings.json").read_bytes() == before


def test_install_mcp_on_an_existing_install_keeps_the_main_entry(repo):
    install(repo)
    main_entry = claude_entries(repo)[0]
    install(repo, mcp=True)
    assert claude_entries(repo)[0] == main_entry


def test_plain_install_repairs_a_stale_mcp_entry(repo):
    install(repo, mcp=True)
    settings = repo / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["hooks"]["PreToolUse"][1]["matcher"] = "mcp__probe__.*"
    data["hooks"]["PreToolUse"][1]["hooks"][0]["onFailure"] = "allow"
    settings.write_text(json.dumps(data), encoding="utf-8")
    install(repo)
    entries = claude_entries(repo)
    assert entries[1]["matcher"] == CLAUDE_CODE_MCP_HOOK_MATCHER
    assert entries[1]["hooks"][0]["onFailure"] == "block"


def test_uninstall_mcp_removes_only_the_mcp_entry(repo):
    install(repo)
    plain = (repo / ".claude" / "settings.json").read_text(encoding="utf-8")
    install(repo, mcp=True)
    output = uninstall(repo, mcp_only=True)
    assert "the main hook is unchanged" in output
    assert json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8")) == json.loads(plain)
    assert "no Aegis MCP hook found" in uninstall(repo, mcp_only=True)
    assert kinds(claude_entries(repo)) == [(claude_code_hook_matcher(), HOOK_KIND_MAIN)]


def test_full_uninstall_removes_both_entries_and_keeps_other_hooks(repo):
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir()
    user_entry = {"matcher": "mcp__.*", "hooks": [{"type": "command", "command": "user-audit --mcp"}]}
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [user_entry]}}), encoding="utf-8")
    install(repo, mcp=True)
    assert len(claude_entries(repo)) == 3
    uninstall(repo)
    assert claude_entries(repo) == [user_entry]


@pytest.mark.parametrize("command", [
    "aeg hook-run --mcp --substrate claude-code", "aeg hook-run --mcp --mcp", "aeg hook-run --mcp extra",
    "user-wrapper aeg hook-run --mcp", "sh -c 'aeg hook-run --mcp'",
])
def test_other_command_shapes_are_not_ours(command):
    assert _managed_hook_kind({"type": "command", "command": command}) is None


def test_mixed_command_forms_are_not_ours():
    hook = {"type": "command", "command": "aeg hook-run --substrate codex",
            "command_windows": "aeg.exe hook-run --substrate codex --mcp"}
    assert _managed_hook_kind(hook) is None


def test_doctor_reports_mcp_protection(repo):
    with fake_aeg(repo):
        assert cmd_install(repo, assume_yes=True, output_stream=io.StringIO()) == 0
        checks = {check.name: check for check in run_hook_doctor(repo, target="claude-code")}
        assert checks["claude-code MCP hook registration"].status == "PASS"
        assert "MCP protection is off" in checks["claude-code MCP hook registration"].message
        assert cmd_install(repo, assume_yes=True, mcp=True, output_stream=io.StringIO()) == 0
        checks = {check.name: check for check in run_hook_doctor(repo, target="claude-code")}
    assert all(check.status == "PASS" for check in checks.values()), checks
    assert "MCP protection hook is registered" in checks["claude-code MCP hook registration"].message
    for suffix in ("substrate", "matcher", "failure mode", "executable"):
        assert checks[f"claude-code MCP hook 1 {suffix}"].status == "PASS"
    assert checks["claude-code hook registration"].status == "PASS"
    assert "claude-code hook 2 matcher" not in checks


def test_doctor_warns_on_a_changed_mcp_matcher(repo):
    install(repo, mcp=True)
    settings = repo / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["hooks"]["PreToolUse"][1]["matcher"] = "mcp__probe__.*"
    settings.write_text(json.dumps(data), encoding="utf-8")
    checks = {check.name: check for check in run_hook_doctor(repo, target="claude-code")}
    assert checks["claude-code MCP hook 1 matcher"].status == "WARN"


def test_doctor_counts_the_mcp_policy_list(repo):
    write_policy(repo, allow_mcp_tools=["mcp__probe__echo", "mcp__probe__ping"])
    checks = {check.name: check for check in run_hook_doctor(repo, target="claude-code")}
    assert ("allow_mcp_tools", "2") in checks["hook policy file"].details


def test_cli_flags(repo, monkeypatch):
    monkeypatch.chdir(repo)
    with fake_aeg(repo), patch("sys.stdout", new_callable=io.StringIO):
        assert main(["install", "--yes", "--mcp"]) == 0
        assert main(["install", "--yes", "--target", "codex", "--mcp"]) == 0
    assert [kind for _, kind in kinds(claude_entries(repo))] == [HOOK_KIND_MAIN, HOOK_KIND_MCP]
    assert [kind for _, kind in kinds(codex_entries(repo))] == [HOOK_KIND_MAIN, HOOK_KIND_MCP]
    with patch("sys.stdout", new_callable=io.StringIO):
        assert main(["uninstall", "--yes", "--mcp"]) == 0
        assert main(["uninstall", "--yes", "--target", "codex", "--mcp"]) == 0
    assert [kind for _, kind in kinds(claude_entries(repo))] == [HOOK_KIND_MAIN]
    assert [kind for _, kind in kinds(codex_entries(repo))] == [HOOK_KIND_MAIN]


# --- install, uninstall, doctor: Codex -----------------------------------------


def test_codex_mcp_entry_leaves_the_trusted_entry_byte_for_byte(repo):
    install(repo, target="codex")
    before = codex_text(repo)
    output = install(repo, target="codex", mcp=True)
    after = codex_text(repo)
    # Codex trusts an entry by a hash of its fields; the old text must survive as is.
    assert after.startswith(before)
    assert after[len(before):].startswith("\n# Aegis MCP PreToolUse hook for Codex.")
    assert kinds(codex_entries(repo)) == [(CODEX_AEGIS_HOOK_MATCHER, HOOK_KIND_MAIN),
                                          (CODEX_MCP_HOOK_MATCHER, HOOK_KIND_MCP)]
    assert "approve it in Codex /hooks as well" in output
    mcp_hook = codex_entries(repo)[1]["hooks"][0]
    assert mcp_hook["command"].endswith("--substrate codex --mcp")
    if os.name == "nt":
        assert mcp_hook["command_windows"].endswith("--substrate codex --mcp")
    install(repo, target="codex", mcp=True)
    install(repo, target="codex")
    assert codex_text(repo) == after
    uninstall(repo, target="codex", mcp_only=True)
    assert tomlkit.parse(codex_text(repo)).unwrap() == tomlkit.parse(before).unwrap()


def test_codex_fresh_install_with_mcp(tmp_path):
    result, already = build_installed_codex_config_text(
        "", "aeg hook-run --substrate codex", mcp_command="aeg hook-run --substrate codex --mcp", add_mcp=True,
    )
    assert not already
    entries = tomlkit.parse(result).unwrap()["hooks"]["PreToolUse"]
    assert [entry["matcher"] for entry in entries] == [CODEX_AEGIS_HOOK_MATCHER, CODEX_MCP_HOOK_MATCHER]
    assert "Managed by `aeg install --target codex --mcp`" in result
    assert build_installed_codex_config_text(
        result, "aeg hook-run --substrate codex", mcp_command="aeg hook-run --substrate codex --mcp", add_mcp=True,
    ) == (result, True)
    # Without the MCP command an existing MCP entry is left alone, never rewritten as main.
    assert build_installed_codex_config_text(result, "aeg hook-run --substrate codex") == (result, True)
    removed, count = build_uninstalled_codex_config_text(result, kinds=(HOOK_KIND_MCP,))
    assert count == 1
    assert [e["matcher"] for e in tomlkit.parse(removed).unwrap()["hooks"]["PreToolUse"]] == [CODEX_AEGIS_HOOK_MATCHER]
    removed, count = build_uninstalled_codex_config_text(result)
    assert count == 2
    assert "hooks" not in tomlkit.parse(removed).unwrap()


@pytest.mark.parametrize("original", [
    "# owner\nmodel = 'example' # keep\n[hooks]\nPreToolUse = [] # empty\n",
    'hooks = {PreToolUse = [], Stop = []} # inline\n',
    '["hooks"]\n"PreToolUse" = [{matcher="Read", hooks=[{type="command", command="user-hook"}]}]\n',
    '[[hooks.Stop]]\ncommand = "user-hook"\n',
])
def test_codex_mcp_install_preserves_valid_toml_variants(original):
    before = tomlkit.parse(original).unwrap()
    result, already = build_installed_codex_config_text(
        original, "aeg hook-run --substrate codex", mcp_command="aeg hook-run --substrate codex --mcp", add_mcp=True,
    )
    assert not already
    after = tomlkit.parse(result).unwrap()
    added = after["hooks"]["PreToolUse"][-2:]
    assert [entry["matcher"] for entry in added] == [CODEX_AEGIS_HOOK_MATCHER, CODEX_MCP_HOOK_MATCHER]
    del after["hooks"]["PreToolUse"][-2:]
    if "PreToolUse" not in before.get("hooks", {}):
        del after["hooks"]["PreToolUse"]
    if "hooks" not in before:
        del after["hooks"]
    assert after == before
    for comment in ("# owner", "# keep", "# empty", "# inline"):
        if comment in original:
            assert comment in result
    removed, count = build_uninstalled_codex_config_text(result)
    assert count == 2
    assert "aeg hook-run" not in json.dumps(tomlkit.parse(removed).unwrap().get("hooks", {}))


def test_codex_mcp_entry_without_substrate_is_refused():
    text = '[[hooks.PreToolUse]]\nmatcher = "x"\n[[hooks.PreToolUse.hooks]]\ntype = "command"\ncommand = "aeg hook-run --mcp"\n'
    with pytest.raises(Exception, match="--substrate codex"):
        build_installed_codex_config_text(text, "aeg hook-run --substrate codex",
                                          mcp_command="aeg hook-run --substrate codex --mcp")


def test_codex_doctor_reports_the_separate_trust(repo):
    with fake_aeg(repo):
        assert cmd_install(repo, target="codex", assume_yes=True, mcp=True, output_stream=io.StringIO()) == 0
        checks = {check.name: check for check in run_hook_doctor(repo, target="codex")}
    assert all(check.status == "PASS" for check in checks.values()), checks
    assert "approve it in /hooks" in checks["codex MCP hook registration"].next_step
    assert checks["codex MCP hook 1 matcher"].status == "PASS"


def test_main_matchers_are_unchanged():
    assert AEGIS_HOOK_MATCHER == "Write|Edit|MultiEdit|NotebookEdit|Bash|Read|Grep|Glob"
    assert CODEX_AEGIS_HOOK_MATCHER == "Write|Edit|Bash|Read|apply_patch"
