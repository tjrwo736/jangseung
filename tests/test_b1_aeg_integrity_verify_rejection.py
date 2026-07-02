import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED,
    B1_AEG_GUARD_EVIDENCE_OVERCLAIM_REJECTED,
    B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED,
    B1_AEG_GUARD_EVIDENCE_REPLAY_CONSISTENT,
    B1_AEG_GUARD_FIELD_MISMATCH_REJECTED,
    B1_AEG_GUARD_NOT_CHECKED_PROMOTION_REJECTED,
    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED,
    B1_AEG_GUARD_REPORTED_ONLY_PROMOTION_REJECTED,
    B1_AEG_INTEGRITY_DENY_ONLY_GUARD,
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_INTEGRITY_VERIFY_REJECTION_VOCABULARY,
    B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_CHECKED,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_TAMPER_PROOF,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    REPORTED_ONLY,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence import b1_aeg_integrity_verify
from src.evidence.b1_aeg_integrity_evidence_binding import (
    build_b1_aeg_guard_evidence_record,
)
from src.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard
from src.evidence.b1_aeg_integrity_verify import (
    b1_aeg_guard_evidence_record_digest_from_mapping,
    verify_b1_aeg_guard_evidence_record,
)


class B1AegIntegrityVerifyFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.work = self.repo / "work"
        self.aeg = self.repo / ".aeg"
        self.ledger = self.aeg / "ledger.jsonl"
        self.manifest = self.aeg / "manifest"
        self.evidence_packet = self.aeg / "runs" / "run-001" / "evidence_packet.json"
        self.verify_basis = self.aeg / "runs" / "run-001" / "verify_basis.json"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.evidence_packet.parent.mkdir(parents=True)
        self.ledger.write_text('{"run_id":"run-001","entry":"baseline"}\n', encoding="utf-8")
        self.manifest.write_text(
            json.dumps({"run_id": "run-001", "basis": "baseline-manifest"}, sort_keys=True),
            encoding="utf-8",
        )
        self.evidence_packet.write_text(
            json.dumps({"run_id": "run-001", "verdict": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )
        self.verify_basis.write_text(
            json.dumps({"run_id": "run-001", "basis": "baseline-verify"}, sort_keys=True),
            encoding="utf-8",
        )


class B1AegIntegrityVerifyRejectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B1AegIntegrityVerifyFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_valid_b1c_guard_evidence_record_replays_consistent(self):
        record = self._valid_record()

        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertTrue(result.consistent)
        self.assertEqual(result.status, B1_AEG_GUARD_EVIDENCE_REPLAY_CONSISTENT)
        self.assertEqual(result.rejection_codes, ())
        self.assertEqual(result.scope_status, B1_AEG_VERIFY_ONLY_NOT_ENFORCEMENT)
        self.assertEqual(result.tamper_proof_status, NOT_TAMPER_PROOF)
        self.assertEqual(result.external_anchor_status, NOT_EXTERNAL_ANCHORED)
        self.assertEqual(result.os_enforcement_status, NOT_OS_ENFORCED)
        self.assertEqual(result.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(result.wiring_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(result.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.phase11a_status, PHASE11A_NOT_STARTED)

    def test_guard_decision_digest_tamper_is_rejected_even_when_record_rebound(self):
        record = self._valid_record()
        record["guard_decision"]["denial_reason"] = "B1_AEG_TEST_TAMPERED_DENIAL_REASON"
        self._rebind_record_digest(record)

        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertFalse(result.consistent)
        self.assertIn(B1_AEG_GUARD_DECISION_DIGEST_MISMATCH_REJECTED, result.rejection_codes)

    def test_evidence_record_digest_tamper_is_rejected(self):
        record = self._valid_record()
        record["evidence_record_digest"] = "0" * 64

        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertFalse(result.consistent)
        self.assertIn(B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED, result.rejection_codes)

    def test_same_record_canonical_digest_mismatch_is_rejected(self):
        record = self._valid_record()
        record["record_id"] = "b1-aeg-guard-evidence:" + ("f" * 64)

        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertFalse(result.consistent)
        self.assertIn(B1_AEG_GUARD_EVIDENCE_RECORD_DIGEST_MISMATCH_REJECTED, result.rejection_codes)

    def test_bound_guard_fields_mismatch_rejected_even_when_record_rebound(self):
        for field in (
            "submitted_path",
            "resolved_path",
            "protected_root",
            "target_class",
            "denial_reason",
            "wiring_status",
        ):
            with self.subTest(field=field):
                record = self._valid_record()
                record[field] = f"B1_AEG_TEST_TAMPERED_{field.upper()}"
                self._rebind_record_digest(record)

                result = verify_b1_aeg_guard_evidence_record(record)

                self.assertFalse(result.consistent)
                self.assertIn(B1_AEG_GUARD_FIELD_MISMATCH_REJECTED, result.rejection_codes)

    def test_no_mutation_observation_tamper_rejected_even_when_record_rebound(self):
        for field, value in (
            ("write_performed", True),
            ("filesystem_mutation_performed", True),
            ("mutation_observed", True),
            ("no_mutation_observed", False),
        ):
            with self.subTest(field=field):
                record = self._valid_record()
                record["no_mutation_observation"][field] = value
                self._rebind_record_digest(record)

                result = verify_b1_aeg_guard_evidence_record(record)

                self.assertFalse(result.consistent)
                self.assertIn(
                    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_MISMATCH_REJECTED,
                    result.rejection_codes,
                )

    def test_overclaim_labels_are_rejected(self):
        labels = (
            "B1_" + "COMPLETE",
            "TAMPER_" + "PROOF",
            "EXTERNAL_" + "ANCHOR_ACTIVE",
            "FILESYSTEM_" + "ENFORCED",
            "EXECUTOR_" + "ISOLATED",
            "LIVE_" + "EXECUTOR_READY",
            "SAFE_" + "TO_RUN",
        )

        for label in labels:
            with self.subTest(label=label):
                record = self._valid_record()
                record["overclaim_label"] = label

                result = verify_b1_aeg_guard_evidence_record(record)

                self.assertFalse(result.consistent)
                self.assertIn(B1_AEG_GUARD_EVIDENCE_OVERCLAIM_REJECTED, result.rejection_codes)

    def test_reported_only_guard_denial_evidence_promotion_rejected(self):
        record = self._valid_record()
        record["guard_denial_evidence_trust_boundary"] = REPORTED_ONLY
        record["guard_denial_evidence_judgment_basis"] = True

        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertFalse(result.consistent)
        self.assertIn(B1_AEG_GUARD_REPORTED_ONLY_PROMOTION_REJECTED, result.rejection_codes)

    def test_not_checked_and_known_gap_promotion_rejected(self):
        cases = (
            {"not_checked_source": NOT_CHECKED, "not_checked_result": "PASS"},
            {"known_gap_source": B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE, "known_gap_result": "CLEAN"},
            {"known_gap_baseline_status": "ENFORCED"},
        )

        for tamper in cases:
            with self.subTest(tamper=tamper):
                record = self._valid_record()
                record.update(tamper)
                self._rebind_record_digest(record)

                result = verify_b1_aeg_guard_evidence_record(record)

                self.assertFalse(result.consistent)
                self.assertIn(B1_AEG_GUARD_NOT_CHECKED_PROMOTION_REJECTED, result.rejection_codes)

    def test_b1_a_b_c_state_boundaries_are_preserved(self):
        record = self._valid_record()
        result = verify_b1_aeg_guard_evidence_record(record)

        self.assertEqual(record["known_gap_baseline_status"], B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(record["raw_direct_path_status"], WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE)
        self.assertEqual(record["guard_decision"]["component"], B1_AEG_INTEGRITY_DENY_ONLY_GUARD)
        self.assertTrue(result.consistent)
        self.assertNotIn("B1_" + "COMPLETE", B1_AEG_INTEGRITY_VERIFY_REJECTION_VOCABULARY)
        self.assertEqual(result.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(result.phase11a_status, PHASE11A_NOT_STARTED)

    def test_verify_module_does_not_add_write_permission_runtime_or_provider_scope(self):
        source = inspect.getsource(b1_aeg_integrity_verify)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".ch" + "mod(",
            "ch" + "mod(",
            ".ch" + "own(",
            "ch" + "own(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "sub" + "process",
            "shutil",
            "sock" + "et",
            "write" + "_file",
            "run" + "_command",
            "http" + "_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _valid_record(self):
        decision = decide_b1_aeg_integrity_guard(
            repo_root=self.fixture.repo,
            submitted_path=Path(".aeg") / "b1d-verify-target.txt",
        )
        return build_b1_aeg_guard_evidence_record(guard_decision=decision).to_record()

    def _rebind_record_digest(self, record):
        digest = b1_aeg_guard_evidence_record_digest_from_mapping(record)
        record["evidence_record_digest"] = digest
        record["record_id"] = f"b1-aeg-guard-evidence:{digest}"


if __name__ == "__main__":
    unittest.main()
