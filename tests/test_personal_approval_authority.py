"""Checkout files may restrict a hook, but only a person's separate storage may authorize."""

import io
import json
import os
from unittest.mock import patch

import pytest

from jangseung.classify.hook_policy import load_hook_policy
from jangseung.cli.allow_once import cmd_allow_once
from jangseung.cli.hook_run import render_hook_response
from jangseung.cli.policy import cmd_policy_add, cmd_policy_adopt, policy_path
from jangseung.state.allow_once import ALLOW_ONCE_FILE, approved_once, grant_once
from jangseung.state.approvals import approval_root
from jangseung.state.approvals import _user_home as os_user_home


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "project"
    (root / ".aeg").mkdir(parents=True)
    return root


def decision(repo, tool, tool_input, host="codex"):
    raw = json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": "fixture",
                      "hook_event_name": "PreToolUse", "permission_mode": "default", "cwd": str(repo)})
    return render_hook_response(raw, repo_root=repo, substrate=host, working_dir=repo).permission_decision


def test_checkout_grants_need_explicit_adoption_but_restrictions_apply_immediately(repo):
    legacy = repo / ".aeg/policy.json"
    legacy.write_text(json.dumps({"allow_paths": [".env"], "allow_commands": ["pytest"],
                                  "allow_mcp_tools": ["mcp__example__inspect"], "protect_paths": ["notes.txt"]}))
    assert decision(repo, "Read", {"file_path": ".env"}) == "deny"
    assert decision(repo, "Bash", {"command": "pytest"}) != "allow"
    assert decision(repo, "mcp__example__inspect", {}) == "deny"
    assert decision(repo, "mcp__example__inspect", {}, "claude-code") == "ask"
    assert decision(repo, "Write", {"file_path": "notes.txt", "content": "ok"}) == "deny"
    assert cmd_policy_add(repo, commands=["ruff check"], assume_yes=True) == 0
    assert not load_hook_policy(repo).approves_command(("pytest",))
    assert not load_hook_policy(repo).allow_mcp_tools
    assert cmd_policy_adopt(repo, input_stream=io.StringIO("n\n")) == 0
    assert not load_hook_policy(repo).approves_command(("pytest",))
    out = io.StringIO()

    class Review(io.StringIO):
        def readline(self, *args):
            assert all(entry in out.getvalue() for entry in ("pytest", "ruff check", "notes.txt", "mcp__example__inspect", ".env"))
            legacy.write_text(json.dumps({"allow_mcp_tools": ["mcp__other__inspect"]}))
            return "y\n"

    assert cmd_policy_adopt(repo, input_stream=Review(), output_stream=out) == 0
    assert not policy_path(repo).is_relative_to(repo)
    assert decision(repo, "mcp__example__inspect", {}) == "allow"
    assert decision(repo, "mcp__other__inspect", {}) == "deny"
    assert decision(repo, "Read", {"file_path": ".env"}) == "allow"
    assert decision(repo, "Bash", {"command": "pytest"}) == "allow"
    assert decision(repo, "Write", {"file_path": "notes.txt", "content": "ok"}) == "deny"


def test_checkouts_and_environment_do_not_supply_authority(repo, monkeypatch):
    other = repo.parent / "other"
    (other / ".aeg").mkdir(parents=True)
    assert cmd_policy_add(repo, commands=["pytest"], assume_yes=True) == 0
    grant_once("tool inspect", repo)
    grant = (approval_root(repo) / ALLOW_ONCE_FILE).read_bytes()
    (repo / ".aeg" / ALLOW_ONCE_FILE).write_bytes(grant)
    (other / ".aeg" / ALLOW_ONCE_FILE).write_bytes(grant)
    (other / ".aeg/policy.json").write_bytes(policy_path(repo).read_bytes())
    os_home = os_user_home()
    monkeypatch.setenv("HOME", str(repo))
    monkeypatch.setenv("USERPROFILE", str(repo))
    assert os_user_home() == os_home != repo
    assert approved_once("tool inspect", repo)
    assert not approved_once("tool inspect", other)
    assert not load_hook_policy(other).approves_command(("pytest",))
    assert decision(other, "Write", {"file_path": str(policy_path(repo)), "content": "data"}) == "deny"
    # Legacy grants are never consulted, even in their originating directory.
    (approval_root(repo) / ALLOW_ONCE_FILE).unlink()
    assert not approved_once("tool inspect", repo)


