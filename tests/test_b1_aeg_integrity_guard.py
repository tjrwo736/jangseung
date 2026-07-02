import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from src.contracts import (
    B1_AEG_DIRECT_TARGET_DENIED,
    B1_AEG_EVIDENCE_TARGET_DENIED,
    B1_AEG_INTEGRITY_DENY_ONLY_GUARD,
    B1_AEG_INTEGRITY_GUARD_VOCABULARY,
    B1_AEG_LEDGER_TARGET_DENIED,
    B1_AEG_MANIFEST_TARGET_DENIED,
    B1_AEG_NOT_PROTECTED_TARGET,
    B1_AEG_OUT_OF_SCOPE,
    B1_AEG_PROTECTED_TARGET,
    B1_AEG_SYMLINK_TARGET_DENIED,
    B1_AEG_TRAVERSAL_TARGET_DENIED,
    B1_AEG_VERIFY_BASIS_TARGET_DENIED,
    DENIED_BY_B1_AEG_INTEGRITY_GUARD,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_FILESYSTEM_ENFORCED,
    NOT_OS_ENFORCED,
    NOT_WIRED_TO_EXECUTOR_WRITE_PATH,
    PHASE11A_NOT_STARTED,
)
from src.evidence import b1_aeg_integrity_guard
from src.evidence.b1_aeg_integrity_guard import decide_b1_aeg_integrity_guard


