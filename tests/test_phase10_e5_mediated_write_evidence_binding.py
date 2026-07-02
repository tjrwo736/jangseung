import hashlib
import inspect
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.contracts import (
    AEG_WRITE_DENIED_BY_MEDIATED_PATH,
    BINDING_DIGEST_PRESENT,
    DENIED_WRITE_DECISION_EVIDENCE_BOUND,
    EVIDENCE_BINDING_PRESENT,
    EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED,
    MEDIATED_WRITE_DENIED,
    MEDIATED_WRITE_EVIDENCE_BOUND,
    NO_MUTATION_OBSERVATION_BOUND,
    NOT_EXTERNAL_ANCHORED,
    NOT_FILESYSTEM_ENFORCED,
    NOT_TAMPER_PROOF,
    OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH,
    RAW_DIRECT_WRITE_STILL_BYPASSABLE,
    VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
    WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE,
    WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED,
    WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE,
    WRITE_CLASS_AEG_STATE_WRITE,
    WRITE_CLASS_OUTSIDE_REPO_WRITE,
)
from src.evidence import mediated_write_evidence_binding
from src.evidence.mediated_aeg_write_path import request_mediated_aeg_write_text
from src.evidence.mediated_repo_boundary_write_path import request_mediated_outside_repo_write_text
from src.evidence.mediated_write_evidence_binding import (
    build_denied_write_no_mutation_observation,
    build_mediated_write_evidence_record,
    mediated_write_evidence_binding_digest,
)


