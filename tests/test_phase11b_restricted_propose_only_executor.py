import inspect
import tempfile
import unittest
from pathlib import Path

from src.contracts import LIVE_EXECUTOR_AUTHORITY_ON_HOLD, SAFE_DEFAULT
from src.evidence import restricted_propose_only_executor
from src.evidence.action_decision_routing import (
    ACTION_DECISION_PACKET_VERIFY_ACCEPTED,
    STORE_ADJACENT_CANDIDATE_ACCEPTED,
    bind_action_decision_packet_evidence,
    evaluate_store_adjacent_candidate_gate,
    verify_action_decision_packet_evidence,
)
from src.evidence.executor_output_ingress import (
    PARSE_OK,
    ActionDecisionPacket,
    ingest_executor_output,
)
from src.evidence.restricted_propose_only_executor import (
    ALLOWED_STUB_ACTION_CANDIDATES,
    ALLOWED_STUB_FIXTURE_IDS,
    PROPOSE_PATCH_FIXTURE_ID,
    build_restricted_propose_only_stub_executor_evidence,
    build_restricted_stub_fixture_input,
    produce_restricted_propose_only_stub_output,
)
from src.evidence.structured_action_capabilities import (
    CAPABILITY_GATE_ALLOWED,
    CAPABILITY_GATE_LIMITED_ALLOWED,
)
from src.evidence.structured_actions import (
    NOOP,
    PROPOSE_PATCH,
    REQUEST_EXPLANATION,
    REQUEST_RISK_CLASSIFICATION,
    VALID_STRUCTURED_ACTION,
)


