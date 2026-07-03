import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agents.noop import execute_contract as noop_execute_contract
from src.cli.main import _cmd_init, _cmd_run
from src.contracts import (
    B1_AEG_DIRECT_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    PHASE11B_LIVE_EXECUTOR_NOT_STARTED,
    SAFE_DEFAULT,
    STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED,
    STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED,
    STORE_WRITE_MEDIATION_FIELDS,
    STORE_WRITE_MEDIATION_RESULT_BLOCKED,
    STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED,
    STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED,
    STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
)
from src.evidence.binding import (
    manifest_hash,
    sha256_json,
    store_write_mediation_manifest_fields,
)
from src.evidence.store_write_mediation import expected_store_write_mediation_metadata_hash
from src.evidence.verify import verify_latest


class Phase11BStoreWriteMediationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_actual_run_blocks_executor_attributed_aeg_direct_and_traversal_writes(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)

        evidence, _ = self._latest_evidence_with_path()
        blocked_events = [
            event
            for event in evidence["store_write_mediation_events"]
            if event["write_provenance_type"] == STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED
        ]

        self.assertEqual(len(blocked_events), 2)
        self.assertTrue(evidence["store_write_mediation_enabled"])
        self.assertEqual(evidence["store_write_mediation_scope"], "executor_attributed_aeg_direct_traversal_writes_only")
        self.assertTrue(evidence["executor_attributed_write_blocked"])
        self.assertTrue(evidence["trusted_runtime_write_allowed"])
        self.assertEqual(evidence["blocked_write_target_count"], 2)
        self.assertEqual(evidence["blocked_write_created_files_count"], 0)
        self.assertEqual(evidence["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
        self.assertEqual(evidence["known_gap_aeg_direct_traversal_status"], STORE_WRITE_KNOWN_GAP_AEG_DIRECT_TRAVERSAL_BLOCKED)
        self.assertEqual(evidence["known_gap_non_aeg_status"], STORE_WRITE_KNOWN_GAP_NON_AEG_UNCHANGED)
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["phase11b_live_executor_status"], PHASE11B_LIVE_EXECUTOR_NOT_STARTED)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)

        target_classes = {event["guard_decision"]["target_class"] for event in blocked_events}
        self.assertEqual(target_classes, {B1_AEG_DIRECT_TARGET_DENIED, B1_AEG_TRAVERSAL_TARGET_DENIED})
        for event in blocked_events:
            self.assertTrue(event["guard_router_invoked"])
            self.assertFalse(event["write_performed"])
            self.assertFalse(event["target_file_created"])
            self.assertFalse(event["fallback_to_unwired"])
            self.assertEqual(event["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_BLOCKED)
            self.assertEqual(event["write_provenance_type"], STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED)
            self.assertFalse(Path(event["canonical_target"]).exists())

        self.assertFalse((self.repo / ".aeg" / "executor-direct-blocked.json").exists())
        self.assertFalse((self.repo / ".aeg" / "executor-traversal-blocked.json").exists())
        self.assertTrue(verify_latest(self.repo).ok)

    def test_trusted_runtime_save_run_still_writes_ledger_evidence_and_manifest(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)

        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"

        self.assertTrue(evidence_path.exists())
        self.assertTrue(manifest_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertTrue(ledger_path.read_text(encoding="utf-8").strip())
        self.assertTrue(evidence["trusted_runtime_write_allowed"])
        self.assertFalse(evidence["executor_attributed_write_blocked"])
        self.assertEqual(evidence["blocked_write_created_files_count"], 0)
        self.assertEqual(
            evidence["bound_store_write_mediation_metadata_hash"],
            manifest["store_write_mediation_manifest_hash"],
        )
        self.assertTrue(verify_latest(self.repo).ok)

    def test_executor_self_report_cannot_claim_trusted_provenance(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)

        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        spoof_event = next(
            event
            for event in evidence["store_write_mediation_events"]
            if event["write_provenance_type"] == STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED
            and event["executor_claimed_provenance"] == STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        )
        self.assertEqual(spoof_event["write_provenance_type"], STORE_WRITE_PROVENANCE_EXECUTOR_ATTRIBUTED)
        self.assertFalse(spoof_event["executor_self_report_used"])
        self.assertFalse(spoof_event["trusted_runtime_claim_allowed"])

        evidence["store_write_mediation_events"][0]["executor_self_report_used"] = True
        evidence["store_write_mediation_events"][0]["write_provenance_type"] = STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("executor self-report trusted provenance" in error for error in verify.errors),
            verify.errors,
        )

    def test_deterministic_call_site_provenance_is_required(self):
        self._init()
        self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["write_provenance_source"] = "executor_self_report"
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(any("write_provenance_source mismatch" in error for error in verify.errors), verify.errors)

    def test_wired_path_failure_falls_back_to_existing_unwired_store_write(self):
        self._init()
        with patch("src.state.store._trusted_runtime_store_write_gate", side_effect=RuntimeError("wired route failed")):
            self.assertEqual(self._run("fix typo in README"), 0)

        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"

        self.assertTrue(evidence_path.exists())
        self.assertTrue(manifest_path.exists())
        self.assertTrue(ledger_path.exists())
        self.assertTrue(evidence["rollback_used"])
        self.assertTrue(evidence["fallback_to_unwired"])
        self.assertTrue(evidence["fallback_evidence_recorded"])
        self.assertEqual(evidence["write_mediation_result"], STORE_WRITE_MEDIATION_RESULT_FALLBACK_TO_UNWIRED)
        self.assertTrue(
            any(event["fallback_to_unwired"] for event in evidence["store_write_mediation_events"])
        )
        self.assertEqual(
            evidence["bound_store_write_mediation_metadata_hash"],
            manifest["store_write_mediation_manifest_hash"],
        )
        self.assertTrue(verify_latest(self.repo).ok)

    def test_blocked_claim_with_created_file_count_is_rejected_even_when_rebound(self):
        self._init()
        with patch("src.cli.main.execute_contract", side_effect=self._executor_with_aeg_write_attempts):
            self.assertEqual(self._run("fix typo in README"), 0)
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["blocked_write_created_files_count"] = 1
        self._rebind_store_write_mediation(evidence, evidence_path, manifest, manifest_path)

        verify = verify_latest(self.repo)

        self.assertFalse(verify.ok)
        self.assertTrue(
            any("blocked_write_created_files_count > 0" in error for error in verify.errors),
            verify.errors,
        )

    def _executor_with_aeg_write_attempts(self, task_text, classification, law_result):
        result = noop_execute_contract(task_text, classification, law_result)
        result["executor_attributed_aeg_write_attempts"] = [
            {
                "target": ".aeg/executor-direct-blocked.json",
                "payload": "blocked direct",
                "executor_claimed_provenance": STORE_WRITE_PROVENANCE_TRUSTED_RUNTIME,
            },
            {
                "target": ".aeg/runs/../executor-traversal-blocked.json",
                "payload": "blocked traversal",
            },
        ]
        return result

    def _init(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return _cmd_init(self.repo)

    def _run(self, task):
        with contextlib.redirect_stdout(io.StringIO()):
            return _cmd_run(self.repo, task)

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def _latest_evidence_with_path(self):
        entry = self._ledger_entries()[-1]
        path = self.repo / entry["evidence_path"]
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_manifest_with_path(self):
        entry = self._ledger_entries()[-1]
        path = self.repo / entry["manifest_path"]
        return json.loads(path.read_text(encoding="utf-8")), path

    def _ledger_entries(self):
        ledger_path = self.repo / ".aeg" / "ledger.jsonl"
        return [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _rebind_store_write_mediation(self, evidence, evidence_path, manifest, manifest_path):
        evidence["store_write_mediation_metadata_hash"] = expected_store_write_mediation_metadata_hash(evidence)
        for field in STORE_WRITE_MEDIATION_FIELDS:
            manifest[field] = evidence[field]
        manifest["store_write_mediation_manifest_hash"] = sha256_json(
            store_write_mediation_manifest_fields(manifest)
        )
        evidence["bound_store_write_mediation_metadata_hash"] = manifest["store_write_mediation_manifest_hash"]
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
