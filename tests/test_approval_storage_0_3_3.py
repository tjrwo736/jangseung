"""0.3.3: four fixes to the personal approval storage that 0.3.2 introduced.

* The profile folder is found without loading ``ctypes`` on every hook call.
* The folder approvals are kept under no longer depends on the Python version.
* A profile folder that cannot hold approvals means "no personal approvals",
  not "every path is protected"; a project that overlaps the storage stays blocked.
* Grants left in ``.aeg/policy.json`` are pointed out when a session starts.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from jangseung.classify.hook_policy import (
    NOTICE_LEGACY_GRANTS_IGNORED, NOTICE_NO_PERSONAL_STORAGE, load_hook_policy,
)
from jangseung.cli.hook_run import render_hook_response
from jangseung.cli.policy import cmd_policy_add, cmd_policy_adopt
from jangseung.cli.session_check import run_session_check, session_report
from jangseung.state import approvals

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / ".aeg").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    return root


def _decision(project, tool, tool_input):
    raw = json.dumps({"tool_name": tool, "tool_input": tool_input, "tool_use_id": "t", "cwd": str(project),
                      "permission_mode": "default", "hook_event_name": "PreToolUse", "session_id": "s"})
    return render_hook_response(raw, repo_root=project, working_dir=project).permission_decision


def _edit(project):
    return _decision(project, "Edit", {"file_path": "src/a.py", "old_string": "1", "new_string": "2"})


def _approve(project, **kwargs):
    out = io.StringIO()
    assert cmd_policy_add(project, input_stream=io.StringIO("y\n"), output_stream=out, **kwargs) == 0, out.getvalue()


# --- the folder name does not depend on the Python version


def test_the_approval_key_uses_only_the_bits_every_python_reports(monkeypatch, tmp_path):
    # Python 3.12+ on Windows reports a 64-bit volume serial; earlier versions its low 32 bits.
    newer = SimpleNamespace(st_dev=0xBC2F_1234_3018_871A, st_ino=4222124650849438)
    older = SimpleNamespace(st_dev=0x3018_871A, st_ino=4222124650849438)
    monkeypatch.setattr(approvals.os, "name", "nt")
    key_new, legacy_new = approvals._project_keys(tmp_path, newer)
    key_old, legacy_old = approvals._project_keys(tmp_path, older)
    assert key_new == key_old == legacy_old
    assert legacy_new != key_new  # what 0.3.2 wrote under Python 3.12+


def test_approvals_0_3_2_stored_under_the_old_name_still_apply_and_move_on_the_next_write(project, monkeypatch,
                                                                                         isolated_approval_home):
    real = approvals._project_keys

    def keys(repo, identity):
        key, _ = real(repo, identity)
        return key, "0" * 64  # as if 0.3.2 had used another name

    old = isolated_approval_home / ".jangseung" / "approvals" / ("0" * 64)
    old.mkdir(parents=True)
    (old / "policy.json").write_text(json.dumps({"allow_commands": ["pytest"]}), encoding="utf-8")
    monkeypatch.setattr(approvals, "_project_keys", keys)
    assert load_hook_policy(project).allow_commands == (("pytest",),)
    assert old.is_dir()  # a read moves nothing
    _approve(project, commands=["ruff"])
    stable = approvals.approval_root(project)
    assert stable.name != "0" * 64 and not old.exists()
    assert set(load_hook_policy(project).allow_commands) == {("pytest",), ("ruff",)}


# --- a profile folder that cannot hold approvals


def _unlocatable():
    raise KeyError("getpwuid(): uid not found")


def test_an_unlocatable_profile_means_no_personal_approvals_not_a_blocked_project(project, monkeypatch):
    _approve(project, commands=["pytest"])
    assert load_hook_policy(project).allow_commands == (("pytest",),)
    monkeypatch.setattr(approvals, "_user_home", _unlocatable)
    policy = load_hook_policy(project)
    assert policy.error is None and policy.allow_commands == () and policy.paths.protect_paths == ()
    assert NOTICE_NO_PERSONAL_STORAGE in policy.notices
    assert _edit(project) == "allow"  # ordinary work goes on
    assert _decision(project, "Read", {"file_path": ".env"}) == "deny"  # the built-in rules still apply
    problems, _ = session_report(project, plugin=True)
    assert any("profile folder" in problem for problem in problems)
    assert cmd_policy_add(project, commands=["ruff"], assume_yes=True, output_stream=io.StringIO()) == 1


def test_a_linked_profile_folder_is_treated_the_same(project, monkeypatch, tmp_path):
    real = tmp_path / "real-profile"
    real.mkdir()
    link = tmp_path / "linked-profile"
    try:
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(real), str(link))
        else:
            link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create a directory link here")
    monkeypatch.setattr(approvals, "_user_home", lambda: link)
    policy = load_hook_policy(project)
    assert policy.error is None and NOTICE_NO_PERSONAL_STORAGE in policy.notices
    assert _edit(project) == "allow"
    assert not (real / ".jangseung").exists()


def test_the_team_file_and_checkout_protections_still_apply_without_a_profile(project, monkeypatch):
    (project / ".aeg" / "policy.json").write_text(json.dumps({"protect_paths": ["src/a.py"]}), encoding="utf-8")
    monkeypatch.setattr(approvals, "_user_home", _unlocatable)
    assert _edit(project) != "allow"


def test_a_project_that_holds_the_storage_stays_blocked_even_with_an_unusable_profile(tmp_path, monkeypatch):
    # The profile is a link AND the project contains the storage: the stricter rule wins.
    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    real = project / "profile"
    real.mkdir()
    link = tmp_path / "linked-profile"
    try:
        if os.name == "nt":
            import _winapi

            _winapi.CreateJunction(str(real), str(link))
        else:
            link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create a directory link here")
    monkeypatch.setattr(approvals, "_user_home", lambda: link)
    policy = load_hook_policy(project)
    assert policy.error == "personal_approval_directory_unavailable" and policy.paths.protect_paths == ("*",)


# --- grants left in the checkout are pointed out


def test_legacy_grants_are_pointed_out_until_adopted_or_removed(project):
    legacy = project / ".aeg" / "policy.json"
    legacy.write_text(json.dumps({"allow_commands": ["pytest"], "protect_paths": ["notes.txt"]}), encoding="utf-8")
    policy = load_hook_policy(project)
    assert NOTICE_LEGACY_GRANTS_IGNORED in policy.notices and policy.allow_commands == ()
    problems, notes = session_report(project, plugin=True)
    assert problems == [] and len(notes) == 1 and "aeg policy adopt" in notes[0]
    out = io.StringIO()
    start = json.dumps({"hook_event_name": "SessionStart", "cwd": str(project)})
    assert run_session_check(["--plugin"], stdin=io.StringIO(start), stdout=out) == 0
    message = json.loads(out.getvalue())["systemMessage"]
    assert "Note:" in message and "protection may be off" not in message

    assert cmd_policy_adopt(project, input_stream=io.StringIO("y\n"), output_stream=io.StringIO()) == 0
    assert load_hook_policy(project).notices == ()
    assert session_report(project, plugin=True) == ([], [])


def test_a_checkout_file_with_only_protections_needs_no_note(project):
    (project / ".aeg" / "policy.json").write_text(json.dumps({"protect_paths": ["notes.txt"]}), encoding="utf-8")
    assert load_hook_policy(project).notices == ()
    out = io.StringIO()
    start = json.dumps({"hook_event_name": "SessionStart", "cwd": str(project)})
    run_session_check(["--plugin"], stdin=io.StringIO(start), stdout=out)
    assert out.getvalue() == "{}\n"


# --- the profile folder without ctypes (Windows)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the registry lookup is for Windows")


@windows_only
def test_the_registry_names_the_folder_the_shell_names():
    found = approvals._profile_from_registry()
    if found is None:
        pytest.skip("more than one user hive is open to this process; the shell is asked instead")
    import ctypes

    buffer = ctypes.create_unicode_buffer(260)
    assert ctypes.windll.shell32.SHGetFolderPathW(None, 0x28, None, 0, buffer) == 0
    assert os.path.normcase(str(found)) == os.path.normcase(buffer.value)


@windows_only
def test_a_hook_call_finds_the_profile_without_loading_ctypes(tmp_path):
    if approvals._profile_from_registry() is None:
        pytest.skip("more than one user hive is open to this process; the shell is asked instead")
    project = tmp_path / "project"
    (project / ".aeg").mkdir(parents=True)
    code = (
        "import sys; sys.path.insert(0, sys.argv[1])\n"
        "from jangseung.classify.hook_policy import load_hook_policy\n"
        "policy = load_hook_policy(sys.argv[2])\n"
        "print(policy.error, 'ctypes' in sys.modules)\n"
    )
    done = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(REPO_ROOT), str(project)],
                          capture_output=True, text=True, timeout=60)
    assert done.stdout.split() == ["None", "False"], done.stderr


def test_registry_answers_that_need_guessing_are_refused(monkeypatch):
    winreg = pytest.importorskip("winreg")

    def with_users(names, value="C:\\Users\\someone"):
        monkeypatch.setattr(winreg, "EnumKey", lambda key, index: names[index] if index < len(names) else (_ for _ in ()).throw(OSError()))
        monkeypatch.setattr(winreg, "OpenKey", lambda *args, **kwargs: _Key())
        monkeypatch.setattr(winreg, "CloseKey", lambda key: None)
        monkeypatch.setattr(winreg, "QueryValueEx", lambda key, name: (value, 2))
        return approvals._profile_from_registry()

    class _Key:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    services = [".DEFAULT", "S-1-5-18", "S-1-5-19", "S-1-5-20"]
    one = "S-1-5-21-1-2-3-1001"
    assert with_users([*services, one, one + "_Classes"]) == Path("C:\\Users\\someone")
    assert with_users(services) is None  # a service account: no person's hive
    assert with_users([*services, one, "S-1-5-21-1-2-3-1002"]) is None  # an administrator sees several
    assert with_users([*services, one], value="%SystemDrive%\\Users\\someone") is None  # would need the environment
    assert with_users([*services, one], value="Users\\someone") is None