class Phase11bRestrictedProposeOnlyExecutorTests(unittest.TestCase):
    def test_stub_accepts_only_deterministic_fixture_input(self):
        fixture_input = build_restricted_stub_fixture_input(PROPOSE_PATCH_FIXTURE_ID)

        output = produce_restricted_propose_only_stub_output(fixture_input)

        self.assertEqual(fixture_input, {"fixture_id": PROPOSE_PATCH_FIXTURE_ID})
        self.assertEqual(output["action_type"], PROPOSE_PATCH)
        self.assertNotIsInstance(output, ActionDecisionPacket)

        with self.assertRaises(ValueError):
            build_restricted_stub_fixture_input("unknown")
        with self.assertRaises(ValueError):
            produce_restricted_propose_only_stub_output(
                {"fixture_id": PROPOSE_PATCH_FIXTURE_ID, "extra": "not allowed"}
            )
        with self.assertRaises(ValueError):
            produce_restricted_propose_only_stub_output({"fixture_id": "unknown"})

    def test_stub_outputs_only_allowed_raw_structured_action_candidates(self):
        expected_action_types = {
            NOOP,
            REQUEST_EXPLANATION,
            REQUEST_RISK_CLASSIFICATION,
            PROPOSE_PATCH,
        }
        actual_action_types = set()

        for fixture_id in ALLOWED_STUB_FIXTURE_IDS:
            with self.subTest(fixture_id=fixture_id):
                output = produce_restricted_propose_only_stub_output(
                    build_restricted_stub_fixture_input(fixture_id)
                )
                actual_action_types.add(output["action_type"])

                self.assertIn(output["action_type"], ALLOWED_STUB_ACTION_CANDIDATES)
                self.assertNotIn("packet_id", output)
                self.assertNotIn("created_by", output)
                self.assertNotIn("authority", output)
                self.assertNotIn("execution_allowed", output)
                self.assertNotIn("mutation_allowed", output)
                self.assertNotIn("write_authority_granted", output)

        self.assertEqual(actual_action_types, expected_action_types)

    def test_stub_output_flows_through_ingress_packet_evidence_and_metadata_candidate(self):
        for fixture_id in ALLOWED_STUB_FIXTURE_IDS:
            with self.subTest(fixture_id=fixture_id):
                output = produce_restricted_propose_only_stub_output(
                    build_restricted_stub_fixture_input(fixture_id)
                )

                packet = ingest_executor_output(output)
                evidence = bind_action_decision_packet_evidence(packet)
                verify = verify_action_decision_packet_evidence(evidence, packet)
                candidate = evaluate_store_adjacent_candidate_gate(packet)

                self.assertEqual(packet.parse_status, PARSE_OK)
                self.assertEqual(packet.validation_result.status, VALID_STRUCTURED_ACTION)
                self.assertIn(
                    packet.capability_result.gate_result,
                    (CAPABILITY_GATE_ALLOWED, CAPABILITY_GATE_LIMITED_ALLOWED),
                )
                self.assertEqual(verify.status, ACTION_DECISION_PACKET_VERIFY_ACCEPTED)
                self.assertTrue(verify.accepted)
                self.assertEqual(candidate.gate_status, STORE_ADJACENT_CANDIDATE_ACCEPTED)
                self.assertTrue(candidate.candidate_accepted)
                self._assert_no_execution_mutation_write_or_store_route(packet)

    def test_stub_output_is_deterministic_and_caller_mutation_does_not_affect_fixture(self):
        fixture_input = build_restricted_stub_fixture_input(PROPOSE_PATCH_FIXTURE_ID)
        first = produce_restricted_propose_only_stub_output(fixture_input)
        first["payload"]["target_files"].append("mutated-by-caller.py")

        second = produce_restricted_propose_only_stub_output(fixture_input)

        self.assertNotIn("mutated-by-caller.py", second["payload"]["target_files"])
        self.assertEqual(
            second["payload"]["target_files"],
            ["docs/example_proposal.md"],
        )

    def test_stub_does_not_mutate_filesystem(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            output = produce_restricted_propose_only_stub_output(
                build_restricted_stub_fixture_input(PROPOSE_PATCH_FIXTURE_ID)
            )

            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(output["action_type"], PROPOSE_PATCH)
            self.assertEqual(before, after)

    def test_stub_evidence_records_restricted_no_authority_contract(self):
        evidence = build_restricted_propose_only_stub_executor_evidence()

        self.assertTrue(evidence["deterministic_fixture_input_only"])
        self.assertTrue(evidence["deterministic_structured_output_only"])
        self.assertTrue(evidence["output_is_raw_structured_action_candidate_data"])
        self.assertFalse(evidence["output_is_action_decision_packet"])
        self.assertFalse(evidence["completed_action_decision_packet_submission_allowed"])
        self.assertFalse(evidence["tool_calls_allowed"])
        self.assertFalse(evidence["code_execution_allowed"])
        self.assertFalse(evidence["provider_model_network_allowed"])
        self.assertFalse(evidence["shell_process_allowed"])
        self.assertFalse(evidence["filesystem_mutation_allowed"])
        self.assertFalse(evidence["store_direct_access_allowed"])
        self.assertFalse(evidence["dynamic_import_allowed"])
        self.assertFalse(evidence["eval_exec_allowed"])
        self.assertFalse(evidence["runtime_introspection_allowed"])
        self.assertFalse(evidence["executor_authority_claim_allowed"])
        self.assertEqual(evidence["live_executor_authority"], LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(evidence["safe_default"], SAFE_DEFAULT)

    def test_stub_source_has_no_forbidden_runtime_surfaces(self):
        source = inspect.getsource(restricted_propose_only_executor)
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

    def _assert_no_execution_mutation_write_or_store_route(self, packet):
        self.assertFalse(packet.execution_allowed)
        self.assertFalse(packet.mutation_allowed)
        self.assertFalse(packet.write_authority_granted)
        self.assertFalse(packet.store_routing_allowed)
        self.assertFalse(packet.store_path_reachable)
        self.assertEqual(packet.live_executor_authority, LIVE_EXECUTOR_AUTHORITY_ON_HOLD)
        self.assertEqual(packet.safe_default, SAFE_DEFAULT)


if __name__ == "__main__":
    unittest.main()
