"""0.1.3 installer regressions: preserve settings and prepare recording."""
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from unittest.mock import patch

import pytest
import tomlkit

from src.cli.hook_run import run_aeg_hook_run
from src.cli.install import (
    InstallStructureError, build_installed_codex_config_text,
    build_uninstalled_codex_config_text, build_uninstalled_settings,
    cmd_install, cmd_uninstall, is_aegis_hook, resolve_hook_command,
)


@pytest.mark.parametrize("original", [
    "# owner\nmodel = 'example' # keep\n[hooks]\nPreToolUse = [] # empty\n",
    'hooks = {PreToolUse = [], Stop = []} # inline\n',
    'hooks = {Stop = []} # inline\n',
    '["hooks"]\n"PreToolUse" = [{matcher="Read", hooks=[{type="command", command="user-hook"}]}]\n',
    '[[hooks.Stop]]\ncommand = "user-hook"\n',
    'instructions = """\n[[hooks.PreToolUse.hooks]]\ncommand = "aeg hook-run --substrate codex"\n"""\n',
])
def test_codex_install_preserves_valid_toml_variants(original):
    before = tomlkit.parse(original).unwrap()
    result, already = build_installed_codex_config_text(original, "aeg hook-run --substrate codex")
    assert not already
    after = tomlkit.parse(result).unwrap()
    assert len(after["hooks"]["PreToolUse"]) == len(before.get("hooks", {}).get("PreToolUse", [])) + 1
    del after["hooks"]["PreToolUse"][-1]
    if "PreToolUse" not in before.get("hooks", {}):
        del after["hooks"]["PreToolUse"]
    if "hooks" not in before:
        del after["hooks"]
    assert after == before
    for comment in ("# owner", "# keep", "# empty", "# inline"):
        if comment in original:
            assert comment in result
    assert build_installed_codex_config_text(result, "aeg hook-run --substrate codex") == (result, True)
    removed, count = build_uninstalled_codex_config_text(result)
    assert count == 1
    assert "aeg hook-run" not in json.dumps(tomlkit.parse(removed).unwrap().get("hooks", {}))


