"""Live hook decision recording and hash-chain verification tests."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.cli.hook_run import (
    EXIT_ALLOW_OR_ASK,
    EXIT_BLOCK,
    HOOK_DECISION_RECORDING_FAILED_REASON,
    SUBSTRATE_CODEX,
    build_aeg_hook_run_contract_evidence,
    render_hook_response,
    run_aeg_hook_run,
)
from src.cli.main import (
    _cmd_evidence_list,
    _cmd_evidence_show,
    _cmd_evidence_verify_hooks,
)
from src.state.hook_ledger import (
    HOOK_LEDGER_FILE,
    HOOK_RECORD_HASH_GENESIS,
    read_hook_ledger,
    verify_hook_ledger,
)


class HookLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        (self.repo / ".aeg").mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_allow_ask_deny_and_fail_closed_are_recorded(self):
        cases = (
            (
                {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "allow"},
                "allow",
                False,
            ),
            (
                {"tool_name": "Bash", "tool_input": {"command": "dd if=/dev/zero of=x bs=1 count=1"}, "tool_use_id": "ask"},
                "ask",
                False,
            ),
            (
                {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}, "tool_use_id": "deny"},
                "deny",
                False,
            ),
            ("not-json", "deny", True),
        )
        for raw, expected_permission, expected_fail_closed in cases:
            exit_code, payload, _ = self._run(raw)
            self.assertEqual(payload["hookSpecificOutput"]["permissionDecision"], expected_permission)
            self.assertIn(exit_code, (EXIT_ALLOW_OR_ASK, EXIT_BLOCK))

        items = read_hook_ledger(self.repo)
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item.readable for item in items))
        self.assertEqual(
            [(item.record["permission_decision"], item.record["fail_closed"]) for item in items],
            [("allow", False), ("ask", False), ("deny", False), ("deny", True)],
        )
        self.assertEqual(items[0].record["previous_record_hash"], HOOK_RECORD_HASH_GENESIS)
        self.assertEqual(items[-1].record["previous_record_hash"], items[-2].record["record_hash"])

    def test_raw_tool_input_and_secret_are_never_stored(self):
        secret = "sk-proj-DO-NOT-STORE-abcdefghijklmnop"
        self._run(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": ".env", "content": f"API_KEY={secret}"},
                "tool_use_id": "secret",
            }
        )

        ledger_text = (self.repo / ".aeg" / HOOK_LEDGER_FILE).read_text(encoding="utf-8")
        self.assertNotIn(secret, ledger_text)
        self.assertNotIn("tool_input", ledger_text)
        record = json.loads(ledger_text)
        self.assertEqual(record["tool_name"], "Write")

    def test_recording_failure_preserves_judgment_and_adds_reason_code(self):
        raw = json.dumps(
            {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "t"}
        )
        before = render_hook_response(raw, repo_root=self.repo)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("src.cli.hook_run.append_hook_decision_record", side_effect=OSError("disk unavailable")):
            exit_code = run_aeg_hook_run(
                stdin=io.StringIO(raw),
                stdout=stdout,
                stderr=stderr,
                repo_root=self.repo,
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, before.exit_code)
        self.assertEqual(
            payload["hookSpecificOutput"]["permissionDecision"],
            before.permission_decision,
        )
        self.assertIn(HOOK_DECISION_RECORDING_FAILED_REASON, stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_hash_chain_passes_then_tampering_fails(self):
        self._run({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "1"})
        self._run({"tool_name": "Read", "tool_input": {"file_path": "LICENSE"}, "tool_use_id": "2"})
        self.assertTrue(verify_hook_ledger(self.repo).ok)

        path = self.repo / ".aeg" / HOOK_LEDGER_FILE
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        records[0]["tool_name"] = "Tampered"
        path.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")

        result = verify_hook_ledger(self.repo)
        self.assertFalse(result.ok)
        self.assertTrue(any("record_hash mismatch" in error for error in result.errors))

    def test_middle_record_deletion_breaks_sequence_and_previous_hash(self):
        for index in range(3):
            self._run(
                {"tool_name": "Read", "tool_input": {"file_path": f"file-{index}"}, "tool_use_id": str(index)}
            )
        path = self.repo / ".aeg" / HOOK_LEDGER_FILE
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join((lines[0], lines[2])) + "\n", encoding="utf-8")

        result = verify_hook_ledger(self.repo)

        self.assertFalse(result.ok)
        self.assertTrue(any("sequence_number mismatch" in error for error in result.errors))
        self.assertTrue(any("previous_record_hash mismatch" in error for error in result.errors))

    def test_substrate_exit_codes_are_recorded_exactly(self):
        dangerous = {
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
            "tool_use_id": "dangerous",
        }
        claude_exit, _, _ = self._run(dangerous)
        codex_exit, _, _ = self._run(dangerous, substrate=SUBSTRATE_CODEX)
        records = [item.record for item in read_hook_ledger(self.repo)]

        self.assertEqual(claude_exit, EXIT_BLOCK)
        self.assertEqual(records[0]["exit_code"], EXIT_BLOCK)
        self.assertEqual(codex_exit, EXIT_ALLOW_OR_ASK)
        self.assertEqual(records[1]["exit_code"], EXIT_ALLOW_OR_ASK)
        self.assertEqual(records[1]["substrate"], SUBSTRATE_CODEX)

    def test_recording_does_not_change_golden_permission_or_exit(self):
        cases = (
            {"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "allow"},
            {"tool_name": "Write", "tool_input": {"file_path": "src/app.py", "content": "x"}, "tool_use_id": "allow-write"},
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}, "tool_use_id": "deny"},
            "not-json",
        )
        for raw in cases:
            encoded = raw if isinstance(raw, str) else json.dumps(raw)
            before = render_hook_response(encoded, repo_root=self.repo)
            after_exit, after_payload, _ = self._run(raw)
            with self.subTest(raw=encoded[:30]):
                self.assertEqual(after_exit, before.exit_code)
                self.assertEqual(
                    after_payload["hookSpecificOutput"]["permissionDecision"],
                    before.permission_decision,
                )

    def test_hook_records_are_listed_shown_and_verified_by_cli(self):
        self._git_init()
        self._run({"tool_name": "Read", "tool_input": {"file_path": "README.md"}, "tool_use_id": "cli"})
        record = read_hook_ledger(self.repo)[0].record

        list_code, list_output = self._capture(_cmd_evidence_list, self.repo)
        show_code, show_output = self._capture(
            _cmd_evidence_show,
            self.repo,
            record["record_hash"][:12],
        )
        verify_code, verify_output = self._capture(_cmd_evidence_verify_hooks, self.repo)

        self.assertEqual((list_code, show_code, verify_code), (0, 0, 0))
        self.assertIn("HOOK", list_output)
        self.assertIn("[decision]", show_output)
        self.assertIn("permission_decision: allow", show_output)
        self.assertIn("status: PASS", verify_output)

    def test_contract_matches_the_recording_wiring(self):
        contract = build_aeg_hook_run_contract_evidence()
        self.assertTrue(contract["store_write_performed"])
        self.assertEqual(contract["store_write_scope"], ".aeg/hook_ledger.jsonl")
        self.assertTrue(contract["hook_recording_append_only"])
        self.assertTrue(contract["hook_recording_tamper_evident_not_tamper_proof"])
        self.assertFalse(contract["raw_tool_input_stored_in_hook_ledger"])
        self.assertFalse(contract["recording_failure_changes_permission_decision"])
        self.assertFalse(contract["recording_failure_changes_exit_code"])

    def _run(self, payload_or_text, *, substrate=None):
        raw = payload_or_text if isinstance(payload_or_text, str) else json.dumps(payload_or_text)
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = run_aeg_hook_run(
            stdin=io.StringIO(raw),
            stdout=stdout,
            stderr=stderr,
            repo_root=self.repo,
            substrate=substrate,
        )
        return exit_code, json.loads(stdout.getvalue()), stderr.getvalue()

    def _git_init(self) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    @staticmethod
    def _capture(function, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = function(*args, **kwargs)
        return exit_code, output.getvalue()


if __name__ == "__main__":
    unittest.main()
