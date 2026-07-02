import hashlib
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from src.contracts import (
    B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE,
    B1_AEG_INTEGRITY_KNOWN_GAP_VOCABULARY,
    B1_AEG_INTEGRITY_NOT_EXECUTOR_ISOLATED,
    B1_AEG_INTEGRITY_NOT_HARDENED,
    LIVE_EXECUTOR_AUTHORITY_ON_HOLD,
    NOT_FILESYSTEM_ENFORCED,
    PHASE11A_NOT_STARTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
)


@dataclass(frozen=True)
class B1AegIntegrityKnownGapObservation:
    fixture_name: str
    submitted_path: str
    resolved_path: str
    before_digest: str
    after_digest: str
    mutation_observed: bool
    baseline: str = B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE
    observed_result: str = WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE
    expected_red_marker: str = WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED
    known_gap_marker: str = WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE
    hardening_status: str = B1_AEG_INTEGRITY_NOT_HARDENED
    executor_isolation_status: str = B1_AEG_INTEGRITY_NOT_EXECUTOR_ISOLATED
    filesystem_enforcement_status: str = NOT_FILESYSTEM_ENFORCED
    live_executor_authority_status: str = LIVE_EXECUTOR_AUTHORITY_ON_HOLD
    phase11a_status: str = PHASE11A_NOT_STARTED


class B1AegIntegrityRepoLikeFixture:
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

    def write_text(
        self,
        *,
        fixture_name: str,
        submitted_path: Path,
        payload: str,
        append: bool = False,
    ) -> B1AegIntegrityKnownGapObservation:
        before_digest = self._digest(submitted_path)
        submitted_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with submitted_path.open(mode, encoding="utf-8") as handle:
            handle.write(payload)
        after_digest = self._digest(submitted_path)
        return B1AegIntegrityKnownGapObservation(
            fixture_name=fixture_name,
            submitted_path=str(submitted_path),
            resolved_path=str(submitted_path.resolve()),
            before_digest=before_digest,
            after_digest=after_digest,
            mutation_observed=before_digest != after_digest and submitted_path.exists(),
        )

    def create_aeg_symlink_alias(self) -> Path:
        alias = self.repo / "aeg-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def _digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class B1AegIntegrityCurrentStateKnownGapHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = B1AegIntegrityRepoLikeFixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_direct_aeg_write_is_currently_bypassable_known_gap_baseline(self):
        observation = self.fixture.write_text(
            fixture_name="direct_aeg_write",
            submitted_path=self.fixture.aeg / "b1a-direct-write.txt",
            payload="b1-a direct .aeg write known gap\n",
        )

        self._assert_current_known_gap(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_traversal_into_aeg_write_is_currently_bypassable_known_gap_baseline(self):
        observation = self.fixture.write_text(
            fixture_name="traversal_into_aeg",
            submitted_path=self.fixture.work / ".." / ".aeg" / "b1a-traversal-write.txt",
            payload="b1-a traversal .aeg write known gap\n",
        )

        self._assert_current_known_gap(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_symlink_alias_into_aeg_write_is_currently_bypassable_known_gap_baseline(self):
        try:
            alias = self.fixture.create_aeg_symlink_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")

        observation = self.fixture.write_text(
            fixture_name="symlink_alias_into_aeg",
            submitted_path=alias / "b1a-symlink-write.txt",
            payload="b1-a symlink alias .aeg write known gap\n",
        )

        self._assert_current_known_gap(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))
        self.assertNotIn(".aeg", Path(observation.submitted_path).parts)

    def test_ledger_append_and_overwrite_are_currently_bypassable_known_gap_baseline(self):
        append_observation = self.fixture.write_text(
            fixture_name="ledger_append",
            submitted_path=self.fixture.ledger,
            payload='{"run_id":"run-001","entry":"tamper-append"}\n',
            append=True,
        )
        overwrite_observation = self.fixture.write_text(
            fixture_name="ledger_overwrite",
            submitted_path=self.fixture.ledger,
            payload='{"run_id":"run-001","entry":"tamper-overwrite"}\n',
        )

        self._assert_current_known_gap(append_observation)
        self._assert_current_known_gap(overwrite_observation)
        self.assertTrue(self._is_relative_to(Path(overwrite_observation.resolved_path), self.fixture.aeg.resolve()))

    def test_manifest_overwrite_is_currently_bypassable_known_gap_baseline(self):
        observation = self.fixture.write_text(
            fixture_name="manifest_overwrite",
            submitted_path=self.fixture.manifest,
            payload=json.dumps({"run_id": "run-001", "basis": "tampered-manifest"}, sort_keys=True),
        )

        self._assert_current_known_gap(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_evidence_packet_and_verify_basis_rewrite_are_currently_bypassable_known_gap_baseline(self):
        evidence_observation = self.fixture.write_text(
            fixture_name="evidence_packet_rewrite",
            submitted_path=self.fixture.evidence_packet,
            payload=json.dumps({"run_id": "run-001", "verdict": "tampered"}, sort_keys=True),
        )
        verify_observation = self.fixture.write_text(
            fixture_name="verify_basis_rewrite",
            submitted_path=self.fixture.verify_basis,
            payload=json.dumps({"run_id": "run-001", "basis": "tampered-verify"}, sort_keys=True),
        )

        self._assert_current_known_gap(evidence_observation)
        self._assert_current_known_gap(verify_observation)
        self.assertTrue(self._is_relative_to(Path(evidence_observation.resolved_path), self.fixture.aeg.resolve()))
        self.assertTrue(self._is_relative_to(Path(verify_observation.resolved_path), self.fixture.aeg.resolve()))

    def test_known_gap_labels_are_preserved_without_enforcement_claims(self):
        observation = self.fixture.write_text(
            fixture_name="label_review_write",
            submitted_path=self.fixture.aeg / "b1a-label-review.txt",
            payload="b1-a label review known gap\n",
        )
        labels = (
            observation.baseline,
            observation.observed_result,
            observation.expected_red_marker,
            observation.known_gap_marker,
            observation.hardening_status,
            observation.executor_isolation_status,
            observation.filesystem_enforcement_status,
            observation.live_executor_authority_status,
            observation.phase11a_status,
        )

        self._assert_current_known_gap(observation)
        self.assertEqual(set(labels), set(B1_AEG_INTEGRITY_KNOWN_GAP_VOCABULARY))

    def _assert_current_known_gap(self, observation: B1AegIntegrityKnownGapObservation) -> None:
        self.assertTrue(observation.mutation_observed)
        self.assertEqual(observation.baseline, B1_AEG_INTEGRITY_KNOWN_GAP_BASELINE)
        self.assertEqual(observation.observed_result, WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE)
        self.assertEqual(observation.expected_red_marker, WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED)
        self.assertEqual(observation.known_gap_marker, WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE)
        self.assertEqual(observation.hardening_status, B1_AEG_INTEGRITY_NOT_HARDENED)
        self.assertEqual(observation.executor_isolation_status, B1_AEG_INTEGRITY_NOT_EXECUTOR_ISOLATED)
        self.assertEqual(observation.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(observation.live_executor_authority_status, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(observation.phase11a_status, PHASE11A_NOT_STARTED)

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True


if __name__ == "__main__":
    unittest.main()