@pytest.mark.parametrize("bad", ["broken = [", "hooks = 'bad'", "[hooks]\nPreToolUse = 'bad'", "[[hooks.PreToolUse]]\nhooks=[1]"])
def test_codex_invalid_config_has_no_side_effects(tmp_path, bad):
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text(bad, encoding="utf-8")
    assert cmd_install(tmp_path, target="codex", assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_text(encoding="utf-8") == bad
    assert list(config.parent.iterdir()) == [config]
    assert not (tmp_path / ".aeg").exists()


@pytest.mark.parametrize("command", [
    "echo 'aeg hook-run maintenance notice'", "/bin/echo /usr/bin/aeg hook-run",
    "other hook-run", "aeg hook-run && user-hook", "aeg hook-run --unrelated-option",
    "python -c 'src.cli hook-run'", "my-aeg hook-run",
])
def test_claude_uninstall_preserves_mentions_and_wrappers(tmp_path, command):
    hook = {"type": "command", "command": command}
    original = {"hooks": {"PreToolUse": [{"hooks": [hook]}]}}
    assert not is_aegis_hook(hook)
    assert build_uninstalled_settings(original) == (original, 0)
    config = tmp_path / ".claude" / "settings.json"
    config.parent.mkdir()
    config.write_text(json.dumps(original), encoding="utf-8")
    before = config.read_bytes()
    assert cmd_uninstall(tmp_path, assume_yes=True, output_stream=io.StringIO()) == 0
    assert config.read_bytes() == before
    assert list(config.parent.iterdir()) == [config]


@pytest.mark.parametrize("hook", [
    {"type": "command", "command": "echo", "args": ["-m", "src.cli", "hook-run"]},
    {"type": "command", "command": "aeg", "args": ["other", "hook-run"]},
    {"type": "prompt", "command": "aeg hook-run"},
    {"type": "command", "command": "aeg hook-run", "command_windows": "user-hook"},
])
def test_ambiguous_or_non_command_hooks_are_not_removed(hook):
    assert not is_aegis_hook(hook)


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_first_install_records_without_manual_init(tmp_path, target):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "README.md").write_text("fixture", encoding="utf-8")
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 0
    assert (tmp_path / ".aeg" / ".gitignore").read_text(encoding="utf-8") == "*\n"
    stdout = io.StringIO()
    assert run_aeg_hook_run(stdin=io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat README.md"}, "tool_use_id": "install-smoke"})),
                            stdout=stdout, stderr=io.StringIO(), repo_root=tmp_path, substrate=target) == 0
    assert "hook_decision_recording_failed" not in stdout.getvalue()
    assert json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert (tmp_path / ".aeg" / "hook_ledger.jsonl").is_file()
    assert not (tmp_path / ".aeg" / "ledger.jsonl").exists()
    assert subprocess.run(["git", "check-ignore", "-q", ".aeg/hook_ledger.jsonl"], cwd=tmp_path).returncode == 0


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_install_cancel_and_missing_state_repair(tmp_path, target):
    assert cmd_install(tmp_path, target=target, input_stream=io.StringIO("n\n"), output_stream=io.StringIO()) == 0
    assert list(tmp_path.iterdir()) == []
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 0
    state = tmp_path / ".aeg"
    (state / ".gitignore").unlink()
    state.rmdir()
    config = tmp_path / (".codex/config.toml" if target == "codex" else ".claude/settings.json")
    original = config.read_bytes()
    assert cmd_install(tmp_path, target=target, input_stream=io.StringIO("n\n"), output_stream=io.StringIO()) == 0
    assert not state.exists()
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 0
    assert state.is_dir()
    assert config.read_bytes() == original
    (state / "hook_ledger.jsonl").write_text("existing records\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in state.iterdir()}
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 0
    assert {path.name: path.read_bytes() for path in state.iterdir()} == before
    assert not list(config.parent.glob("*.aegis-backup-*"))


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_bad_state_does_not_change_config(tmp_path, target):
    config = tmp_path / (".codex/config.toml" if target == "codex" else ".claude/settings.json")
    config.parent.mkdir()
    config.write_text("model = 'example'\n" if target == "codex" else '{"model":"example"}', encoding="utf-8")
    original = config.read_bytes()
    (tmp_path / ".aeg").write_text("not a directory", encoding="utf-8")
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_bytes() == original


@pytest.mark.parametrize("executable", ["/tmp/my project/aeg", "/tmp/O'Brien/aeg", "/tmp/my project/python3.10"])
def test_shell_hook_path_is_quoted_and_removable(executable):
    python = executable.endswith("python3.10")
    with patch("src.cli.install.shutil.which", return_value=None if python else executable), patch("src.cli.install.sys.executable", executable):
        command = resolve_hook_command(substrate="codex")
    assert shlex.split(command) == [executable, *(["-m", "src.cli"] if python else []), "hook-run", "--substrate", "codex"]
    assert is_aegis_hook({"type": "command", "command": command})


@pytest.mark.skipif(os.name == "nt", reason="actual POSIX shell quoting check")
def test_shell_executes_spaced_path(tmp_path):
    directory = tmp_path / "O'Brien project"
    directory.mkdir()
    executable = directory / "aeg"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n", encoding="utf-8")
    executable.chmod(0o700)
    with patch("src.cli.install.shutil.which", return_value=str(executable)):
        command = resolve_hook_command(substrate="codex")
    result = subprocess.run(["/bin/sh", "-c", command], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["hook-run", "--substrate", "codex"]


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_atomic_write_failure_keeps_config(tmp_path, target):
    config = tmp_path / (".codex/config.toml" if target == "codex" else ".claude/settings.json")
    config.parent.mkdir()
    config.write_text("model = 'example'\n" if target == "codex" else '{"model":"example"}', encoding="utf-8")
    original = config.read_bytes()
    with patch("src.cli.install.os.replace", side_effect=OSError("disk unavailable")):
        assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_bytes() == original
    assert not list(config.parent.glob(".aeg-config-*"))


@pytest.mark.parametrize("target", ["claude-code", "codex"])
def test_non_utf8_settings_are_rejected_without_writes(tmp_path, target):
    config = tmp_path / (".codex/config.toml" if target == "codex" else ".claude/settings.json")
    config.parent.mkdir()
    config.write_bytes(b"\xff")
    assert cmd_install(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 1
    assert cmd_uninstall(tmp_path, target=target, assume_yes=True, output_stream=io.StringIO()) == 1
    assert config.read_bytes() == b"\xff"
    assert not (tmp_path / ".aeg").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only attribute cleanup")
def test_readonly_temp_is_cleaned_on_replace_failure(tmp_path):
    from src.cli.install import _atomic_write_text
    config = tmp_path / "settings.json"
    config.write_text("original", encoding="utf-8")
    config.chmod(0o444)
    try:
        with patch("src.cli.install.os.replace", side_effect=PermissionError("read only")):
            with pytest.raises(PermissionError):
                _atomic_write_text(config, "new")
        assert config.read_text(encoding="utf-8") == "original"
        assert list(tmp_path.iterdir()) == [config]
    finally:
        config.chmod(0o600)
