"""Codex teardown must round-trip without losing unrelated TOML configuration."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest
import tomlkit

from src.cli.install import (
    InstallStructureError, build_installed_codex_config_text,
    build_uninstalled_codex_config_text, cmd_uninstall,
)


@pytest.mark.parametrize("command", [
    "aeg hook-run --substrate codex", "/usr/bin/aeg hook-run --substrate codex",
    "'/home/some user/bin/aeg' hook-run --substrate codex",
    "C:\\Python\\Scripts\\aeg.exe hook-run --substrate codex",
    '"C:\\Program Files\\Python\\python.exe" -m src.cli hook-run --substrate codex',
    "C:\\Program Files\\Python\\python.exe -m src.cli hook-run --substrate codex",
    "/usr/bin/python3.10 -m src.cli hook-run --substrate codex",
    "aeg hook-run",  # legacy config remains removable
])
def test_generated_commands_removed(command):
    text, _ = build_installed_codex_config_text("", command)
    result, count = build_uninstalled_codex_config_text(text)
    assert count == 1
    assert not tomlkit.parse(result).get("hooks")


@pytest.mark.parametrize("command", [
    "echo aeg hook-run --substrate codex", "echo /usr/bin/aeg hook-run --substrate codex",
    "/usr/bin/aeg hook-run --substrate codex && other-command",
    "my-aeg hook-run --substrate codex", "aeg hook-run --substrate codex; echo hello",
])
def test_mentions_or_wrappers_are_preserved(command):
    text, _ = build_installed_codex_config_text("", command)
    assert build_uninstalled_codex_config_text(text) == (text, 0)


def test_mixed_hooks_comments_other_events_and_multiline_text_survive():
    text = '''# owner configuration
model = 'example' # retain inline comment
instructions = """Example, not actual configuration:
[[hooks.PreToolUse.hooks]]
command = "aeg hook-run --substrate codex"
"""
[[hooks.PreToolUse]]
matcher = 'Bash'
[[hooks.PreToolUse.hooks]]
type = 'command'
command = 'aeg hook-run --substrate codex'
[[hooks.PreToolUse.hooks]]
type = 'command'
command = 'user-hook' # retain user hook
[[hooks.Stop]]
command = 'aeg hook-run --substrate codex'
[mcp_servers.example]
command = 'example-mcp'
'''
    original = tomlkit.parse(text).unwrap()
    result, count = build_uninstalled_codex_config_text(text)
    expected = original
    del expected["hooks"]["PreToolUse"][0]["hooks"][0]
    assert tomlkit.parse(result).unwrap() == expected
    assert count == 1
    assert "# owner configuration" in result
    assert "# retain inline comment" in result
    assert "# retain user hook" in result
    assert build_uninstalled_codex_config_text(result) == (result, 0)


def test_quoted_keys_inline_hooks_windows_command_and_empty_user_entry():
    text = '''["hooks"]
PreToolUse = [{matcher = "Read", hooks = []}, {matcher = "Bash", hooks = [{type="command", command="user-hook"}, {type="command", command_windows='C:\\Python\\aeg.exe hook-run --substrate codex'}]}]
'''
    result, count = build_uninstalled_codex_config_text(text)
    entries = tomlkit.parse(result)["hooks"]["PreToolUse"]
    assert count == 1
    assert entries[0]["hooks"] == []
    assert len(entries[1]["hooks"]) == 1
    assert entries[1]["hooks"][0]["command"] == "user-hook"


def test_mixed_platform_hook_is_preserved():
    text = '''[[hooks.PreToolUse]]
matcher = "Bash"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "user-hook"
command_windows = "aeg hook-run --substrate codex"
'''
    assert build_uninstalled_codex_config_text(text) == (text, 0)


@pytest.mark.parametrize("executable,args,removed", [
    ("aeg.exe", ["hook-run", "--substrate", "codex"], 1),
    ("python.exe", ["-m", "src.cli", "hook-run", "--substrate", "codex"], 1),
    ("other.exe", ["-m", "src.cli", "hook-run"], 0),
    ("aeg.exe", ["other", "hook-run"], 0),
])
def test_exec_form_requires_exact_generated_argv(executable, args, removed):
    text = tomlkit.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": executable, "args": args}]}]}})
    _, count = build_uninstalled_codex_config_text(text)
    assert count == removed


@pytest.mark.parametrize("text", ["broken = [", "hooks = 'bad'", "[hooks]\nPreToolUse = 'bad'", "[[hooks.PreToolUse]]\nhooks = [1]"])
def test_invalid_config_aborts(text, tmp_path):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text(text, encoding="utf-8")
    with pytest.raises(InstallStructureError):
        build_uninstalled_codex_config_text(text)
    assert cmd_uninstall(tmp_path, target="codex", assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_text(encoding="utf-8") == text
    assert list(config.parent.iterdir()) == [config]


def test_preview_cancel_backup_and_idempotence(tmp_path):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    text, _ = build_installed_codex_config_text("model = 'example'\n", "aeg hook-run --substrate codex")
    config.write_text(text, encoding="utf-8")
    out = io.StringIO()
    assert cmd_uninstall(tmp_path, target="codex", input_stream=io.StringIO("n\n"), output_stream=out) == 0
    assert config.read_text(encoding="utf-8") == text
    assert "cancelled" in out.getvalue()
    assert "---" in out.getvalue()
    assert len(list(config.parent.iterdir())) == 1
    assert cmd_uninstall(tmp_path, target="codex", input_stream=io.StringIO("y\n"), output_stream=out) == 0
    assert tomlkit.parse(config.read_text(encoding="utf-8")).unwrap() == {"model": "example"}
    backups = list(config.parent.glob("*.aegis-backup-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == text
    assert cmd_uninstall(tmp_path, target="codex", assume_yes=True, output_stream=out) == 0
    assert len(list(config.parent.glob("*.aegis-backup-*"))) == 1


def test_backup_failure_does_not_modify_config(tmp_path):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    text, _ = build_installed_codex_config_text("", "aeg hook-run --substrate codex")
    config.write_text(text, encoding="utf-8")
    with mock.patch("src.cli.install._backup_file", side_effect=PermissionError("test")):
        assert cmd_uninstall(tmp_path, target="codex", assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_text(encoding="utf-8") == text


def test_cli_install_uninstall_round_trip_preserves_claude(tmp_path):
    claude = tmp_path / ".claude" / "settings.json"
    claude.parent.mkdir()
    claude.write_text(json.dumps({"user": "untouched"}), encoding="utf-8")
    original = claude.read_bytes()
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONIOENCODING="utf-8")
    for command in ("install", "uninstall", "uninstall"):
        result = subprocess.run([sys.executable, "-m", "src.cli", command, "--target", "codex", "--yes", "--path", str(tmp_path)], cwd=tmp_path, env=env, capture_output=True)
        assert result.returncode == 0, result.stderr
    assert not tomlkit.parse((tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")).get("hooks")
    assert claude.read_bytes() == original