@pytest.mark.parametrize("adopt", [True, False])
def test_concurrent_revocation_during_review_is_not_restored(repo, adopt):
    assert cmd_policy_add(repo, commands=["pytest"], assume_yes=True) == 0
    (repo / ".aeg/policy.json").write_text(json.dumps({"allow_commands": ["ruff check"]}))

    class Revoked(io.StringIO):
        def readline(self, *args):
            policy_path(repo).unlink()
            return "y\n"

    if adopt:
        assert cmd_policy_adopt(repo, input_stream=Revoked()) == 1
    else:
        assert cmd_policy_add(repo, commands=["ruff check"], input_stream=Revoked()) == 1
    assert not load_hook_policy(repo).allow_commands


def test_malformed_restrictions_hold_trusted_grants_and_file_writes(repo):
    grant_once("tool inspect", repo)
    assert cmd_policy_add(repo, mcp_tools=["mcp__example__inspect"], assume_yes=True) == 0
    (repo / ".aeg/policy.json").write_text('{"protect_paths":')
    assert decision(repo, "Write", {"file_path": "ordinary.txt", "content": "ok"}) == "deny"
    assert decision(repo, "Bash", {"command": "tool inspect"}) != "allow"
    assert decision(repo, "mcp__example__inspect", {}) == "deny"


def test_mcp_grants_do_not_follow_the_agent_out_of_its_project(repo):
    assert cmd_policy_add(repo, mcp_tools=["mcp__example__inspect"], assume_yes=True) == 0
    raw = json.dumps({"tool_name": "mcp__example__inspect", "tool_input": {}, "tool_use_id": "fixture",
                      "cwd": str(repo.parent)})
    assert render_hook_response(raw, repo_root=repo, substrate="codex", working_dir=repo.parent).permission_decision == "deny"


def test_unsafe_or_overlapping_authority_root_is_unusable(repo):
    nested = repo / "profile"
    nested.mkdir()
    with patch("jangseung.state.approvals._user_home", return_value=nested):
        assert cmd_policy_add(repo, commands=["pytest"], assume_yes=True) == 1
        assert cmd_allow_once(repo, "tool inspect") == 1
        assert not approved_once("tool inspect", repo)
        assert not (nested / ".jangseung").exists()
    root = approval_root(repo, create=True)
    assert cmd_policy_add(root, commands=["pytest"], assume_yes=True) == 1
    assert decision(root, "Write", {"file_path": "policy.json", "content": "data"}) == "deny"


def test_authority_rejects_redirected_parent(repo, isolated_approval_home):
    target = repo / "fixture-dir"
    target.mkdir()
    redirect = isolated_approval_home / ".jangseung"
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(target), str(redirect))
    else:
        redirect.symlink_to(target, target_is_directory=True)
    try:
        assert cmd_policy_add(repo, commands=["pytest"], assume_yes=True) == 1
        assert cmd_allow_once(repo, "tool inspect") == 1
        assert not approved_once("tool inspect", repo)
        assert list(target.iterdir()) == []
    finally:
        if os.name == "nt":
            redirect.rmdir()
        else:
            redirect.unlink()


def test_invalid_personal_grant_store_rejected_as_a_whole(repo):
    grant_once("tool inspect", repo)
    path = approval_root(repo) / ALLOW_ONCE_FILE
    data = json.loads(path.read_bytes())
    data["entries"]["bad"] = "invalid"
    path.write_text(json.dumps(data))
    assert not approved_once("tool inspect", repo)
    assert cmd_allow_once(repo, None, status=True) == 1
    assert cmd_allow_once(repo, None, clear=True) == 1
    assert cmd_allow_once(repo, "other inspect") == 1
