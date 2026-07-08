"""Tests for Phase 11-D-2 ``aeg hook-run`` stdin/stdout/exit-code wiring."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.cli.hook_run import (
    CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE,
    CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON,
    EXIT_ALLOW_OR_ASK,
    EXIT_BLOCK,
    PERMISSION_ALLOW,
    PERMISSION_ASK,
    PERMISSION_DENY,
    PHASE11D_2_COMPLETE_LABEL,
    SUBSTRATE_CLAUDE_CODE,
    SUBSTRATE_CODEX,
    build_aeg_hook_run_contract_evidence,
    render_hook_response,
)
from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT

REPO_ROOT = Path(__file__).resolve().parent.parent


def _render(payload_or_text, repo_root):
    if isinstance(payload_or_text, str):
        raw = payload_or_text
    else:
        raw = json.dumps(payload_or_text)
    return render_hook_response(raw, repo_root=repo_root)


def _render_for_substrate(payload_or_text, repo_root, substrate):
    if isinstance(payload_or_text, str):
        raw = payload_or_text
    else:
        raw = json.dumps(payload_or_text)
    return render_hook_response(raw, repo_root=repo_root, substrate=substrate)


def _permission_from_stdout(stdout_json: str) -> str:
    parsed = json.loads(stdout_json)
    return parsed["hookSpecificOutput"]["permissionDecision"]


class RenderHookResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo_root = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- normal (safe / non-blocking) -----------------------------------

    def test_normal_write_maps_to_allow_exit_zero(self):
        result = _render(
            {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}, "tool_use_id": "t1"},
            self.repo_root,
        )
        self.assertEqual(result.permission_decision, PERMISSION_ALLOW)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertEqual(_permission_from_stdout(result.stdout_json), PERMISSION_ALLOW)

    def test_normal_edit_maps_to_allow_exit_zero(self):
        result = _render(
            {"tool_name": "Edit", "tool_input": {"file_path": "app.py", "old_string": "a", "new_string": "b"}, "tool_use_id": "t2"},
            self.repo_root,
        )
        self.assertEqual(result.permission_decision, PERMISSION_ALLOW)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)

    def test_normal_apply_patch_maps_to_allow_exit_zero(self):
        result = _render(
            {
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: README.md\n"
                        "@@\n"
                        "+new line\n"
                        "*** End Patch"
                    )
                },
                "tool_use_id": "t-apply-patch",
            },
            self.repo_root,
        )
        self.assertEqual(result.permission_decision, PERMISSION_ALLOW)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertNotIn("unsupported_or_unknown_tool_name:apply_patch", result.reason)

    def test_single_quoted_apply_patch_normal_path_maps_to_allow_exit_zero(self):
        result = _render(
            {
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Add File: 'README.md'\n"
                        "+new line\n"
                        "*** End Patch"
                    )
                },
                "tool_use_id": "t-apply-patch",
            },
            self.repo_root,
        )
        self.assertEqual(result.permission_decision, PERMISSION_ALLOW)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertNotIn("unsupported_or_unknown_tool_name:apply_patch", result.reason)

    def test_read_never_denies_and_never_hard_blocks(self):
        result = _render(
            {"tool_name": "Read", "tool_input": {"file_path": "app.py"}, "tool_use_id": "t3"},
            self.repo_root,
        )
        self.assertIn(result.permission_decision, (PERMISSION_ALLOW, PERMISSION_ASK))
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)

    def test_unclassified_bash_default_substrate_maps_to_ask(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dd if=/dev/zero of=tmp.bin bs=1 count=1"},
            "tool_use_id": "t-bash",
        }

        result = _render(payload, self.repo_root)

        self.assertEqual(result.permission_decision, PERMISSION_ASK)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertIn("substrate=claude-code", result.reason)
        self.assertNotIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, result.reason)

    def test_unclassified_bash_claude_code_substrate_still_maps_to_ask(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dd if=/dev/zero of=tmp.bin bs=1 count=1"},
            "tool_use_id": "t-bash",
        }

        result = _render_for_substrate(payload, self.repo_root, SUBSTRATE_CLAUDE_CODE)

        self.assertEqual(result.permission_decision, PERMISSION_ASK)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertNotIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, result.reason)

    def test_unclassified_bash_codex_substrate_upgrades_ask_defer_to_deny(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dd if=/dev/zero of=tmp.bin bs=1 count=1"},
            "tool_use_id": "t-bash",
        }

        result = _render_for_substrate(payload, self.repo_root, SUBSTRATE_CODEX)

        self.assertEqual(result.permission_decision, PERMISSION_DENY)
        self.assertEqual(result.exit_code, EXIT_BLOCK)
        self.assertEqual(result.hook_decision, "defer")
        self.assertIn("substrate=codex", result.reason)
        self.assertIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, result.reason)

    def test_unknown_substrate_defaults_to_claude_code_ask_behavior(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "dd if=/dev/zero of=tmp.bin bs=1 count=1"},
            "tool_use_id": "t-bash",
        }

        result = _render_for_substrate(payload, self.repo_root, "unknown")

        self.assertEqual(result.permission_decision, PERMISSION_ASK)
        self.assertEqual(result.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertIn("substrate=claude-code", result.reason)
        self.assertNotIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, result.reason)

    # --- dangerous (must deny + block) ----------------------------------

    def test_protected_path_writes_deny_and_block(self):
        for path in (".env", ".github/workflows/ci.yml", ".aeg/x", "Dockerfile", "pyproject.toml", "src/law/x.py"):
            with self.subTest(path=path):
                result = _render(
                    {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}, "tool_use_id": "t"},
                    self.repo_root,
                )
                self.assertEqual(result.permission_decision, PERMISSION_DENY)
                self.assertEqual(result.exit_code, EXIT_BLOCK)
                self.assertEqual(_permission_from_stdout(result.stdout_json), PERMISSION_DENY)

    def test_apply_patch_risky_or_malformed_targets_deny_and_block(self):
        cases = (
            (
                "env_add",
                "*** Begin Patch\n*** Add File: .env\n+API_KEY=x\n*** End Patch",
            ),
            (
                "quoted_env_add",
                "*** Begin Patch\n*** Add File: \".env\"\n+API_KEY=x\n*** End Patch",
            ),
            (
                "workflow_add",
                "*** Begin Patch\n*** Add File: .github/workflows/x.yml\n+name: x\n*** End Patch",
            ),
            (
                "env_delete",
                "*** Begin Patch\n*** Delete File: .env\n*** End Patch",
            ),
            (
                "repo_external",
                "*** Begin Patch\n*** Update File: /etc/passwd\n@@\n+x\n*** End Patch",
            ),
            (
                "mixed",
                "*** Begin Patch\n*** Update File: README.md\n@@\n+x\n*** Add File: .env\n+K=v\n*** End Patch",
            ),
            (
                "malformed",
                "*** Begin Patch\n*** Update File: README.md\n@@\n+x",
            ),
            (
                "malformed_quote",
                "*** Begin Patch\n*** Add File: READ\"ME.md\n+x\n*** End Patch",
            ),
        )

        for label, command in cases:
            with self.subTest(label=label):
                result = _render(
                    {
                        "tool_name": "apply_patch",
                        "tool_input": {"command": command},
                        "tool_use_id": "t",
                    },
                    self.repo_root,
                )
                self.assertEqual(result.permission_decision, PERMISSION_DENY)
                self.assertEqual(result.exit_code, EXIT_BLOCK)
                self.assertNotIn("unsupported_or_unknown_tool_name:apply_patch", result.reason)

    def test_dangerous_bash_denies_and_blocks(self):
        for command in ("rm -rf /", "git reset --hard HEAD~3", "git clean -fd"):
            with self.subTest(command=command):
                result = _render(
                    {"tool_name": "Bash", "tool_input": {"command": command}, "tool_use_id": "t"},
                    self.repo_root,
                )
                self.assertEqual(result.permission_decision, PERMISSION_DENY)
                self.assertEqual(result.exit_code, EXIT_BLOCK)

    def test_codex_substrate_does_not_change_clear_deny_or_allow(self):
        deny = _render_for_substrate(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
                "tool_use_id": "t-deny",
            },
            self.repo_root,
            SUBSTRATE_CODEX,
        )
        allow = _render_for_substrate(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"},
                "tool_use_id": "t-allow",
            },
            self.repo_root,
            SUBSTRATE_CODEX,
        )

        self.assertEqual(deny.permission_decision, PERMISSION_DENY)
        self.assertEqual(deny.exit_code, EXIT_BLOCK)
        self.assertNotIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, deny.reason)
        self.assertEqual(allow.permission_decision, PERMISSION_ALLOW)
        self.assertEqual(allow.exit_code, EXIT_ALLOW_OR_ASK)
        self.assertNotIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, allow.reason)

    def test_protected_write_with_missing_tool_use_id_still_denies(self):
        # Downgrade guard: an invalid input must not skip path judgment and
        # become ask. Missing tool_use_id is invalid -> hard deny.
        result = _render(
            {"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "x"}},
            self.repo_root,
        )
        self.assertEqual(result.permission_decision, PERMISSION_DENY)
        self.assertEqual(result.exit_code, EXIT_BLOCK)

    # --- fail-closed (never allow) --------------------------------------

    def test_fail_closed_inputs_never_allow_and_block(self):
        cases = {
            "invalid_json": "this is not json {{{",
            "empty_stdin": "",
            "whitespace_stdin": "   \n  ",
            "array_json": "[1,2,3]",
            "string_json": '"hello"',
            "number_json": "42",
            "null_json": "null",
        }
        for label, raw in cases.items():
            with self.subTest(case=label):
                result = render_hook_response(raw, repo_root=self.repo_root)
                self.assertNotEqual(result.permission_decision, PERMISSION_ALLOW)
                self.assertEqual(result.permission_decision, PERMISSION_DENY)
                self.assertEqual(result.exit_code, EXIT_BLOCK)
                self.assertTrue(result.fail_closed)
                self.assertNotEqual(_permission_from_stdout(result.stdout_json), PERMISSION_ALLOW)

    def test_invalid_shape_inputs_hard_deny(self):
        cases = {
            "missing_all": {},
            "missing_tool_use_id": {"tool_name": "Write", "tool_input": {"file_path": "x"}},
            "unknown_tool": {"tool_name": "Frobnicate", "tool_input": {"x": 1}, "tool_use_id": "t"},
            "null_tool_input": {"tool_name": "Bash", "tool_input": None, "tool_use_id": "t"},
            "int_tool_name": {"tool_name": 5, "tool_input": {}, "tool_use_id": "t"},
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                result = _render(payload, self.repo_root)
                self.assertEqual(result.permission_decision, PERMISSION_DENY)
                self.assertEqual(result.exit_code, EXIT_BLOCK)
                self.assertTrue(result.fail_closed)

    def test_no_input_ever_yields_allow_except_genuinely_safe(self):
        # Sweep the full failure + dangerous matrix and assert not a single one
        # yields allow. (Safe reads/writes are covered separately.)
        never_allow = [
            "not json",
            "",
            "[1]",
            '{"tool_name":"Write","tool_input":{"file_path":".env","content":"k"},"tool_use_id":"t"}',
            '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"},"tool_use_id":"t"}',
            '{"tool_name":"Zzz","tool_input":{},"tool_use_id":"t"}',
            '{"tool_name":"Write"}',
        ]
        for raw in never_allow:
            with self.subTest(raw=raw[:40]):
                result = render_hook_response(raw, repo_root=self.repo_root)
                self.assertNotEqual(result.permission_decision, PERMISSION_ALLOW)

    # --- secret safety ---------------------------------------------------

    def test_secret_in_tool_input_not_echoed_in_output(self):
        secret = "sk-supersecret-DO-NOT-LEAK-9182"
        result = _render(
            {"tool_name": "Write", "tool_input": {"file_path": ".env", "content": f"API_KEY={secret}"}, "tool_use_id": "t"},
            self.repo_root,
        )
        self.assertNotIn(secret, result.stdout_json)
        self.assertNotIn(secret, result.stderr_text)
        self.assertNotIn(secret, result.reason)

    # --- Claude Code output schema ---------------------------------------

    def test_stdout_matches_claude_code_hookspecificoutput_schema(self):
        result = _render(
            {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}, "tool_use_id": "t"},
            self.repo_root,
        )
        parsed = json.loads(result.stdout_json)
        self.assertIn("hookSpecificOutput", parsed)
        hso = parsed["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], CLAUDE_CODE_HOOK_EVENT_NAME_PRETOOLUSE)
        self.assertIn(hso["permissionDecision"], (PERMISSION_ALLOW, PERMISSION_DENY, PERMISSION_ASK))
        self.assertIsInstance(hso["permissionDecisionReason"], str)

    def test_deny_writes_stderr_reason_allow_ask_do_not(self):
        deny = _render(
            {"tool_name": "Write", "tool_input": {"file_path": ".env", "content": "x"}, "tool_use_id": "t"},
            self.repo_root,
        )
        self.assertTrue(deny.stderr_text)
        ask = _render(
            {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}, "tool_use_id": "t"},
            self.repo_root,
        )
        self.assertEqual(ask.stderr_text, "")

    def test_evidence_records_real_io_and_no_install(self):
        evidence = build_aeg_hook_run_contract_evidence()
        self.assertEqual(evidence["completion_label"], PHASE11D_2_COMPLETE_LABEL)
        self.assertTrue(evidence["reads_stdin"])
        self.assertTrue(evidence["writes_stdout"])
        self.assertTrue(evidence["returns_exit_code"])
        self.assertTrue(evidence["stdin_treated_as_untrusted_raw_executor_output"])
        self.assertFalse(evidence["judgment_brain_modified"])
        self.assertFalse(evidence["failure_ever_maps_to_allow"])
        self.assertFalse(evidence["raw_tool_input_echoed_in_reason"])
        self.assertEqual(
            evidence["substrate_selection_source"],
            "explicit_hook_run_substrate_argument",
        )
        self.assertFalse(evidence["tool_name_used_for_substrate_detection"])
        self.assertEqual(evidence["default_substrate"], SUBSTRATE_CLAUDE_CODE)
        self.assertTrue(evidence["missing_or_unknown_substrate_defaults_to_claude_code"])
        self.assertTrue(evidence["codex_substrate_ask_defer_upgraded_to_deny"])
        self.assertEqual(
            evidence["codex_substrate_upgrade_reason_code"],
            CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON,
        )
        self.assertFalse(evidence["settings_json_modified"])
        self.assertFalse(evidence["hook_installed"])
        self.assertFalse(evidence["claude_code_execution_performed"])
        self.assertFalse(evidence["tool_execution_performed"])
        self.assertFalse(evidence["store_write_performed"])
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)


class AegHookRunSubprocessEndToEndTests(unittest.TestCase):
    """Proves the real stdin -> stdout -> exit-code path via an actual process."""

    def _invoke(self, stdin_text: str, extra_args: list[str] | None = None):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"PYTHONPATH": str(REPO_ROOT), "PATH": __import__("os").environ.get("PATH", "")}
            command = [sys.executable, "-m", "src.cli", "hook-run"]
            command.extend(extra_args or [])
            proc = subprocess.run(
                command,
                input=stdin_text,
                capture_output=True,
                text=True,
                cwd=tmp,
                env=env,
            )
        return proc

    def test_subprocess_dangerous_write_denies_exit_2(self):
        proc = self._invoke(
            '{"tool_name":"Write","tool_input":{"file_path":".env","content":"x"},"tool_use_id":"t"}'
        )
        self.assertEqual(proc.returncode, EXIT_BLOCK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_DENY)

    def test_subprocess_unclassified_bash_default_substrate_asks_exit_0(self):
        proc = self._invoke(
            '{"tool_name":"Bash","tool_input":{"command":"dd if=/dev/zero of=tmp.bin bs=1 count=1"},"tool_use_id":"t"}'
        )
        self.assertEqual(proc.returncode, EXIT_ALLOW_OR_ASK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_ASK)

    def test_subprocess_unclassified_bash_codex_substrate_denies_exit_2(self):
        proc = self._invoke(
            '{"tool_name":"Bash","tool_input":{"command":"dd if=/dev/zero of=tmp.bin bs=1 count=1"},"tool_use_id":"t"}',
            ["--substrate", "codex"],
        )
        self.assertEqual(proc.returncode, EXIT_BLOCK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_DENY)
        self.assertIn(CODEX_ASK_DEFER_UPGRADED_TO_DENY_REASON, proc.stdout)

    def test_subprocess_normal_write_allows_exit_0(self):
        proc = self._invoke(
            '{"tool_name":"Write","tool_input":{"file_path":"src/app.py","content":"x"},"tool_use_id":"t"}'
        )
        self.assertEqual(proc.returncode, EXIT_ALLOW_OR_ASK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_ALLOW)

    def test_subprocess_invalid_json_denies_exit_2(self):
        proc = self._invoke("this is not json {{{")
        self.assertEqual(proc.returncode, EXIT_BLOCK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_DENY)

    def test_subprocess_empty_stdin_denies_exit_2(self):
        proc = self._invoke("")
        self.assertEqual(proc.returncode, EXIT_BLOCK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_DENY)

    def test_subprocess_dangerous_bash_denies_exit_2(self):
        proc = self._invoke(
            '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"},"tool_use_id":"t"}'
        )
        self.assertEqual(proc.returncode, EXIT_BLOCK)
        self.assertEqual(_permission_from_stdout(proc.stdout), PERMISSION_DENY)


if __name__ == "__main__":
    unittest.main()
