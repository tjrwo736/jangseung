import hashlib
import inspect
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.contracts import (
    B1_AEG_DIRECT_TARGET_DENIED,
    B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED,
    B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF,
    B1_AEG_EVIDENCE_TARGET_DENIED,
    B1_AEG_GUARD_DECISION_BOUND,
    B1_AEG_GUARD_EVIDENCE_BINDING,
    B1_AEG_GUARD_EVIDENCE_DIGEST,
    B1_AEG_GUARD_EVIDENCE_RECORD,
    B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
    B1_AEG_INTEGRITY_EVIDENCE_BINDING_VOCABULARY,
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_LEDGER_TARGET_DENIED,
    B1_AEG_MANIFEST_TARGET_DENIED,
    B1_AEG_SYMLINK_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    B1_AEG_VERIFY_BASIS_TARGET_DENIED,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
)
from src.evidence import b1_aeg_integrity_evidence_binding
from src.evidence.b1_aeg_integrity_evidence_binding import (
    b1_aeg_guard_evidence_digest,
    build_b1_aeg_guard_evidence_record,
)
from src.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard


class B1AegIntegrityEvidenceBindingFixture:
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

    def create_aeg_symlink_alias(self) -> Path:
        alias = self.repo / "aeg-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B1AegIntegrityEvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B1AegIntegrityEvidenceBindingFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_direct_aeg_guard_denial_binds_to_evidence_record(self):
        record = self._record_for_target(Path(".aeg") / "b1c-direct.txt")

        self._assert_guard_evidence_record(record, B1_AEG_DIRECT_TARGET_DENIED)
        self.assertEqual(record.submitted_path, str(Path(".aeg") / "b1c-direct.txt"))

    def test_traversal_aeg_guard_denial_binds_to_evidence_record(self):
        record = self._record_for_target(Path("work") / ".." / ".aeg" / "b1c-traversal.txt")

        self._assert_guard_evidence_record(record, B1_AEG_TRAVERSAL_TARGET_DENIED)

    def test_symlink_aeg_guard_denial_binds_to_evidence_record_when_available(self):
        try:
            alias = self.fixture.create_aeg_symlink_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")

        record = self._record_for_target(alias / "b1c-symlink.txt")

        self._assert_guard_evidence_record(record, B1_AEG_SYMLINK_TARGET_DENIED)
        self.assertNotIn(".aeg", Path(record.submitted_path).parts)

    def test_ledger_manifest_evidence_and_verify_basis_denials_bind_to_records(self):
        cases = (
            (self.fixture.ledger, B1_AEG_LEDGER_TARGET_DENIED),
            (self.fixture.manifest, B1_AEG_MANIFEST_TARGET_DENIED),
            (self.fixture.evidence_packet, B1_AEG_EVIDENCE_TARGET_DENIED),
            (self.fixture.verify_basis, B1_AEG_VERIFY_BASIS_TARGET_DENIED),
        )

        for target, target_class in cases:
            with self.subTest(target=target):
                before_digest = self.fixture.digest(target)

                record = self._record_for_target(target)

                after_digest = self.fixture.digest(target)
                self._assert_guard_evidence_record(record, target_class)
                self.assertEqual(after_digest, before_digest)

    def test_digest_and_record_id_are_deterministic_for_same_input(self):
        decision = decide_b1_aeg_integrity_guard(
            repo_root=self.fixture.repo,
            submitted_path=Path(".aeg") / "b1c-deterministic.txt",
        )

        first = build_b1_aeg_guard_evidence_record(guard_decision=decision)
        second = build_b1_aeg_guard_evidence_record(guard_decision=decision)

        self.assertEqual(first.guard_decision_digest, second.guard_decision_digest)
        self.assertEqual(first.evidence_record_digest, second.evidence_record_digest)
        self.assertEqual(first.record_id, second.record_id)
        self.assertEqual(first.to_record(), second.to_record())
        self.assertEqual(first.evidence_record_digest, b1_aeg_guard_evidence_digest(first))
        self.assertTrue(first.record_id.startswith("b1-aeg-guard-evidence:"))
        self.assertEqual(len(first.guard_decision_digest), 64)
        self.assertEqual(len(first.evidence_record_digest), 64)

    def test_changed_target_class_or_denial_reason_changes_digest_and_record_id(self):
        decision = decide_b1_aeg_integrity_guard(
            repo_root=self.fixture.repo,
            submitted_path=Path(".aeg") / "b1c-change.txt",
        )
        base_record = build_b1_aeg_guard_evidence_record(guard_decision=decision)
        changed_target_class = replace(
            decision,
            target_class=B1_AEG_LEDGER_TARGET_DENIED,
            decision_id="b1-aeg-integrity-guard:changed-target-class",
        )
        changed_denial_reason = replace(
            decision,
            denial_reason="B1_AEG_TEST_CHANGED_DENIAL_REASON",
            decision_id="b1-aeg-integrity-guard:changed-denial-reason",
        )

        changed_records = (
            build_b1_aeg_guard_evidence_record(guard_decision=changed_target_class),
            build_b1_aeg_guard_evidence_record(guard_decision=changed_denial_reason),
        )

        for changed_record in changed_records:
            with self.subTest(record_id=changed_record.record_id):
                self.assertNotEqual(changed_record.guard_decision_digest, base_record.guard_decision_digest)
                self.assertNotEqual(changed_record.evidence_record_digest, base_record.evidence_record_digest)
                self.assertNotEqual(changed_record.record_id, base_record.record_id)

    def test_no_mutation_observation_is_bound(self):
        missing_target = self.fixture.aeg / "b1c-not-created.txt"

        record = self._record_for_target(missing_target)

        self.assertFalse(missing_target.exists())
        self.assertEqual(record.no_mutation_observation_status, B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND)
        self.assertEqual(
            record.no_mutation_observation["observation_status"],
            B1_AEG_GUARD_NO_MUTATION_OBSERVATION_BOUND,
        )
        self.assertTrue(record.no_mutation_observation["no_mutation_observed"])
        self.assertFalse(record.no_mutation_observation["mutation_observed"])
        self.assertFalse(record.no_mutation_observation["write_performed"])
        self.assertFalse(record.no_mutation_observation["filesystem_mutation_performed"])

    def test_binding_does_not_mutate_filesystem(self):
        target = self.fixture.aeg / "b1c-no-mutation-target.txt"
        ledger_before = self.fixture.digest(self.fixture.ledger)

        record = self._record_for_target(target)

        ledger_after = self.fixture.digest(self.fixture.ledger)
        self.assertFalse(target.exists())
        self.assertEqual(ledger_after, ledger_before)
        self.assertFalse(record.filesystem_mutation_performed)

    def test_binding_does_not_claim_completion_or_external_anchor(self):
        record = self._record_for_target(Path(".aeg") / "b1c-boundary.txt")
        forbidden_completion_label = "B1_" + "COMPLETE"

        self.assertFalse(record.enforcement_complete_claimed)
        self.assertFalse(record.executor_write_path_wired)
        self.assertEqual(record.tamper_proof_status, B1_AEG_EVIDENCE_BINDING_NOT_TAMPER_PROOF)
        self.assertEqual(record.external_anchor_status, B1_AEG_EVIDENCE_BINDING_NOT_EXTERNAL_ANCHORED)
        self.assertEqual(record.known_gap_baseline_status, B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(record.raw_direct_path_status, WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE)
        self.assertNotIn(forbidden_completion_label, B1_AEG_INTEGRITY_EVIDENCE_BINDING_VOCABULARY)

    def test_binding_module_does_not_add_write_permission_runtime_or_provider_scope(self):
        source = inspect.getsource(b1_aeg_integrity_evidence_binding)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".chmod(",
            "chmod(",
            ".chown(",
            "chown(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "shutil",
            "socket",
            "write_file",
            "run_command",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _record_for_target(self, target: Path):
        decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=target)
        return build_b1_aeg_guard_evidence_record(guard_decision=decision)

    def _assert_guard_evidence_record(self, record, target_class: str) -> None:
        self.assertEqual(record.component, B1_AEG_GUARD_EVIDENCE_BINDING)
        self.assertEqual(record.record_type, B1_AEG_GUARD_EVIDENCE_RECORD)
        self.assertEqual(record.guard_decision_binding_status, B1_AEG_GUARD_DECISION_BOUND)
        self.assertEqual(record.digest_status, B1_AEG_GUARD_EVIDENCE_DIGEST)
        self.assertEqual(record.target_class, target_class)
        self.assertEqual(record.denial_reason, DENIED_BY_B1_AEG_INTEGRITY_GUARD)
        self.assertEqual(record.wiring_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(record.os_enforcement_status, NOT_OS_ENFORCED)
        self.assertEqual(record.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(record.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record.phase11a_status, PHASE11A_NOT_STARTED)
        self.assertEqual(record.guard_decision["target_class"], target_class)
        self.assertEqual(record.guard_decision["submitted_path"], record.submitted_path)
        self.assertEqual(record.guard_decision["resolved_path"], record.resolved_path)
        self.assertEqual(record.guard_decision["protected_root"], record.protected_root)
        self.assertEqual(record.guard_decision["wiring_status"], record.wiring_status)
        self.assertEqual(record.evidence_record_digest, b1_aeg_guard_evidence_digest(record))


if __name__ == "__main__":
    unittest.main()