class Phase10E5Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.aeg = self.repo / ".aeg"
        self.work = self.repo / "work"
        self.outside = root / "outside-sibling"
        self.evidence = self.aeg / "runs" / "run-001" / "evidence.json"
        self.existing_outside = self.outside / "existing-outside.txt"
        self._create()

    def _create(self) -> None:
        self.work.mkdir(parents=True)
        self.evidence.parent.mkdir(parents=True)
        self.outside.mkdir(parents=True)
        self.evidence.write_text(
            json.dumps({"run_id": "run-001", "marker": "baseline"}, sort_keys=True),
            encoding="utf-8",
        )
        self.existing_outside.write_text("phase10-e5 outside baseline\n", encoding="utf-8")

    @staticmethod
    def digest(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase10E5MediatedWriteEvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.fixture = Phase10E5Fixture(Path(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_e3_mediated_aeg_denial_is_bound_to_evidence_record(self):
        before_digest = self.fixture.digest(self.fixture.evidence)
        before_exists = self.fixture.evidence.exists()

        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.evidence,
            payload=json.dumps({"run_id": "run-001", "marker": "tampered"}, sort_keys=True),
            actor="phase10-e5-test",
            operation="replace",
            request_id="e5-e3-aeg-evidence-denial",
        )

        after_digest = self.fixture.digest(self.fixture.evidence)
        record = self._record_for_result(result, before_exists, before_digest, self.fixture.evidence.exists(), after_digest)

        self.assertEqual(after_digest, before_digest)
        self.assertEqual(result.decision_status, MEDIATED_WRITE_DENIED)
        self.assertEqual(record.binding_status, MEDIATED_WRITE_EVIDENCE_BOUND)
        self.assertEqual(record.evidence_binding_status, EVIDENCE_BINDING_PRESENT)
        self.assertEqual(record.denied_write_decision_evidence_status, DENIED_WRITE_DECISION_EVIDENCE_BOUND)
        self.assertEqual(record.binding_digest_status, BINDING_DIGEST_PRESENT)
        self.assertEqual(record.no_mutation_observation_status, NO_MUTATION_OBSERVATION_BOUND)
        self.assertEqual(record.request_id, "e5-e3-aeg-evidence-denial")
        self.assertEqual(record.decision_id, result.decision_id)
        self.assertEqual(record.write_class, WRITE_CLASS_AEG_STATE_WRITE)
        self.assertEqual(record.canonical_target, str(self.fixture.evidence.resolve()))
        self.assertEqual(record.denial_reason, AEG_WRITE_DENIED_BY_MEDIATED_PATH)
        self.assertEqual(record.policy_source, "phase10_e3_mediated_aeg_write_denial_v0")
        self.assertEqual(record.raw_direct_write_status, RAW_DIRECT_WRITE_STILL_BYPASSABLE)
        self.assertEqual(record.filesystem_enforcement_status, NOT_FILESYSTEM_ENFORCED)
        self.assertEqual(record.external_enforcement_status, EXTERNAL_ENFORCEMENT_NOT_IMPLEMENTED)
        self.assertFalse(record.live_executor_authority_granted)
        self.assert_record_is_bound_without_overclaim(record)

    def test_e4_mediated_outside_repo_denial_is_bound_to_evidence_record(self):
        before_digest = self.fixture.digest(self.fixture.existing_outside)
        before_exists = self.fixture.existing_outside.exists()

        result = request_mediated_outside_repo_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.existing_outside,
            payload="phase10-e5 outside overwrite should not be written\n",
            actor="phase10-e5-test",
            operation="replace",
            request_id="e5-e4-outside-repo-denial",
        )

        after_digest = self.fixture.digest(self.fixture.existing_outside)
        record = self._record_for_result(
            result,
            before_exists,
            before_digest,
            self.fixture.existing_outside.exists(),
            after_digest,
        )

        self.assertEqual(after_digest, before_digest)
        self.assertEqual(result.decision_status, MEDIATED_WRITE_DENIED)
        self.assertEqual(record.binding_status, MEDIATED_WRITE_EVIDENCE_BOUND)
        self.assertEqual(record.request_id, "e5-e4-outside-repo-denial")
        self.assertEqual(record.decision_id, result.decision_id)
        self.assertEqual(record.write_class, WRITE_CLASS_OUTSIDE_REPO_WRITE)
        self.assertEqual(record.canonical_target, str(self.fixture.existing_outside.resolve()))
        self.assertEqual(record.denial_reason, OUTSIDE_REPO_WRITE_DENIED_BY_MEDIATED_PATH)
        self.assertEqual(record.policy_source, "phase10_e4_outside_repo_write_denial_v0")
        self.assert_record_is_bound_without_overclaim(record)

    def test_binding_digest_and_id_are_deterministic_for_same_input(self):
        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.aeg / "deterministic.txt",
            payload="phase10-e5 deterministic target should not be written\n",
            actor="phase10-e5-test",
            request_id="e5-deterministic-input",
        )
        observation = build_denied_write_no_mutation_observation(
            canonical_target=result.path_resolution.canonical_target,
            target_exists_before=False,
            target_exists_after=False,
            content_digest_before="MISSING",
            content_digest_after="MISSING",
            observation_source="phase10_e5_targeted_test_digest",
        )

        first = build_mediated_write_evidence_record(
            denied_result=result,
            no_mutation_observation=observation,
        )
        second = build_mediated_write_evidence_record(
            denied_result=result,
            no_mutation_observation=observation,
        )

        self.assertEqual(first.binding_digest, second.binding_digest)
        self.assertEqual(first.binding_id, second.binding_id)
        self.assertEqual(first.to_record(), second.to_record())
        self.assertEqual(first.binding_digest, mediated_write_evidence_binding_digest(first))
        self.assertTrue(first.binding_id.startswith("mediated-write-evidence:"))
        self.assertEqual(len(first.binding_digest), 64)

    def test_changed_request_decision_target_or_no_mutation_input_changes_digest_and_id(self):
        base_result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.aeg / "base.txt",
            payload="phase10-e5 base target should not be written\n",
            actor="phase10-e5-test",
            request_id="e5-change-base",
        )
        base_observation = build_denied_write_no_mutation_observation(
            canonical_target=base_result.path_resolution.canonical_target,
            target_exists_before=False,
            target_exists_after=False,
            content_digest_before="MISSING",
            content_digest_after="MISSING",
            observation_source="phase10_e5_targeted_test_digest",
        )
        base_record = build_mediated_write_evidence_record(
            denied_result=base_result,
            no_mutation_observation=base_observation,
        )

        changed_request_result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.aeg / "base.txt",
            payload="phase10-e5 base target should not be written\n",
            actor="phase10-e5-test",
            request_id="e5-change-request",
        )
        changed_target_result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.aeg / "changed-target.txt",
            payload="phase10-e5 changed target should not be written\n",
            actor="phase10-e5-test",
            request_id="e5-change-base",
        )
        changed_decision_result = replace(base_result, decision_id="tampered-decision-id")
        changed_observation = build_denied_write_no_mutation_observation(
            canonical_target=base_result.path_resolution.canonical_target,
            target_exists_before=False,
            target_exists_after=True,
            content_digest_before="MISSING",
            content_digest_after="tampered-digest",
            observation_source="phase10_e5_targeted_test_digest",
        )

        changed_records = (
            build_mediated_write_evidence_record(
                denied_result=changed_request_result,
                no_mutation_observation=base_observation,
            ),
            build_mediated_write_evidence_record(
                denied_result=changed_decision_result,
                no_mutation_observation=base_observation,
            ),
            build_mediated_write_evidence_record(
                denied_result=changed_target_result,
                no_mutation_observation=build_denied_write_no_mutation_observation(
                    canonical_target=changed_target_result.path_resolution.canonical_target,
                    target_exists_before=False,
                    target_exists_after=False,
                    content_digest_before="MISSING",
                    content_digest_after="MISSING",
                    observation_source="phase10_e5_targeted_test_digest",
                ),
            ),
            build_mediated_write_evidence_record(
                denied_result=base_result,
                no_mutation_observation=changed_observation,
            ),
        )

        for changed_record in changed_records:
            with self.subTest(binding_id=changed_record.binding_id):
                self.assertNotEqual(changed_record.binding_digest, base_record.binding_digest)
                self.assertNotEqual(changed_record.binding_id, base_record.binding_id)

    def test_mismatch_rejection_is_not_implemented_in_e5_binding_helper(self):
        result = request_mediated_aeg_write_text(
            repo_root=self.fixture.repo,
            submitted_target=self.fixture.aeg / "mismatch-source.txt",
            payload="phase10-e5 mismatch source should not be written\n",
            actor="phase10-e5-test",
            request_id="e5-mismatch-rejection-not-implemented",
        )
        mismatched_observation = build_denied_write_no_mutation_observation(
            canonical_target=str(self.fixture.existing_outside.resolve()),
            target_exists_before=True,
            target_exists_after=True,
            content_digest_before=self.fixture.digest(self.fixture.existing_outside),
            content_digest_after=self.fixture.digest(self.fixture.existing_outside),
            observation_source="phase10_e5_mismatch_fixture",
        )

        record = build_mediated_write_evidence_record(
            denied_result=result,
            no_mutation_observation=mismatched_observation,
        )

        self.assertNotEqual(record.canonical_target, record.no_mutation_observation["canonical_target"])
        self.assertEqual(
            record.verify_mismatch_rejection_status,
            VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED,
        )

    def test_e1_known_gap_vocabulary_remains_currently_bypassable(self):
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_CURRENTLY_BYPASSABLE, "CURRENTLY_BYPASSABLE")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_EXPECTED_RED, "EXPECTED_RED")
        self.assertEqual(WRITE_BYPASS_HARNESS_RESULT_KNOWN_GAP_BASELINE, "KNOWN_GAP_BASELINE")

    def test_e5_binding_module_does_not_add_write_permission_or_external_scope(self):
        source = inspect.getsource(mediated_write_evidence_binding)
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
            "write_file",
            "read_file",
            "run_command",
            "http_request",
        )

        for forbidden_call in forbidden_calls:
            with self.subTest(forbidden_call=forbidden_call):
                self.assertNotIn(forbidden_call, source)

    def _record_for_result(
        self,
        result,
        target_exists_before: bool,
        content_digest_before: str,
        target_exists_after: bool,
        content_digest_after: str,
    ):
        observation = build_denied_write_no_mutation_observation(
            canonical_target=result.path_resolution.canonical_target,
            target_exists_before=target_exists_before,
            target_exists_after=target_exists_after,
            content_digest_before=content_digest_before,
            content_digest_after=content_digest_after,
            observation_source="phase10_e5_targeted_test_digest",
        )
        return build_mediated_write_evidence_record(
            denied_result=result,
            no_mutation_observation=observation,
        )

    def assert_record_is_bound_without_overclaim(self, record) -> None:
        record_dict = record.to_record()
        self.assertEqual(record.binding_digest, mediated_write_evidence_binding_digest(record))
        self.assertEqual(record.tamper_proof_status, NOT_TAMPER_PROOF)
        self.assertEqual(record.external_anchor_status, NOT_EXTERNAL_ANCHORED)
        self.assertEqual(record.verify_mismatch_rejection_status, VERIFY_MISMATCH_REJECTION_NOT_IMPLEMENTED)
        self.assertNotEqual(record.tamper_proof_status, "TAMPER_PROOF")
        self.assertNotEqual(record.external_anchor_status, "EXTERNALLY_ENFORCED")
        self.assertFalse(record.live_executor_authority_granted)
        self.assertEqual(record_dict["no_mutation_observation"]["observation_status"], NO_MUTATION_OBSERVATION_BOUND)
        self.assertTrue(record_dict["no_mutation_observation"]["no_mutation_observed"])
        self.assertFalse(record_dict["no_mutation_observation"]["mutation_observed"])
        self.assertFalse(record_dict["no_mutation_observation"]["write_performed"])
        self.assertEqual(record_dict["request"]["request_id"], record.request_id)
        self.assertEqual(record_dict["mediated_write_decision"]["decision_id"], record.decision_id)
        self.assertEqual(record_dict["path_resolution"]["canonical_target"], record.canonical_target)


if __name__ == "__main__":
    unittest.main()
