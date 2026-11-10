"""Read-only evidence list/show CLI coverage for hook records."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from jangseung.cli.main import _cmd_evidence_list, _cmd_evidence_show
from jangseung.state.evidence_query import REDACTED_CREDENTIAL
from jangseung.state.hook_ledger import append_hook_decision_record


class EvidenceCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.state = self.repo / ".aeg"
        self.state.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_list_is_newest_first_and_honors_limit(self):
        older = self._append("Read", "2026-07-01T00:00:00Z")
        newer = self._append("Write", "2026-07-02T00:00:00Z")

        exit_code, output = self._capture(_cmd_evidence_list, self.repo, limit=1)

        self.assertEqual(exit_code, 0)
        self.assertIn("status: OK", output)
        self.assertIn(newer["record_hash"], output)
        self.assertNotIn(older["record_hash"], output)
        self.assertIn("HOOK", output)
        self.assertIn("hook_record:yes", output)

    def test_show_uses_sections_instead_of_flat_record_dump(self):
        record = self._append("Read", "2026-07-01T00:00:00Z")

        exit_code, output = self._capture(_cmd_evidence_show, self.repo, record["record_hash"][:12])

        self.assertEqual(exit_code, 0)
        for section in ("[summary]", "[decision]", "[integrity]"):
            self.assertIn(section, output)
        self.assertIn("status: OK", output)
        self.assertIn("permission_decision: allow", output)
        self.assertLess(len(output.splitlines()), 40)

    def test_list_and_show_do_not_modify_state(self):
        record = self._append("Read", "2026-07-01T00:00:00Z")
        before = self._state_hash()

        self.assertEqual(self._capture(_cmd_evidence_list, self.repo)[0], 0)
        self.assertEqual(self._capture(_cmd_evidence_show, self.repo, record["record_hash"])[0], 0)

        self.assertEqual(self._state_hash(), before)

    def test_corrupt_ledger_entry_is_unreadable_and_listing_continues(self):
        before = self._append("Read", "2026-07-01T00:00:00Z")
        after = self._append("Write", "2026-07-02T00:00:00Z")
        ledger = self.state / "hook_ledger.jsonl"
        first, second = ledger.read_bytes().splitlines()
        ledger.write_bytes(first + b"\n{not-json\n" + second + b"\n")

        exit_code, output = self._capture(_cmd_evidence_list, self.repo)

        self.assertEqual(exit_code, 0)
        self.assertIn("status: DEGRADED", output)
        self.assertIn(before["record_hash"], output)
        self.assertIn(after["record_hash"], output)
        self.assertIn("hook-ledger-line-2", output)
        self.assertIn("UNREADABLE", output)

    def test_show_redacts_credential_shapes_in_human_and_json_output(self):
        secret = "sk-proj-abcdefghijklmnopqrstuv"
        record = self._append("Read", "2026-07-01T00:00:00Z", reason_codes=[f"debug with {secret}"])

        human_code, human_output = self._capture(_cmd_evidence_show, self.repo, record["record_hash"])
        json_code, json_output = self._capture(
            _cmd_evidence_show,
            self.repo,
            record["record_hash"],
            as_json=True,
        )
        list_code, list_output = self._capture(_cmd_evidence_list, self.repo, as_json=True)

        self.assertEqual((human_code, json_code, list_code), (0, 0, 0))
        self.assertNotIn(secret, human_output)
        self.assertNotIn(secret, json_output)
        self.assertNotIn(secret, list_output)
        self.assertIn(REDACTED_CREDENTIAL, human_output)
        self.assertIn(REDACTED_CREDENTIAL, json_output)
        parsed = json.loads(json_output)
        self.assertEqual(parsed["kind"], "hook")
        self.assertEqual(parsed["record"]["reason_codes"], [f"debug with {REDACTED_CREDENTIAL}"])

    def test_empty_state_is_a_successful_empty_list(self):
        exit_code, output = self._capture(_cmd_evidence_list, self.repo)
        json_code, json_output = self._capture(_cmd_evidence_list, self.repo, as_json=True)

        self.assertEqual((exit_code, json_code), (0, 0))
        self.assertIn("status: EMPTY", output)
        self.assertEqual(json.loads(json_output), {"items": [], "status": "EMPTY"})

    def test_state_left_by_the_removed_run_runtime_is_ignored_and_untouched(self):
        run_dir = self.state / "runs" / "run-legacy"
        run_dir.mkdir(parents=True)
        for filename in ("run.json", "evidence.json", "manifest.json"):
            (run_dir / filename).write_text("{}\n", encoding="utf-8")
        entry = {"run_id": "run-legacy", "recorded_at": "2026-07-03T00:00:00Z", "status": "CLEAN_CORE"}
        (self.state / "ledger.jsonl").write_text(json.dumps(entry) + "\n{not-json\n", encoding="utf-8")
        (self.state / "config.json").write_text('{"legacy": true}\n', encoding="utf-8")
        before = self._state_hash()

        empty_code, empty_output = self._capture(_cmd_evidence_list, self.repo, as_json=True)
        show_code, show_output = self._capture(_cmd_evidence_show, self.repo, "run-legacy", as_json=True)
        self.assertEqual(self._state_hash(), before)
        record = self._append("Read", "2026-07-01T00:00:00Z")
        list_code, list_output = self._capture(_cmd_evidence_list, self.repo, as_json=True)

        self.assertEqual((empty_code, show_code, list_code), (0, 1, 0))
        self.assertEqual(json.loads(empty_output), {"items": [], "status": "EMPTY"})
        self.assertEqual(json.loads(show_output)["status"], "NOT_FOUND")
        listed = json.loads(list_output)
        self.assertEqual(listed["status"], "OK")
        self.assertEqual([(item["kind"], item["id"]) for item in listed["items"]], [("hook", record["record_hash"])])
        for name in ("ledger.jsonl", "config.json", "runs/run-legacy/evidence.json"):
            self.assertTrue((self.state / name).is_file(), name)
        self.assertEqual((self.state / "ledger.jsonl").read_text(encoding="utf-8"), json.dumps(entry) + "\n{not-json\n")

    def _append(self, tool_name: str, timestamp: str, *, reason_codes: list[str] | None = None) -> dict:
        return append_hook_decision_record(
            self.repo,
            substrate="claude-code",
            tool_name=tool_name,
            hook_decision="allow",
            permission_decision="allow",
            fail_closed=False,
            reason_codes=reason_codes or ["fixture"],
            exit_code=0,
            timestamp=timestamp,
        )

    def _state_hash(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(self.state.rglob("*"), key=lambda item: item.as_posix()):
            digest.update(path.relative_to(self.state).as_posix().encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _capture(function, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = function(*args, **kwargs)
        return exit_code, output.getvalue()


if __name__ == "__main__":
    unittest.main()