class B1AegIntegrityGuardFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.work = self.repo / "work"
        self.aeg = self.repo / ".aeg"
        self.ledger = self.aeg / "ledger.jsonl"
        self.manifest = self.aeg / "manifest"
        self.evidence_packet = self.aeg / "runs" / "run-001" / "evidence_packet.json"
        self.verify_basis = self.aeg / "runs" / "run-001" / "verify_basis.json"
        self.public_note = self.repo / "notes" / "public.txt"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.public_note.parent.mkdir(parents=True)
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
        self.public_note.write_text("public baseline\n", encoding="utf-8")

    def create_aeg_symlink_alias(self) -> Path:
        alias = self.repo / "aeg-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B1AegIntegrityDenyOnlyGuardTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B1AegIntegrityGuardFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_direct_aeg_target_is_denied_by_guard(self):
        target = Path(".aeg") / "b1b-direct.txt"

        decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=target)

        self._assert_denied_guard_decision(decision, self.fixture.aeg / "b1b-direct.txt")
        self.assertEqual(decision.target_class, B1_AEG_DIRECT_TARGET_DENIED)

    def test_traversal_aeg_target_is_denied_by_guard(self):
        target = Path("work") / ".." / ".aeg" / "b1b-traversal.txt"

        decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=target)

        self._assert_denied_guard_decision(decision, self.fixture.aeg / "b1b-traversal.txt")
        self.assertEqual(decision.target_class, B1_AEG_TRAVERSAL_TARGET_DENIED)

    def test_symlink_alias_aeg_target_is_denied_by_guard_when_available(self):
        try:
            alias = self.fixture.create_aeg_symlink_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")
        target = alias / "b1b-symlink.txt"

        decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=target)

        self._assert_denied_guard_decision(decision, self.fixture.aeg / "b1b-symlink.txt")
        self.assertEqual(decision.target_class, B1_AEG_SYMLINK_TARGET_DENIED)
        self.assertNotIn(".aeg", target.parts)

    def test_ledger_manifest_evidence_and_verify_basis_targets_are_denied_by_guard(self):
        cases = (
            (self.fixture.ledger, B1_AEG_LEDGER_TARGET_DENIED),
            (self.fixture.manifest, B1_AEG_MANIFEST_TARGET_DENIED),
            (self.fixture.evidence_packet, B1_AEG_EVIDENCE_TARGET_DENIED),
            (self.fixture.verify_basis, B1_AEG_VERIFY_BASIS_TARGET_DENIED),
        )

        for target, target_class in cases:
            with self.subTest(target=target):
                before_digest = self.fixture.digest(target)

                decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=target)

                after_digest = self.fixture.digest(target)
                self._assert_denied_guard_decision(decision, target)
                self.assertEqual(decision.target_class, target_class)
                self.assertEqual(after_digest, before_digest)

    def test_denied_guard_decision_causes_no_mutation(self):
        missing_target = self.fixture.aeg / "b1b-not-created.txt"
        before_digest = self.fixture.digest(self.fixture.ledger)

        decision = decide_b1_aeg_integrity_guard(repo_root=self.fixture.repo, submitted_path=missing_target)

        after_digest = self.fixture.digest(self.fixture.ledger)
        self._assert_denied_guard_decision(decision, missing_target)
        self.assertFalse(missing_target.exists())
        self.assertEqual(after_digest, before_digest)

    def test_non_aeg_path_does_not_create_write_authority_grant(self):
        decision = decide_b1_aeg_integrity_guard(
            repo_root=self.fixture.repo,
            submitted_path=Path("notes") / "public.txt",
        )

        self.assertFalse(decision.protected_target)
        self.assertEqual(decision.protected_target_status, B1_AEG_NOT_PROTECTED_TARGET)
        self.assertEqual(decision.target_class, B1_AEG_NOT_PROTECTED_TARGET)
        self.assertEqual(decision.denial_reason, B1_AEG_OUT_OF_SCOPE)
        self.assertFalse(decision.capability_grant_created)
        self.assertFalse(decision.write_performed)
        self.assertFalse(decision.filesystem_mutation_performed)
        self.assertEqual(decision.wiring_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)

    def test_guard_decision_contains_required_fields(self):
        decision = decide_b1_aeg_integrity_guard(
            repo_root=self.fixture.repo,
            submitted_path=Path(".aeg") / "b1b-fields.txt",
        )
        record = decision.to_record()

        for field in (
            "submitted_path",
            "resolved_path",
            "protected_root",
            "target_class",
            "denial_reason",
            "wiring_status",
        ):
            with self.subTest(field=field):
                self.assertIn(field, record)

    def test_guard_vocabulary_does_not_claim_b1_completion(self):
        forbidden_completion_label = "B1_" + "COMPLETE"

        self.assertIn(B1_AEG_INTEGRITY_DENY_ONLY_GUARD, B1_AEG_INTEGRITY_GUARD_VOCABULARY)
        self.assertNotIn(forbidden_completion_label, B1_AEG_INTEGRITY_GUARD_VOCABULARY)

    def test_guard_module_does_not_add_permission_runtime_or_write_scope(self):
        source = inspect.getsource(b1_aeg_integrity_guard)
        forbidden_calls = (
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "subprocess",
            "shutil",
            "socket",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _assert_denied_guard_decision(self, decision, expected_resolved_path: Path) -> None:
        self.assertEqual(decision.component, B1_AEG_INTEGRITY_DENY_ONLY_GUARD)
        self.assertEqual(decision.denial_reason, DENIED_BY_B1_AEG_INTEGRITY_GUARD)
        self.assertEqual(decision.protected_target_status, B1_AEG_PROTECTED_TARGET)
        self.assertTrue(decision.protected_target)
        self.assertEqual(Path(decision.resolved_path), expected_resolved_path.resolve())
        self.assertEqual(Path(decision.protected_root), self.fixture.aeg.resolve())
        self.assertEqual(decision.wiring_status, NOT_WIRED_TO_EXECUTOR_WRITE_PATH)
        self.assertEqual(decision.os_enforcement_status, NOT_OS_ENFORCED)
        self.assertEqual(decision.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(decision.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(decision.phase11a_status, PHASE11A_NOT_STARTED)
        self.assertFalse(decision.write_performed)
        self.assertFalse(decision.filesystem_mutation_performed)
        self.assertFalse(decision.capability_grant_created)
        self.assertFalse(decision.executor_write_path_wired)


if __name__ == "__main__":
    unittest.main()
