import hashlib
import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from src.contracts import (
    WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
)
from src.evidence.write_bypass_harness import write_bypass_harness_registry


NO_MEDIATOR_PRESENT = "NO_MEDIATOR_PRESENT"
NO_WRITE_MEDIATION_PRESENT = "NO_WRITE_MEDIATION_PRESENT"


@dataclass(frozen=True)
class BypassObservation:
    wbyp_id: str
    registry_title: str
    fixture_name: str
    submitted_path: str
    resolved_path: str
    before_digest: str
    after_digest: str
    mutation_observed: bool
    observed_result: str = WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE
    expected_red_marker: str = WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED
    known_gap_marker: str = WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE
    mediator_observation: str = NO_MEDIATOR_PRESENT
    write_mediation_observation: str = NO_WRITE_MEDIATION_PRESENT


class RepoLikeBypassFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.aeg = self.repo / ".aeg"
        self.work = self.repo / "work"
        self.sibling_outside = root / "outside-sibling"
        self.absolute_outside = (root / "absolute-outside").resolve()
        self.evidence = self.aeg / "runs" / "run-001" / "evidence.json"
        self.manifest = self.aeg / "manifests" / "run-001" / "manifest.json"
        self.ledger = self.aeg / "ledger.jsonl"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.sibling_outside.mkdir(parents=True)
        self.absolute_outside.mkdir(parents=True)
        self.evidence.parent.mkdir(parents=True)
        self.manifest.parent.mkdir(parents=True)
        self.evidence.write_text(
            json.dumps({"run_id": "run-001", "marker": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )
        self.manifest.write_text(
            json.dumps({"run_id": "run-001", "evidence_path": str(self.evidence)}, sort_keys=True),
            encoding="utf-8",
        )
        self.ledger.write_text('{"run_id":"run-001","entry":"baseline"}\n', encoding="utf-8")
        (self.repo / ".gitignore").write_text(".aeg/\n.env\n.env.*\n", encoding="utf-8")

    def write_text(
        self,
        *,
        wbyp_entry: dict[str, object],
        fixture_name: str,
        submitted_path: Path,
        payload: str,
        append: bool = False,
    ) -> BypassObservation:
        before_digest = self._digest(submitted_path)
        if not submitted_path.parent.exists():
            submitted_path.parent.mkdir(parents=True)
        mode = "a" if append else "w"
        with submitted_path.open(mode, encoding="utf-8") as handle:
            handle.write(payload)
        after_digest = self._digest(submitted_path)
        return BypassObservation(
            wbyp_id=str(wbyp_entry["id"]),
            registry_title=str(wbyp_entry["title"]),
            fixture_name=fixture_name,
            submitted_path=str(submitted_path),
            resolved_path=str(submitted_path.resolve()),
            before_digest=before_digest,
            after_digest=after_digest,
            mutation_observed=before_digest != after_digest and submitted_path.exists(),
        )

    def create_aeg_alias(self) -> Path:
        alias = self.repo / "runtime-state-alias"
        alias.symlink_to(self.aeg, target_is_directory=True)
        return alias

    @staticmethod
    def _digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase10E1WriteBypassKnownGapTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = RepoLikeBypassFixture(Path(self.tempdir.name))
        self.registry = {entry["id"]: entry for entry in write_bypass_harness_registry()}

    def tearDown(self):
        self.tempdir.cleanup()

    def test_wbyp_001_direct_aeg_write_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-001", "Direct .aeg Write Denial")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="direct_aeg_write",
            submitted_path=self.fixture.aeg / "e1-direct-write.txt",
            payload="phase10-e1 direct aeg write known gap\n",
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_wbyp_002_traversal_aeg_write_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-002", ".aeg Path Traversal Denial")
        submitted_path = self.fixture.work / ".." / ".aeg" / "e1-traversal-write.txt"

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="traversal_into_aeg",
            submitted_path=submitted_path,
            payload="phase10-e1 traversal aeg write known gap\n",
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_wbyp_003_symlink_aeg_write_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-003", "Symlink Alias Into .aeg Denial")
        try:
            alias = self.fixture.create_aeg_alias()
        except OSError as exc:
            self.skipTest(f"symlink fixture unavailable: {exc}")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="symlink_alias_into_aeg",
            submitted_path=alias / "e1-symlink-write.txt",
            payload="phase10-e1 symlink aeg write known gap\n",
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))
        self.assertNotIn(".aeg", Path(observation.submitted_path).parts)

    def test_wbyp_004_outside_repo_sibling_write_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-004", "Outside Repo Write Denial")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="outside_repo_sibling_write",
            submitted_path=self.fixture.sibling_outside / "e1-sibling-outside.txt",
            payload="phase10-e1 outside repo sibling write known gap\n",
        )

        self._assert_known_gap_observation(observation)
        self.assertFalse(self._is_relative_to(Path(observation.resolved_path), self.fixture.repo.resolve()))

    def test_wbyp_004_outside_repo_absolute_write_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-004", "Outside Repo Write Denial")
        submitted_path = self.fixture.absolute_outside / "e1-absolute-outside.txt"

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="outside_repo_absolute_write",
            submitted_path=submitted_path,
            payload="phase10-e1 outside repo absolute write known gap\n",
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(Path(observation.submitted_path).is_absolute())
        self.assertFalse(self._is_relative_to(Path(observation.resolved_path), self.fixture.repo.resolve()))

    def test_wbyp_022_evidence_overwrite_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-022", "Ledger Chain Walk After Write Evidence Tamper")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="aeg_evidence_overwrite",
            submitted_path=self.fixture.evidence,
            payload=json.dumps({"run_id": "run-001", "marker": "tampered-evidence"}, sort_keys=True),
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_wbyp_022_manifest_overwrite_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-022", "Ledger Chain Walk After Write Evidence Tamper")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="aeg_manifest_overwrite",
            submitted_path=self.fixture.manifest,
            payload=json.dumps({"run_id": "run-001", "marker": "tampered-manifest"}, sort_keys=True),
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def test_wbyp_022_ledger_append_records_currently_bypassable_known_gap(self):
        entry = self._registry_entry("WBYP-022", "Ledger Chain Walk After Write Evidence Tamper")

        observation = self.fixture.write_text(
            wbyp_entry=entry,
            fixture_name="aeg_ledger_append",
            submitted_path=self.fixture.ledger,
            payload='{"run_id":"run-001","entry":"tamper-append"}\n',
            append=True,
        )

        self._assert_known_gap_observation(observation)
        self.assertTrue(self._is_relative_to(Path(observation.resolved_path), self.fixture.aeg.resolve()))

    def _registry_entry(self, wbyp_id: str, title: str) -> dict[str, object]:
        entry = self.registry[wbyp_id]
        self.assertEqual(entry["id"], wbyp_id)
        self.assertEqual(entry["title"], title)
        return entry

    def _assert_known_gap_observation(self, observation: BypassObservation) -> None:
        self.assertTrue(observation.mutation_observed)
        self.assertEqual(observation.observed_result, WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE)
        self.assertEqual(observation.expected_red_marker, WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED)
        self.assertEqual(observation.known_gap_marker, WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE)
        self.assertEqual(observation.mediator_observation, NO_MEDIATOR_PRESENT)
        self.assertEqual(observation.write_mediation_observation, NO_WRITE_MEDIATION_PRESENT)
        self.assertIn(observation.observed_result, WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY)
        self.assertIn(observation.expected_red_marker, WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY)
        self.assertIn(observation.known_gap_marker, WRITE_BYPASS_HARNESS_KNOWN_GAP_RESULT_VOCABULARY)

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True


if __name__ == "__main__":
    unittest.main()
