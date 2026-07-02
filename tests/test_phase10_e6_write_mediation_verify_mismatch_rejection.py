import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    BYPASS_RESULT_MISMATCH_REJECTED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    MEDIATED_WRITE_BOUNDARY_FIELDS,
    MEDIATED_WRITE_EVIDENCE_MISMATCH_REJECTED,
    NOT_CHECKED_PASS_OVERCLAIM_REJECTED,
    PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED,
    REPORTED_ONLY_PROOF_REJECTED,
    RUNTIME_WIRING_NOT_IMPLEMENTED,
    STATUS_OVERCLAIM_REJECTED,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
    WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED,
)
from src.evidence.binding import manifest_hash, sha256_json
from src.evidence.mediated_write_boundary import expected_mediated_write_boundary_metadata_hash


REPO_ROOT = Path(__file__).resolve().parents[1]


class Phase10E6WriteMediationVerifyMismatchRejectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self._git("init")
        self._git("config", "user.email", "aegis@example.invalid")
        self._git("config", "user.name", "Aegis Test")
        (self.repo / ".gitignore").write_text(".aeg/\n.env\n.env.*\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test\n", encoding="utf-8")
        (self.repo / "src" / "agents").mkdir(parents=True)
        (self.repo / "src" / "agents" / "executor.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.repo / "src" / "classify").mkdir(parents=True)
        (self.repo / "src" / "classify" / "rules.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "init")
        self._aeg("init")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_normal_phase10e_component_state_replays_consistent(self):
        self._aeg("run", "fix typo in README")

        verify = self._aeg("verify")
        evidence = self._latest_evidence()

        self._assert_verify_consistent(verify)
        self.assertEqual(
            evidence["phase10e_write_mediation_component_status"],
            PHASE10E_WRITE_MEDIATION_COMPONENTS_VERIFIED_UNWIRED,
        )
        self.assertEqual(evidence["runtime_wiring_status"], RUNTIME_WIRING_NOT_IMPLEMENTED)
        self.assertEqual(evidence["live_executor_authority_status"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertIn("mediator_contract_hash replay matched", verify.stdout)
        self.assertIn("mediated_write_binding_hash replay matched", verify.stdout)
        self.assertIn("bypass_fixture_result_hash replay matched", verify.stdout)
        self.assertIn("Phase 10-E mismatch rejection found no forged overclaim fields", verify.stdout)
        self.assertIn("runtime wiring status remained RUNTIME_WIRING_NOT_IMPLEMENTED", verify.stdout)
        self.assertIn("live executor authority status remained LIVE_EXECUTOR_AUTHORITY_ON_HOLD", verify.stdout)

    def test_mediation_enforced_overclaim_rejected(self):
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["mediation_enforced"] = True
        self._write_json(evidence_path, evidence)

        verify = self._aeg("verify", check=False)

        self._assert_verify_failed(verify)
        self.assertIn(STATUS_OVERCLAIM_REJECTED, verify.stdout)
        self.assertIn("mediation_enforced=true", verify.stdout)

    def test_write_mediation_enforced_overclaim_rejected_even_when_rebound(self):
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        manifest, manifest_path = self._latest_manifest_with_path()
        evidence["write_mediation_enforced"] = True
        evidence["mediated_write_boundary_metadata_hash"] = expected_mediated_write_boundary_metadata_hash(evidence)
        self._sync_mediated_write_boundary_manifest(evidence, manifest)
        self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

        verify = self._aeg("verify", check=False)

        self._assert_verify_failed(verify)
        self.assertIn(STATUS_OVERCLAIM_REJECTED, verify.stdout)
        self.assertIn("write_mediation_enforced=true", verify.stdout)

    def test_scaffold_only_component_active_or_enforced_overclaim_rejected(self):
        for field, value in (
            ("mediator_status", "ENFORCED"),
            ("write_denial_status", "ACTIVE"),
            ("bypass_harness_status", "COVERAGE_COMPLETE"),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                evidence[field] = value
                self._write_json(evidence_path, evidence)

                verify = self._aeg("verify", check=False)

                self._assert_verify_failed(verify)
                self.assertIn(STATUS_OVERCLAIM_REJECTED, verify.stdout)
                self.assertIn(f"{field}={value}", verify.stdout)

    def test_wbyp_001_expected_red_result_mismatch_rejected(self):
        for forged_result in ("PASS", "BLOCKED", "ENFORCED"):
            with self.subTest(forged_result=forged_result):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                evidence["bypass_test_results"] = [
                    {
                        "wbyp_id": "WBYP-001",
                        "expected_red_marker": WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
                        "observed_result": forged_result,
                    }
                ]
                self._write_json(evidence_path, evidence)

                verify = self._aeg("verify", check=False)

                self._assert_verify_failed(verify)
                self.assertIn(BYPASS_RESULT_MISMATCH_REJECTED, verify.stdout)
                self.assertIn(f"WBYP-001 expected-red result cannot be {forged_result}", verify.stdout)

    def test_known_gap_promoted_to_enforced_denial_rejected(self):
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["bypass_test_results"] = {
            "WBYP-001": {
                "wbyp_id": "WBYP-001",
                "known_gap_marker": WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
                "observed_result": "ENFORCED",
                "enforced_denial": True,
            }
        }
        self._write_json(evidence_path, evidence)

        verify = self._aeg("verify", check=False)

        self._assert_verify_failed(verify)
        self.assertIn(BYPASS_RESULT_MISMATCH_REJECTED, verify.stdout)
        self.assertIn("known gap baseline cannot be reported as enforced denial", verify.stdout)

    def test_phase10e_component_hash_tamper_rejected_even_when_rebound(self):
        for field, rejection_code in (
            ("mediated_write_binding_hash", MEDIATED_WRITE_EVIDENCE_MISMATCH_REJECTED),
            ("mediator_contract_hash", WRITE_MEDIATION_COMPONENT_MISMATCH_REJECTED),
            ("bypass_fixture_result_hash", BYPASS_RESULT_MISMATCH_REJECTED),
        ):
            with self.subTest(field=field):
                self._aeg("run", "fix typo in README")
                evidence, evidence_path = self._latest_evidence_with_path()
                manifest, manifest_path = self._latest_manifest_with_path()
                evidence[field] = "0" * 64
                evidence["mediated_write_boundary_metadata_hash"] = (
                    expected_mediated_write_boundary_metadata_hash(evidence)
                )
                self._sync_mediated_write_boundary_manifest(evidence, manifest)
                self._write_evidence_and_manifest_with_bound_hash(evidence_path, evidence, manifest_path, manifest)

                verify = self._aeg("verify", check=False)

                self._assert_verify_failed(verify)
                self.assertIn(rejection_code, verify.stdout)
                self.assertIn(f"{field} mismatch", verify.stdout)

    def test_reported_only_write_denial_as_judgment_basis_rejected(self):
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["executor_reported_write_denied"] = True
        evidence["judgment_basis"] = True
        self._write_json(evidence_path, evidence)

        verify = self._aeg("verify", check=False)

        self._assert_verify_failed(verify)
        self.assertIn(REPORTED_ONLY_PROOF_REJECTED, verify.stdout)
        self.assertIn("executor_reported_write_denied cannot become judgment basis", verify.stdout)

    def test_not_checked_or_scaffold_only_status_promoted_to_pass_rejected(self):
        self._aeg("run", "fix typo in README")
        evidence, evidence_path = self._latest_evidence_with_path()
        evidence["write_mediation_status"] = "PASS"
        evidence["mediation_scaffold_status"] = "CLEAN"
        self._write_json(evidence_path, evidence)

        verify = self._aeg("verify", check=False)

        self._assert_verify_failed(verify)
        self.assertIn(NOT_CHECKED_PASS_OVERCLAIM_REJECTED, verify.stdout)
        self.assertIn("write_mediation_status=PASS", verify.stdout)
        self.assertIn("mediation_scaffold_status=CLEAN", verify.stdout)

    def _aeg(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=self.repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def _git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def _assert_verify_consistent(self, verify):
        self.assertIn("status: REPLAY_CONSISTENT", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)

    def _assert_verify_failed(self, verify):
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("status: REPLAY_FAILED", verify.stdout)
        self.assertIn("verification_scope: deterministic_replay_and_binding_validation", verify.stdout)
        self.assertIn("independent_oracle: false", verify.stdout)
        self.assertNotIn("status: PASS", verify.stdout)
        self.assertNotIn("Traceback", verify.stdout + verify.stderr)

    def _latest_evidence(self):
        evidence, _ = self._latest_evidence_with_path()
        return evidence

    def _latest_evidence_with_path(self):
        entry = self._latest_ledger_entry()
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "evidence.json"
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_manifest_with_path(self):
        entry = self._latest_ledger_entry()
        path = self.repo / ".aeg" / "runs" / entry["run_id"] / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")), path

    def _latest_ledger_entry(self):
        ledger = self.repo / ".aeg" / "ledger.jsonl"
        line = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line][-1]
        return json.loads(line)

    def _sync_mediated_write_boundary_manifest(self, evidence, manifest):
        for field in MEDIATED_WRITE_BOUNDARY_FIELDS:
            manifest[field] = evidence[field]
        manifest["mediated_write_boundary_manifest_hash"] = sha256_json(
            {field: manifest[field] for field in MEDIATED_WRITE_BOUNDARY_FIELDS}
        )
        evidence["bound_mediated_write_boundary_metadata_hash"] = manifest[
            "mediated_write_boundary_manifest_hash"
        ]

    def _write_evidence_and_manifest_with_bound_hash(self, evidence_path, evidence, manifest_path, manifest):
        self._write_json(manifest_path, manifest)
        evidence["bound_manifest_hash"] = manifest_hash(manifest)
        self._write_json(evidence_path, evidence)

    def _write_json(self, path, payload):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
