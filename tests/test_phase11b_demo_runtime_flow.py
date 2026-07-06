import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import demo_runtime_flow
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    ACTION_DECISION_PACKET_VERIFY_NOT_RUN,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
)
from src.evidence.demo_runtime_flow import (
    COMPLETION_LABEL,
    DANGEROUS_DENIED_OUTCOME,
    DANGEROUS_REQUEST_SCENARIO_ID,
    DANGEROUS_REQUEST_TASK,
    DEMO_DANGEROUS_TERMINAL_FLOW,
    DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED,
    DEMO_RESULT_EVIDENCE_VERIFY_REJECTED,
    DEMO_SAFE_TERMINAL_FLOW,
    HIGH_DANGEROUS_REQUEST_CLASSIFICATION,
    LOW_SAFE_PROPOSAL_CLASSIFICATION,
    SAFE_PROPOSAL_OUTCOME,
    SAFE_PROPOSAL_SCENARIO_ID,
    SAFE_PROPOSAL_TASK,
    build_demo_runtime_flow_batch,
    build_phase11b_3_completion_baseline_evidence,
    expected_demo_result_evidence_hash,
    run_demo_runtime_flow,
    verify_demo_result_evidence,
)
from src.evidence.proposal_evidence import PROPOSAL_EVIDENCE_VERIFY_ACCEPTED
from src.evidence.restricted_propose_only_executor import (
    README_TYPO_PROPOSE_PATCH_FIXTURE_ID,
)
from src.evidence.structured_actions import PROPOSE_PATCH, VALID_STRUCTURED_ACTION


