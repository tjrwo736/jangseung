import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import proposal_evidence
from src.evidence.executor_output_ingress import ingest_executor_output
from src.evidence.proposal_evidence import (
    PROPOSAL_EVIDENCE_VERIFY_ACCEPTED,
    PROPOSAL_EVIDENCE_VERIFY_REJECTED,
    PROPOSAL_OVERCLAIM_REJECTION_FIXTURES_VERSION,
    bind_propose_patch_proposal_evidence,
    build_proposal_overclaim_rejection_fixture_results,
    build_restricted_stub_proposal_evidence_batch,
    expected_proposal_evidence_hash,
    verify_proposal_evidence,
)
from src.evidence.restricted_propose_only_executor import (
    NOOP_FIXTURE_ID,
    PROPOSE_PATCH_FIXTURE_ID,
    build_restricted_stub_fixture_input,
    produce_restricted_propose_only_stub_output,
)


class Phase11bProposalEvidenceTests(unittest.TestCase):
    def test_propose_patch_binds_inert_proposal_evidence_after_required_flow(self):
        packet = self._propose_patch_packet()

        evidence = bind_propose_patch_proposal_evidence(packet)
        verify = verify_proposal_evidence(evidence, packet)

        self.assertTrue(verify.accepted)
        self.assertEqual(verify.status, PROPOSAL_EVIDENCE_VERIFY_ACCEPTED)
        self.assertTrue(evidence["proposal_id"].startswith("proposal-"))
        self.assertEqual(evidence["proposal_summary"], "Propose an inert documentation patch as data.")
        self.assertEqual(evidence["target_files"], ("docs/example_proposal.md",))
        self.assertEqual(evidence["patch_summary"], "Add a review-only proposal note.")
        self.assertIn("Review the proposed", evidence["patch_plan"][0])
        self.assertIn("diff --git", evidence["patch_diff"])
        self.assertEqual(evidence["risk_classification"], "LOW")
        self.assertEqual(evidence["proposal_accepted"], True)
        self.assertTrue(evidence["patch_diff_is_inert_data"])
        self._assert_no_execution_mutation_write_store_or_application(evidence)

    def test_proposal_evidence_rejects_required_overclaims_even_after_rehash(self):
        packet = self._propose_patch_packet()
        evidence = bind_propose_patch_proposal_evidence(packet)
        overclaim_fields = (
            "proposal_applied",
            "patch_applied",
            "patch_proposal_claims_applied",
            "mutation_allowed",
            "write_authority_granted",
            "execution_allowed",
            "store_path_reachable",
            "store_routing_allowed",
            "live_executor_ready",
            "executor_claims_done",
            "executor_claims_safe",
            "executor_claims_verified",
            "executor_claims_write_authority",
            "executor_claims_mutation_authority",
        )

        for field in overclaim_fields:
            with self.subTest(field=field):
                tampered = dict(evidence)
                tampered[field] = True
                tampered["proposal_evidence_hash"] = expected_proposal_evidence_hash(tampered)

                verify = verify_proposal_evidence(tampered, packet)

                self.assertFalse(verify.accepted)
                self.assertEqual(verify.status, PROPOSAL_EVIDENCE_VERIFY_REJECTED)
                self.assertTrue(
                    any(field in reason for reason in verify.rejection_reasons),
                    verify.rejection_reasons,
                )

    def test_proposal_evidence_rejects_non_equivalence_overclaims(self):
        packet = self._propose_patch_packet()
        evidence = bind_propose_patch_proposal_evidence(packet)
        non_equivalence_fields = (
            "metadata_only_candidate_is_store_write",
            "propose_patch_is_write",
            "propose_patch_is_mutation",
            "propose_patch_is_store_write",
            "propose_patch_is_apply_patch",
            "proposal_evidence_is_patch_application",
            "valid_structured_action_is_authorized_capability",
            "authorized_capability_is_action_executed",
            "proposal_accepted_is_proposal_applied",
        )

        for field in non_equivalence_fields:
            with self.subTest(field=field):
                tampered = dict(evidence)
                tampered[field] = True
                tampered["proposal_evidence_hash"] = expected_proposal_evidence_hash(tampered)

                verify = verify_proposal_evidence(tampered, packet)

                self.assertFalse(verify.accepted)
                self.assertEqual(verify.status, PROPOSAL_EVIDENCE_VERIFY_REJECTED)
                self.assertTrue(
                    any(field in reason for reason in verify.rejection_reasons),
                    verify.rejection_reasons,
                )

    def test_proposal_evidence_requires_runtime_packet_argument_for_verify(self):
        packet = self._propose_patch_packet()
        evidence = bind_propose_patch_proposal_evidence(packet)

        verify = verify_proposal_evidence(evidence)

        self.assertFalse(verify.accepted)
        self.assertEqual(verify.status, PROPOSAL_EVIDENCE_VERIFY_REJECTED)
        self.assertIn(
            "runtime-built ActionDecisionPacket required for proposal verification",
            verify.rejection_reasons,
        )

    def test_non_propose_patch_packet_does_not_verify_as_proposal_evidence(self):
        packet = ingest_executor_output(
            produce_restricted_propose_only_stub_output(
                build_restricted_stub_fixture_input(NOOP_FIXTURE_ID)
            )
        )

        evidence = bind_propose_patch_proposal_evidence(packet)
        verify = verify_proposal_evidence(evidence, packet)

        self.assertFalse(evidence["proposal_accepted"])
        self.assertFalse(verify.accepted)
        self.assertEqual(verify.status, PROPOSAL_EVIDENCE_VERIFY_REJECTED)
        self.assertIn("action_type mismatch", verify.rejection_reasons)

    def test_proposal_evidence_rejects_packet_mismatches_after_rehash(self):
        packet = self._propose_patch_packet()
        evidence = bind_propose_patch_proposal_evidence(packet)
        tampered = dict(evidence)
        tampered["target_files"] = ("src/other.py",)
        tampered["proposal_evidence_hash"] = expected_proposal_evidence_hash(tampered)

        verify = verify_proposal_evidence(tampered, packet)

        self.assertFalse(verify.accepted)
        self.assertTrue(
            any("target_files" in reason for reason in verify.rejection_reasons),
            verify.rejection_reasons,
        )

    def test_proposal_overclaim_fixture_builder_rejects_all_overclaims(self):
        records = build_proposal_overclaim_rejection_fixture_results(
            self._propose_patch_packet()
        )

        self.assertGreaterEqual(len(records), 20)
        for record in records:
            with self.subTest(field=record["overclaim_field"]):
                self.assertEqual(
                    record["fixture_set_version"],
                    PROPOSAL_OVERCLAIM_REJECTION_FIXTURES_VERSION,
                )
                self.assertEqual(
                    record["verify_status"],
                    PROPOSAL_EVIDENCE_VERIFY_REJECTED,
                )
                self.assertFalse(record["accepted"])
                self._assert_no_execution_mutation_write_store_or_application(record)

    def test_restricted_stub_proposal_evidence_batch_records_terminal_flow(self):
        batch = build_restricted_stub_proposal_evidence_batch(self._propose_patch_packet())

        self.assertEqual(
            batch["phase11b_3_2_restricted_propose_only_stub_executor"],
            "COMPLETE",
        )
        self.assertEqual(
            batch["phase11b_3_3_proposal_evidence_verify_binding"],
            "COMPLETE",
        )
        self.assertEqual(batch["proposal_evidence_verify_status"], PROPOSAL_EVIDENCE_VERIFY_ACCEPTED)
        self.assertTrue(batch["proposal_evidence_verify_accepted"])
        self.assertIn("proposal_evidence_verify", batch["flow"])
        self.assertFalse(batch["proposal_evidence_is_patch_application"])
        self.assertFalse(batch["proposal_accepted_is_proposal_applied"])
        self._assert_no_execution_mutation_write_store_or_application(batch)

    def test_proposal_evidence_does_not_mutate_filesystem(self):
        packet = self._propose_patch_packet()
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            evidence = bind_propose_patch_proposal_evidence(packet)
            verify = verify_proposal_evidence(evidence, packet)

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertTrue(verify.accepted)
            self.assertEqual(before, after)
            self._assert_no_execution_mutation_write_store_or_application(evidence)

    def test_proposal_evidence_source_has_no_forbidden_runtime_surfaces(self):
        source = inspect.getsource(proposal_evidence)
        forbidden_fragments = (
            "OpenAI",
            "Ollama",
            "requests",
            "socket",
            "subprocess",
            "os.system",
            "popen",
            ".open(",
            "open(",
            ".write_text(",
            ".write_bytes(",
            ".touch(",
            ".mkdir(",
            ".unlink(",
            ".rename(",
            ".replace(",
            "exec(",
            "eval(",
            "__import__(",
            "importlib",
            "inspect.",
            "sys._getframe",
            "globals(",
            "locals(",
            "vars(",
            "src.state.store",
            "from src.state import store",
            "store.",
        )

        for forbidden_fragment in forbidden_fragments:
            with self.subTest(forbidden_fragment=forbidden_fragment):
                self.assertNotIn(forbidden_fragment, source)

    def _propose_patch_packet(self):
        return ingest_executor_output(
            produce_restricted_propose_only_stub_output(
                build_restricted_stub_fixture_input(PROPOSE_PATCH_FIXTURE_ID)
            )
        )

    def _assert_no_execution_mutation_write_store_or_application(self, record):
        self.assertFalse(record["execution_allowed"])
        self.assertFalse(record["mutation_allowed"])
        self.assertFalse(record["write_authority_granted"])
        self.assertFalse(record["store_routing_allowed"])
        self.assertFalse(record["store_path_reachable"])
        self.assertFalse(record["live_executor_ready"])
        if "proposal_applied" in record:
            self.assertFalse(record["proposal_applied"])
        if "patch_applied" in record:
            self.assertFalse(record["patch_applied"])
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)


if __name__ == "__main__":
    unittest.main()
