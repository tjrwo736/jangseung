"""Tests for ``aeg install`` / ``aeg uninstall`` settings merge + safety."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.cli.install import (
    AEGIS_HOOK_MATCHER,
    CODEX_AEGIS_HOOK_MATCHER,
    HOOK_EVENT_NAME,
    InstallStructureError,
    TARGET_CODEX,
    WINDOWS_AEGIS_HOOK_MATCHER,
    build_installed_codex_config_text,
    build_installed_settings,
    build_uninstalled_settings,
    claude_code_hook_matcher,
    cmd_install,
    cmd_uninstall,
    codex_config_path,
    is_aegis_hook,
    is_aegis_hook_command,
    load_settings,
    resolve_claude_code_hook_command,
    resolve_hook_command,
    resolve_hook_command_parts,
    resolve_windows_hook_command_parts,
    settings_path,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

_USER_HOOK = "/usr/local/bin/my-own-hook.sh"


def _aegis_entry(command):
    return {
        "matcher": AEGIS_HOOK_MATCHER,
        "hooks": [{"type": "command", "command": command}],
    }


class BuildMergeLogicTests(unittest.TestCase):
    def test_resolve_hook_command_references_hook_run(self):
        command = resolve_hook_command()
        self.assertIn("hook-run", command)
        self.assertNotIn("--substrate", command)
        self.assertTrue(is_aegis_hook_command(command))

    def test_resolve_hook_command_parts_references_hook_run(self):
        command, args = resolve_hook_command_parts()
        self.assertIsInstance(command, str)
        self.assertIn("hook-run", args)

    def test_resolve_hook_command_can_encode_codex_substrate(self):
        command = resolve_hook_command(substrate=TARGET_CODEX)
        self.assertIn("hook-run", command)
        self.assertIn("--substrate codex", command)
        self.assertTrue(is_aegis_hook_command(command))

    def test_windows_claude_code_hook_uses_exec_form_args(self):
        python_path = r"C:\Users\Name With Space\AppData\Local\Temp\aeg venv\Scripts\python.exe"
        with mock.patch("src.cli.install.shutil.which", return_value=None), mock.patch(
            "src.cli.install.sys.executable",
            python_path,
        ):
            command, args = resolve_claude_code_hook_command(platform="win32")

        self.assertEqual(command, python_path)
        self.assertEqual(args, ("-m", "src.cli", "hook-run"))

        data, already = build_installed_settings(
            {},
            command,
            args=args,
            matcher=claude_code_hook_matcher(platform="win32"),
        )
        self.assertFalse(already)
        self.assertEqual(
            data["hooks"][HOOK_EVENT_NAME][0]["matcher"],
            WINDOWS_AEGIS_HOOK_MATCHER,
        )
        hook = data["hooks"][HOOK_EVENT_NAME][0]["hooks"][0]
        self.assertEqual(hook["command"], python_path)
        self.assertEqual(hook["args"], ["-m", "src.cli", "hook-run"])
        self.assertTrue(is_aegis_hook(hook))

    def test_claude_code_matcher_adds_powershell_only_on_windows(self):
        self.assertEqual(claude_code_hook_matcher(platform="linux"), AEGIS_HOOK_MATCHER)
        self.assertEqual(claude_code_hook_matcher(platform="darwin"), AEGIS_HOOK_MATCHER)
        self.assertEqual(
            claude_code_hook_matcher(platform="win32"),
            WINDOWS_AEGIS_HOOK_MATCHER,
        )

    def test_windows_hook_uses_aeg_exe_when_available(self):
        aeg_path = r"C:\Users\Name With Space\venv\Scripts\aeg.exe"
        with mock.patch("src.cli.install.shutil.which", return_value=aeg_path):
            command, args = resolve_windows_hook_command_parts()

        self.assertEqual(command, aeg_path)
        self.assertEqual(args, ("hook-run",))

    def test_windows_hook_ignores_non_exe_aeg_shim(self):
        python_path = r"C:\Users\Name With Space\venv\Scripts\python.exe"
        with mock.patch(
            "src.cli.install.shutil.which",
            return_value=r"C:\Users\Name With Space\venv\Scripts\aeg.cmd",
        ), mock.patch("src.cli.install.sys.executable", python_path):
            command, args = resolve_windows_hook_command_parts()

        self.assertEqual(command, python_path)
        self.assertEqual(args, ("-m", "src.cli", "hook-run"))

    def test_posix_claude_code_hook_keeps_shell_form(self):
        command, args = resolve_claude_code_hook_command(platform="linux")

        self.assertIsNone(args)
        self.assertIn("hook-run", command)
        data, _ = build_installed_settings({}, command, args=args)
        hook = data["hooks"][HOOK_EVENT_NAME][0]["hooks"][0]
        self.assertEqual(hook, {"type": "command", "command": command})

    def test_is_aegis_hook_command_does_not_match_user_hooks(self):
        self.assertFalse(is_aegis_hook_command(_USER_HOOK))
        self.assertFalse(is_aegis_hook_command("echo done"))
        self.assertFalse(is_aegis_hook_command(None))

    def test_install_into_empty_creates_structure(self):
        new_data, already = build_installed_settings({}, "aeg hook-run")
        self.assertFalse(already)
        entries = new_data["hooks"][HOOK_EVENT_NAME]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], AEGIS_HOOK_MATCHER)

    def test_install_preserves_all_existing_content(self):
        original = {
            "model": "claude-sonnet-5",
            "env": {"FOO": "bar"},
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": _USER_HOOK}]}
                ],
                "PostToolUse": [
                    {"matcher": "Write", "hooks": [{"type": "command", "command": "echo done"}]}
                ],
            },
        }
        new_data, already = build_installed_settings(original, "aeg hook-run")
        self.assertFalse(already)
        # user content preserved verbatim
        self.assertEqual(new_data["model"], "claude-sonnet-5")
        self.assertEqual(new_data["env"], {"FOO": "bar"})
        self.assertEqual(new_data["hooks"]["PostToolUse"], original["hooks"]["PostToolUse"])
        pre = new_data["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 2)
        self.assertEqual(pre[0]["hooks"][0]["command"], _USER_HOOK)  # user hook untouched
        self.assertTrue(is_aegis_hook_command(pre[1]["hooks"][0]["command"]))
        # original object not mutated
        self.assertEqual(len(original["hooks"]["PreToolUse"]), 1)

    def test_install_is_idempotent_no_duplicate(self):
        data, _ = build_installed_settings({}, "aeg hook-run")
        again, already = build_installed_settings(data, "aeg hook-run")
        self.assertTrue(already)
        self.assertEqual(len(again["hooks"][HOOK_EVENT_NAME]), 1)

    def test_install_is_idempotent_for_windows_exec_form_hook(self):
        data, _ = build_installed_settings(
            {},
            r"C:\Users\Name With Space\venv\Scripts\python.exe",
            args=["-m", "src.cli", "hook-run"],
        )
        again, already = build_installed_settings(data, "aeg hook-run")

        self.assertTrue(already)
        self.assertEqual(len(again["hooks"][HOOK_EVENT_NAME]), 1)

    def test_uninstall_removes_only_aegis_keeps_user(self):
        data = {
            "model": "x",
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": _USER_HOOK}]},
                    _aegis_entry("aeg hook-run"),
                ]
            },
        }
        new_data, removed = build_uninstalled_settings(data)
        self.assertEqual(removed, 1)
        pre = new_data["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["hooks"][0]["command"], _USER_HOOK)
        self.assertEqual(new_data["model"], "x")

    def test_uninstall_removes_windows_exec_form_aegis_hook(self):
        data = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": _USER_HOOK}]},
                    {
                        "matcher": AEGIS_HOOK_MATCHER,
                        "hooks": [
                            {
                                "type": "command",
                                "command": r"C:\Users\x\venv\Scripts\python.exe",
                                "args": ["-m", "src.cli", "hook-run"],
                            }
                        ],
                    },
                ]
            }
        }

        new_data, removed = build_uninstalled_settings(data)

        self.assertEqual(removed, 1)
        pre = new_data["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["hooks"][0]["command"], _USER_HOOK)

    def test_uninstall_cleans_up_empty_structures(self):
        data = {"hooks": {"PreToolUse": [_aegis_entry("aeg hook-run")]}}
        new_data, removed = build_uninstalled_settings(data)
        self.assertEqual(removed, 1)
        self.assertNotIn("hooks", new_data)  # empty hooks removed

    def test_uninstall_keeps_mixed_entry_other_hooks(self):
        data = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {"type": "command", "command": _USER_HOOK},
                            {"type": "command", "command": "aeg hook-run"},
                        ],
                    }
                ]
            }
        }
        new_data, removed = build_uninstalled_settings(data)
        self.assertEqual(removed, 1)
        kept = new_data["hooks"]["PreToolUse"][0]["hooks"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["command"], _USER_HOOK)

    def test_uninstall_with_no_aegis_removes_nothing(self):
        data = {"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": _USER_HOOK}]}
        ]}}
        new_data, removed = build_uninstalled_settings(data)
        self.assertEqual(removed, 0)
        self.assertEqual(new_data, data)

    def test_codex_config_into_empty_creates_project_hook_block(self):
        text, already = build_installed_codex_config_text(
            "",
            "aeg hook-run --substrate codex",
        )

        self.assertFalse(already)
        self.assertIn("[[hooks.PreToolUse]]", text)
        self.assertIn(f'matcher = "{CODEX_AEGIS_HOOK_MATCHER}"', text)
        self.assertIn("[[hooks.PreToolUse.hooks]]", text)
        self.assertIn('type = "command"', text)
        self.assertIn('command = "aeg hook-run --substrate codex"', text)

    def test_codex_config_preserves_existing_text_and_appends(self):
        original = 'model = "gpt-5"\n\n[tool_suggest]\ndisabled_tools = []\n'

        text, already = build_installed_codex_config_text(
            original,
            "aeg hook-run --substrate codex",
        )

        self.assertFalse(already)
        self.assertTrue(text.startswith(original))
        self.assertIn("[[hooks.PreToolUse]]", text)
        self.assertIn('command = "aeg hook-run --substrate codex"', text)

    def test_codex_config_is_idempotent_when_codex_hook_present(self):
        text, _ = build_installed_codex_config_text(
            "",
            "aeg hook-run --substrate codex",
        )

        again, already = build_installed_codex_config_text(
            text,
            "aeg hook-run --substrate codex",
        )

        self.assertTrue(already)
        self.assertEqual(again, text)
        self.assertEqual(again.count("[[hooks.PreToolUse.hooks]]"), 1)

    def test_codex_config_rejects_aegis_hook_without_codex_substrate(self):
        existing = (
            "[[hooks.PreToolUse]]\n"
            'matcher = "Bash"\n\n'
            "[[hooks.PreToolUse.hooks]]\n"
            'type = "command"\n'
            'command = "aeg hook-run"\n'
        )

        with self.assertRaises(InstallStructureError):
            build_installed_codex_config_text(
                existing,
                "aeg hook-run --substrate codex",
            )


class LoadSettingsTests(unittest.TestCase):
    def test_absent_file_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, existed, error = load_settings(settings_path(tmp))
            self.assertIsNone(error)
            self.assertFalse(existed)
            self.assertEqual(data, {})

    def test_invalid_json_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = settings_path(tmp)
            path.parent.mkdir(parents=True)
            path.write_text("{ not json ,,,", encoding="utf-8")
            data, existed, error = load_settings(path)
            self.assertIsNotNone(error)
            self.assertIsNone(data)
            self.assertTrue(existed)


class CmdFlowTests(unittest.TestCase):
    def test_install_n_cancels_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            rc = cmd_install(
                tmp, assume_yes=False, input_stream=io.StringIO("n\n"), output_stream=out
            )
            self.assertEqual(rc, 0)
            self.assertIn("cancelled", out.getvalue())
            self.assertFalse(settings_path(tmp).exists())

    def test_install_y_writes_and_backs_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = settings_path(tmp)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"hooks": {"PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": _USER_HOOK}]}
                ]}}),
                encoding="utf-8",
            )
            out = io.StringIO()
            rc = cmd_install(
                tmp, assume_yes=False, input_stream=io.StringIO("y\n"), output_stream=out
            )
            self.assertEqual(rc, 0)
            written = json.loads(path.read_text(encoding="utf-8"))
            hooks = [
                h
                for entry in written["hooks"]["PreToolUse"]
                for h in entry["hooks"]
            ]
            commands = [h["command"] for h in hooks]
            self.assertIn(_USER_HOOK, commands)  # user hook preserved
            self.assertTrue(any(is_aegis_hook(h) for h in hooks))
            backups = list(path.parent.glob("settings.json.aegis-backup-*"))
            self.assertEqual(len(backups), 1)  # backup created

    def test_install_default_target_writes_claude_settings_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            rc = cmd_install(tmp, assume_yes=True, output_stream=out)

            self.assertEqual(rc, 0)
            self.assertTrue(settings_path(tmp).exists())
            self.assertFalse(codex_config_path(tmp).exists())
            written = json.loads(settings_path(tmp).read_text(encoding="utf-8"))
            hook = written["hooks"]["PreToolUse"][0]["hooks"][0]
            self.assertTrue(is_aegis_hook(hook))
            self.assertNotIn("--substrate", " ".join([hook["command"], *hook.get("args", [])]))

    def test_install_target_codex_writes_codex_config_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            rc = cmd_install(
                tmp,
                assume_yes=True,
                target=TARGET_CODEX,
                output_stream=out,
            )

            self.assertEqual(rc, 0)
            self.assertFalse(settings_path(tmp).exists())
            path = codex_config_path(tmp)
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("[[hooks.PreToolUse]]", text)
            self.assertIn(f'matcher = "{CODEX_AEGIS_HOOK_MATCHER}"', text)
            self.assertIn("--substrate codex", text)

    def test_install_global_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            rc = cmd_install(tmp, assume_yes=True, global_requested=True, output_stream=out)
            self.assertEqual(rc, 2)
            self.assertIn("not supported", out.getvalue())
            self.assertFalse(settings_path(tmp).exists())

    def test_install_invalid_json_aborts_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = settings_path(tmp)
            path.parent.mkdir(parents=True)
            original = "{ not json ,,,"
            path.write_text(original, encoding="utf-8")
            out = io.StringIO()
            rc = cmd_install(tmp, assume_yes=True, output_stream=out)
            self.assertEqual(rc, 1)
            self.assertIn("aborted", out.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), original)  # untouched

    def test_uninstall_not_installed_is_quiet_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = settings_path(tmp)
            path.parent.mkdir(parents=True)
            path.write_text('{"model":"x"}', encoding="utf-8")
            out = io.StringIO()
            rc = cmd_uninstall(tmp, assume_yes=True, output_stream=out)
            self.assertEqual(rc, 0)
            self.assertIn("nothing to remove", out.getvalue())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"model": "x"})


class SubprocessInstallTests(unittest.TestCase):
    def _env(self):
        import os

        return {"PYTHONPATH": str(REPO_ROOT), "PATH": os.environ.get("PATH", "")}

    def test_subprocess_install_creates_working_hook_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "src.cli", "install", "--path", tmp, "--yes"],
                capture_output=True, text=True, cwd=tmp, env=self._env(),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(settings_path(tmp).read_text(encoding="utf-8"))
            hook = written["hooks"]["PreToolUse"][0]["hooks"][0]
            self.assertTrue(is_aegis_hook(hook))
            self.assertNotIn("--substrate", " ".join([hook["command"], *hook.get("args", [])]))

    def test_subprocess_install_target_codex_creates_codex_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "install",
                    "--path",
                    tmp,
                    "--yes",
                    "--target",
                    "codex",
                ],
                capture_output=True,
                text=True,
                cwd=tmp,
                env=self._env(),
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = codex_config_path(tmp).read_text(encoding="utf-8")
            self.assertIn("[[hooks.PreToolUse]]", text)
            self.assertIn("--substrate codex", text)


if __name__ == "__main__":
    unittest.main()