class Phase11bDemoRuntimeFlowTests(unittest.TestCase):
    def test_safe_proposal_demo_uses_restricted_stub_and_verifies_evidence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = run_demo_runtime_flow(SAFE_PROPOSAL_TASK, repo_root=root)
            verify = verify_demo_result_evidence(result)

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

        self.assertEqual(before, after)
        self.assertTrue(verify.accepted)
        self.assertEqual(verify.status, DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED)
        self.assertEqual(result["scenario_id"], SAFE_PROPOSAL_SCENARIO_ID)
        self.assertEqual(result["task"], SAFE_PROPOSAL_TASK)
        self.assertEqual(result["terminal_flow"], DEMO_SAFE_TERMINAL_FLOW)
        self.assertEqual(result["selected_fixture_id"], README_TYPO_PROPOSE_PATCH_FIXTURE_ID)
        self.assertEqual(result["request_classification"], LOW_SAFE_PROPOSAL_CLASSIFICATION)
        self.assertEqual(result["outcome"], SAFE_PROPOSAL_OUTCOME)
        self.assertEqual(result["action_type"], PROPOSE_PATCH)
        self.assertEqual(result["packet_parse_status"], "PARSE_OK")
        self.assertEqual(result["validation_status"], VALID_STRUCTURED_ACTION)
        self.assertTrue(result["validation_valid"])
        self.assertEqual(
            result["action_decision_packet_evidence_verify_status"],
            ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
        )
        self.assertTrue(result["action_decision_packet_evidence_verify_accepted"])
        self.assertEqual(
            result["metadata_candidate_gate_status"],
            STORE_ADJACENT_CANDIDATE_ACCEPTED,
        )
        self.assertTrue(result["metadata_only_candidate_accepted"])
        self.assertTrue(result["proposal_evidence_generated"])
        self.assertEqual(
            result["proposal_evidence_verify_status"],
            PROPOSAL_EVIDENCE_VERIFY_ACCEPTED,
        )
        self.assertTrue(result["proposal_evidence_verify_accepted"])
        self.assertEqual(result["proposal_target_files"], ("README.md",))
        self.assertIn("README typo", result["proposal_patch_summary"])
        self._assert_no_execution_mutation_write_or_store_route(result)

    def test_dangerous_request_demo_is_denied_before_ingress(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = run_demo_runtime_flow(DANGEROUS_REQUEST_TASK, repo_root=root)
            verify = verify_demo_result_evidence(result)

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

        self.assertEqual(before, after)
        self.assertTrue(verify.accepted)
        self.assertEqual(verify.status, DEMO_RESULT_EVIDENCE_VERIFY_ACCEPTED)
        self.assertEqual(result["scenario_id"], DANGEROUS_REQUEST_SCENARIO_ID)
        self.assertEqual(result["task"], DANGEROUS_REQUEST_TASK)
        self.assertEqual(result["terminal_flow"], DEMO_DANGEROUS_TERMINAL_FLOW)
        self.assertEqual(result["selected_fixture_id"], None)
        self.assertEqual(
            result["request_classification"],
            HIGH_DANGEROUS_REQUEST_CLASSIFICATION,
        )
        self.assertEqual(result["risk_classification"], "HIGH")
        self.assertEqual(result["outcome"], DANGEROUS_DENIED_OUTCOME)
        self.assertTrue(result["blocked"])
        self.assertTrue(result["denied"])
        self.assertTrue(result["user_gate_required"])
        self.assertFalse(result["structured_action_candidate_produced"])
        self.assertFalse(result["raw_output_ingress_run"])
        self.assertFalse(result["runtime_built_action_decision_packet_produced"])
        self.assertEqual(
            result["action_decision_packet_evidence_verify_status"],
            ACTION_DECISION_PACKET_VERIFY_NOT_RUN,
        )
        self.assertFalse(result["metadata_only_candidate_produced"])
        self.assertFalse(result["proposal_evidence_applicable"])
        self.assertFalse(result["proposal_evidence_generated"])
        denial_text = " ".join(result["denial_reasons"])
        self.assertIn(".env", denial_text)
        self.assertIn("push", denial_text)
        self.assertIn("gate", denial_text)
        self._assert_no_execution_mutation_write_or_store_route(result)

    def test_dangerous_request_verify_rejects_execution_write_push_and_completion_overclaims(self):
        result = run_demo_runtime_flow(DANGEROUS_REQUEST_TASK)
        overclaim_fields = (
            "request_executed",
            "patch_applied",
            "filesystem_mutated",
            "store_written",
            "pushed",
            "verified_safe",
            "request_completed",
            "proposal_applied",
            "execution_allowed",
            "mutation_allowed",
            "write_authority_granted",
            "store_routing_allowed",
            "store_path_reachable",
        )

        for field in overclaim_fields:
            with self.subTest(field=field):
                tampered = dict(result)
                tampered[field] = True
                tampered["demo_result_evidence_hash"] = (
                    expected_demo_result_evidence_hash(tampered)
                )

                verify = verify_demo_result_evidence(tampered)

                self.assertFalse(verify.accepted)
                self.assertEqual(verify.status, DEMO_RESULT_EVIDENCE_VERIFY_REJECTED)
                self.assertTrue(
                    any(field in reason for reason in verify.rejection_reasons),
                    verify.rejection_reasons,
                )

    def test_demo_batch_records_both_scenarios_and_completion_baseline(self):
        batch = build_demo_runtime_flow_batch()
        baseline = build_phase11b_3_completion_baseline_evidence()

        self.assertEqual(batch["phase11b_3_4_demo_runtime_flow"], "COMPLETE")
        self.assertTrue(batch["safe_proposal_demo_result_verify_accepted"])
        self.assertTrue(batch["dangerous_request_demo_result_verify_accepted"])
        self.assertEqual(
            batch["safe_proposal_demo"]["outcome"],
            SAFE_PROPOSAL_OUTCOME,
        )
        self.assertEqual(
            batch["dangerous_request_demo"]["outcome"],
            DANGEROUS_DENIED_OUTCOME,
        )
        self._assert_no_execution_mutation_write_or_store_route(batch)

        self.assertEqual(baseline["completion_label"], COMPLETION_LABEL)
        self.assertEqual(
            baseline["phase11b_3_1_structural_contract_enforcement"],
            "COMPLETE_AS_STRUCTURAL_CONTRACT_ENFORCEMENT",
        )
        self.assertEqual(
            baseline["phase11b_3_2_restricted_propose_only_stub_executor"],
            "COMPLETE_AS_DETERMINISTIC_RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR",
        )
        self.assertEqual(
            baseline["phase11b_3_3_proposal_evidence_verify_binding"],
            "COMPLETE_AS_INERT_PROPOSAL_EVIDENCE_VERIFY_BINDING",
        )
        self.assertEqual(
            baseline["phase11b_3_4_demo_runtime_flow"],
            "COMPLETE_AS_DETERMINISTIC_NO_PROVIDER_DEMO_RUNTIME_FLOW",
        )
        self.assertEqual(
            baseline["phase11b_3_5_completion_baseline"],
            "COMPLETE_AS_COMPLETION_BASELINE",
        )
        self.assertFalse(baseline["completion_baseline_is_provider_readiness"])
        self.assertFalse(baseline["completion_baseline_is_write_authority"])
        self._assert_no_execution_mutation_write_or_store_route(baseline)

    def test_completion_baseline_doc_smoke(self):
        doc = Path("docs/phase11b_3_completion_baseline_v0.md").read_text(
            encoding="utf-8"
        )

        self.assertIn(COMPLETION_LABEL, doc)
        self.assertIn("11-B-3-1 = COMPLETE_AS_STRUCTURAL_CONTRACT_ENFORCEMENT", doc)
        self.assertIn(
            "11-B-3-2 = COMPLETE_AS_DETERMINISTIC_RESTRICTED_PROPOSE_ONLY_STUB_EXECUTOR",
            doc,
        )
        self.assertIn(
            "11-B-3-3 = COMPLETE_AS_INERT_PROPOSAL_EVIDENCE_VERIFY_BINDING",
            doc,
        )
        self.assertIn(
            "11-B-3-4 = COMPLETE_AS_DETERMINISTIC_NO_PROVIDER_DEMO_RUNTIME_FLOW",
            doc,
        )
        self.assertIn("11-B-3-5 = COMPLETE_AS_COMPLETION_BASELINE", doc)
        self.assertIn("live_executor_authority = LIVE_EXECUTOR_AUTHORITY_ON_HOLD", doc)
        self.assertIn("safe default = hold_current_state", doc)
        self.assertIn("Phase 11-B-3 full Claude/Fable audit and user decision", doc)
        self.assertIn("provider demo adapter scope gate", doc)
        self.assertIn("11-B-4 planning", doc)

        forbidden_labels = (
            "LIVE_EXECUTOR_" + "READY",
            "MODEL_EXECUTOR_" + "READY",
            "WRITE_AUTHORITY_" + "SAFE",
            "ACTION_EXECUTION_" + "READY",
            "MUTATION_AUTHORITY_" + "GRANTED",
            "PROVIDER_" + "READY",
            "AUTONOMOUS_AGENT_" + "READY",
            "BYPASS_" + "IMPOSSIBLE",
            "TAMPER_" + "PROOF",
        )
        for label in forbidden_labels:
            with self.subTest(label=label):
                self.assertNotIn(label, doc)

    def test_demo_runtime_flow_source_has_no_forbidden_runtime_surfaces(self):
        source = inspect.getsource(demo_runtime_flow)
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

    def _assert_no_execution_mutation_write_or_store_route(self, record):
        self.assertFalse(record["execution_allowed"])
        self.assertFalse(record["mutation_allowed"])
        self.assertFalse(record["write_authority_granted"])
        self.assertFalse(record["store_routing_allowed"])
        self.assertFalse(record["store_path_reachable"])
        self.assertFalse(record["live_executor_ready"])
        self.assertEqual(record["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(record["safe_default"], SAFE_DEFAULT)
        self.assertTrue(record["no_write"])
        self.assertTrue(record["no_patch_application"])
        self.assertTrue(record["no_filesystem_mutation"])
        self.assertTrue(record["no_store_write"])
        self.assertTrue(record["no_execution"])


if __name__ == "__main__":
    unittest.main()
